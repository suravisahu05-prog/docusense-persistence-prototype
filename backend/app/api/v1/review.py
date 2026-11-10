"""Scan history, Mark Resolved / Ignore, and audit trail endpoints (Task 6.2)."""
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import scan_registry as reg

router = APIRouter(tags=["review"])


class StatusChange(BaseModel):
    action: Literal["resolve", "ignore", "reopen"]
    actor: str = Field("anonymous", max_length=80)
    note: str | None = Field(None, max_length=500)


@router.get("/scans")
async def scan_history(limit: int = 50):
    return {"scans": reg.list_scans(min(max(limit, 1), 200))}


@router.post("/scans/{scan_id}/findings/{finding_id}/status")
async def change_status(scan_id: str, finding_id: str, body: StatusChange):
    result = reg.set_finding_status(scan_id, finding_id, body.action, body.actor.strip() or "anonymous", body.note)
    if result is None:
        raise HTTPException(404, detail="Finding not found for this scan.")
    return result


@router.get("/scans/{scan_id}/audit")
async def scan_audit(scan_id: str):
    if reg.get_scan(scan_id) is None:
        raise HTTPException(404, detail="Scan not found.")
    return {"scan_id": scan_id, "audit": reg.get_audit(scan_id)}


@router.get("/audit")
async def full_audit(limit: int = 200):
    return {"audit": reg.get_audit(None, min(max(limit, 1), 1000))}
