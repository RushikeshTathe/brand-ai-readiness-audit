# Crawl-Render Audit — Component Documentation

Components developed for the layered single-page audit in
`skills/crawl-render-audit/scripts/`, plus tests in `tests/`.
Shared conventions: **observations first, conclusions second**; every
network/render boundary is timeboxed; nothing raises on transport failure —
failures are returned as data. Dependencies: `requests`, `beautifulsoup4`,
`lxml` (Playwright optional, renderer only).

Pipeline overview:

```text
URL
 ↓ http_fetch.fetch_url            status, headers, raw HTML
 ↓ waf_detector.detect_blockade    blocked? kind? (gate: skip render/CSR if blocked)
 ↓ ai_robots.fetch/check           robots policy for 18 AI user-agents
 ↓ sitemap.discover_and_fetch      baseline locations (info only)
 ↓ text_extract.extract_text       raw word counts + text
 ↓ jsonld_facts.extract/flatten    schema objects + fact-value blob
 ↓ renderer.render_url             rendered DOM (timeboxed, optional)
 ↓ text_extract.expansion_stats    raw-vs-rendered screening (observation)
 ↓ facts.compare_facts             presence matrix raw / JSON-LD / rendered
 ↓ rules.apply_rules               ACCESS/POLICY/RENDER/SCHEMA/SCREEN findings
```

Entry point: `audit.audit_url()` (see §10). Legacy multi-page modules
(`crawler.py`, `robots.py`, `structured_data.py`, `page_analysis.py`) are
unchanged and still serve `orchestrator.py`.

---

## 1. `http_fetch.py` — direct HTTP fetch
**Task:** URL → status, headers, raw HTML (research layer 1: can the request reach the page?).

- `fetch_url(url, timeout=15, user_agent="BrandAuditBot/1.0", allow_redirects=True, max_bytes=3_000_000) -> dict`
  - Returns `{url, final_url, status, headers (lowercased keys), raw_html, redirect_chain[{url,status}], elapsed_s, error, content_type, truncated}`. Never raises; `status=0` + `error` string on failure (`timeout`, `ssl-error`, `connection-error`, `request-error`).
  - Read-only GET with fixed `User-Agent`; body truncated at `max_bytes` (`truncated: true`).
- `normalize_url(url)` — prepends `https://` when missing, strips one trailing slash; raises `ValueError` on empty/invalid input (caught by `fetch_url`).
- `origin_of(url)` — `scheme://netloc`, used for robots/sitemap lookup.

## 2. `waf_detector.py` — WAF / challenge detector
**Task:** HTTP response → provider-neutral blockade signal (research rule 1).

- `detect_blockade(status, headers, raw_html, error=None) -> {blocked, kind, signals, status}`
  - `kind ∈ {None, "http-block", "rate-limited", "waf-challenge", "transport-error"}` — generic labels only, never vendor names.
  - Triggers: 429 / `retry-after` → rate-limited; 403/406/409/423/451 (+ minimal body) → http-block; challenge `<title>`/body markers (captcha, clearance cookies, sensor scripts) → waf-challenge; any transport `error` → transport-error.
  - Only inspects the first ~50 KB of HTML. Clean 200 pages return `{blocked: False, ...}`.
- **Nordstrom constraint:** callers must check this gate *before* any JS diagnosis (see `audit.py`, `rules.py`).

## 3. `ai_robots.py` — robots parser with AI-bot directives
**Task:** robots.txt → per-AI-agent access verdicts (research strong signal; Healthline layer).

- `AI_BOTS` — 18 agents (`gptbot`, `chatgpt-user`, `oai-searchbot`, `claudebot`, `claude-web`, `perplexitybot`, `google-extended`, `bytespider`, `amazonbot`, `applebot-extended`, `diffbot`, `ccbot`, `cohere-ai`, …), each tagged `live-search-agent` / `training-crawler` / `service-crawler` (informational; both kinds can fire).
- `fetch_robots_txt(origin, timeout, user_agent)` — `{available, status, text (≤200 KB), url, error}`; missing file is data, not failure.
- `parse_robots_txt(text)` — offline RFC 9309 subset → `{groups[{agents, allow, disallow, crawl_delay}], sitemaps}`; longest-prefix match, `Allow` wins ties, empty `Disallow` = allow-all.
- `check_ai_access(robots_text, target_paths=["/"]) -> {ai_directives_found, bots{token: {kind, blocked_paths, matched_rule}}, blocked_bots, sitemaps, note}` — falls back to the `*` group when an agent has no explicit group.

## 4. `sitemap.py` — sitemap discovery (baseline only)
**Task:** origin/robots → sitemap locations. Per research, sitemap data must never pass/fail a site.

- `discover_sitemap_urls(robots_text, origin)` — `Sitemap:` lines (absolute or origin-resolved) + default `/sitemap.xml`, de-duplicated, order-preserving.
- `fetch_sitemap(url, timeout)` — `{url, available, status, content_type, is_index, locs (≤5000), count, error}`; XML parse errors captured, never raised.
- `discover_and_fetch(...)` — `{candidate_urls, sitemaps}` context bundle consumed by `audit.py` as info.

## 5. `renderer.py` — Playwright renderer (timeboxed)
**Task:** URL → rendered DOM (research layer 5).

- `render_url(url, timeout_s=25, wait_ms=1500, user_agent=...) -> {ok, url, final_url, rendered_html, status, error, elapsed_s}` — headless Chromium, `domcontentloaded` + bounded settle, browser always closed. Never raises.
- Graceful degradation: missing `playwright` package or browser binaries → `{ok: False, error: "playwright-not-installed" | "render-error: ..."}`; pipeline continues raw-only. Needs `pip install playwright && playwright install chromium`.

## 6. `text_extract.py` — raw/rendered text extraction
**Task:** HTML/DOM → word counts + text (counts are observations; facts decide).

- `extract_text(raw_html, strip_boilerplate=False) -> {text, word_count, char_count}` — drops `script/style/noscript/template`, collapses whitespace; optional nav/header/footer stripping for boilerplate-robust comparison.
- `expansion_stats(raw, rendered) -> {raw_words, rendered_words, abs_gain, pct_gain, screening_triggered}` — screening fires at **>30 % and >100 words** (or empty-raw → >100 rendered words). Consumed only as `SCREEN-001` input.

## 7. `jsonld_facts.py` — JSON-LD parser + fact values
**Task:** raw HTML → schema objects + searchable fact values (research layer 4 fallback; Dot & Key lesson).

- `extract_jsonld_objects(raw_html) -> {objects, errors}` — all `ld+json` blocks; expands `@graph` and top-level arrays; malformed blocks recorded with snippet, never raised.
- `flatten_fact_values(objects) -> {text_blob, facts}` — `text_blob`: lowercased concatenation for literal matching; `facts`: typed slots (`prices`, `price_currencies`, `availability`, `names`, `descriptions`, `questions`, `answers` (FAQPage pairs), `ratings`, `sameAs`, `types`), de-duplicated.

## 8. `facts.py` — target-fact comparison
**Task:** target facts → presence matrix across raw / JSON-LD / rendered (research core: facts > metrics).

- Fact shape: `{key, value, aliases[]?}` — aliases are accepted paraphrases (the extension point for semantic/LLM matching without a dependency here).
- `normalize(text)` — casefold, NBSP/currency folding (`₹→rs`, `$→usd`, …), whitespace collapse; plus digits-only fallback so `"1,299"` matches `"1299"`.
- `compare_facts(facts, raw_text, jsonld_blob, rendered_text=None, semantic_match=None) -> {matrix, summary}` — row: `{key, in_raw, in_jsonld, in_rendered (None if not rendered), via_raw, via_rendered, js_dependent, jsonld_rescue}`.
  - `js_dependent` ⟺ ¬raw ∧ ¬JSON-LD ∧ rendered (fact-level proof; Saraswat guard).
  - `jsonld_rescue` ⟺ ¬raw ∧ JSON-LD (Dot & Key guard).
  - `semantic_match(fact, blob_norm) -> bool` hook lets callers inject LLM/embedding similarity; JSON-LD matching stays literal; hook exceptions are swallowed.
- `summary`: `{total, in_raw, in_jsonld, js_dependent, jsonld_rescue, missing_everywhere}`.

## 9. `rules.py` — decision rules → candidate findings
Implements the five provisional research rules 1:1, with counterexample guards:

| ID | Fires when | Severity |
|---|---|---|
| `ACCESS-001` | `blockade.blocked` (any kind incl. transport-error) | critical |
| `POLICY-001` | `blocked_bots` non-empty (live agents → high, else medium) | high/medium |
| `RENDER-001` | ≥1 `js_dependent` fact and render succeeded | high |
| `SCHEMA-001` | ≥1 `jsonld_rescue` fact (positive signal) | info |
| `SCREEN-001` | expansion screening tripped without fact-level proof | low/medium |

Guards: `POLICY-001` is evaluated independently (Healthline); everything after `ACCESS-001` returns early — no CSR/expansion claims under blockade (Nordstrom). Finding shape: `{id, title, severity, evidence{}, suggested_action, mechanism, priority (1–6), confidence}` — a superset of the report contract (`id/title/severity/evidence/suggested_action`).

## 10. `audit.py` — pipeline entry point
Wires layers 1–6 in research order (§8 flowchart).

```python
from audit import audit_url
result = audit_url(
    "https://example.com/product",
    target_facts=[{"key": "price", "value": "Rs. 495", "aliases": ["INR 495"]}],
    target_paths=["/product"],   # robots paths under test (default ["/"])
    render=True,                 # False = raw-only, no browser needed
    http_timeout_s=15, robots_timeout_s=15, render_timeout_s=25,
    semantic_match=None, user_agent="BrandAuditBot/1.0",
)
result["findings"]  # rules output
result["signals"]   # full observation bundle (http, blockade, ai_access,
                    # robots/sitemap availability, raw/rendered counts,
                    # expansion, jsonld types, fact_summary, fact_matrix)
result["timings"]   # per-layer seconds {http_s, robots_s, raw_extract_s,
                    # jsonld_s, render_s?, total_s}
```

Notes: robots/sitemap are always attempted (independent layers); rendering is skipped when blocked (`render_error: "render-skipped-blockade"`); sitemap failures degrade to empty candidates.

## 11. Tests
- `tests/test_crawl_render_rules.py` (10 tests, offline synthetic signals) — four key-case regressions (Dot & Key / Healthline / Nordstrom / Saraswat Bank), one true-positive CSR case, parser units (Allow-wins, empty-Disallow, missing-robots, 429, clean-200, expansion threshold).
- `tests/test_crawl_render_runtime.py` (4 tests, live) — raw-only budget 45 s/site per site (measured 0.6–2.2 s on example.com / wikipedia.org / docs.github.com); render timebox 60 s wall (measured ~9.6 s, skips cleanly without browser binaries).
- Full suite: **71/71 passing**; legacy orchestrator imports unaffected (new modules only, no edits to existing files).

## 12. `SKILL.md` role
`skills/crawl-render-audit/SKILL.md` is the frozen contract for agents: layered procedure, `audit_url` usage, validated-rules table, counterexample must-not-break list, non-claims, module map, finding contract, measured runtimes, and the optional-Playwright install note.
