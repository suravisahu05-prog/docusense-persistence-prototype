-- DocuSense persistence schema (Task 6.2)
CREATE TABLE IF NOT EXISTS scans (
    scan_id          TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    status           TEXT,
    documents_parsed INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    payload_json     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_documents (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id   TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    filename  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    scan_id      TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    finding_id   TEXT NOT NULL,
    source       TEXT NOT NULL CHECK (source IN ('technical', 'general')),
    title        TEXT,
    severity     TEXT,
    status       TEXT NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open', 'resolved', 'ignored')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (scan_id, finding_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id     TEXT NOT NULL,
    finding_id  TEXT NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('resolve', 'ignore', 'reopen')),
    old_status  TEXT NOT NULL,
    new_status  TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'anonymous',
    note        TEXT,
    at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_audit_scan ON audit_log(scan_id);
