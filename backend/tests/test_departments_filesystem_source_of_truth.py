from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config.settings import BackendSettings
from app.services.department_service import DepartmentService


def test_list_departments_reads_from_filesystem(tmp_path: Path) -> None:
    root = tmp_path / "depart"
    (root / "finance").mkdir(parents=True)
    (root / "hr").mkdir(parents=True)
    service = DepartmentService(settings=BackendSettings(data_departments_root=root, data_dir=tmp_path))

    names = [item.department_id for item in service.list_departments()]

    assert names == ["finance", "hr"]


def test_get_missing_department_returns_404(tmp_path: Path) -> None:
    service = DepartmentService(settings=BackendSettings(data_departments_root=tmp_path / "depart", data_dir=tmp_path))
    with pytest.raises(HTTPException) as exc:
        service.get_department("missing")
    assert exc.value.status_code == 404


def test_list_files_reflects_manual_file_changes(tmp_path: Path) -> None:
    root = tmp_path / "depart"
    dept = root / "quality"
    dept.mkdir(parents=True)
    service = DepartmentService(settings=BackendSettings(data_departments_root=root, data_dir=tmp_path))

    before = service.list_department_files("quality")
    (dept / "doc1.txt").write_text("hello", encoding="utf-8")
    after_add = service.list_department_files("quality")
    (dept / "doc1.txt").unlink()
    after_delete = service.list_department_files("quality")

    assert before == []
    assert [item.name for item in after_add] == ["doc1.txt"]
    assert after_delete == []
