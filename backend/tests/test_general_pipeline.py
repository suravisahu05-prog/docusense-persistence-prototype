from app.services.scan_pipeline import run_scan
from app.services.llm import demo_llm
def test_conflict_and_scope():
    docs=[{"doc":"P.pdf","markdown":"# R\nRefund within 30 days. The warranty is 24 months.","doc_date":"2026"},
          {"doc":"W.html","markdown":"# R\nRefund within 14 days. Battery warranty is 12 months.","doc_date":"2026"}]
    r=run_scan(docs,demo_llm)
    topics=[c["topic"] for c in r["contradictions"]]
    assert any("Refund" in t for t in topics)
    assert not any("Warranty" in t for t in topics)   # scope differs -> suppressed
