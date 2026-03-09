from __future__ import annotations

from pathlib import Path

from app.config.settings import BackendSettings
from app.database.sqlite import SQLiteStore
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.services.department_service import DepartmentService


def _service(tmp_path: Path) -> DepartmentService:
    settings = BackendSettings(
        data_departments_root=tmp_path / "depart",
        data_dir=tmp_path,
        metadata_db_path=tmp_path / "metadata.db",
    )
    store = SQLiteStore(settings.metadata_db_path)
    return DepartmentService(
        department_repository=DepartmentRepository(store),
        document_repository=DocumentRepository(store),
        settings=settings,
    )


def test_list_departments_reads_from_metadata_and_creates_missing_folder(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_department(None, "Finance", "fin")
    # remove physical folder to verify metadata is source of truth and folder is auto-restored
    (tmp_path / "depart" / "finance").rmdir()

    names = [item.department_id for item in service.list_departments()]

    assert names == ["finance"]
    assert (tmp_path / "depart" / "finance").is_dir()


def test_departments_persist_after_service_restart(tmp_path: Path) -> None:
    svc1 = _service(tmp_path)
    svc1.create_department(None, "Quality", "q")

    svc2 = _service(tmp_path)
    names = [item.department_id for item in svc2.list_departments()]

    assert names == ["quality"]
