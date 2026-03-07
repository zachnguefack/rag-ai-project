from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.domain.user import User
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.models.schema.document import (
    AdminDocumentListResponse,
    DocumentACLGrantResponse,
    DocumentACLResponse,
    DocumentACLRevocationResponse,
    DocumentAuditEventResponse,
    DocumentAuditListResponse,
    DocumentContentResponse,
    DocumentCreateRequest,
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentMetadataDetailResponse,
    DocumentMetadataResponse,
    DocumentResponse,
    DocumentSearchResponse,
    DocumentSummaryResponse,
    DocumentUpdateRequest,
    DocumentVersionResponse,
)
from app.security.policies import Permission
from app.services.audit_service import AuditService
from app.services.document_access_service import DocumentAccessService
from app.services.rbac_service import RBACService


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        rbac_service: RBACService | None = None,
        document_access_service: DocumentAccessService | None = None,
        user_document_access_repository: UserDocumentAccessRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._documents = document_repository or DocumentRepository()
        self._rbac = rbac_service or RBACService(document_repository=self._documents)
        self._access = document_access_service or DocumentAccessService(document_repository=self._documents, rbac_service=self._rbac)
        self._user_access = user_document_access_repository or UserDocumentAccessRepository()
        self._audit = audit_service or AuditService()

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

    def list_visible_documents(
        self,
        user: User,
        *,
        limit: int,
        offset: int,
        department_id: str | None,
        document_type: str | None,
        classification: str | None,
        status_value: str | None,
        owner: str | None,
    ) -> DocumentListResponse:
        self._rbac.enforce_permission(user, Permission.READ_DOCUMENT)
        scope = set(self._access.compute_authorized_document_ids(user))
        scoped_records = [record for record in self._documents.list() if record.document_id in scope]
        filtered = self._apply_filters(scoped_records, department_id, document_type, classification, status_value, owner)
        paginated = filtered[offset : offset + limit]
        items = [self._to_document_summary_response(record) for record in paginated]
        return DocumentListResponse(items=items, count=len(items), total=len(filtered), limit=limit, offset=offset)

    def search_visible_documents(
        self,
        user: User,
        *,
        query: str,
        limit: int,
        offset: int,
        department_id: str | None,
        document_type: str | None,
        classification: str | None,
        status_value: str | None,
        owner: str | None,
    ) -> DocumentSearchResponse:
        self._rbac.enforce_permission(user, Permission.SEARCH_DOCUMENT)
        base = self.list_visible_documents(
            user,
            limit=10_000,
            offset=0,
            department_id=department_id,
            document_type=document_type,
            classification=classification,
            status_value=status_value,
            owner=owner,
        )
        q = query.strip().lower()
        results = [
            item
            for item in base.items
            if q in item.title.lower()
            or q in item.document_id.lower()
            or q in item.owner.lower()
            or q in item.department_id.lower()
            or q in item.classification.lower()
            or q in item.document_type.lower()
            or q in item.status.lower()
        ]
        paginated = results[offset : offset + limit]
        return DocumentSearchResponse(items=paginated, count=len(paginated), total=len(results), limit=limit, offset=offset, query=query)

    def get_document_metadata(self, user: User, document_id: str) -> DocumentMetadataDetailResponse:
        self._access.enforce_document_access(user, document_id)
        record = self._must_get_document(document_id)
        return self._to_document_metadata_detail(record)

    def get_document_content(self, user: User, document_id: str) -> DocumentContentResponse:
        self._access.enforce_document_access(user, document_id)
        record = self._must_get_document(document_id)
        return DocumentContentResponse(document_id=record.document_id, content=self._extract_content(record), current_version=record.current_version)

    def get_document_acl(self, user: User, document_id: str) -> DocumentACLResponse:
        if self._rbac.validate_permission(user, Permission.MANAGE_USERS).granted is False:
            self._access.enforce_document_access(user, document_id)
        record = self._must_get_document(document_id)
        grants = self._user_access.list_for_document(document_id)
        explicit_user_grants = [
            DocumentACLGrantResponse(user_id=grant.user_id, granted_at=grant.granted_at, granted_by=grant.granted_by)
            for grant in grants
            if grant.is_active
        ]
        revoked_grants = [
            DocumentACLRevocationResponse(user_id=grant.user_id, revoked_at=grant.revoked_at)
            for grant in grants
            if not grant.is_active and grant.revoked_at is not None
        ]
        return DocumentACLResponse(
            document_id=record.document_id,
            owning_department=record.department_id,
            owner=record.owner,
            classification=record.classification,
            status=record.status,
            explicit_user_grants=explicit_user_grants,
            revoked_grants=revoked_grants,
        )

    def admin_list_documents(
        self,
        user: User,
        *,
        limit: int,
        offset: int,
        department_id: str | None,
        document_type: str | None,
        classification: str | None,
        status_value: str | None,
        owner: str | None,
    ) -> AdminDocumentListResponse:
        self._rbac.enforce_permission(user, Permission.MANAGE_USERS)
        filtered = self._apply_filters(self._documents.list(), department_id, document_type, classification, status_value, owner)
        paginated = filtered[offset : offset + limit]
        items = [self._to_document_summary_response(record) for record in paginated]
        return AdminDocumentListResponse(items=items, count=len(items), total=len(filtered), limit=limit, offset=offset)

    def admin_get_document(self, user: User, document_id: str) -> DocumentResponse:
        self._rbac.enforce_permission(user, Permission.MANAGE_USERS)
        return self._to_document_response(self._must_get_document(document_id))

    def reassign_document_department(self, user: User, document_id: str, department_id: str) -> DocumentMetadataDetailResponse:
        self._rbac.enforce_permission(user, Permission.MANAGE_USERS)
        record = self._must_get_document(document_id)
        record.department_id = department_id
        if record.versions:
            record.versions[-1].metadata.department_id = department_id
        record.updated_at = datetime.now(timezone.utc)
        self._documents.upsert(record)
        return self._to_document_metadata_detail(record)

    def admin_get_document_audit(self, user: User, document_id: str, *, limit: int, offset: int) -> DocumentAuditListResponse:
        self._rbac.enforce_permission(user, Permission.READ_AUDIT_LOG)
        self._must_get_document(document_id)
        events = self._audit.list_events(limit=1000, offset=0)
        filtered = [event for event in events if document_id in event.documents_retrieved]
        payload = [
            DocumentAuditEventResponse(
                event_id=event.event_id,
                action="queried",
                actor_user_id=event.user_id,
                timestamp=event.timestamp,
                details=f"Question: {event.question}",
            )
            for event in filtered
        ]
        paginated = payload[offset : offset + limit]
        return DocumentAuditListResponse(items=paginated, count=len(paginated))

    def _must_get_document(self, document_id: str) -> DocumentRecord:
        record = self._documents.get(document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        return record

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

    def _to_document_summary_response(self, record: DocumentRecord) -> DocumentSummaryResponse:
        return DocumentSummaryResponse(
            document_id=record.document_id,
            title=record.title,
            department_id=record.department_id,
            owner=record.owner,
            classification=record.classification,
            document_type=record.document_type,
            status=record.status,
            updated_at=record.updated_at,
            current_version=record.current_version,
            indexed=record.current_version > 0,
        )

    def _to_document_metadata_detail(self, record: DocumentRecord) -> DocumentMetadataDetailResponse:
        return DocumentMetadataDetailResponse(
            document_id=record.document_id,
            title=record.title,
            department_id=record.department_id,
            owner=record.owner,
            classification=record.classification,
            document_type=record.document_type,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            current_version=record.current_version,
            indexed=record.current_version > 0,
        )

    @staticmethod
    def _apply_filters(
        records: list[DocumentRecord],
        department_id: str | None,
        document_type: str | None,
        classification: str | None,
        status_value: str | None,
        owner: str | None,
    ) -> list[DocumentRecord]:
        filtered = records
        if department_id is not None:
            filtered = [record for record in filtered if record.department_id == department_id]
        if document_type is not None:
            filtered = [record for record in filtered if record.document_type == document_type]
        if classification is not None:
            filtered = [record for record in filtered if record.classification == classification]
        if status_value is not None:
            filtered = [record for record in filtered if record.status == status_value]
        if owner is not None:
            filtered = [record for record in filtered if record.owner == owner]
        return sorted(filtered, key=lambda item: item.updated_at, reverse=True)
