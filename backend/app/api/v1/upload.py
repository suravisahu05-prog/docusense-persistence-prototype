from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4
import logging
from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from app.core.config import ALLOWED_EXTENSIONS, settings
from app.services.parser import DocumentParseError, parse_document
from app.services.technical_rules import extract_technical_eav
from app.services.contradiction_engine import analyze_eav, dashboard_payload
from app.services.scan_pipeline import run_scan
from app.services.llm import get_llm, mode_name
from app.services.scan_registry import save_scan, get_scan

router = APIRouter(tags=["documents"])
logger = logging.getLogger("docusense.upload")

@router.post("/upload-and-scan")
async def upload_and_scan(files: list[UploadFile] = File(...)):
    """Multi-file ingestion and parsing. Contradiction analysis is a later stage."""
    if not files:
        raise HTTPException(400, "Upload at least one document.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    upload_dir = Path(settings.temp_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    scan_id, parsed_docs, errors = str(uuid4()), [], []

    for upload in files:
        filename = Path(upload.filename or "unnamed").name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            errors.append({"filename": filename, "code": "UNSUPPORTED_FILE_TYPE",
                           "message": f"Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"})
            await upload.close()
            continue

        data = await upload.read(max_bytes + 1)
        await upload.close()
        if not data:
            errors.append({"filename": filename, "code": "EMPTY_FILE",
                           "message": "The uploaded file is empty."})
            continue
        if len(data) > max_bytes:
            errors.append({"filename": filename, "code": "FILE_TOO_LARGE",
                           "message": f"Maximum file size is {settings.max_upload_mb} MB."})
            continue

        temp_path = None
        try:
            with NamedTemporaryFile(mode="wb", suffix=suffix, prefix="docusense_",
                                    dir=upload_dir, delete=False) as tmp:
                tmp.write(data)
                temp_path = Path(tmp.name)
            result = await run_in_threadpool(parse_document, temp_path, filename)
            result["status"] = "parsed"
            result["document_id"] = str(uuid4())
            parsed_docs.append(result)
        except DocumentParseError as exc:
            logger.warning("Parsing failed for %s: %s", filename, exc)
            errors.append({"filename": filename, "code": "PARSING_FAILED",
                           "message": str(exc)})
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    if not parsed_docs:
        raise HTTPException(422, detail={
            "message": "No files could be parsed.", "file_errors": errors
        })
    statements = []
    for doc in parsed_docs:
        statements.extend(extract_technical_eav(
            doc["markdown"], doc["document_id"], doc["filename"]
        ))
    findings = analyze_eav(statements)
    analysis = dashboard_payload(scan_id, parsed_docs, statements, findings)
    analysis.update({
        "status": "analyzed_with_errors" if errors else "analysis_complete",
        "documents_received": len(files), "documents_parsed": len(parsed_docs),
        "documents_failed": len(errors), "documents": parsed_docs, "errors": errors,
        "extraction_version": "technical_rules_v1",
        "note": "Rule-based technical EAV extraction and conservative MVP checks; human review is required."
    })
    try:  # Stage 2-4: general EAV + scope/temporal filter (Claude if key set, else demo rules)
        general = await run_in_threadpool(run_scan, [
            {"doc": d["filename"], "markdown": d["markdown"], "doc_date": None}
            for d in parsed_docs], get_llm())
        general["extractor"] = mode_name()
        analysis["general_analysis"] = general
    except Exception as exc:  # never break the technical path
        logger.warning("General scan failed: %s", exc)
        analysis["general_analysis"] = {"error": str(exc)}
    save_scan(scan_id, analysis)
    return analysis

@router.get("/scans/{scan_id}/dashboard")
async def get_scan_dashboard(scan_id: str):
    """Return the dashboard payload for a scan held in this API process."""
    result = get_scan(scan_id)
    if result is None:
        raise HTTPException(404, detail="Scan not found or expired after API restart.")
    return {**result["dashboard"], "general_analysis": result.get("general_analysis")}
