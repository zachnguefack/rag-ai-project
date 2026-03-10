from __future__ import annotations

from pathlib import Path

from rag_v2.data_loader import DocumentIngestionPipeline


def test_ingestion_adds_department_document_and_source_metadata(tmp_path: Path) -> None:
    dept_dir = tmp_path / "data" / "depart" / "dept-it"
    dept_dir.mkdir(parents=True)
    policy = dept_dir / "policy_it.md"
    policy.write_text("IT security policy", encoding="utf-8")

    pipeline = DocumentIngestionPipeline()
    docs, report = pipeline.load_file_paths([policy])

    assert report.loaded_files == 1
    assert docs
    metadata = docs[0].metadata
    assert metadata["department_id"] == "dept-it"
    assert metadata["document_name"] == "policy_it.md"
    assert metadata["source_path"] == str(policy.resolve())


def test_markdown_is_supported_extension() -> None:
    pipeline = DocumentIngestionPipeline()
    assert ".md" in pipeline.SUPPORTED_EXTENSIONS
    assert ".markdown" in pipeline.SUPPORTED_EXTENSIONS
