"""
Contradiction Detection Engine - Piyush's modules
  Task 2.1  LLM wrapper -> EAV JSON triples
  Task 2.2  Comparison matrix (Entity / Attribute / Value matching)
  Task 2.3  False Alarm Filter (scope + temporal checks)

The LLM call is injected (llm_call: str -> str), so you can plug in Claude,
OpenAI, or a local model without touching the rest of the pipeline.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from datetime import date
from difflib import SequenceMatcher
from itertools import combinations
from typing import Callable, Optional

# ------------------------------------------------------------------ data model
@dataclass
class Triple:
    entity: str
    attribute: str
    value: str
    scope: str = "general"          # who/what it applies to ("battery", "customers")
    effective: Optional[str] = None  # ISO date or year, e.g. "2026" / "2026-03-01"
    doc: str = ""
    section: str = ""
    quote: str = ""                  # exact supporting sentence (evidence for Stage 4)

# ------------------------------------------------------------------ Task 2.1
EXTRACTION_PROMPT = """You are an information-extraction engine.
Convert the text below into factual statements as JSON triples.
Return ONLY a JSON array, no prose, no markdown fences.

Each item must have:
  "entity"    : the thing described (e.g. "Laptop warranty")
  "attribute" : the property (e.g. "duration", "refund_period", "deadline")
  "value"     : the value exactly as stated (e.g. "24 months")
  "scope"     : who/what it applies to; use "general" if unrestricted
                (e.g. "battery", "international students")
  "effective" : date/year the statement is valid from if stated, else null
  "quote"     : the exact sentence the fact came from

Rules: only extract explicit facts. Do not infer. Skip opinions.

TEXT:
{chunk}
"""

def extract_triples(chunk: str, doc: str, section: str,
                    llm_call: Callable[[str], str],
                    doc_date: Optional[str] = None) -> list[Triple]:
    raw = llm_call(EXTRACTION_PROMPT.format(chunk=chunk))
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []  # log + retry in production
    out = []
    for it in items:
        if not all(k in it for k in ("entity", "attribute", "value")):
            continue
        out.append(Triple(
            entity=str(it["entity"]).strip(),
            attribute=str(it["attribute"]).strip(),
            value=str(it["value"]).strip(),
            scope=str(it.get("scope") or "general").strip(),
            effective=it.get("effective") or doc_date,  # fall back to document date
            doc=doc, section=section, quote=it.get("quote", ""),
        ))
    return out

# ------------------------------------------------------------------ normalisation
_UNIT_TO_DAYS = {"day": 1, "days": 1, "week": 7, "weeks": 7,
                 "month": 30, "months": 30, "year": 365, "years": 365}

def norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("_", " ")).strip()

def parse_value(v: str):
    """Return ('num', days_or_number, unit) or ('text', normalized)."""
    v = re.sub(r"(?<=\d),(?=\d)", "", v)          # 5,00,000 -> 500000
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?", v)
    if m:
        num, unit = float(m.group(1)), (m.group(2) or "").lower()
        if unit in _UNIT_TO_DAYS:
            return ("dur", num * _UNIT_TO_DAYS[unit])
        return ("num", num)
    return ("text", norm_text(v))

def values_equal(a: str, b: str) -> bool:
    pa, pb = parse_value(a), parse_value(b)
    if pa[0] == pb[0] == "text":
        return SequenceMatcher(None, pa[1], pb[1]).ratio() > 0.9
    return pa == pb

def similar(a: str, b: str, threshold=0.8) -> bool:
    # Swap this for sentence-transformers cosine similarity for better recall.
    return SequenceMatcher(None, norm_text(a), norm_text(b)).ratio() >= threshold

# ------------------------------------------------------------------ Task 2.2
@dataclass
class Candidate:
    a: Triple
    b: Triple
    confidence: float = 0.0
    status: str = "CANDIDATE"
    reason: str = ""

def build_comparison_matrix(triples: list[Triple]) -> list[Candidate]:
    """Pair every two triples from DIFFERENT docs that share entity+attribute
    but disagree on value."""
    cands = []
    for a, b in combinations(triples, 2):
        if a.doc == b.doc and a.section == b.section:
            continue  # optional: also flag intra-document conflicts
        if not (similar(a.entity, b.entity) and similar(a.attribute, b.attribute)):
            continue
        if values_equal(a.value, b.value):
            continue
        conf = (SequenceMatcher(None, norm_text(a.entity), norm_text(b.entity)).ratio()
                + SequenceMatcher(None, norm_text(a.attribute), norm_text(b.attribute)).ratio()) / 2
        cands.append(Candidate(a, b, confidence=round(conf, 2)))
    return cands

# ------------------------------------------------------------------ Task 2.3
def _year(t: Triple) -> Optional[int]:
    if not t.effective:
        return None
    m = re.match(r"(\d{4})", str(t.effective))
    return int(m.group(1)) if m else None

def false_alarm_filter(cands: list[Candidate],
                       current_year: int = date.today().year) -> list[Candidate]:
    result = []
    for c in cands:
        # Scope check: different scopes => both can be true
        if norm_text(c.a.scope) != norm_text(c.b.scope) and not (
                "general" in (norm_text(c.a.scope), norm_text(c.b.scope)) and False):
            c.status, c.reason = "SUPPRESSED", f"Scope differs ({c.a.scope} vs {c.b.scope})"
            continue
        ya, yb = _year(c.a), _year(c.b)
        # Temporal check: different effective years => policy evolution, unless
        # the newer one is not actually current.
        if ya and yb and ya != yb:
            c.status = "SUPERSEDED"
            c.reason = f"Policy changed {min(ya, yb)} -> {max(ya, yb)}"
            continue
        # Same period (or unknown) + same scope => real conflict
        c.status = "NEEDS HUMAN REVIEW"
        c.reason = "Same entity, attribute, scope and period; values differ"
        if ya is None or yb is None:
            c.confidence = round(c.confidence * 0.85, 2)  # date unknown -> less sure
        result.append(c)
    return result

def severity(c: Candidate) -> str:
    return "Critical" if c.confidence >= 0.9 else "Moderate" if c.confidence >= 0.75 else "Minor"

# ------------------------------------------------------------------ output for dashboard
def to_report_json(real: list[Candidate], docs_scanned: int) -> dict:
    """Single payload for Gauransh's dashboard (summary cards + contradiction cards)."""
    items = []
    for i, c in enumerate(real, 1):
        items.append({
            "id": i,
            "topic": f"{c.a.entity} / {c.a.attribute}",
            "severity": severity(c),
            "confidence": round(c.confidence * 100),   # percent
            "status": c.status,
            "scope": c.a.scope,
            "effective": c.a.effective or c.b.effective,
            "source_a": {"doc": c.a.doc, "section": c.a.section, "value": c.a.value, "quote": c.a.quote},
            "source_b": {"doc": c.b.doc, "section": c.b.section, "value": c.b.value, "quote": c.b.quote},
        })
    counts = {s: sum(1 for x in items if x["severity"] == s) for s in ("Critical", "Moderate", "Minor")}
    score = max(0, round(100 - 100 * len(items) / max(docs_scanned, 1)))
    return {"documents_scanned": docs_scanned, "counts": counts,
            "consistency_score": score, "contradictions": items}

# ------------------------------------------------------------------ demo
if __name__ == "__main__":
    triples = [
        Triple("Laptop", "warranty duration", "24 months", "full product", "2026", "Spec.pdf", "2.1", "The warranty lasts 24 months."),
        Triple("Laptop", "warranty duration", "12 months", "battery", "2026", "FAQ.html", "3", "Battery warranty is 12 months."),
        Triple("Refund", "refund period", "30 days", "customers", "2024", "Policy2024.pdf", "4.2", "Refund within 30 days."),
        Triple("Refund", "refund period", "14 days", "customers", "2025", "Policy2025.pdf", "4.2", "Refund within 14 days."),
        Triple("Refund", "refund period", "14 days", "customers", "2026", "Policy2026.pdf", "4.2", "Refund within 14 days."),
        Triple("Refund", "refund period", "30 days", "customers", "2026", "Website.html", "Returns", "Refund within 30 days."),
    ]
    cands = build_comparison_matrix(triples)
    print(f"Raw candidates: {len(cands)}")
    real = false_alarm_filter(cands, 2026)
    print(f"After false-alarm filter: {len(real)}\n")
    for c in real:
        print(f"[{severity(c)}] {c.a.entity} / {c.a.attribute}")
        print(f"  A: {c.a.value} ({c.a.doc}) | B: {c.b.value} ({c.b.doc})")
        print(f"  {c.status}: {c.reason} | confidence {c.confidence}")
    print("\nSuppressed:")
    for c in cands:
        if c.status in ("SUPPRESSED", "SUPERSEDED"):
            print(f"  - {c.a.doc} vs {c.b.doc}: {c.status} ({c.reason})")
    print("\n--- JSON for dashboard ---")
    print(json.dumps(to_report_json(real, docs_scanned=5), indent=2))
