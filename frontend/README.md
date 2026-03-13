# React Admin Dashboard (FastAPI Integration)

Internal admin/testing dashboard for the existing backend API.

## Run locally

1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Configure:
   - `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`)
   - `VITE_API_KEY` (must match backend `x-api-key` when required)
3. Install and run:
   ```bash
   npm install
   npm run dev
   ```

## Implemented modules

- Login + JWT session persistence
- Protected routes + logout
- Dashboard summary with health check
- Profile (`/auth/me`, `/users/me`, `/users/permissions`)
- Users list/detail with role/department/document access actions
- Departments list/detail + create
- Department upload and path/folder ingestion
- Documents list/search/detail + indexing + admin reassignment/audit
- RBAC roles/permissions/matrix + validation tester
- RAG tester (`/rag/query` and `/chat/ask`)
- Audit logs list/detail
- Health/system page

## Known backend-coupling notes

- UI uses only existing endpoints present in `backend/app/api/v1`.
- Some endpoint payloads are rendered in JSON panels for fast backend validation and schema drift tolerance.
- If endpoint permissions deny access for current user, page surfaces API error message directly.
