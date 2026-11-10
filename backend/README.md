# DocuSense AI — FastAPI Backend

## Implemented
- FastAPI app and versioned API route.
- CORS middleware configured using `.env`.
- Centralized HTTP, validation and unexpected-error handlers.
- Multi-file `POST /api/v1/upload-and-scan`.
- Supports `.pdf`, `.docx`, `.txt`, `.md`.
- Docling conversion for PDF/DOCX; direct UTF-8 parsing for TXT/MD.
- Markdown block segmentation into headings, paragraphs and lists.
- Technical EAV extraction for polling, timeout, retry, firmware, temperature, payload and voltage settings.
- Conservative conflict checks with dashboard-ready findings and a scan dashboard endpoint.
- Temporary uploads deleted after parsing; partial success supported.

## Setup — Windows PowerShell
```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

## Setup — macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI and `/health` for health check.

## Test upload
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/upload-and-scan" \\
  -F "files=@policy-a.pdf" -F "files=@policy-b.docx" -F "files=@notes.txt"
```
In Swagger, choose multiple files in the `files` field.

## Parser
`app/services/parser.py` exposes `parse_document(file_path, original_filename=None)`.
Docling is used for PDF/DOCX. TXT/MD are read directly. The parser returns Markdown, blocks, and character/block counts.

## Configuration
Set exact frontend origins in `CORS_ORIGINS`, comma-separated. Default upload limit is 25 MB per file; change with `MAX_UPLOAD_MB`.

## Scope and production caveats
This endpoint completes ingestion and parsing, not statement extraction or contradiction detection. Scanned PDFs may require enabling/configuring Docling OCR and its model dependencies. Docling can have a substantial first install and may download model assets. Before handling real client documents, add authentication, authorization, malware scanning, rate limiting, persistent storage, retention controls, audit logs and HTTPS. The current endpoint reads each file into memory with a per-file cap and is intended as an MVP.

## Technical configuration analysis (Tasks 4.1–4.3)

- Test catalogue: `docs/technical_conflict_test_catalog.md`
- Machine-readable fixtures: `docs/technical_conflict_fixtures.json`
- Rule-set: `app/services/technical_rules.py`
- EAV comparison/dashboard mapping: `app/services/contradiction_engine.py`
- Scan registry: `app/services/scan_registry.py` (process-local MVP storage)
- Tests: `tests/test_technical_pipeline.py`

The upload endpoint now runs technical EAV extraction and conservative checks after parsing. It returns statements, findings, summary cards, and a `scan_id`. Retrieve dashboard data with `GET /api/v1/scans/{scan_id}/dashboard`. The registry is in memory and is cleared on API restart; use a database for persistent production dashboards.

Important: a 60-second polling interval versus a 30-second gateway timeout is treated as a potential integration risk, not a direct logical contradiction. The settings describe different things. A same-attribute timeout mismatch in overlapping scope is treated as a direct conflict. All findings require human review.
