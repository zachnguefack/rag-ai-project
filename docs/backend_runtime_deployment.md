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
