"""Task 6.3: integration tests - upload -> scan -> SQLite -> review -> audit, through the real HTTP API."""
import pytest
from fastapi.testclient import TestClient

SENSOR = b"Sensor polling interval is 60 seconds.\nDevice request timeout is 60 seconds."
GATEWAY = b"Cloud gateway timeout limit is 30 seconds.\nDevice request timeout is 30 seconds."
POLICY_A = b"# Refunds\nRefund within 30 days."
POLICY_B = b"# Refunds\nRefund within 14 days."


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "uploads"))
    from app.main import app
    with TestClient(app) as c:   # triggers lifespan -> init_db
        yield c


def _scan(client, *named):
    files = [("files", (n, d, "text/plain")) for n, d in named]
    return client.post("/api/v1/upload-and-scan", files=files)


def test_upload_is_saved_and_survives_reload(client):
    r = _scan(client, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY))
    assert r.status_code == 200
    scan_id = r.json()["scan_id"]
    d = client.get(f"/api/v1/scans/{scan_id}/dashboard")
    assert d.status_code == 200
    assert len(d.json()["findings"]) == len(r.json()["findings"]) > 0


def test_scan_history_lists_scans_and_counts(client):
    _scan(client, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY))
    _scan(client, ("a.md", POLICY_A), ("b.md", POLICY_B))
    scans = client.get("/api/v1/scans").json()["scans"]
    assert len(scans) == 2
    assert all(s["open_findings"] == s["findings"] for s in scans)
    assert {"sensor.txt", "gateway.txt"} <= {f for s in scans for f in s["documents"]}


def test_mark_resolved_updates_status_and_writes_audit(client):
    scan = _scan(client, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY)).json()
    fid = scan["findings"][0]["finding_id"]
    r = client.post(f"/api/v1/scans/{scan['scan_id']}/findings/{fid}/status",
                    json={"action": "resolve", "actor": "suravi", "note": "fixed in spec v2"})
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    dash = client.get(f"/api/v1/scans/{scan['scan_id']}/dashboard").json()
    assert next(f for f in dash["findings"] if f["finding_id"] == fid)["review_status"] == "resolved"
    audit = client.get(f"/api/v1/scans/{scan['scan_id']}/audit").json()["audit"]
    assert len(audit) == 1
    assert (audit[0]["action"], audit[0]["old_status"], audit[0]["new_status"], audit[0]["actor"]) == \
           ("resolve", "open", "resolved", "suravi")


def test_ignore_then_reopen_keeps_full_history(client):
    scan = _scan(client, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY)).json()
    sid, fid = scan["scan_id"], scan["findings"][0]["finding_id"]
    for action in ("ignore", "reopen", "resolve"):
        assert client.post(f"/api/v1/scans/{sid}/findings/{fid}/status", json={"action": action}).status_code == 200
    audit = client.get(f"/api/v1/scans/{sid}/audit").json()["audit"]
    assert [a["action"] for a in reversed(audit)] == ["ignore", "reopen", "resolve"]
    hist = client.get("/api/v1/scans").json()["scans"][0]
    assert hist["resolved_findings"] == 1 and hist["open_findings"] == hist["findings"] - 1


def test_general_contradiction_can_be_resolved(client):
    scan = _scan(client, ("a.md", POLICY_A), ("b.md", POLICY_B)).json()
    gen = scan["general_analysis"].get("contradictions", [])
    assert gen, "demo extractor should flag 30 vs 14 days"
    fid = f"G-{gen[0]['id']}"
    assert client.post(f"/api/v1/scans/{scan['scan_id']}/findings/{fid}/status",
                       json={"action": "ignore"}).status_code == 200
    dash = client.get(f"/api/v1/scans/{scan['scan_id']}/dashboard").json()
    assert dash["general_analysis"]["contradictions"][0]["review_status"] == "ignored"


def test_unknown_ids_and_bad_actions_are_rejected(client):
    scan = _scan(client, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY)).json()
    sid = scan["scan_id"]
    assert client.post(f"/api/v1/scans/{sid}/findings/NOPE/status", json={"action": "resolve"}).status_code == 404
    assert client.post(f"/api/v1/scans/{sid}/findings/x/status", json={"action": "delete"}).status_code == 422
    assert client.get("/api/v1/scans/missing/dashboard").status_code == 404
    assert client.get("/api/v1/scans/missing/audit").status_code == 404


def test_bad_upload_is_not_saved(client):
    r = client.post("/api/v1/upload-and-scan", files=[("files", ("x.exe", b"abc", "application/octet-stream"))])
    assert r.status_code == 422
    assert client.get("/api/v1/scans").json()["scans"] == []


def test_data_persists_across_app_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "keep.db"))
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "u"))
    from app.main import app
    with TestClient(app) as c1:
        scan = _scan(c1, ("sensor.txt", SENSOR), ("gateway.txt", GATEWAY)).json()
        fid = scan["findings"][0]["finding_id"]
        c1.post(f"/api/v1/scans/{scan['scan_id']}/findings/{fid}/status", json={"action": "resolve"})
    with TestClient(app) as c2:   # simulates stopping and restarting uvicorn
        dash = c2.get(f"/api/v1/scans/{scan['scan_id']}/dashboard")
        assert dash.status_code == 200
        assert next(f for f in dash.json()["findings"] if f["finding_id"] == fid)["review_status"] == "resolved"
