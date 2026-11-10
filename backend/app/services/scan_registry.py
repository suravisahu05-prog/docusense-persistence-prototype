"""SQLite-backed scan registry (Task 6.2). Replaces the old in-memory dict.

Same public API as before (save_scan / get_scan) so the upload endpoint is unchanged.
"""
import json
from app.db.database import connect

STATUS_LABEL = {"open": "needs_review", "resolved": "resolved", "ignored": "ignored"}


def _extract_findings(payload: dict) -> list[dict]:
    rows = []
    for f in payload.get("findings", []):
        rows.append({"finding_id": f["finding_id"], "source": "technical",
                     "title": f.get("attribute"), "severity": f.get("severity")})
    for c in (payload.get("general_analysis") or {}).get("contradictions", []):
        rows.append({"finding_id": f"G-{c['id']}", "source": "general",
                     "title": c.get("topic"), "severity": c.get("severity")})
    return rows


def save_scan(scan_id: str, payload: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scans (scan_id, status, documents_parsed, documents_failed, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (scan_id, payload.get("status"), payload.get("documents_parsed", 0),
             payload.get("documents_failed", 0), json.dumps(payload)))
        conn.execute("DELETE FROM scan_documents WHERE scan_id = ?", (scan_id,))
        conn.executemany("INSERT INTO scan_documents (scan_id, filename) VALUES (?, ?)",
                         [(scan_id, d["filename"]) for d in payload.get("documents", [])])
        for r in _extract_findings(payload):
            conn.execute(
                "INSERT OR IGNORE INTO findings (scan_id, finding_id, source, title, severity) VALUES (?, ?, ?, ?, ?)",
                (scan_id, r["finding_id"], r["source"], r["title"], r["severity"]))


def get_scan(scan_id: str) -> dict | None:
    """Return the saved payload with each finding's CURRENT review status merged in."""
    with connect() as conn:
        row = conn.execute("SELECT payload_json FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if row is None:
            return None
        statuses = {r["finding_id"]: r["status"] for r in conn.execute(
            "SELECT finding_id, status FROM findings WHERE scan_id = ?", (scan_id,))}
    payload = json.loads(row["payload_json"])
    for f in payload.get("findings", []):
        f["review_status"] = statuses.get(f["finding_id"], "open")
        f["status"] = STATUS_LABEL[f["review_status"]]
    for c in (payload.get("general_analysis") or {}).get("contradictions", []):
        c["review_status"] = statuses.get(f"G-{c['id']}", "open")
    payload["dashboard"]["findings"] = payload["findings"]
    return payload


def list_scans(limit: int = 50) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("""
            SELECT s.scan_id, s.created_at, s.status, s.documents_parsed, s.documents_failed,
                   COUNT(f.finding_id) AS findings,
                   COALESCE(SUM(f.status = 'open'), 0)     AS open_findings,
                   COALESCE(SUM(f.status = 'resolved'), 0) AS resolved_findings,
                   COALESCE(SUM(f.status = 'ignored'), 0)  AS ignored_findings
            FROM scans s LEFT JOIN findings f ON f.scan_id = s.scan_id
            GROUP BY s.scan_id ORDER BY s.created_at DESC, s.rowid DESC LIMIT ?""", (limit,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["documents"] = [x["filename"] for x in conn.execute(
                "SELECT filename FROM scan_documents WHERE scan_id = ?", (r["scan_id"],))]
            out.append(d)
        return out


ACTIONS = {"resolve": "resolved", "ignore": "ignored", "reopen": "open"}


def set_finding_status(scan_id: str, finding_id: str, action: str, actor: str, note: str | None) -> dict | None:
    """Change a finding's status AND write the audit row in one transaction."""
    new_status = ACTIONS[action]
    with connect() as conn:
        row = conn.execute("SELECT status FROM findings WHERE scan_id = ? AND finding_id = ?",
                           (scan_id, finding_id)).fetchone()
        if row is None:
            return None
        old_status = row["status"]
        conn.execute("UPDATE findings SET status = ?, updated_at = datetime('now') "
                     "WHERE scan_id = ? AND finding_id = ?", (new_status, scan_id, finding_id))
        conn.execute("INSERT INTO audit_log (scan_id, finding_id, action, old_status, new_status, actor, note) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (scan_id, finding_id, action, old_status, new_status, actor, note))
    return {"scan_id": scan_id, "finding_id": finding_id, "old_status": old_status, "status": new_status}


def get_audit(scan_id: str | None = None, limit: int = 200) -> list[dict]:
    q, args = "SELECT * FROM audit_log", []
    if scan_id:
        q += " WHERE scan_id = ?"
        args.append(scan_id)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(q, args)]
