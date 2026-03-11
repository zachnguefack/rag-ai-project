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

        self.documents.upsert(
            DocumentRecord(
                document_id="sop-it-0002-backup-restore-validation",
                title="SOP-IT-0002 Backup Restore Validation",
                department_id="dept-operations",
                document_type="pdf",
                owner="u-ops",
                classification="internal",
                status="active",
                storage_path="/tmp/SOP-IT-0002_Backup_Restore_Validation.pdf",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Restore validation steps",
                        metadata=DocumentMetadata(
                            department_id="dept-operations",
                            owner="u-ops",
                            classification="internal",
                            document_type="pdf",
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

        metadata_filter = fake.calls[-1]["metadata_filter"]
        self.assertEqual(metadata_filter["$and"][0], {"department_id": {"$in": ["dept-operations"]}})
        doc_scope = metadata_filter["$and"][1]["$or"][0]["document_id"]["$in"]
        self.assertIn("doc-ops", doc_scope)


    def test_allow_list_filter_supports_source_and_source_path_keys(self) -> None:
        fake = FakeRetrievalService()
        user = User(
            user_id=self.user_ops.user_id,
            username=self.user_ops.username,
            email=self.user_ops.email,
            department_id=self.user_ops.department_id,
            department_ids=self.user_ops.department_ids,
            is_active=self.user_ops.is_active,
            roles=self.user_ops.roles,
            document_allow_list=frozenset({"/tmp/doc-ops.md"}),
        )
        retriever = SecureRetriever(fake, self.access_service)

        retriever.retrieve(
            question="q",
            user=user,
            mode="balanced",
            strict_document_scope=False,
            department_id="dept-operations",
        )

        metadata_filter = fake.calls[-1]["metadata_filter"]
        self.assertEqual(metadata_filter["$and"][0], {"department_id": {"$in": ["dept-operations"]}})

        scope_or = metadata_filter["$and"][1]["$or"]
        doc_scope = scope_or[0]["document_id"]["$in"]
        self.assertIn("doc-ops", doc_scope)
        self.assertIn("/tmp/doc-ops.md", scope_or[1]["$or"][0]["source_path"]["$in"])
        self.assertIn("/tmp/doc-ops.md", scope_or[1]["$or"][1]["source"]["$in"])

    def test_empty_authorized_scope_returns_safe_empty_result_without_query(self) -> None:
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

        self.assertEqual(fake.calls, [])
        self.assertIn("No relevant information", result["answer"])

    def test_secure_retriever_expands_document_id_candidates_for_filter(self) -> None:
        fake = FakeRetrievalService()
        retriever = SecureRetriever(fake, self.access_service)

        retriever.retrieve(
            question="restore validation",
            user=self.user_ops,
            mode="balanced",
            strict_document_scope=False,
            document_ids=["sop-it-0002-backup-restore-validation"],
        )

        metadata_filter = fake.calls[-1]["metadata_filter"]
        doc_candidates = metadata_filter["$and"][1]["$or"][0]["document_id"]["$in"]
        self.assertIn("sop-it-0002-backup-restore-validation", doc_candidates)
        self.assertIn("sop_it_0002_backup_restore_validation", doc_candidates)

    def test_secure_retriever_keeps_citations_with_noncanonical_document_labels(self) -> None:
        class CitationService(FakeRetrievalService):
            def query(self, *, question: str, mode: str, strict_document_scope: bool | None, metadata_filter: dict | None) -> dict:
                self.calls.append({"question": question, "mode": mode, "strict_document_scope": strict_document_scope, "metadata_filter": metadata_filter})
                return {
                    "answer": "answer",
                    "citations": [{"document": "SOP-IT-0002_Backup_Restore_Validation.pdf"}],
                    "confidence": {"score": 0.7},
                }

        fake = CitationService()
        retriever = SecureRetriever(fake, self.access_service)
        result = retriever.retrieve(
            question="restore validation",
            user=self.user_ops,
            mode="balanced",
            strict_document_scope=False,
            document_ids=["sop-it-0002-backup-restore-validation"],
        )
        self.assertEqual(len(result["citations"]), 1)


    def test_requesting_unauthorized_document_id_is_forbidden(self) -> None:
        fake = FakeRetrievalService()
        retriever = SecureRetriever(fake, self.access_service)

        with self.assertRaises(HTTPException):
            retriever.retrieve(
                question="q",
                user=self.user_ops,
                mode="balanced",
                strict_document_scope=False,
                document_ids=["doc-finance"],
            )

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
