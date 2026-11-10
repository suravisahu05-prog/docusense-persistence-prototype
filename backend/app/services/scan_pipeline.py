"""
scan_pipeline.py  -  Piyush's single entry point.

Harsh calls:   run_scan(parsed_docs, llm_call)
Gauransh gets: the returned dict (as JSON from the FastAPI endpoint)

parsed_docs (from Harsh's parser.py) = list of:
    {"doc": "Policy2026.pdf", "markdown": "# Refund\n...", "doc_date": "2026"}
"""
import re
from app.services.eav_engine import (extract_triples, build_comparison_matrix,
                        false_alarm_filter, to_report_json)

def split_markdown(md: str):
    """Split markdown into (section_title, text) chunks at headings."""
    parts = re.split(r"(?m)^(#{1,4}\s+.+)$", md)
    chunks, title = [], "Intro"
    for p in parts:
        if re.match(r"^#{1,4}\s+", p or ""):
            title = p.lstrip("# ").strip()
        elif p and p.strip():
            chunks.append((title, p.strip()))
    return chunks

def run_scan(parsed_docs: list[dict], llm_call) -> dict:
    triples, log = [], []
    for d in parsed_docs:
        before = len(triples)
        for section, text in split_markdown(d["markdown"]):
            triples += extract_triples(text, d["doc"], section,
                                       llm_call, d.get("doc_date"))
        log.append({"doc": d["doc"], "facts_extracted": len(triples) - before})
    candidates = build_comparison_matrix(triples)       # Task 2.2
    real = false_alarm_filter(candidates)                # Task 2.3
    report = to_report_json(real, docs_scanned=len(parsed_docs))
    report["extraction"] = log                           # extra info; frontend may ignore
    return report


# ---------------- demo with a fake LLM (no API key needed) ----------------
if __name__ == "__main__":
    import json

    def fake_llm(prompt: str) -> str:
        if "30 days" in prompt:
            v, q = "30 days", "Refund within 30 days."
        else:
            v, q = "14 days", "Refund within 14 days."
        return json.dumps([{"entity": "Refund", "attribute": "refund period",
                            "value": v, "scope": "customers",
                            "effective": None, "quote": q}])

    docs = [  # what Harsh's parser.py would return
        {"doc": "Policy2026.pdf", "markdown": "## 4.2 Refunds\nRefund within 14 days.", "doc_date": "2026"},
        {"doc": "Website.html",   "markdown": "## Returns\nRefund within 30 days.",     "doc_date": "2026"},
    ]
    print(json.dumps(run_scan(docs, fake_llm), indent=2))
