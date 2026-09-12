"""
Single-page crawl-render audit pipeline.

Implements the research flow (README Section 8):
  URL -> direct HTTP -> WAF/HTTP gate -> robots.txt policy
      -> raw HTML extraction -> target-fact check -> JSON-LD extraction
      -> browser rendering (if facts not already resolved) -> raw vs rendered comparison
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
from typing import Any, Callable, Dict, List, Optional

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
    target_facts: Optional[List[Dict[str, Any]]] = None,
    target_paths: Optional[List[str]] = None,
    render: bool = True,
    http_timeout_s: int = 15,
    robots_timeout_s: int = 15,
    render_timeout_s: int = 25,
    semantic_match: Optional[Callable[[Dict[str, Any], str], bool]] = None,
    user_agent: str = "BrandAuditBot/1.0",
) -> Dict[str, Any]:
    """
    Run the single-page crawl-render audit for one target URL.
    Returns a dictionary containing raw signals, rule findings, timing breakdowns, and status.
    """
    t0 = time.time()
    timings: Dict[str, float] = {}
    target_facts = target_facts or []

    # Layer 1: Direct HTTP Fetch
    t = time.time()
    http_obs = fetch_url(url, timeout=http_timeout_s, user_agent=user_agent)
    timings["http_s"] = round(time.time() - t, 3)

    # Layer 2: WAF / HTTP Gate Detection
    blockade = detect_blockade(
        http_obs.get("status", 0),
        http_obs.get("headers", {}),
        http_obs.get("raw_html", ""),
        http_obs.get("error"),
    )

    origin = origin_of(http_obs.get("url") or url)

    # Layer 3: Robots Policy Check (Independent layer, always attempted)
    t = time.time()
    robots_obs = fetch_robots_txt(origin, timeout=robots_timeout_s, user_agent=user_agent)
    timings["robots_s"] = round(time.time() - t, 3)
    ai_access = check_ai_access(robots_obs.get("text", ""), target_paths or ["/"])

    # Layer 4: Sitemap Baseline Check (Best-effort observation, never raises or blocks)
    try:
        sitemap_obs = discover_and_fetch(
            robots_obs.get("text", ""), origin, timeout=robots_timeout_s
        )
    except Exception:
        sitemap_obs = {"candidate_urls": [], "sitemaps": []}

    raw_html = http_obs.get("raw_html", "")

    # Layer 5: Raw HTML Extraction & Pre-render Fact Parsing
    t = time.time()
    raw_text = extract_text(raw_html)
    timings["raw_extract_s"] = round(time.time() - t, 3)

    # Layer 6: JSON-LD Fallback & Schema Fact Extraction
    t = time.time()
    jsonld_obs = extract_jsonld_objects(raw_html)
    flat = flatten_fact_values(jsonld_obs.get("objects", []))
    timings["jsonld_s"] = round(time.time() - t, 3)

    # Pre-render Target Fact Resolution Check:
    # If target_facts are provided and ALL are already found in raw HTML or JSON-LD,
    # Playwright rendering is not required to resolve facts.
    pre_render_facts_resolved = False
    if target_facts:
        pre_fact_result = compare_facts(
            target_facts,
            raw_text["text"],
            flat.get("text_blob", ""),
            rendered_text=None,
            semantic_match=semantic_match,
        )
        matrix = pre_fact_result.get("matrix", [])
        if matrix and all(
            (item.get("in_raw") or item.get("found_raw") or item.get("raw_found"))
            or (item.get("in_jsonld") or item.get("found_jsonld") or item.get("jsonld_found"))
            for item in matrix
        ):
            pre_render_facts_resolved = True

    # Layer 7: Browser Client-side Rendering (Playwright Execution)
    rendered_html: Optional[str] = None
    render_obs: Dict[str, Any] = {"ok": False, "error": "render-skipped"}
    rendered_text: Dict[str, Any] = {"text": "", "word_count": 0, "char_count": 0}

    if render and not blockade.get("blocked") and not pre_render_facts_resolved:
        t = time.time()
        render_obs = render_url(
            http_obs.get("final_url") or url,
            timeout_s=render_timeout_s,
            user_agent=user_agent,
        )
        timings["render_s"] = round(time.time() - t, 3)

        if render_obs.get("ok"):
            raw_rendered = render_obs.get("rendered_html")
            rendered_html = (
                str(raw_rendered)
                if raw_rendered and not isinstance(raw_rendered, str)
                else (raw_rendered or "")
            )
            rendered_text = extract_text(rendered_html)
    elif blockade.get("blocked"):
        render_obs = {"ok": False, "error": "render-skipped-blockade"}
    elif pre_render_facts_resolved:
        render_obs = {"ok": False, "error": "render-skipped-facts-resolved"}

    # Expansion calculation (Raw vs Rendered Text Comparison)
    expansion = (
        expansion_stats(raw_text, rendered_text)
        if render_obs.get("ok")
        else {
            "raw_words": raw_text["word_count"],
            "rendered_words": None,
            "abs_gain": None,
            "pct_gain": None,
            "screening_triggered": False,
        }
    )

    # Layer 8: Target-fact Comparison across Raw / JSON-LD / Rendered
    fact_result = compare_facts(
        target_facts,
        raw_text["text"],
        flat.get("text_blob", ""),
        rendered_text["text"] if render_obs.get("ok") else None,
        semantic_match=semantic_match,
    )

    # Aggregate All Audit Signals
    signals: Dict[str, Any] = {
        "url": http_obs.get("url", url),
        "final_url": http_obs.get("final_url"),
        "http_status": http_obs.get("status", 0),
        "blockade": blockade,
        "ai_access": ai_access,
        "robots_available": robots_obs.get("available", False),
        "sitemap": {
            "candidates": sitemap_obs.get("candidate_urls", []),
            "fetched": len(sitemap_obs.get("sitemaps", [])),
        },
        "raw": {
            "word_count": raw_text.get("word_count", 0),
            "char_count": raw_text.get("char_count", 0),
        },
        "rendered": (
            {
                "word_count": rendered_text.get("word_count", 0),
                "char_count": rendered_text.get("char_count", 0),
            }
            if render_obs.get("ok")
            else None
        ),
        "render_ok": bool(render_obs.get("ok")),
        "render_error": render_obs.get("error"),
        "expansion": expansion,
        "jsonld": {
            "objects_count": len(jsonld_obs.get("objects", [])),
            "errors_count": len(jsonld_obs.get("errors", [])),
            "types": sorted(set(flat.get("facts", {}).get("types", []))),
        },
        "fact_summary": fact_result.get("summary", {}),
        "fact_matrix": fact_result.get("matrix", []),
    }

    # Layer 9: Rule Engine & Finding Generation
    findings = apply_rules(signals)

    timings["total_s"] = round(time.time() - t0, 3)

    return {
        "status": "success" if http_obs.get("status") == 200 else "failed",
        "url": url,
        "http": http_obs,
        "waf": blockade,
        "robots": robots_obs,
        "sitemap": sitemap_obs,
        "raw_extraction": raw_text,
        "json_ld": jsonld_obs.get("objects", []),
        "extracted_facts": flat.get("facts", {}),
        "rendering": {
            "needed": render and not pre_render_facts_resolved,
            "executed": bool(render_obs.get("ok")),
            "word_count": rendered_text.get("word_count", 0),
            "extracted_facts": (
                extract_text(rendered_html) if rendered_html else {}
            ),
        },
        "fact_comparison": fact_result,
        "signals": signals,
        "findings": findings,
        "timings": timings,
        "error": http_obs.get("error"),
    }