from __future__ import annotations

import mimetypes
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status

from app.config.settings import BackendSettings, load_settings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.persistence.department import DepartmentRecord
from app.models.persistence.document import DocumentRecord
from app.models.schema.admin import DepartmentFileSummaryResponse
from app.services.audit_service import AuditService
from app.services.rag_service import RAGApplicationService


@dataclass(slots=True)
class DepartmentDescriptor:
    department_id: str
    name: str
    description: str
    path: Path


class DepartmentService:
    _safe_pattern = re.compile(r"[^a-z0-9_-]+")

    def __init__(
        self,
        department_repository: DepartmentRepository | None = None,
        document_repository: DocumentRepository | None = None,
        user_document_access_repository: UserDocumentAccessRepository | None = None,
        settings: BackendSettings | None = None,
        rag_service: RAGApplicationService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._departments = department_repository or DepartmentRepository()
        self._documents = document_repository or DocumentRepository()
        self._user_doc_access = user_document_access_repository or UserDocumentAccessRepository()
        self._settings = settings or load_settings()
        self._rag_service = rag_service
        self._audit = audit_service or AuditService()
        self._root = self._settings.data_departments_root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def sanitize_department_identifier(cls, value: str) -> str:
        candidate = (value or "").strip().lower()
        candidate = candidate.replace(" ", "-")
        candidate = cls._safe_pattern.sub("-", candidate)
        candidate = re.sub(r"-+", "-", candidate).strip("-_")
        if not candidate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department name.")
        if candidate in {".", ".."}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department name.")
        return candidate

    def _safe_department_path(self, department_key: str) -> Path:
        safe = self.sanitize_department_identifier(department_key)
        target = (self._root / safe).resolve()
        if self._root not in target.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department path.")
        return target

    def _descriptor_for_dir(self, path: Path) -> DepartmentDescriptor:
        dept_id = path.name
        record = self._departments.get(dept_id)
        return DepartmentDescriptor(
            department_id=dept_id,
            name=record.name if record else dept_id,
            description=record.description if record else "",
            path=path,
        )

    def list_departments(self) -> list[DepartmentDescriptor]:
        return [self._descriptor_for_dir(path) for path in sorted(self._root.iterdir()) if path.is_dir()]

    def create_department(self, department_id: str | None, name: str, description: str, actor_user_id: str | None = None) -> DepartmentDescriptor:
        source = department_id or name
        identifier = self.sanitize_department_identifier(source)
        target = self._safe_department_path(identifier)
        if target.exists():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists.")
        try:
            target.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unable to create department directory: {exc}") from exc

        self._departments.upsert(DepartmentRecord(department_id=identifier, name=name.strip(), description=description))
        self._audit.record_query_event(
            user_id=actor_user_id or "system",
            question=f"department.create:{identifier}",
            documents_retrieved=[],
            answer_generated=f"Department created with repository {target}",
            confidence_score=1.0,
        )
        return self._descriptor_for_dir(target)

    def get_department(self, department_id: str) -> DepartmentDescriptor:
        path = self._safe_department_path(department_id)
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
        return self._descriptor_for_dir(path)

    def list_department_files(self, department_id: str) -> list[DepartmentFileSummaryResponse]:
        dept = self.get_department(department_id)
        files: list[DepartmentFileSummaryResponse] = []
        for path in sorted(dept.path.iterdir()):
            if not path.is_file():
                continue
            stat = path.stat()
            files.append(
                DepartmentFileSummaryResponse(
                    name=path.name,
                    path=str(path),
                    size_bytes=stat.st_size,
                    content_type=mimetypes.guess_type(path.name)[0],
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
        return files

    def list_documents_for_department(self, department_id: str) -> list[DocumentRecord]:
        self.get_department(department_id)
        return self._documents.list_by_department(department_id)

    def delete_file(self, department_id: str, filename: str) -> None:
        dept = self.get_department(department_id)
        target = (dept.path / Path(filename).name).resolve()
        if dept.path not in target.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        target.unlink()

    def delete_department(self, department_id: str, *, actor_user_id: str) -> dict[str, int | str]:
        department = self.get_department(department_id)
        dept_dir = department.path

        docs = self._documents.list_by_department(department_id)
        sources_to_remove: list[str] = []
        for doc in docs:
            if doc.storage_path:
                sources_to_remove.append(str(Path(doc.storage_path).resolve()))
            for version in doc.versions:
                if version.storage_path:
                    sources_to_remove.append(str(Path(version.storage_path).resolve()))
            self._user_doc_access.delete_for_document(doc.document_id)
            self._documents.delete(doc.document_id)

        if self._rag_service and sources_to_remove:
            self._rag_service.remove_document_sources(sorted(set(sources_to_remove)))

        file_count = sum(1 for p in dept_dir.rglob("*") if p.is_file()) if dept_dir.exists() else 0
        if dept_dir.exists():
            shutil.rmtree(dept_dir)

        self._departments.delete(department_id)

        self._audit.record_query_event(
            user_id=actor_user_id,
            question=f"department.delete:{department_id}",
            documents_retrieved=[doc.document_id for doc in docs],
            answer_generated=(
                f"Deleted department={department_id}, docs={len(docs)}, files={file_count}, "
                f"repository={dept_dir}"
            ),
            confidence_score=1.0,
        )
        return {
            "department_id": department_id,
            "deleted_documents": len(docs),
            "deleted_files": file_count,
            "deleted_repository": str(dept_dir),
        }
