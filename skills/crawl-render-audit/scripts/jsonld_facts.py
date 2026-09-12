"""
JSON-LD parser with fact-value extraction.

Task: raw HTML -> schema objects + fact values.
Research layer 4: "Does raw JSON-LD provide a fallback?" — even when
normal markup is dynamic, prices/ratings/answers in JSON-LD can rescue
machine readability (Dot & Key lesson: price in JSON-LD despite large
DOM expansion).

Stdlib json + BeautifulSoup. Handles @graph, arrays, malformed blocks
(gracefully skipped with error records, never raising).
"""

import json
import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup

_WS_RE = re.compile(r"\s+")


def _clean(text: Any) -> str:
    if text is None:
        return ""
    return _WS_RE.sub(" ", str(text)).strip()


def extract_jsonld_objects(raw_html: str) -> Dict:
    """Return {"objects": [...], "errors": [...]} from all ld+json blocks."""
    soup = BeautifulSoup(raw_html or "", "lxml")
    objects: List[Dict] = []
    errors: List[Dict] = []

    def _add(node: Any):
        if isinstance(node, dict):
            # Expand @graph containers.
            if isinstance(node.get("@graph"), list):
                for child in node["@graph"]:
                    _add(child)
            else:
                objects.append(node)
        elif isinstance(node, list):
            for child in node:
                _add(child)

    for i, script in enumerate(soup.find_all("script", type="application/ld+json")):
        content = script.string or script.get_text() or ""
        if not content.strip():
            continue
        try:
            _add(json.loads(content))
        except json.JSONDecodeError as e:
            errors.append({"block": i, "error": str(e), "snippet": content[:200]})
    return {"objects": objects, "errors": errors}


def _walk_strings(node: Any, out: List[str]):
    if isinstance(node, str):
        s = _clean(node)
        if s:
            out.append(s)
    elif isinstance(node, dict):
        for v in node.values():
            _walk_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_strings(v, out)


def flatten_fact_values(objects: List[Dict]) -> Dict:
    """Extract searchable fact values: prices, availability, names, Q&A, ratings.

    Returns {"text_blob": str, "facts": {...}} where facts holds typed slots.
    `text_blob` is the normalized concatenation used for fact matching.
    """
    facts: Dict[str, Any] = {
        "prices": [],
        "price_currencies": [],
        "availability": [],
        "names": [],
        "descriptions": [],
        "questions": [],
        "answers": [],
        "ratings": [],
        "sameAs": [],
        "types": [],
    }
    strings: List[str] = []
    for obj in objects:
        t = obj.get("@type")
        if isinstance(t, list):
            facts["types"].extend([str(x) for x in t])
        elif t:
            facts["types"].append(str(t))
        _walk_strings(obj, strings)
        # Typed slots (best-effort, schema-agnostic key scan).
        def scan(node: Any):
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = str(k).lower()
                    if kl == "price" and v is not None:
                        facts["prices"].append(_clean(v))
                    elif kl in ("pricecurrency",):
                        facts["price_currencies"].append(_clean(v))
                    elif kl == "availability" and v is not None:
                        facts["availability"].append(_clean(v).split("/")[-1])
                    elif kl == "name" and v is not None:
                        facts["names"].append(_clean(v))
                    elif kl in ("description", "headline") and v is not None:
                        facts["descriptions"].append(_clean(v))
                    elif kl == "questionname" or (kl == "name" and isinstance(v, str)):
                        pass
                    elif kl == "sameas":
                        vals = v if isinstance(v, list) else [v]
                        facts["sameAs"].extend([_clean(x) for x in vals if _clean(x)])
                    elif kl in ("ratingvalue", "reviewcount", "aggregateRating"):
                        facts["ratings"].append(_clean(v))
                    scan(v)
            elif isinstance(node, list):
                for v in node:
                    scan(v)
        scan(obj)
        # FAQPage Q&A pairs.
        try:
            if (obj.get("@type") == "FAQPage" or "FAQPage" in str(obj.get("@type"))):
                for ent in obj.get("mainEntity", []) or []:
                    q = _clean(ent.get("name")) if isinstance(ent, dict) else ""
                    a = ""
                    acc = (ent.get("acceptedAnswer") or {}) if isinstance(ent, dict) else {}
                    if isinstance(acc, dict):
                        a = _clean(acc.get("text"))
                    if q:
                        facts["questions"].append(q)
                    if a:
                        facts["answers"].append(a)
        except Exception:
            pass
    blob = _clean(" | ".join(strings)).lower()
    # De-duplicate preserving order.
    for k, v in facts.items():
        if isinstance(v, list):
            seen, ded = set(), []
            for x in v:
                if x not in seen:
                    seen.add(x)
                    ded.append(x)
            facts[k] = ded
    return {"text_blob": blob, "facts": facts}
