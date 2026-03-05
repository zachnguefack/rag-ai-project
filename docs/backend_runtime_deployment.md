# Backend Runtime Deployment (Single-Tenant, No Docker)

This backend is designed for **single-tenant** enterprise deployments without Docker.

## Linux target
- Reverse proxy: **Nginx**
- Process manager: **systemd**
- App server: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Windows target
- Reverse proxy / hosting: **IIS** (ARR or reverse proxy)
- Process manager: **Windows Service**
- App server: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Database target
- Primary RDBMS: **Microsoft SQL Server**
- Connection string configured via `RAG_DATABASE_URL`
- Example:
  - `mssql+pyodbc://sa:***@db-host:1433/rag_enterprise?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes`

## OpenAPI / Swagger usage

When the service is running, FastAPI exposes interactive API documentation by default:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON schema: `/openapi.json`

### Testing endpoints from Swagger UI

1. Open `/docs` in your browser.
2. For protected endpoints, click **Authorize** and paste `Bearer <jwt-token>` obtained from `POST /api/v1/auth/login`.
3. If API key validation is enabled (`RAG_ALLOW_UNAUTHENTICATED=false`), provide `x-api-key` in the authorization modal.
4. Use endpoint examples and schema docs to execute requests directly from the UI.

### Documentation conventions in this backend

- Endpoints are grouped by tags: `Authentication`, `Users`, `Documents`, `RAG Query`, `Admin`, `Audit`, and `System`.
- Request and response payloads are defined via Pydantic models for consistent, typed OpenAPI generation.
- Summaries, descriptions, and common error responses are declared at route level to keep docs explicit and maintainable.
