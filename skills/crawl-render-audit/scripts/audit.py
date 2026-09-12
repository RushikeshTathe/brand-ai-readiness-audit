"""
Single-page crawl-render audit pipeline.

Implements the research flow (README Section 8):

  URL -> direct HTTP -> WAF/HTTP gate -> robots.txt policy
      -> raw HTML extraction -> target-fact check -> JSON-LD extraction
      -> browser rendering -> raw vs rendered comparison
      -> target-fact comparison -> finding generation

Usage:
    from audit import audit_url
    result = audit_url("https://example.com/product",
                       target_facts=[{"key": "price", "value": "Rs. 495"}])

Timeboxes: http_timeout_s, robots_timeout_s, render_timeout_s; set
render=False for raw-only mode. Never raises on network/render failure —
failures become observations plus ACCESS findings.
"""

import time
from typing import Callable, Dict, List, Optional

from http_fetch import fetch_url, origin_of
from waf_detector import detect_blockade
from ai_robots import fetch_robots_txt, check_ai_access
from sitemap import discover_and_fetch
from text_extract import extract_text, expansion_stats
from jsonld_facts import extract_jsonld_objects, flatten_fact_values
from facts import compare_facts
from renderer import render_url
from rules import apply_rules


def audit_url(
    url: str,
    target_facts: Optional[List[Dict]] = None,
    target_paths: Optional[List[str]] = None,
    render: bool = True,
    http_timeout_s: int = 15,
    robots_timeout_s: int = 15,
    render_timeout_s: int = 25,
    semantic_match: Optional[Callable[[Dict, str], bool]] = None,
    user_agent: str = "BrandAuditBot/1.0",
) -> Dict:
    """Run the layered audit for one URL. Returns {signals, findings, timings}."""
    t0 = time.time()
    timings: Dict[str, float] = {}
    target_facts = target_facts or []

    # Layer 1: direct HTTP.
    t = time.time()
    http_obs = fetch_url(url, timeout=http_timeout_s, user_agent=user_agent)
    timings["http_s"] = round(time.time() - t, 3)

    # Layer 2: WAF / HTTP gate.
    blockade = detect_blockade(
        http_obs["status"], http_obs["headers"], http_obs["raw_html"], http_obs["error"]
    )

    origin = origin_of(http_obs["url"])
    # Robots policy (independent layer; always attempted).
    t = time.time()
    robots_obs = fetch_robots_txt(origin, timeout=robots_timeout_s, user_agent=user_agent)
    timings["robots_s"] = round(time.time() - t, 3)
    ai_access = check_ai_access(robots_obs.get("text", ""), target_paths or ["/"])

    # Sitemap baseline (observation only, best-effort, never a finding).
    try:
        sitemap_obs = discover_and_fetch(robots_obs.get("text", ""), origin, timeout=robots_timeout_s)
    except Exception:
        sitemap_obs = {"candidate_urls": [], "sitemaps": []}

    raw_html = http_obs.get("raw_html", "")

    # Layer 3: raw HTML extraction + pre-render fact check.
    t = time.time()
    raw_text = extract_text(raw_html)
    timings["raw_extract_s"] = round(time.time() - t, 3)

    # Layer 4: JSON-LD fallback.
    t = time.time()
    jsonld_obs = extract_jsonld_objects(raw_html)
    flat = flatten_fact_values(jsonld_obs["objects"])
    timings["jsonld_s"] = round(time.time() - t, 3)

    rendered_html: Optional[str] = None
    render_obs: Dict = {"ok": False, "error": "render-skipped"}
    rendered_text = {"text": "", "word_count": 0, "char_count": 0}
    if render and not blockade.get("blocked"):
        t = time.time()
        render_obs = render_url(http_obs.get("final_url") or url,
                                timeout_s=render_timeout_s, user_agent=user_agent)
        timings["render_s"] = round(time.time() - t, 3)
        if render_obs.get("ok"):
            rendered_html = render_obs.get("rendered_html", "")
            rendered_text = extract_text(rendered_html or "")
    elif blockade.get("blocked"):
        render_obs = {"ok": False, "error": "render-skipped-blockade"}

    expansion = expansion_stats(raw_text, rendered_text) if render_obs.get("ok") else {
        "raw_words": raw_text["word_count"], "rendered_words": None,
        "abs_gain": None, "pct_gain": None, "screening_triggered": False,
    }

    # Layers 5-6: target-fact comparison across raw / JSON-LD / rendered.
    fact_result = compare_facts(
        target_facts,
        raw_text["text"],
        flat["text_blob"],
        rendered_text["text"] if render_obs.get("ok") else None,
        semantic_match=semantic_match,
    )

    signals = {
        "url": http_obs["url"],
        "final_url": http_obs.get("final_url"),
        "http_status": http_obs["status"],
        "blockade": blockade,
        "ai_access": ai_access,
        "robots_available": robots_obs.get("available"),
        "sitemap": {"candidates": sitemap_obs.get("candidate_urls", []),
                    "fetched": len(sitemap_obs.get("sitemaps", []))},
        "raw": {"word_count": raw_text["word_count"], "char_count": raw_text["char_count"]},
        "rendered": {"word_count": rendered_text["word_count"],
                     "char_count": rendered_text["char_count"]} if render_obs.get("ok") else None,
        "render_ok": bool(render_obs.get("ok")),
        "render_error": render_obs.get("error"),
        "expansion": expansion,
        "jsonld": {"objects_count": len(jsonld_obs["objects"]),
                   "errors_count": len(jsonld_obs["errors"]),
                   "types": sorted(set(flat["facts"].get("types", [])))},
        "fact_summary": fact_result["summary"],
        "fact_matrix": fact_result["matrix"],
    }
    findings = apply_rules(signals)
    timings["total_s"] = round(time.time() - t0, 3)
    return {"signals": signals, "findings": findings, "timings": timings}
