"""Rule-based extraction for configuration, technical limits and firmware specs.

This is an explainable MVP extractor, not a replacement for a trained NER/LLM
extractor. It emits normalized EAV records and preserves source evidence.
"""
from __future__ import annotations
import re
from typing import Any

_NUMBER = r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|min|hours?|hrs?|h|hz|khz|mhz|ghz|%|bytes?|kb|mb|gb|°c|c)?"
RULES: list[dict[str, Any]] = [
    {"attribute": "polling_interval", "patterns": [rf"(?:poll(?:ing)?\s*(?:interval|frequency|period)|sample\s*interval)\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "duration"},
    {"attribute": "gateway_timeout", "patterns": [rf"(?:gateway\s*)?(?:request\s*)?timeout(?:\s*limit)?\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "duration"},
    {"attribute": "request_timeout", "patterns": [rf"request\s*timeout\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "duration"},
    {"attribute": "retry_interval", "patterns": [rf"retry\s*(?:interval|delay|backoff)\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "duration"},
    {"attribute": "max_retries", "patterns": [r"(?:maximum|max)\s*retries\s*(?:is|of|:|=)?\s*(?P<value>\d+)"], "kind": "count"},
    {"attribute": "firmware_version", "patterns": [r"firmware\s*(?:version|rev(?:ision)?)\s*(?:is|:|=)?\s*(?P<value>v?\d+(?:\.\d+){1,3})"], "kind": "version"},
    {"attribute": "min_operating_temperature", "patterns": [rf"(?:minimum|min)\s*(?:operating\s*)?temperature\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "temperature"},
    {"attribute": "max_operating_temperature", "patterns": [rf"(?:maximum|max)\s*(?:operating\s*)?temperature\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "temperature"},
    {"attribute": "max_payload_size", "patterns": [rf"(?:maximum|max)\s*(?:payload|message)\s*size\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "size"},
    {"attribute": "voltage", "patterns": [rf"(?:supply\s*)?voltage\s*(?:is|of|:|=)?\s*{_NUMBER}"], "kind": "voltage"},
]
_UNIT_TO_BASE = {"ms": .001, "millisecond": .001, "milliseconds": .001,
                 "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
                 "min": 60, "mins": 60, "minute": 60, "minutes": 60,
                 "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600}

def _normalise(value: str, unit: str | None, kind: str):
    if kind == "duration":
        u = (unit or "s").lower()
        return float(value) * _UNIT_TO_BASE.get(u, 1), "seconds"
    if kind == "temperature":
        return float(value), (unit or "C").lower()
    if kind == "voltage":
        return float(value), (unit or "V").upper()
    if kind == "size":
        return float(value), (unit or "bytes").lower()
    if kind == "count":
        return int(float(value)), "count"
    return value, unit or "version"

def _scope(text: str) -> str:
    lower = text.lower()
    for token in ("sensor", "device", "firmware", "gateway", "cloud backend", "api", "broker", "controller"):
        if token in lower:
            return token
    return "unspecified"

def extract_technical_eav(markdown: str, document_id: str, filename: str) -> list[dict[str, Any]]:
    """Extract EAVs from each line, retaining evidence and document provenance."""
    statements = []
    for line_no, raw_line in enumerate(markdown.splitlines(), start=1):
        line = raw_line.strip().lstrip("-*> ")
        if not line:
            continue
        for rule in RULES:
            # Prevent overlapping matches: a gateway request timeout is the
            # gateway cap, while a sensor request timeout is the client value.
            if rule["attribute"] == "gateway_timeout" and "gateway" not in line.lower():
                continue
            if rule["attribute"] == "request_timeout" and "gateway" in line.lower():
                continue
            for pattern in rule["patterns"]:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if not match:
                    continue
                value, unit = _normalise(match.group("value"), match.groupdict().get("unit"), rule["kind"])
                scope = _scope(line)
                statements.append({
                    "statement_id": f"{document_id}:{line_no}:{rule['attribute']}",
                    "document_id": document_id, "source_file": filename,
                    "line": line_no, "entity": scope, "attribute": rule["attribute"],
                    "value": value, "unit": unit, "scope": scope,
                    "condition": "unspecified", "effective_from": None,
                    "effective_to": None, "evidence": raw_line.strip(),
                    "extractor": "technical_rules_v1", "confidence": 0.86,
                })
                break
    return statements
