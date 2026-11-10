"""
llm.py - LLM wrapper. Harsh imports get_llm() and passes it to run_scan().

  - If ANTHROPIC_API_KEY is set  -> real Claude extraction (understands ANY wording)
  - Otherwise                    -> rule-based DEMO extractor (no key; only knows the
                                    patterns listed below - for testing only)
"""
import json, os, re

def claude_llm(prompt: str) -> str:
    import anthropic                                   # pip install anthropic
    client = anthropic.Anthropic()                     # reads ANTHROPIC_API_KEY
    msg = client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text

# ---------------------------------------------------------------- DEMO extractor
_UNITS = r"(seconds?|minutes?|hours?|days?|weeks?|months?|years?)"
_KEYWORDS = ["refund", "warranty", "registration", "deadline", "polling",
             "timeout", "return", "support", "trial", "notice"]

# (entity, attribute, regex, value-builder). Applied to each sentence.
_CONTRACT_RULES = [
    ("Contract", "duration",
     r"valid for a period of (\d+)\s*" + _UNITS,
     lambda m: f"{m.group(1)} {m.group(2)}"),
    ("Payment", "total consideration",
     r"total consideration of\s*\D{0,2}([\d,]{4,})",
     lambda m: f"INR {m.group(1).rstrip(',')}"),
    ("Payment", "instalments",
     r"payable in ([a-z ]+?) instal",
     lambda m: m.group(1).replace("a single", "single") + " instalment(s)"),
    ("Termination", "notice period",
     r"(\d+)\s*" + _UNITS + r"'?\s*(?:written )?notice",
     lambda m: f"{m.group(1)} {m.group(2)}"),
    ("Termination", "early termination",
     r"\b(either|neither) party may terminate",
     lambda m: "allowed by notice" if m.group(1).lower() == "either"
               else "not allowed before expiry"),
    ("Confidentiality", "duration",
     r"confidentiality.*?(\d+)\s*" + _UNITS,
     lambda m: f"{m.group(1)} {m.group(2)}"),
    ("Dispute resolution", "jurisdiction",
     r"courts? in ([^.]+)",
     lambda m: m.group(1).strip()),
]

def _split_sentences(text: str):
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", flat) if s.strip()]

def demo_llm(prompt: str) -> str:
    """Rule-based stand-in for the LLM. For testing only."""
    text = prompt.split("TEXT:", 1)[-1]
    year = re.search(r"\b(20\d\d)\b", text)
    eff = year.group(1) if year else None
    triples = []

    for sent in _split_sentences(text):                       # contract-style rules
        for entity, attr, pattern, build in _CONTRACT_RULES:
            m = re.search(pattern, sent, re.I)
            if m:
                triples.append({"entity": entity, "attribute": attr,
                                "value": build(m), "scope": "general",
                                "effective": eff, "quote": sent})
    if triples:
        return json.dumps(triples)

    for sent in re.split(r"(?<=[.!?])\s+|\n", text):          # generic "<keyword> ... N units"
        m = re.search(r"(\d+)\s*" + _UNITS, sent, re.I)
        kw = next((k for k in _KEYWORDS if k in sent.lower()), None)
        if m and kw:
            scope = "battery" if "battery" in sent.lower() else "general"
            triples.append({"entity": kw.capitalize(), "attribute": "period",
                            "value": f"{m.group(1)} {m.group(2)}", "scope": scope,
                            "effective": eff, "quote": sent.strip()})
    return json.dumps(triples)

def get_llm():
    return claude_llm if os.getenv("ANTHROPIC_API_KEY") else demo_llm

def mode_name() -> str:
    return "Claude" if os.getenv("ANTHROPIC_API_KEY") else "DEMO rule-based extractor"
