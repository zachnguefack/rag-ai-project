from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from langchain_community.document_loaders import CSVLoader, Docx2txtLoader, PyMuPDFLoader, TextLoader
from langchain_community.document_loaders.excel import UnstructuredExcelLoader
from langchain_core.documents import Document

try:
    import pandas as pd
except Exception:  # optional dependency
    pd = None

LOGGER = logging.getLogger("rag_v2.ingestion")


@dataclass(slots=True)
class IngestionReport:
    total_files: int = 0
    loaded_files: int = 0
    failed_files: int = 0
    total_documents: int = 0
    by_extension: Dict[str, int] = field(default_factory=dict)


class DocumentIngestionPipeline:
    """Robust ingestion with extension-aware loaders and metadata normalization."""

    SUPPORTED_EXTENSIONS: Sequence[str] = (".pdf", ".txt", ".csv", ".docx", ".xlsx", ".json")

    def __init__(self, log_level: str = "INFO"):
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )

    @staticmethod
    def _normalize_metadata(md: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        md = dict(md or {})
        md["source"] = str(source_file.resolve())
        md["file_name"] = source_file.name
        md["ext"] = source_file.suffix.lower().lstrip(".")
        md["loaded_at"] = datetime.now(tz=timezone.utc).isoformat()
        return md

    @staticmethod
    def _load_json(path: Path) -> List[Document]:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return [Document(page_content=json.dumps(obj, ensure_ascii=False, indent=2), metadata={"source": str(path)})]

    @staticmethod
    def _load_xlsx_fallback(path: Path) -> List[Document]:
        if pd is None:
            raise RuntimeError("pandas unavailable for Excel fallback")
        df = pd.read_excel(path)
        return [Document(page_content=df.to_csv(index=False), metadata={"source": str(path)})]

    def _load_single_file(self, path: Path) -> List[Document]:
        ext = path.suffix.lower()
        if ext == ".pdf":
            return PyMuPDFLoader(str(path)).load()
        if ext == ".txt":
            return TextLoader(str(path), encoding="utf-8").load()
        if ext == ".csv":
            return CSVLoader(str(path)).load()
        if ext == ".docx":
            return Docx2txtLoader(str(path)).load()
        if ext == ".xlsx":
            try:
                return UnstructuredExcelLoader(str(path)).load()
            except Exception as exc:
                LOGGER.warning("Excel unstructured loader failed for %s (%s). Fallback to pandas.", path.name, exc)
                return self._load_xlsx_fallback(path)
        if ext == ".json":
            return self._load_json(path)
        return []

    def load_documents(self, data_dir: str | Path) -> tuple[List[Document], IngestionReport]:
        base = Path(data_dir).resolve()
        if not base.exists():
            raise FileNotFoundError(f"Data directory not found: {base}")

        files = [p for p in base.glob("**/*") if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS]
        report = IngestionReport(total_files=len(files))
        docs: List[Document] = []

        for file_path in files:
            ext = file_path.suffix.lower()
            try:
                loaded = self._load_single_file(file_path)
                if not loaded:
                    continue
                for doc in loaded:
                    doc.metadata = self._normalize_metadata(getattr(doc, "metadata", {}) or {}, file_path)
                docs.extend(loaded)
                report.loaded_files += 1
                report.by_extension[ext] = report.by_extension.get(ext, 0) + len(loaded)
            except Exception as exc:
                report.failed_files += 1
                LOGGER.exception("Failed to load file=%s: %s", file_path, exc)

        report.total_documents = len(docs)
        LOGGER.info("Ingestion complete. files=%s loaded=%s failed=%s docs=%s", report.total_files, report.loaded_files, report.failed_files, report.total_documents)
        return docs, report


def load_all_documents(data_dir: str, log_level: str = "INFO"):
    pipeline = DocumentIngestionPipeline(log_level=log_level)
    docs, _ = pipeline.load_documents(data_dir)
    return docs
