from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.database.repositories.document_repo import DocumentRepository
from app.models.domain.user import User
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.models.schema.document import (
    DocumentCreateRequest,
    DocumentDeleteResponse,
    DocumentMetadataResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionResponse,
)
from app.security.policies import DOCUMENT_GLOBAL_ACCESS_ROLES, Permission, RoleName
from app.services.rbac_service import RBACService


class DocumentService:
    def __init__(self, document_repository: DocumentRepository | None = None, rbac_service: RBACService | None = None) -> None:
        self._documents = document_repository or DocumentRepository()
        self._rbac = rbac_service or RBACService(document_repository=self._documents)

    def create_document(self, user: User, request: DocumentCreateRequest) -> DocumentResponse:
        self._rbac.enforce_permission(user, Permission.INGEST_DOCUMENT)
        if self._documents.get(request.document_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists.")

        metadata = self._metadata_from_request(request.metadata)
        record = DocumentRecord(
            document_id=request.document_id,
            title=request.title,
            document_type=request.document_type,
            owner_user_id=request.metadata.owner,
            classification=request.metadata.classification,
            status=request.metadata.status,
            department=request.metadata.department,
            allowed_roles=self._extract_roles(request.metadata.permissions),
            allowed_users=self._extract_users(request.metadata.permissions),
            allowed_departments=request.metadata.allowed_departments,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            versions=[
                DocumentVersionRecord(
                    version_id=f"{request.document_id}-v1",
                    document_id=request.document_id,
                    version_number=1,
                    content=request.content,
                    storage_path=f"/documents/{request.document_id}/v1",
                    checksum=self._checksum(request.content),
                    indexed=request.metadata.status in {"approved", "indexed"},
                    approved_at=datetime.now(timezone.utc),
                    metadata=metadata,
                )
            ],
        )
        self._documents.upsert(record)
        return self._to_document_response(record)

    def update_document(self, user: User, document_id: str, request: DocumentUpdateRequest) -> DocumentResponse:
        self._rbac.enforce_permission(user, Permission.UPDATE_DOCUMENT)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        self._ensure_mutation_access(user, record)

        metadata = self._metadata_from_request(request.metadata)
        next_version = record.current_version + 1
        record.title = request.title
        record.document_type = request.document_type
        record.classification = request.metadata.classification
        record.department = request.metadata.department
        record.status = request.metadata.status
        record.owner_user_id = request.metadata.owner
        record.allowed_roles = self._extract_roles(request.metadata.permissions)
        record.allowed_users = self._extract_users(request.metadata.permissions)
        record.allowed_departments = request.metadata.allowed_departments
        record.updated_at = datetime.now(timezone.utc)
        record.versions.append(
            DocumentVersionRecord(
                version_id=f"{document_id}-v{next_version}",
                document_id=document_id,
                version_number=next_version,
                content=request.content,
                storage_path=f"/documents/{document_id}/v{next_version}",
                checksum=self._checksum(request.content),
                indexed=request.metadata.status in {"approved", "indexed"},
                approved_at=datetime.now(timezone.utc),
                metadata=metadata,
            )
        )
        self._documents.upsert(record)
        return self._to_document_response(record)

    def delete_document(self, user: User, document_id: str) -> DocumentDeleteResponse:
        self._rbac.enforce_permission(user, Permission.DELETE_DOCUMENT)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        self._ensure_mutation_access(user, record)

        self._documents.delete(document_id)
        return DocumentDeleteResponse(document_id=document_id, deleted=True)

    def get_document(self, user: User, document_id: str) -> DocumentResponse:
        self._rbac.enforce_document_access(user, document_id)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        return self._to_document_response(record)

    def list_document_versions(self, user: User, document_id: str) -> list[DocumentVersionResponse]:
        self._rbac.enforce_document_access(user, document_id)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        return [
            DocumentVersionResponse(
                version_id=v.version_id,
                document_id=v.document_id,
                version_number=v.version_number,
                storage_path=v.storage_path,
                checksum=v.checksum,
                indexed=v.indexed,
                approved_at=v.approved_at,
                content=v.content,
                metadata=self._to_metadata_response(v.metadata),
            )
            for v in record.versions
        ]

    def list_documents(self, user: User) -> list[DocumentResponse]:
        docs: list[DocumentResponse] = []
        for record in self._documents.list():
            try:
                self._rbac.enforce_document_access(user, record.document_id)
            except HTTPException:
                continue
            docs.append(self._to_document_response(record))
        return docs

    def _ensure_mutation_access(self, user: User, document: DocumentRecord) -> None:
        if user.role_names & DOCUMENT_GLOBAL_ACCESS_ROLES:
            return
        if document.owner_user_id == user.user_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can modify this document.")

    @staticmethod
    def _extract_roles(permissions: list[str]) -> list[str]:
        return [p.split(":", 1)[1] for p in permissions if p.startswith("role:") and p.split(":", 1)[1] in RoleName._value2member_map_]

    @staticmethod
    def _extract_users(permissions: list[str]) -> list[str]:
        return [p.split(":", 1)[1] for p in permissions if p.startswith("user:")]

    def _metadata_from_request(self, metadata: DocumentMetadataResponse) -> DocumentMetadata:
        return DocumentMetadata(
            department=metadata.department,
            owner=metadata.owner,
            classification=metadata.classification,
            status=metadata.status,
            permissions=metadata.permissions,
            allowed_roles=self._extract_roles(metadata.permissions),
            allowed_user_ids=self._extract_users(metadata.permissions),
            allowed_departments=metadata.allowed_departments,
        )

    def _to_document_response(self, record: DocumentRecord) -> DocumentResponse:
        latest = record.versions[-1]
        return DocumentResponse(
            document_id=record.document_id,
            title=record.title,
            document_type=record.document_type,
            status=record.status,
            current_version=record.current_version,
            content=latest.content,
            created_at=record.created_at,
            updated_at=record.updated_at,
            metadata=self._to_metadata_response(latest.metadata),
        )

    @staticmethod
    def _to_metadata_response(metadata: DocumentMetadata) -> DocumentMetadataResponse:
        return DocumentMetadataResponse(
            department=metadata.department,
            owner=metadata.owner,
            classification=metadata.classification,
            status=metadata.status,
            permissions=metadata.permissions,
            allowed_departments=metadata.allowed_departments,
        )

    @staticmethod
    def _checksum(content: str) -> str:
        return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
