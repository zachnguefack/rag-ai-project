from __future__ import annotations

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
from app.security.policies import Permission
from app.services.document_access_service import DocumentAccessService
from app.services.rbac_service import RBACService


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        rbac_service: RBACService | None = None,
        document_access_service: DocumentAccessService | None = None,
    ) -> None:
        self._documents = document_repository or DocumentRepository()
        self._rbac = rbac_service or RBACService(document_repository=self._documents)
        self._access = document_access_service or DocumentAccessService(document_repository=self._documents, rbac_service=self._rbac)

    def create_document(self, user: User, request: DocumentCreateRequest) -> DocumentResponse:
        self._rbac.enforce_permission(user, Permission.INGEST_DOCUMENT)
        if self._documents.get(request.document_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document already exists.")

        metadata = self._metadata_from_request(request.metadata)
        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            document_id=request.document_id,
            title=request.title,
            owner=request.metadata.owner,
            department_id=request.metadata.department_id,
            document_type=request.metadata.document_type,
            classification=request.metadata.classification,
            status=request.metadata.status,
            created_at=now,
            updated_at=now,
            versions=[DocumentVersionRecord(version=1, content=request.content, metadata=metadata)],
        )
        self._documents.upsert(record)
        return self._to_document_response(record)

    def update_document(self, user: User, document_id: str, request: DocumentUpdateRequest) -> DocumentResponse:
        self._rbac.enforce_permission(user, Permission.UPDATE_DOCUMENT)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        self._access.enforce_document_access(user, document_id)

        metadata = self._metadata_from_request(request.metadata)
        next_version = record.current_version + 1
        record.title = request.title
        record.classification = request.metadata.classification
        record.department_id = request.metadata.department_id
        record.document_type = request.metadata.document_type
        record.status = request.metadata.status
        record.owner = request.metadata.owner
        record.updated_at = datetime.now(timezone.utc)
        record.versions.append(DocumentVersionRecord(version=next_version, content=request.content, metadata=metadata))
        self._documents.upsert(record)
        return self._to_document_response(record)

    def delete_document(self, user: User, document_id: str) -> DocumentDeleteResponse:
        self._rbac.enforce_permission(user, Permission.DELETE_DOCUMENT)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        self._access.enforce_document_access(user, document_id)

        self._documents.delete(document_id)
        return DocumentDeleteResponse(document_id=document_id, deleted=True)

    def get_document(self, user: User, document_id: str) -> DocumentResponse:
        self._access.enforce_document_access(user, document_id)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        return self._to_document_response(record)

    def list_document_versions(self, user: User, document_id: str) -> list[DocumentVersionResponse]:
        self._access.enforce_document_access(user, document_id)
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")

        return [
            DocumentVersionResponse(version=version.version, content=version.content, metadata=self._to_metadata_response(version.metadata))
            for version in record.versions
        ]

    @staticmethod
    def _extract_content(record: DocumentRecord) -> str:
        if not record.versions:
            return ""
        return record.versions[-1].content

    @staticmethod
    def _metadata_from_request(request: DocumentMetadataResponse) -> DocumentMetadata:
        return DocumentMetadata(
            department_id=request.department_id,
            owner=request.owner,
            classification=request.classification,
            document_type=request.document_type,
            status=request.status,
        )

    @staticmethod
    def _to_metadata_response(metadata: DocumentMetadata) -> DocumentMetadataResponse:
        return DocumentMetadataResponse(
            department_id=metadata.department_id,
            owner=metadata.owner,
            classification=metadata.classification,
            document_type=metadata.document_type,
            status=metadata.status,
        )

    def _to_document_response(self, record: DocumentRecord) -> DocumentResponse:
        latest_metadata = record.versions[-1].metadata if record.versions else DocumentMetadata(
            department_id=record.department_id,
            owner=record.owner,
            classification=record.classification,
            document_type=record.document_type,
            status=record.status,
        )
        return DocumentResponse(
            document_id=record.document_id,
            title=record.title,
            current_version=record.current_version,
            content=self._extract_content(record),
            metadata=self._to_metadata_response(latest_metadata),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
