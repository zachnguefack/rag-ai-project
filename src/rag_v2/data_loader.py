from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from langchain_community.document_loaders import (
    DirectoryLoader,
    PyMuPDFLoader,
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
)
from langchain_community.document_loaders.excel import UnstructuredExcelLoader

try:
    import pandas as pd
except Exception:
    pd = None

logger = logging.getLogger("rag_v2.data_loader")


def _setup_logger(level: str = "INFO") -> None:
    if logger.handlers:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _normalize_metadata(md: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
    md = dict(md or {})
    md["source"] = str(file_path)
    md["file_name"] = file_path.name
    md["ext"] = file_path.suffix.lower().lstrip(".")
    md["loaded_at"] = datetime.utcnow().isoformat() + "Z"
    return md


def _load_json_as_text(file_path: Path) -> List[Any]:
    from langchain_core.documents import Document
    try:
        obj = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        obj = json.loads(file_path.read_text(encoding="utf-8-sig"))
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return [Document(page_content=text, metadata={"source": str(file_path)})]


def _load_excel_fallback(file_path: Path) -> List[Any]:
    from langchain_core.documents import Document
    if pd is None:
        raise RuntimeError("pandas not installed; cannot fallback-load Excel")
    df = pd.read_excel(file_path)
    return [Document(page_content=df.to_csv(index=False), metadata={"source": str(file_path)})]


def load_all_documents(data_dir: str, log_level: str = "INFO") -> List[Any]:
    """
    Hybrid loader:
    - PDFs: DirectoryLoader + PyMuPDFLoader (fast, multithreaded, progress)
    - Others: per-file loaders with fallbacks
    """
    _setup_logger(log_level)

    data_path = Path(data_dir).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    documents: List[Any] = []

    # 1) PDFs (fast path)
    pdf_dir_loader = DirectoryLoader(
        path=str(data_path),
        glob="**/*.pdf",
        loader_cls=PyMuPDFLoader,
        show_progress=True,
        use_multithreading=True,
    )
    pdf_docs = pdf_dir_loader.load()
    for d in pdf_docs:
        src = Path(d.metadata.get("source", ""))
        if src.exists():
            d.metadata = _normalize_metadata(d.metadata, src)
    documents.extend(pdf_docs)
    logger.info("Loaded PDFs: %d", len(pdf_docs))

    # 2) Other formats (robust path)
    supported = {".txt", ".csv", ".xlsx", ".docx", ".json"}
    files = [p for p in data_path.glob("**/*") if p.is_file() and p.suffix.lower() in supported]

    for file_path in files:
        ext = file_path.suffix.lower()
        try:
            if ext == ".txt":
                loaded = TextLoader(str(file_path), encoding="utf-8").load()
            elif ext == ".csv":
                loaded = CSVLoader(str(file_path)).load()
            elif ext == ".docx":
                loaded = Docx2txtLoader(str(file_path)).load()
            elif ext == ".xlsx":
                try:
                    loaded = UnstructuredExcelLoader(str(file_path)).load()
                except Exception as e:
                    logger.warning("UnstructuredExcelLoader failed for %s (%s). Using pandas fallback.", file_path.name, e)
                    loaded = _load_excel_fallback(file_path)
            elif ext == ".json":
                loaded = _load_json_as_text(file_path)
            else:
                loaded = []

            for d in loaded:
                d.metadata = _normalize_metadata(getattr(d, "metadata", {}) or {}, file_path)

            documents.extend(loaded)
            logger.info("Loaded %-6s %s -> %d docs", ext, file_path.name, len(loaded))

        except Exception as e:
            logger.error("Failed to load %s: %s", file_path, e)

    logger.info("Total loaded documents: %d", len(documents))
    return documents



if __name__ == "__main__":
    print("=== Testing data loader ===")

    docs = load_all_documents("data", log_level="INFO")

    print(f"\nLoaded {len(docs)} documents.")

    if docs:
        print("\nExample document preview:")
        print("Content preview:", docs[0].page_content[:300])
        print("Metadata:", docs[0].metadata)