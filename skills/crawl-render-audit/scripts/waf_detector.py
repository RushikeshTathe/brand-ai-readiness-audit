"""
WAF / bot-challenge detector (provider-neutral).

Task: HTTP response -> blockade signal.
Research rule 1 (Edge Access Blockade): 403/429 or a challenge page
prevents normal automated retrieval.

Provider-neutral: never names a specific vendor as a failure. Signals are
described generically ("waf-challenge", "rate-limited") with the raw
evidence that triggered them. The decision rule decides severity.

Counterexample driving this (Nordstrom): large raw-vs-rendered expansion
was associated with HTTP 403/WAF, so network access must be checked BEFORE
diagnosing any JavaScript dependency.
"""

import re
from typing import Dict, List

# Generic challenge markers. Deliberately vendor-neutral in output labels;
# patterns below are only match inputs, never emitted as verdicts.
_CHALLENGE_TITLE_RE = re.compile(
    r"(verify you are human|attention required|access denied|forbidden|"
    r"just a moment|checking your browser|are you a robot|"
    r"unusual traffic|security check|captcha|challenge)",
    re.IGNORECASE,
)
_CHALLENGE_BODY_RES = [
    re.compile(r"cf[-_ ]?challenge|__cf_bm|cf_clearance", re.IGNORECASE),
    re.compile(r"perimeterx|px[-_ ]captcha", re.IGNORECASE),
    re.compile(r"datadome|geo.captcha", re.IGNORECASE),
    re.compile(r"akamai.*sensor|_abck=", re.IGNORECASE),
    re.compile(r"captcha|recaptcha|hcaptcha|turnstile", re.IGNORECASE),
    re.compile(r"request unsuccessful.*incapsula|_incap_", re.IGNORECASE),
]


def detect_blockade(
    status: int,
    headers: Dict[str, str],
    raw_html: str,
    error: object = None,
) -> Dict:
    """Return a blockade observation dict.

    Output: {"blocked": bool, "kind": str|None, "signals": [str], "status": int}
    kind is one of: None, "http-block", "rate-limited", "waf-challenge",
    "transport-error".
    """
    headers = headers or {}
    raw_html = raw_html or ""
    signals: List[str] = []

    if error:
        return {
            "blocked": True,
            "kind": "transport-error",
            "signals": [f"transport-error: {error}"],
            "status": status,
        }

    lowered_headers = {str(k).lower(): str(v) for k, v in headers.items()}

    if status == 429:
        signals.append("http-429-too-many-requests")
    elif status in (403, 406, 409, 423, 451):
        signals.append(f"http-{status}-denied")
    elif status in (503, 511) and (
        "challenge" in lowered_headers.get("server", "").lower()
        or "captcha" in raw_html[:20000].lower()
    ):
        signals.append(f"http-{status}-with-challenge-markers")

    retry_after = lowered_headers.get("retry-after")
    if retry_after:
        signals.append("retry-after-header-present")

    # Challenge page heuristics on small HTML sample.
    sample = raw_html[:50000]
    title_match = re.search(r"<title[^>]*>(.*?)</title>", sample, re.IGNORECASE | re.DOTALL)
    if title_match and _CHALLENGE_TITLE_RE.search(title_match.group(1)):
        signals.append("challenge-title-detected")
    for rx in _CHALLENGE_BODY_RES:
        if rx.search(sample):
            signals.append("challenge-body-marker-detected")
            break
    # Tiny HTML body on denied statuses is a classic challenge/edge block.
    if status in (400, 401, 403, 406, 409, 423, 429, 451, 503) and len(sample.strip()) < 2000:
        signals.append("denied-with-minimal-body")

    if not signals:
        return {"blocked": False, "kind": None, "signals": [], "status": status}

    kind = "http-block"
    joined = " ".join(signals)
    if "429" in joined or "retry-after" in joined:
        kind = "rate-limited"
    elif "challenge" in joined or "captcha" in joined:
        kind = "waf-challenge"
    return {"blocked": True, "kind": kind, "signals": signals, "status": status}
