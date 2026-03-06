from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.api.deps import (
    get_audit_service,
    get_department_repository,
    get_document_access_service,
    get_document_repository,
    get_rag_service,
    get_rbac_service,
    get_scope_builder_service,
    get_user_document_access_repository,
    get_user_repository,
)
from app.config.settings import BackendSettings
from app.models.persistence.department import DepartmentRecord
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.models.persistence.user import UserRecord
from app.security.password import hash_password
from app.security.policies import RoleName

logger = logging.getLogger(__name__)

_DEV_PASSWORD = "Password123!"

_DEPARTMENTS: tuple[DepartmentRecord, ...] = (
    DepartmentRecord(department_id="dept-it", name="IT", description="Information technology, infrastructure, and security operations."),
    DepartmentRecord(department_id="dept-qa", name="Quality Assurance", description="Quality systems, change control, and deviation workflows."),
    DepartmentRecord(department_id="dept-finance", name="Finance", description="Accounting, reimbursements, and budget governance."),
    DepartmentRecord(department_id="dept-production", name="Production", description="Manufacturing execution and batch operations."),
    DepartmentRecord(department_id="dept-hr", name="Human Resources", description="People operations, onboarding, and policy management."),
)

_USERS: tuple[dict[str, str | RoleName], ...] = (
    {"user_id": "u-admin", "username": "admin", "email": "admin@local.dev", "department_id": "dept-it", "role": RoleName.SUPER_ADMINISTRATOR},
    {"user_id": "u-it-1", "username": "it_user_1", "email": "it_user_1@local.dev", "department_id": "dept-it", "role": RoleName.STANDARD_USER},
    {"user_id": "u-qa-1", "username": "qa_user_1", "email": "qa_user_1@local.dev", "department_id": "dept-qa", "role": RoleName.STANDARD_USER},
    {"user_id": "u-fin-1", "username": "finance_user_1", "email": "finance_user_1@local.dev", "department_id": "dept-finance", "role": RoleName.STANDARD_USER},
    {"user_id": "u-prod-1", "username": "prod_user_1", "email": "prod_user_1@local.dev", "department_id": "dept-production", "role": RoleName.STANDARD_USER},
    {"user_id": "u-hr-1", "username": "hr_user_1", "email": "hr_user_1@local.dev", "department_id": "dept-hr", "role": RoleName.STANDARD_USER},
)

_DOCUMENTS: tuple[dict[str, str], ...] = (
    {
        "document_id": "SOP-IT-001",
        "title": "Network Access Policy",
        "department_id": "dept-it",
        "owner": "u-admin",
        "document_type": "policy",
        "classification": "internal",
        "status": "active",
        "content": (
            "Network Access Policy\n"
            "1. All network access requests must be submitted through the IT service portal.\n"
            "2. Access is provisioned based on least-privilege and role requirements.\n"
            "3. Multi-factor authentication is mandatory for VPN and privileged systems.\n"
            "4. Quarterly recertification is required for firewall and production network access.\n"
            "5. Emergency access expires automatically after 24 hours unless extended by IT Security."
        ),
    },
    {
        "document_id": "SOP-IT-002",
        "title": "Incident Response Procedure",
        "department_id": "dept-it",
        "owner": "u-admin",
        "document_type": "procedure",
        "classification": "internal",
        "status": "active",
        "content": (
            "Incident Response Procedure\n"
            "Security incident identification begins with triage from SOC alerts and user reports.\n"
            "Escalation process: Severity 1 incidents must be escalated to IT leadership within 15 minutes.\n"
            "Containment and remediation include account isolation, endpoint quarantine, and patch deployment.\n"
            "Post-incident review documents root cause, corrective actions, and evidence retention requirements."
        ),
    },
    {
        "document_id": "SOP-QA-001",
        "title": "Change Control Procedure",
        "department_id": "dept-qa",
        "owner": "u-qa-1",
        "document_type": "sop",
        "classification": "internal",
        "status": "active",
        "content": (
            "Change Control Procedure\n"
            "The change request process starts with a documented CR including impact assessment and rollback plan.\n"
            "Approval workflow requires QA Manager approval, department owner sign-off, and final release authorization.\n"
            "QA review requirements include test evidence, risk classification, and validation summary.\n"
            "Documentation traceability must link the change request, test artifacts, and released SOP revision."
        ),
    },
    {
        "document_id": "SOP-QA-002",
        "title": "Deviation Management SOP",
        "department_id": "dept-qa",
        "owner": "u-qa-1",
        "document_type": "sop",
        "classification": "internal",
        "status": "active",
        "content": (
            "Deviation Management SOP\n"
            "Deviation workflow begins with immediate event recording and assignment of deviation owner.\n"
            "Root cause analysis uses 5-Why or fishbone methods depending on severity.\n"
            "CAPA actions must include owner, due date, and effectiveness verification criteria.\n"
            "QA closes deviations only after evidence review and approval in the quality system."
        ),
    },
    {
        "document_id": "FIN-POLICY-001",
        "title": "Expense Reimbursement Policy",
        "department_id": "dept-finance",
        "owner": "u-fin-1",
        "document_type": "policy",
        "classification": "internal",
        "status": "active",
        "content": (
            "Expense Reimbursement Policy\n"
            "Reimbursement rules require itemized receipts for lodging, travel, and meal expenses over 25 USD.\n"
            "Submission deadlines: employees must submit expenses within 30 calendar days of spend date.\n"
            "Approval levels: manager approval up to 1,000 USD, director approval above 1,000 USD.\n"
            "Non-compliant submissions are returned to the employee for correction within five business days."
        ),
    },
    {
        "document_id": "PROC-PROD-001",
        "title": "Batch Manufacturing Instructions",
        "department_id": "dept-production",
        "owner": "u-prod-1",
        "document_type": "procedure",
        "classification": "internal",
        "status": "active",
        "content": (
            "Batch Manufacturing Instructions\n"
            "Before starting a batch, operators verify line clearance and equipment calibration status.\n"
            "Critical process parameters must be recorded at each production stage in the batch record.\n"
            "Any out-of-range parameter requires immediate production hold and QA notification.\n"
            "Final release requires reconciliation of yields and supervisor sign-off."
        ),
    },
    {
        "document_id": "HR-GUIDE-001",
        "title": "Employee Onboarding Guide",
        "department_id": "dept-hr",
        "owner": "u-hr-1",
        "document_type": "guide",
        "classification": "internal",
        "status": "active",
        "content": (
            "Employee Onboarding Guide\n"
            "New hires complete orientation, policy acknowledgement, and security awareness training in week one.\n"
            "Managers must complete role onboarding checklist and access requests before start date.\n"
            "HR conducts 30-day and 90-day onboarding checkpoints with documented feedback outcomes."
        ),
    },
)

_TEST_QUERIES: tuple[tuple[str, str, list[str]], ...] = (
    ("What is the change control process?", "Change control starts with a documented change request and QA approval workflow.", ["SOP-QA-001"]),
    ("What is the reimbursement policy?", "Employees submit itemized receipts within 30 days and follow approval limits.", ["FIN-POLICY-001"]),
    ("What steps are required during a security incident?", "Incidents are identified, escalated, contained, remediated, and reviewed.", ["SOP-IT-002"]),
    ("What is the deviation management workflow?", "Deviation handling includes recording, root cause analysis, CAPA actions, and QA closure.", ["SOP-QA-002"]),
)


def _bootstrap_enabled(settings: BackendSettings) -> bool:
    app_env = (os.getenv("APP_ENV", settings.app_env) or "").strip().lower()
    explicit_flag = (os.getenv("RAG_DEV_SEED_DATA", "false") or "").strip().lower() == "true"
    return app_env == "development" or explicit_flag


def _write_rag_seed_files(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for document in _DOCUMENTS:
        file_path = data_dir / f"{document['document_id']}.md"
        if file_path.exists():
            continue
        file_path.write_text(
            "\n".join(
                (
                    f"document_id: {document['document_id']}",
                    f"title: {document['title']}",
                    f"department_id: {document['department_id']}",
                    f"owner: {document['owner']}",
                    f"document_type: {document['document_type']}",
                    f"classification: {document['classification']}",
                    f"status: {document['status']}",
                    "",
                    str(document["content"]),
                )
            ),
            encoding="utf-8",
        )


def seed_dev_dataset(settings: BackendSettings) -> None:
    if not _bootstrap_enabled(settings):
        return

    user_repo = get_user_repository()
    if user_repo.get_by_username("admin") is not None:
        logger.info("[SEED] Development dataset already exists; skipping")
        return

    logger.info("[SEED] Creating development dataset")

    department_repo = get_department_repository()
    document_repo = get_document_repository()
    user_document_access_repo = get_user_document_access_repository()
    rbac_service = get_rbac_service(document_repo, user_repo, user_document_access_repo)
    access_service = get_document_access_service(
        document_repo,
        user_document_access_repo,
        get_scope_builder_service(document_repo, user_document_access_repo),
        rbac_service,
    )

    for department in _DEPARTMENTS:
        department_repo.upsert(department)
    logger.info("[SEED] Departments created")

    password_hash = hash_password(_DEV_PASSWORD)
    for account in _USERS:
        user_repo._records[str(account["user_id"])] = UserRecord(
            user_id=str(account["user_id"]),
            username=str(account["username"]),
            email=str(account["email"]),
            password_hash=password_hash,
            department_id=str(account["department_id"]),
            roles=[account["role"]],
        )
    logger.info("[SEED] Users created")

    now = datetime.now(timezone.utc)
    for doc in _DOCUMENTS:
        metadata = DocumentMetadata(
            department_id=doc["department_id"],
            owner=doc["owner"],
            classification=doc["classification"],
            document_type=doc["document_type"],
            status=doc["status"],
        )
        record = DocumentRecord(
            document_id=doc["document_id"],
            title=doc["title"],
            department_id=doc["department_id"],
            owner=doc["owner"],
            document_type=doc["document_type"],
            classification=doc["classification"],
            status=doc["status"],
            created_at=now,
            updated_at=now,
            versions=[DocumentVersionRecord(version=1, content=doc["content"], metadata=metadata)],
        )
        document_repo.upsert(record)
    logger.info("[SEED] Documents created")

    access_service.grant_document_access(user_id="u-it-1", document_id="SOP-QA-001", granted_by="u-admin")
    access_service.grant_document_access(user_id="u-qa-1", document_id="FIN-POLICY-001", granted_by="u-admin")
    logger.info("[SEED] Access grants created")

    access_service.grant_document_access(user_id="u-prod-1", document_id="SOP-QA-002", granted_by="u-admin")
    access_service.revoke_document_access(user_id="u-prod-1", document_id="SOP-QA-002")
    logger.info("[SEED] Access revocations created")

    _write_rag_seed_files(settings.data_dir)
    rag_service = get_rag_service(settings)
    rag_service.run_indexing(force_reindex=True)
    logger.info("[SEED] Vector index built")

    audit_service = get_audit_service()
    audit_service.record_query_event(
        user_id="u-admin",
        question="User login event for admin account",
        documents_retrieved=["auth"],
        answer_generated="admin authenticated successfully via /api/v1/auth/login",
        confidence_score=1.0,
    )
    audit_service.record_query_event(
        user_id="u-it-1",
        question="Document access check for SOP-QA-001",
        documents_retrieved=["SOP-QA-001"],
        answer_generated="Access granted via explicit cross-department permission.",
        confidence_score=0.99,
    )
    audit_service.record_query_event(
        user_id="u-prod-1",
        question="Access denial for SOP-QA-002",
        documents_retrieved=["SOP-QA-002"],
        answer_generated="Access denied due to revoked explicit grant.",
        confidence_score=0.95,
    )

    for question, answer, documents in _TEST_QUERIES:
        audit_service.record_query_event(
            user_id="u-admin",
            question=question,
            documents_retrieved=documents,
            answer_generated=answer,
            confidence_score=0.93,
        )

    logger.info("[SEED] Development dataset ready")
