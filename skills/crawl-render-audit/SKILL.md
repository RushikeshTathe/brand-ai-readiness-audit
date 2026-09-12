# Crawl / Render Audit Skill

## Purpose
Determines whether important website information can be reached and understood by machines,
following a layered diagnostic: reachability -> crawler policy -> raw facts -> JSON-LD
fallback -> rendered facts. Target facts matter more than generic page metrics.

## Capabilities
1. **HTTP Accessibility** - Status codes, redirects, content types, request failures
2. **Edge / WAF detection** - Provider-neutral blockade signal (403/429/challenge)
3. **robots.txt Analysis** - Availability plus AI-bot directives (GPTBot, PerplexityBot, ClaudeBot, ...)
4. **Sitemap Discovery** - Baseline location discovery only (never a pass/fail)
5. **Conservative Crawling** - Same-domain, configurable depth/pages, rate limiting
6. **HTML Inspection** - Title, meta, headings, links, images, structured data
7. **Machine-readable Content** - Fact-level JS-dependency (never word-count alone)
8. **Structured Data** - Schema.org/JSON-LD detection, validation, and fact-value extraction
9. **Broken Links** - Internal link validation with proper error classification

## Layered Procedure (single-page audit)
```
URL -> direct HTTP -> WAF/HTTP gate -> robots.txt policy -> raw HTML extraction
    -> target-fact check -> JSON-LD extraction -> browser rendering
    -> raw vs rendered comparison -> target-fact comparison -> findings
```
Network access is checked BEFORE any JavaScript diagnosis: conclusions drawn under
an edge blockade are unreliable, so rendering/CSR findings are skipped when blocked.

```python
from scripts.audit import audit_url

result = audit_url(
    "https://example.com/product",
    target_facts=[{"key": "price", "value": "Rs. 495", "aliases": ["INR 495"]}],
    target_paths=["/product"],
    render=True,            # False = raw-only mode (no browser needed)
)
print(result["findings"])   # candidate findings (finding contract below)
print(result["signals"])    # observations (status, fact matrix, expansion, ...)
print(result["timings"])    # per-layer runtime
```

## Validated Decision Rules
| ID | Rule | Severity |
|----|------|----------|
| ACCESS-001 | Edge blockade (403/429/challenge) prevents retrieval | critical |
| POLICY-001 | Relevant AI user-agent disallowed on public content | high (live agents) / medium |
| RENDER-001 | Fact missing from raw HTML **and** JSON-LD, present only after render | high |
| SCHEMA-001 | JSON-LD carries facts missing from markup (rescue, positive signal) | info |
| SCREEN-001 | >30% and >100-word expansion triggers inspection only | low/medium warning |

## Counterexamples (must-not-break)
- **Dot & Key**: large DOM expansion + price in JSON-LD -> NO RENDER-001.
- **Healthline**: strong HTML + AI bot block -> POLICY-001 only, layers stay separate.
- **Nordstrom**: 403/WAF -> ACCESS-001 only; no CSR claims under blockade.
- **Saraswat Bank**: rendered growth + rate in static table -> NO RENDER-001.

## Explicit Non-Claims
- "Uses JavaScript", "has sitemap/robots.txt", raw word counts, and DOM expansion
  alone are observations, never failures.
- Missing sitemap / missing robots.txt is never a failure.
- robots.txt permission does not guarantee indexing or retrieval.

## Modules (`scripts/`)
- `audit.py` - layered pipeline entrypoint (`audit_url`)
- `http_fetch.py` - direct GET -> status, headers, raw HTML (never raises)
- `waf_detector.py` - provider-neutral blockade signal
- `ai_robots.py` - offline robots parser + AI-bot access matrix
- `sitemap.py` - sitemap discovery + baseline fetch (info only)
- `renderer.py` - timeboxed Playwright render (optional dep, graceful fallback)
- `text_extract.py` - raw/rendered text + word counts + expansion stats
- `jsonld_facts.py` - schema objects + flattened fact values
- `facts.py` - target-fact presence matrix (raw / JSON-LD / rendered)
- `rules.py` - the 5 validated decision rules
- `crawler.py`, `robots.py`, `structured_data.py`, `page_analysis.py` - multi-page crawl + HTML checks (legacy orchestrator path)

## Finding Contract
```json
{
  "id": "RENDER-001",
  "title": "Important facts are JS-dependent",
  "severity": "high",
  "evidence": {"js_dependent_facts": ["price"]},
  "suggested_action": "Server-render critical facts or duplicate them in JSON-LD.",
  "mechanism": "Facts missing pre-render force full JS execution to observe them.",
  "priority": 3,
  "confidence": "high"
}
```

## Input
- `url`: Target website URL
- `target_facts`: List of `{"key", "value", "aliases"?}` important facts to trace
- `target_paths`: Public content paths to test robots policy against (default `["/"]`)
- `audit_context`: Shared audit context object (multi-page crawl path)

## Output
- `audit_url` result: `{signals, findings, timings}`
- Multi-page path: populated audit context + list of findings with severity levels

## Measured Runtime
- Raw-only mode: ~0.6-2.2s per site (example.com, wikipedia.org, docs.github.com).
- With rendering: +~10s per page (Chromium, timeboxed at 25s; skipped under blockade).
- Tests: `pytest tests/test_crawl_render_rules.py tests/test_crawl_render_runtime.py`

## Optional Dependency
Browser rendering needs Playwright + a browser (`pip install playwright && playwright install chromium`).
Without it, `render_url` returns `ok=False` and the pipeline degrades to raw-only mode.

## Configuration
- `max_pages`: Maximum pages to crawl (default: 20)
- `max_depth`: Maximum crawl depth (default: 2)
- `timeout`: Request timeout in seconds (default: 10/15)
- `delay`: Delay between requests in seconds (default: 1)
- `user_agent`: User agent string (default: "BrandAuditBot/1.0")
