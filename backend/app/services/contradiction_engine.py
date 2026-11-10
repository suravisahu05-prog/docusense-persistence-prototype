"""Conservative EAV comparison and dashboard-ready finding generation."""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha1
from typing import Any

DURATION_ATTRIBUTES = {"polling_interval", "gateway_timeout", "request_timeout", "retry_interval"}

def _same_scope(a: dict, b: dict) -> bool:
    return a.get("scope") == b.get("scope") or "unspecified" in {a.get("scope"), b.get("scope")}

def analyze_eav(statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    by_attribute: dict[str, list[dict]] = defaultdict(list)
    for item in statements:
        by_attribute[item["attribute"]].append(item)

    # Direct conflicts: same attribute, compatible scope and unit, different values.
    for attribute, items in by_attribute.items():
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                if left["document_id"] == right["document_id"] or not _same_scope(left, right):
                    continue
                if left["unit"] != right["unit"] or left["value"] == right["value"]:
                    continue
                findings.append(_finding(
                    "direct_conflict", "high", attribute, left, right,
                    f"The same technical attribute has different values ({left['value']} {left['unit']} vs {right['value']} {right['unit']}) in compatible scopes."
                ))

    # Cross-component operational rule: this is a risk, not a logical contradiction.
    for poll in by_attribute.get("polling_interval", []):
        for timeout in by_attribute.get("gateway_timeout", []) + by_attribute.get("request_timeout", []):
            if poll["document_id"] == timeout["document_id"]:
                continue
            if poll["unit"] == timeout["unit"] == "seconds" and poll["value"] > timeout["value"]:
                findings.append(_finding(
                    "potential_operational_conflict", "medium", "polling_interval_vs_timeout", poll, timeout,
                    f"Polling interval ({poll['value']:g}s) exceeds timeout ({timeout['value']:g}s). Confirm whether the timeout applies to each poll request; these are different settings and are not automatically contradictory."
                ))

    # Device/client request timeout versus upstream gateway cap.
    for request in by_attribute.get("request_timeout", []):
        for gateway in by_attribute.get("gateway_timeout", []):
            if request["document_id"] == gateway["document_id"]:
                continue
            if request["unit"] == gateway["unit"] == "seconds" and request["value"] > gateway["value"]:
                findings.append(_finding(
                    "potential_operational_conflict", "medium", "request_timeout_vs_gateway_timeout", request, gateway,
                    f"Configured request timeout ({request['value']:g}s) exceeds the gateway cap ({gateway['value']:g}s). The upstream gateway may terminate the request first; verify which timeout governs the same request path."
                ))
    return findings

def _finding(kind: str, severity: str, attribute: str, a: dict, b: dict, explanation: str) -> dict:
    digest = sha1(f"{a['statement_id']}|{b['statement_id']}|{attribute}".encode()).hexdigest()[:10]
    return {
        "finding_id": f"F-{digest}",
        "type": kind, "severity": severity, "status": "needs_review",
        "attribute": attribute, "statement_ids": [a["statement_id"], b["statement_id"]],
        "documents": [a["source_file"], b["source_file"]],
        "evidence": [a["evidence"], b["evidence"]], "explanation": explanation,
        "dashboard": {"category": "Technical configuration", "review_required": True},
    }

def dashboard_payload(scan_id: str, documents: list[dict], statements: list[dict], findings: list[dict]) -> dict:
    direct = sum(x["type"] == "direct_conflict" for x in findings)
    risks = sum(x["type"] == "potential_operational_conflict" for x in findings)
    return {
        "scan_id": scan_id, "status": "analysis_complete",
        "summary": {"documents": len(documents), "eav_statements": len(statements),
                    "findings": len(findings), "direct_conflicts": direct,
                    "operational_risks": risks, "review_required": len(findings)},
        "statements": statements, "findings": findings,
        "dashboard": {"scan_id": scan_id, "status": "ready", "cards": [
            {"key": "documents", "label": "Documents", "value": len(documents)},
            {"key": "eav_statements", "label": "Technical statements", "value": len(statements)},
            {"key": "direct_conflicts", "label": "Direct conflicts", "value": direct},
            {"key": "operational_risks", "label": "Operational risks", "value": risks}],
            "findings": findings},
    }
