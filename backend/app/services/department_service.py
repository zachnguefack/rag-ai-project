from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import HTTPException, status

from app.config.settings import BackendSettings, load_settings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.persistence.department import DepartmentRecord
from app.models.persistence.document import DocumentRecord
from app.services.audit_service import AuditService
from app.services.rag_service import RAGApplicationService


class DepartmentService:
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

    @staticmethod
    def _department_folder_name(name: str) -> str:
        value = name.strip()
        if not value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name cannot be empty.")
        if any(token in value for token in ("..", "/", "\\")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name contains unsafe path segments.")
        return value

    def _department_dir(self, name: str) -> Path:
        folder_name = self._department_folder_name(name)
        return (self._settings.data_dir / folder_name).resolve()

    def create_department(self, department_id: str, name: str, description: str, actor_user_id: str | None = None) -> DepartmentRecord:
        if self._departments.get(department_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists.")

        department_dir = self._department_dir(name)
        department_dir.mkdir(parents=True, exist_ok=True)

        created = self._departments.upsert(
            DepartmentRecord(department_id=department_id, name=name, description=description)
        )
        self._audit.record_query_event(
            user_id=actor_user_id or "system",
            question=f"department.create:{department_id}",
            documents_retrieved=[],
            answer_generated=f"Department created with repository {department_dir}",
            confidence_score=1.0,
        )
        return created

    def list_departments(self) -> list[DepartmentRecord]:
        return self._departments.list()

    def get_department(self, department_id: str) -> DepartmentRecord:
        department = self._departments.get(department_id)
        if not department:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
        return department

    def list_documents_for_department(self, department_id: str) -> list[DocumentRecord]:
        self.get_department(department_id)
        return self._documents.list_by_department(department_id)

    def delete_department(self, department_id: str, *, actor_user_id: str) -> dict[str, int | str]:
        department = self.get_department(department_id)
        dept_dir = self._department_dir(department.name)

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

        file_count = 0
        if dept_dir.exists():
            file_count = sum(1 for p in dept_dir.rglob("*") if p.is_file())
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
