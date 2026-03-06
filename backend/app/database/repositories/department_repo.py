from __future__ import annotations

from app.models.persistence.department import DepartmentRecord


class DepartmentRepository:
    _departments: dict[str, DepartmentRecord] = {
        "dept-general": DepartmentRecord(department_id="dept-general", name="General", description="General operations"),
        "dept-operations": DepartmentRecord(department_id="dept-operations", name="Operations", description="Operations and delivery"),
        "dept-engineering": DepartmentRecord(department_id="dept-engineering", name="Engineering", description="Engineering and platform"),
        "dept-compliance": DepartmentRecord(department_id="dept-compliance", name="Compliance", description="Compliance and risk"),
    }

    def list(self) -> list[DepartmentRecord]:
        return list(self._departments.values())

    def get(self, department_id: str) -> DepartmentRecord | None:
        return self._departments.get(department_id)

    def upsert(self, record: DepartmentRecord) -> DepartmentRecord:
        self._departments[record.department_id] = record
        return record
