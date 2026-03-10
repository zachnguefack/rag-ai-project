from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.domain.user import User
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.services.document_access_service import DocumentAccessService
from app.services.scope_builder_service import ScopeBuilderService
from app.services.secure_retriever import SecureRetriever


class FakeRetrievalService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def query(self, *, question: str, mode: str, strict_document_scope: bool | None, metadata_filter: dict | None) -> dict:
        self.calls.append(
            {
                "question": question,
                "mode": mode,
                "strict_document_scope": strict_document_scope,
                "metadata_filter": metadata_filter,
            }
        )
        if strict_document_scope and metadata_filter == {
            "$and": [{"department_id": {"$in": ["dept-unknown"]}}, {"document_id": {"$in": []}}]
        }:
            return {
                "answer": "No relevant information was found in the available documentation.",
                "citations": [],
                "confidence": {"score": 0.0},
            }
        return {
            "answer": "authorized answer",
            "citations": ["doc-ops"],
            "confidence": {"score": 0.9},
        }


class SecureAccessModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = DocumentRepository()
        self.access = UserDocumentAccessRepository()
        self.department_access = UserDepartmentAccessRepository(self.documents._store)
        self.scope_builder = ScopeBuilderService(self.documents, self.access, self.department_access)
        self.access_service = DocumentAccessService(
            document_repository=self.documents,
            user_document_access_repository=self.access,
            scope_builder=self.scope_builder,
        )

        # Extra doc for grant/revoke scenarios.
        self.documents.upsert(
            DocumentRecord(
                document_id="doc-ops",
                title="Ops Policy",
                department_id="dept-operations",
                document_type="policy",
                owner="u-ops",
                classification="internal",
                status="active",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Ops content",
                        metadata=DocumentMetadata(
                            department_id="dept-operations",
                            owner="u-ops",
                            classification="internal",
                            document_type="policy",
                            status="active",
                        ),
                    )
                ],
            )
        )

        self.documents.upsert(
            DocumentRecord(
                document_id="doc-eng",
                title="Engineering Policy",
                department_id="dept-engineering",
                document_type="policy",
                owner="u-eng",
                classification="internal",
                status="active",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Engineering content",
                        metadata=DocumentMetadata(
                            department_id="dept-engineering",
                            owner="u-eng",
                            classification="internal",
                            document_type="policy",
                            status="active",
                        ),
                    )
                ],
            )
        )

        self.documents.upsert(
            DocumentRecord(
                document_id="doc-finance",
                title="Finance Policy",
                department_id="dept-finance",
                document_type="policy",
                owner="u-finance",
                classification="internal",
                status="active",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Finance content",
                        metadata=DocumentMetadata(
                            department_id="dept-finance",
                            owner="u-finance",
                            classification="internal",
                            document_type="policy",
                            status="active",
                        ),
                    )
                ],
            )
        )

        self.user_ops = User(
            user_id="u-ops",
            username="ops",
            email="ops@example.com",
            department_id="dept-operations",
            roles=tuple(),
        )

    def test_user_sees_own_department_documents(self) -> None:
        scope = self.access_service.compute_authorized_document_ids(self.user_ops)
        self.assertIn("doc-ops", scope)

    def test_user_cannot_see_other_department_documents_by_default(self) -> None:
        scope = self.access_service.compute_authorized_document_ids(self.user_ops)
        self.assertNotIn("doc-eng", scope)

    def test_department_assignment_adds_department_documents_to_scope(self) -> None:
        self.department_access.assign(user_id="u-ops", department_id="dept-engineering", assigned_by="u-admin")
        scope = self.access_service.compute_authorized_document_ids(self.user_ops)
        self.assertIn("doc-eng", scope)

    def test_admin_grants_extra_document_to_user(self) -> None:
        grant = self.access_service.grant_document_access(user_id="u-ops", document_id="doc-eng", granted_by="u-admin")
        self.assertTrue(grant.is_active)

    def test_granted_document_appears_in_scope(self) -> None:
        self.access_service.grant_document_access(user_id="u-ops", document_id="doc-eng", granted_by="u-admin")
        scope = self.access_service.compute_authorized_document_ids(self.user_ops)
        self.assertIn("doc-eng", scope)

    def test_revoked_document_disappears_from_scope(self) -> None:
        self.access_service.grant_document_access(user_id="u-ops", document_id="doc-eng", granted_by="u-admin")
        self.access_service.revoke_document_access(user_id="u-ops", document_id="doc-eng")
        scope = self.access_service.compute_authorized_document_ids(self.user_ops)
        self.assertNotIn("doc-eng", scope)

    def test_secure_retriever_excludes_unauthorized_documents(self) -> None:
        fake = FakeRetrievalService()
        retriever = SecureRetriever(fake, self.access_service)
        retriever.retrieve(
            question="q",
            user=self.user_ops,
            mode="balanced",
            strict_document_scope=False,
            department_id="dept-operations",
        )

        self.assertEqual(
            fake.calls[-1]["metadata_filter"],
            {
                "$and": [
                    {"department_id": {"$in": ["dept-operations"]}},
                    {"document_id": {"$in": ["doc-ops"]}},
                ]
            },
        )

    def test_strict_document_scope_blocks_when_no_authorized_evidence(self) -> None:
        fake = FakeRetrievalService()
        retriever = SecureRetriever(fake, self.access_service)
        denied_user = User(
            user_id="u-empty",
            username="empty",
            email="empty@example.com",
            department_id="dept-unknown",
            roles=tuple(),
        )

        result = retriever.retrieve(question="q", user=denied_user, mode="strict", strict_document_scope=True)

        self.assertEqual(
            fake.calls[-1]["metadata_filter"],
            {"$and": [{"department_id": {"$in": ["dept-unknown"]}}, {"document_id": {"$in": []}}]},
        )
        self.assertIn("No relevant information", result["answer"])

    def test_department_scope_denies_unassigned_department(self) -> None:
        fake = FakeRetrievalService()
        retriever = SecureRetriever(fake, self.access_service)

        with self.assertRaises(HTTPException):
            retriever.retrieve(
                question="q",
                user=self.user_ops,
                mode="balanced",
                strict_document_scope=False,
                department_id="dept-finance",
            )


if __name__ == "__main__":
    unittest.main()
