"""
Target-fact comparison (fact presence matrix).

Task: target facts -> fact presence matrix across raw HTML / JSON-LD / rendered.
Research core lesson: "Target facts matter more than generic page metrics."

Pipeline layers:
  raw HTML text  -> JSON-LD fallback -> rendered DOM text.
A fact is JS-dependent ONLY when: missing from raw AND missing from
JSON-LD AND present after rendering (Saraswat/Dot&Key guard).

Matching is deterministic normalization (casefold, whitespace, currency
symbols, comma-stripping). An optional `semantic_match` hook lets callers
inject LLM/embedding similarity without making this module depend on it:
each fact may carry "aliases" (accepted paraphrases) which count as hits.
No network calls here.
"""

import re
from typing import Callable, Dict, List, Optional

_WS_RE = re.compile(r"\s+")

# Characters stripped for loose numeric/price matching: commas, currency words.
_PRICE_CLEAN_RE = re.compile(r"[,\s]")


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip common currency artifacts for matching."""
    t = (text or "").casefold()
    t = t.replace("\u00a0", " ").replace("₹", "rs").replace("€", "eur").replace("£", "gbp").replace("$", "usd")
    t = _WS_RE.sub(" ", t).strip()
    return t


def _variants(fact: Dict) -> List[str]:
    """Return normalized match variants for a fact: value + aliases + digits-only."""
    variants: List[str] = []
    for key in ("value",):
        v = fact.get(key)
        if v:
            variants.append(normalize(str(v)))
    for a in fact.get("aliases", []) or []:
        if a:
            variants.append(normalize(str(a)))
    # Digits-only variant helps price/rate matching ("1,299" vs "1299").
    digits = re.sub(r"\D", "", variants[0]) if variants else ""
    if digits and len(digits) >= 3:
        variants.append(digits)
    return [v for v in variants if v]


def _blob_digits(blob_norm: str) -> str:
    return re.sub(r"\D", "", blob_norm)


def fact_present(fact: Dict, blob_norm: str,
                 semantic_match: Optional[Callable[[Dict, str], bool]] = None) -> Dict:
    """Check one fact against one normalized blob. Returns {present, via}."""
    for variant in _variants(fact):
        if not variant:
            continue
        if variant in blob_norm:
            return {"present": True, "via": "exact"}
        # Digits-only fallback for numeric facts.
        if variant.isdigit() and variant in _blob_digits(blob_norm):
            return {"present": True, "via": "digits"}
    if semantic_match is not None:
        try:
            if semantic_match(fact, blob_norm):
                return {"present": True, "via": "semantic"}
        except Exception:
            pass
    return {"present": False, "via": None}


def compare_facts(
    facts: List[Dict],
    raw_text: str,
    jsonld_blob: str,
    rendered_text: Optional[str] = None,
    semantic_match: Optional[Callable[[Dict, str], bool]] = None,
) -> Dict:
    """Build the presence matrix.

    Each fact: {"key": str, "value": str, "aliases": [str]?}.
    Returns {"matrix": [{key, in_raw, in_jsonld, in_rendered, ...}], "summary": {...}}.
    Missing rendered_text -> in_rendered None (not evaluated).
    """
    raw_norm = normalize(raw_text or "")
    json_norm = normalize(jsonld_blob or "")
    ren_norm = normalize(rendered_text) if rendered_text is not None else None

    matrix = []
    for fact in facts or []:
        r = fact_present(fact, raw_norm, semantic_match)
        j = fact_present(fact, json_norm, None)  # JSON-LD stays literal
        row = {
            "key": fact.get("key", ""),
            "in_raw": r["present"],
            "in_jsonld": j["present"],
            "via_raw": r["via"],
        }
        if ren_norm is None:
            row["in_rendered"] = None
        else:
            rn = fact_present(fact, ren_norm, semantic_match)
            row["in_rendered"] = rn["present"]
            row["via_rendered"] = rn["via"]
        # JS-dependency per research: missing raw AND missing jsonld AND (rendered present).
        row["js_dependent"] = (
            ren_norm is not None
            and not row["in_raw"]
            and not row["in_jsonld"]
            and bool(row["in_rendered"])
        )
        # JSON-LD rescue: missing raw, present in JSON-LD.
        row["jsonld_rescue"] = (not row["in_raw"]) and bool(row["in_jsonld"])
        matrix.append(row)

    def count(pred):
        return sum(1 for m in matrix if pred(m))

    summary = {
        "total": len(matrix),
        "in_raw": count(lambda m: m["in_raw"]),
        "in_jsonld": count(lambda m: m["in_jsonld"]),
        "js_dependent": count(lambda m: m.get("js_dependent")),
        "jsonld_rescue": count(lambda m: m.get("jsonld_rescue")),
        "missing_everywhere": count(
            lambda m: not m["in_raw"] and not m["in_jsonld"]
            and (m.get("in_rendered") is False)
        ),
    }
    return {"matrix": matrix, "summary": summary}
