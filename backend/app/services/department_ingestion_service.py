"""Department ingestion service handling secure upload, registration, and indexing."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from rag_v2.document_ids import normalize_document_id

from app.config.settings import BackendSettings, load_settings
from app.database.repositories.document_repo import DocumentRepository
from app.models.domain.user import User
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.models.schema.admin import DepartmentIngestionResponse, DepartmentUploadResultResponse
from app.security.policies import Permission
from app.services.department_service import DepartmentService
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService


LOGGER = logging.getLogger("app.department_ingestion")


class DepartmentIngestionService:
    """Ingest department documents from uploads/filesystem and trigger indexing."""
    def __init__(
        self,
        *,
        department_service: DepartmentService | None = None,
        document_repository: DocumentRepository | None = None,
        rag_service: RAGApplicationService | None = None,
        rbac_service: RBACService | None = None,
        settings: BackendSettings | None = None,
    ) -> None:
        self._department_service = department_service or DepartmentService(settings=settings)
        self._documents = document_repository or DocumentRepository()
        self._rag_service = rag_service
        self._rbac = rbac_service
        self._settings = settings or load_settings()
        self._supported = {".pdf", ".txt", ".csv", ".docx", ".xlsx", ".json"}
        self._allowed_roots = self._build_allowed_roots()

    def _enforce_admin(self, user: User) -> None:
        """Require elevated permissions for ingestion operations."""
        if self._rbac is not None:
            self._rbac.enforce_permission(user, Permission.INGEST_DOCUMENT)
            self._rbac.enforce_permission(user, Permission.MANAGE_USERS)


    def _build_allowed_roots(self) -> tuple[Path, ...]:
        configured = [item.strip() for item in self._settings.ingest_allowed_roots.split(os.pathsep) if item.strip()]
        roots = [self._coerce_filesystem_path(item).expanduser().resolve() for item in configured]
        if not roots:
            roots = [
                self._settings.data_dir.resolve(),
                Path.cwd().resolve(),
                Path('/tmp').resolve(),
            ]
        return tuple(dict.fromkeys(roots))

    def _allowed_roots_error(self) -> str:
        return f"Provided path is outside allowed ingest roots: {', '.join(str(root) for root in self._allowed_roots)}"

    def _department_dir(self, department_id: str) -> tuple[str, Path]:
        dept = self._department_service.get_department(department_id)
        target = dept.path.resolve()
        target.mkdir(parents=True, exist_ok=True)
        return dept.name, target

    def _validate_allowed_path(self, path: Path) -> Path:
        """Block path traversal by enforcing ingest roots allowlist boundaries."""
        candidate = path.expanduser().resolve(strict=False)
        if not any(candidate == root or root in candidate.parents for root in self._allowed_roots):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=self._allowed_roots_error())
        return candidate

    @staticmethod
    def _coerce_filesystem_path(raw_path: str) -> Path:
        """Normalize user-provided paths, including UNC-style separators."""
        normalized = raw_path.strip()
        if normalized.startswith("\\\\"):
            # Convert Windows UNC notation (\\server\share\file) into a path format
            # pathlib can resolve on POSIX hosts while keeping network semantics.
            normalized = "//" + normalized.lstrip("\\").replace("\\", "/")
        return Path(normalized)

    def _copy_to_department(self, *, source: Path, target: Path, department_id: str) -> None:
        try:
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
        except PermissionError as exc:
            LOGGER.exception(
                "Department ingestion copy permission denied department_id=%s source=%s target=%s",
                department_id,
                source,
                target,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied while accessing {source}") from exc
        except OSError as exc:
            LOGGER.exception(
                "Department ingestion copy failed department_id=%s source=%s target=%s",
                department_id,
                source,
                target,
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to ingest file from {source}") from exc


    @staticmethod
    def _sanitize_document_id(value: str) -> str:
        normalized = normalize_document_id(value)
        return normalized or f"doc-{uuid4().hex[:12]}"

    def _build_document_id(self, source_path: Path) -> str:
        base = self._sanitize_document_id(source_path.stem)
        candidate = base
        suffix = 1
        while self._documents.get(candidate) is not None:
            suffix += 1
            candidate = f"{base}-{suffix}"
        return candidate

    def _checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def _register_file(self, *, department_id: str, owner: str, source_path: Path, storage_path: Path, content_type: str = "") -> DocumentRecord:
        """Create document metadata/version records for an ingested filesystem file."""
        now = datetime.now(timezone.utc)
        content = storage_path.read_text(encoding="utf-8", errors="ignore")
        doc_id = self._build_document_id(source_path)
        ext = storage_path.suffix.lower().lstrip(".") or "file"
        checksum = self._checksum(storage_path)
        metadata = DocumentMetadata(
            department_id=department_id,
            owner=owner,
            classification="internal",
            document_type=ext,
            status="active",
        )
        version = DocumentVersionRecord(
            version_id=f"{doc_id}-v1",
            version=1,
            content=content,
            metadata=metadata,
            storage_path=str(storage_path),
            checksum=checksum,
            indexed=False,
            created_at=now,
        )
        record = DocumentRecord(
            document_id=doc_id,
            title=storage_path.stem,
            original_filename=source_path.name,
            stored_filename=storage_path.name,
            department_id=department_id,
            owner=owner,
            document_type=ext,
            classification="internal",
            status="active",
            storage_path=str(storage_path),
            content_type=content_type,
            size_bytes=storage_path.stat().st_size,
            checksum=checksum,
            indexing_status="pending",
            created_at=now,
            uploaded_at=now,
            updated_at=now,
            versions=[version],
        )
        self._documents.upsert(record)
        return record

    def _validate_upload_files(self, files: list[UploadFile]) -> None:
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded.")
        if not any((item.filename or "").strip() for item in files):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded files are missing filenames.")

    def _enforce_upload_size_limit(self, *, payload: bytes, filename: str) -> None:
        max_size = int(self._settings.max_upload_file_size_bytes)
        if max_size > 0 and len(payload) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File '{filename}' exceeds max upload size of {max_size} bytes.",
            )

    def _index_and_finalize(self, docs: list[DocumentRecord], department_id: str) -> DepartmentIngestionResponse:
        """Trigger indexing and persist indexed status to metadata records."""
        indexed_files = 0
        indexed_chunks = 0
        LOGGER.info("Department ingestion started department_id=%s ingested_documents=%s", department_id, len(docs))
        if self._rag_service is not None and docs:
            summary = self._rag_service.run_indexing(force_reindex=False)
            indexed_files = int(summary.get("indexed_files", 0))
            indexed_chunks = int(summary.get("indexed_chunks", 0))
            for doc in docs:
                if doc.versions:
                    doc.versions[-1].indexed = True
                doc.indexing_status = "indexed"
                doc.last_indexed_at = datetime.now(timezone.utc)
                self._documents.upsert(doc)

        LOGGER.info(
            "Department ingestion completed department_id=%s ingested_documents=%s indexed_files=%s indexed_chunks=%s",
            department_id,
            len(docs),
            indexed_files,
            indexed_chunks,
        )

        return DepartmentIngestionResponse(
            department_id=department_id,
            ingested_documents=len(docs),
            indexed_files=indexed_files,
            indexed_chunks=indexed_chunks,
            storage_paths=[doc.storage_path for doc in docs if doc.storage_path],
        )

    async def ingest_upload(self, *, user: User, department_id: str, files: list[UploadFile]) -> DepartmentUploadResultResponse:
        """Upload files to department storage, register metadata, and run indexing."""
        self._enforce_admin(user)
        self._validate_upload_files(files)
        _, dept_dir = self._department_dir(department_id)
        docs: list[DocumentRecord] = []
        unsupported_files: list[str] = []
        normalized_files: list[tuple[UploadFile, str]] = []

        for file in files:
            filename = Path(file.filename or f"file-{uuid4().hex}").name
            suffix = Path(filename).suffix.lower()
            if suffix not in self._supported:
                unsupported_files.append(filename)
                continue
            normalized_files.append((file, filename))

        if unsupported_files:
            for file in files:
                await file.close()
            supported = ", ".join(sorted(self._supported))
            file_list = ", ".join(sorted(unsupported_files))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type(s): {file_list}. Supported extensions: {supported}",
            )

        for file, filename in normalized_files:
            payload = await file.read()
            self._enforce_upload_size_limit(payload=payload, filename=filename)

            target = dept_dir / filename
            try:
                target.write_bytes(payload)
            except OSError as exc:
                LOGGER.exception("Department upload write failed department_id=%s filename=%s", department_id, filename)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed filesystem write for {filename}.") from exc
            finally:
                await file.close()
            LOGGER.info("Department upload saved department_id=%s filename=%s storage_path=%s", department_id, filename, target)
            docs.append(self._register_file(department_id=department_id, owner=user.user_id, source_path=Path(filename), storage_path=target, content_type=file.content_type or ""))

        if not docs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid files were uploaded.")

        try:
            result = self._index_and_finalize(docs, department_id)
            return DepartmentUploadResultResponse(**result.model_dump(), uploaded_files=self._department_service.list_department_files(department_id))
        except Exception as exc:
            LOGGER.exception("Department ingestion pipeline failed department_id=%s uploaded_count=%s", department_id, len(docs))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ingestion pipeline failed.") from exc

    def ingest_file_path(self, *, user: User, department_id: str, file_path: str) -> DepartmentIngestionResponse:
        self._enforce_admin(user)
        source = self._validate_allowed_path(self._coerce_filesystem_path(file_path))
        if not source.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source file was not found: {source}")
        if not source.is_file():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Provided path is not a file: {source}")
        if source.suffix.lower() not in self._supported:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")
        _, dept_dir = self._department_dir(department_id)
        target = dept_dir / source.name
        self._copy_to_department(source=source, target=target, department_id=department_id)
        LOGGER.info("Department file-path ingestion accepted department_id=%s source=%s target=%s", department_id, source, target)
        doc = self._register_file(department_id=department_id, owner=user.user_id, source_path=source, storage_path=target)
        return self._index_and_finalize([doc], department_id)

    def ingest_folder_path(self, *, user: User, department_id: str, folder_path: str) -> DepartmentIngestionResponse:
        self._enforce_admin(user)
        source_folder = self._validate_allowed_path(self._coerce_filesystem_path(folder_path))
        if not source_folder.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source folder was not found: {source_folder}")
        if not source_folder.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Provided path is not a folder: {source_folder}")
        _, dept_dir = self._department_dir(department_id)
        docs: list[DocumentRecord] = []
        for path in sorted(source_folder.glob("**/*")):
            if not path.is_file() or path.suffix.lower() not in self._supported:
                continue
            target = dept_dir / path.name
            self._copy_to_department(source=path, target=target, department_id=department_id)
            LOGGER.info("Department folder-path ingestion accepted department_id=%s source=%s target=%s", department_id, path, target)
            docs.append(self._register_file(department_id=department_id, owner=user.user_id, source_path=path, storage_path=target))
        if not docs:
            supported = ", ".join(sorted(self._supported))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No supported files found in folder. Supported extensions: {supported}")
        return self._index_and_finalize(docs, department_id)
