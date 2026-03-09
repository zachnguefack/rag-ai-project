# Enterprise RAG Backend Refactor (Metadata + Filesystem + Vector Store)

## Overview
This refactor moves the backend away from filesystem-only department/document discovery and establishes a 3-layer persistence model:

1. **File storage layer**: original files are saved under `DATA_DEPARTMENTS_ROOT` (default `./data/depart`) in per-department folders.
2. **Metadata database layer**: SQLite metadata DB (configurable by `RAG_METADATA_DB_PATH`, default `./data/metadata.db`) stores departments, documents, and ingestion job state.
3. **Vector storage layer**: existing RAG indexing/vectorization remains shared; document metadata keeps department linkage for retrieval filtering.

## Why filesystem-only is insufficient
Filesystem-only department/file enumeration is fragile after restart, difficult to validate, and cannot represent business state (active/inactive departments, indexing status, ownership, upload timestamps, etc.).

Using metadata persistence provides deterministic API behavior, restart-safe listing, and an explicit contract between file lifecycle and retrieval lifecycle.

## Data model

### Department
- `id`
- `department_id`
- `name`
- `slug`
- `description`
- `created_at`
- `is_active`

### Document
- `id`
- `document_id`
- `department_id`
- `original_filename`
- `stored_filename`
- `storage_path`
- `content_type`
- `size_bytes`
- `checksum`
- `uploaded_at`
- `indexing_status`
- `last_indexed_at`
- plus existing document metadata/version payloads used by current APIs

## API behavior
- Department listing now uses metadata as the source of truth.
- Department creation writes metadata and creates physical folder.
- Department file listing resolves from document metadata and verifies physical file presence when available.
- Upload writes file physically and persists document metadata.
- Restart consistency is achieved by reloading repository state from SQLite DB, not memory.

## Configuration
- `DATA_DEPARTMENTS_ROOT=./data/depart`
- `RAG_METADATA_DB_PATH=./data/metadata.db`
- `RAG_MAX_UPLOAD_FILE_SIZE_BYTES`
- `RAG_INGEST_ALLOWED_ROOTS`

## Retrieval scope readiness
The vector store remains shared. Documents are persisted with department linkage so backend filtering can enforce allowed departments/scopes (preparing for RBAC policy-based retrieval).

## Validation commands
```bash
python -m compileall backend/app backend/tests
PYTHONPATH=backend pytest -q backend/tests/test_departments_filesystem_source_of_truth.py \
  backend/tests/test_department_filesystem_ingestion.py \
  backend/tests/test_admin_departments_api_dependencies.py \
  backend/tests/test_department_ingestion_api_contract.py
```

## Compatibility notes
- Existing endpoints remain available.
- Department APIs now treat metadata as source-of-truth; manual folder creation without metadata no longer auto-registers departments.
