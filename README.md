# DocuSense Persistence Prototype (Tasks 6.2 + 6.3)

Prototype built on top of the team's DocuSense FastAPI backend and React frontend.

**Task 6.2 - Database persistence**
- SQLite database (`backend/app/db/schema.sql`): `scans`, `scan_documents`, `findings`, `audit_log`
- Scan results now survive API restarts (the old in-memory registry is replaced in `app/services/scan_registry.py`)
- Scan history, Mark Resolved / Ignore / Reopen, and a full audit trail

**Task 6.3 - Integration**
- Frontend `Mark Resolved` / `Ignore` / `Reopen` buttons now call the API and are saved
- `backend/tests/test_persistence_integration.py`: upload -> scan -> database -> review -> audit, through the real HTTP API

## New API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/scans` | Scan history with open/resolved/ignored counts |
| POST | `/api/v1/scans/{scan_id}/findings/{finding_id}/status` | Body: `{"action": "resolve" or "ignore" or "reopen", "actor": "name", "note": "optional"}` |
| GET | `/api/v1/scans/{scan_id}/audit` | Audit trail for one scan |
| GET | `/api/v1/audit` | Audit trail for everything |

Existing endpoints are unchanged (`POST /api/v1/upload-and-scan`, `GET /api/v1/scans/{id}/dashboard`).

## Run it
Backend (Windows PowerShell):
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
Frontend (second terminal):
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The database file is created automatically at `backend/var/docusense.db` (not committed to Git).

## Run the tests
```
cd backend
pytest
```
Each test uses its own temporary database, so your real data is never touched.

## Credits
Backend (parser, EAV engine, contradiction engine, evaluation) and frontend UI are the team's work. This prototype adds the database, audit trail, review endpoints, and integration tests.
