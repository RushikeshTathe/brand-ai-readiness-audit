"""
Raw/rendered text extraction (word counts + text).

Task: HTML/DOM -> word counts + text.
Research: raw word count and rendered word count ALONE are weak signals —
a large expansion can be nav/widgets/footers. Counts are observations;
only the target-fact comparison + rules draw conclusions.

Strips script/style/noscript, normalizes whitespace, removes boilerplate
optionally (nav/footer) via flag so callers can compare both views.
"""

import re
from typing import Dict
from bs4 import BeautifulSoup

_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9\u00C0-\u024F\u1E00-\u1EFF$₹€£¥.,%+-]+")

BOILERPLATE_SELECTORS = ["nav", "footer", "header", "[role=navigation]", "[role=banner]", "[role=contentinfo]"]


def extract_text(raw_html: str, strip_boilerplate: bool = False) -> Dict:
    """Return {"text": str, "word_count": int, "char_count": int}."""
    soup = BeautifulSoup(raw_html or "", "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    if strip_boilerplate:
        for sel in BOILERPLATE_SELECTORS:
            for tag in soup.select(sel):
                tag.decompose()
    text = soup.get_text(separator=" ")
    text = _WS_RE.sub(" ", text).strip()
    words = _WORD_RE.findall(text)
    return {"text": text, "word_count": len(words), "char_count": len(text)}


def expansion_stats(raw: Dict, rendered: Dict) -> Dict:
    """Compute raw-vs-rendered expansion (observation only)."""
    rw, dw = raw.get("word_count", 0), rendered.get("word_count", 0)
    abs_gain = dw - rw
    pct = (abs_gain / rw * 100.0) if rw > 0 else (float("inf") if dw > 0 else 0.0)
    return {
        "raw_words": rw,
        "rendered_words": dw,
        "abs_gain": abs_gain,
        "pct_gain": round(pct, 1) if pct != float("inf") else float("inf"),
        "screening_triggered": (rw > 0 and dw > rw * 1.3 and abs_gain > 100)
        or (rw == 0 and dw > 100),
    }
