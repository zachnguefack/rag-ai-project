from __future__ import annotations

from fastapi import HTTPException, status

from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.models.persistence.department import DepartmentRecord
from app.models.persistence.document import DocumentRecord


class DepartmentService:
    def __init__(
        self,
        department_repository: DepartmentRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._departments = department_repository or DepartmentRepository()
        self._documents = document_repository or DocumentRepository()

    def create_department(self, department_id: str, name: str, description: str) -> DepartmentRecord:
        if self._departments.get(department_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists.")
        return self._departments.upsert(
            DepartmentRecord(department_id=department_id, name=name, description=description)
        )

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
