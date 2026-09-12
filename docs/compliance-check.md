# Compliance Check: Audit Report + Implementation Plan

**Date:** 2026-09-12
**Method:** file-by-file inventory of the repo, full test-suite run (71/71 passing),
live spot-checks of `audit_url()` (example.com fact trace, transport-error blockade path,
open-robots no-false-positive), and import check of the orchestrator.
**Sources:** `Adobe_R3_Audit_Research_README.md` ("research") and
`implementation_plan.md` ("plan").

Legend: ✅ Done · 🟡 Partial / deviation · ❌ Missing

---

## Part A — Research README (`Adobe_R3_Audit_Research_README.md`)

### A1. Layered diagnostic (§1, §8) — ✅ Done
All five layers implemented in `skills/crawl-render-audit/scripts/audit.py`
(`audit_url()`): reachability → crawler policy → raw-HTML facts → JSON-LD
fallback → rendered facts. Verified live: example.com trace finds the title
fact in raw HTML with zero false findings in 0.36 s.

### A2. Strong signals (§3) — ✅ Done
| Signal | Implementation | Verified |
|---|---|---|
| WAF / HTTP 403 / 429 / bot challenge | `waf_detector.py` → `detect_blockade()` | ✅ live: timeout → `ACCESS-001` critical |
| AI bot restrictions in robots.txt | `ai_robots.py` → `check_ai_access()`, 18-bot directory | ✅ unit-tested |
| Target facts present in raw HTML | `facts.py` → `compare_facts()` | ✅ live + synthetic |
| Target facts missing from raw HTML | same matrix (`in_raw: false`) | ✅ synthetic |
| Target facts in raw JSON-LD | `jsonld_facts.py` → `flatten_fact_values()` | ✅ synthetic |

### A3. Warning-only signal (§3) — ✅ Done
Raw-vs-rendered word expansion (`text_extract.expansion_stats()`,
>30 % + >100 words) only ever yields `SCREEN-001` (low/medium) and only
triggers deeper inspection. Never a failure on its own.

### A4. Rejected standalone checks (§3, §9) — ✅ Done, enforced by design
Raw word count, rendered word count, sitemap existence, sitemap URL count,
and robots.txt presence produce **observations only** — `rules.py` contains
no rule that fails on any of them. Missing sitemap/robots.txt is explicitly
not a failure (`sitemap.py`, `ai_robots.check_ai_access()` note).

### A5. JavaScript rule (§4) — ✅ Done
`JS present ≠ JS dependency` is encoded in `facts.compare_facts()`:
`js_dependent` requires missing-raw AND missing-JSON-LD AND rendered-present.
`page_analysis.py`'s old framework-marker note remains `info`-only.

### A6. Counterexamples (§5) — ✅ Done, all four as regression tests
`tests/test_crawl_render_rules.py`: Dot & Key (rescue ⇒ no `RENDER-001`),
Healthline (policy fires independently), Nordstrom (blockade ⇒ CSR skipped),
Saraswat Bank (static fact beats word growth), plus a true-positive CSR case.

### A7. Provisional rules (§6) — ✅ Done
All five rules implemented 1:1 in `rules.py`
(`ACCESS-001`, `POLICY-001`, `RENDER-001`, `SCHEMA-001`, `SCREEN-001`).

### A8. Finding contract (§7) — ✅ Done
Every rule emits `id, title, severity, evidence{}, suggested_action`
plus `mechanism, priority, confidence` for the orchestrator.

### A9. Explicit non-claims (§10) — ✅ Done
Recorded verbatim in `skills/crawl-render-audit/SKILL.md`.

### A10. Next steps (§11) — 🟡 Partial (4/6)
| Step | Status |
|---|---|
| 1. Test checks on 3–4 fresh websites | 🟡 Raw-only runtime measured on 3 live sites; full fact-traced audits on fresh sites not yet done |
| 2. Measure Playwright/browser-render runtime | ✅ ~9.6 s/page, 25 s timebox (`test_crawl_render_runtime.py`) |
| 3. Validate target-fact comparison on different page types | 🟡 Synthetic only; needs e-commerce/docs/banking pages |
| 4. Re-test the counterexamples | ✅ Synthetic regression tests |
| 5. Freeze `crawl-render-audit/SKILL.md` | ✅ |
| 6. Connect it to the marketplace orchestrator | ❌ `audit.py` is standalone; `orchestrator.py` still uses the legacy crawl path |

---

## Part B — Implementation Plan (`implementation_plan.md`)

### B1. Rubric architecture (§2) — ✅ Done
Deterministic engines, evidence-backed findings, strict finding schemas,
stdlib + requests/bs4/lxml only (Playwright optional), universal standards
(RFC 9309 subset, Schema.org, Flesch-Kincaid via engagement skill).

### B2. Marketplace root & manifest (Phase 1) — ✅ Done
`marketplace.json` (4 skills, exactly one `entrypoint: true`),
`README.md`, `skills/` tree. **Deviation:** skill names differ from the
plan (`crawl-render-audit` / `freshness-corroboration` / `engagement-audit`
instead of `ai-discoverability-audit` / `knowledge-schema-audit` /
`engagement-retention-audit`). Functionally equivalent; rename or alias
before submission if the plan names are normative.

### B3. Specialized-skill scripts (Phases 2–4) — 🟡 Functionality done, names differ
`run_discoverability_check.py`, `run_schema_entity_check.py`,
`run_engagement_check.py` do not exist under those names; their checks are
covered by `audit.py` + `crawler/robots/structured_data/page_analysis.py` +
`consistency.py` + `engagement.py`.

### B4. Reference docs (Phases 2–4) — ❌ Missing as named files
`ai_bot_directory.md`, `llms_txt_spec.md`, `schema_types_guide.md`,
`citation_heuristics.md`, `engagement_rubric.md`, `trust_signals_guide.md`
do not exist. Mitigations in place: the AI-bot directory lives as code in
`ai_robots.AI_BOTS`; generic severity guidance lives in each skill's
`references/checks.md`. **Genuine gap: no `/llms.txt` check exists anywhere**
(plan §4.2 requires it).

### B5. Entrypoint skill (Phase 5) — 🟡 Partial
`SKILL.md` ✅ · `orchestrator.py` ✅ (named `orchestrator.py`, not
`orchestrate_audit.py` — trivial) · scoring/dedup/normalization ✅ ·
`report_formatter.py` ❌ (formatting inline) ·
`references/audit_schema.json` ❌ (no formal JSON-Schema file; only
hand-built-dict tests) · `references/severity_matrix.md` ❌ (logic inline).

### B6. Test suite, docs & packaging (Phase 6) — 🟡 Partial
Existing: `test_basic_checks.py`, `test_report_schema.py`,
`test_finding_normalization.py` + new `test_crawl_render_rules.py`,
`test_crawl_render_runtime.py` (71/71 ✅). Missing per plan:
`test_marketplace_manifest.py`, `test_skills_spec.py` (frontmatter
compliance), `test_synthetic_sites.py` + `mock_data/` fixtures, and the
ZIP packager script (+ <1 MB check).

### B7. Verification plan (§8) — 🟡 Partial
Deterministic-execution-against-fixtures ❌ (no fixtures); schema-conformance
against `audit_schema.json` ❌ (no schema file); manifest/entrypoint test ❌;
`<3 s per site` benchmark 🟡 (raw-only 0.6–2.2 s measured; rendered +~10 s,
which exceeds 3 s — budget needs re-baselining for the render path).

---

## Summary scorecard

| Area | Verdict |
|---|---|
| Research: signals, rules, counterexamples, flow, contract | ✅ Done |
| Research next steps | 🟡 4/6 (fresh-site fact validation + orchestrator wiring remain) |
| Plan: marketplace, orchestrator, skills behavior | ✅ Done (with skill-name deviation) |
| Plan: named reference docs, `/llms.txt`, schema file, fixture tests, packager | ❌ Must still do for full plan compliance |

### Recommended remaining work (priority order)
1. **Wire `audit.py` into `orchestrator.py`** (research step 6) — single-page
   deep-trace alongside the multi-page crawl.
2. **Add `/llms.txt` presence/format check** (plan §4.2; info-grade only, per
   research observation-first principle).
3. **Add `test_synthetic_sites.py` + `mock_data/` fixtures** (poor + optimized
   pages) and run the orchestrator against them.
4. **Add `audit_schema.json` + conformance test**, `test_marketplace_manifest.py`,
   `test_skills_spec.py`, and the ZIP packager.
5. **Write the six missing `references/*.md` files** (or formally adopt
   `checks.md` + in-code directory as their replacement).
6. **Validate target facts on 3–4 fresh live pages** (e-commerce, docs, banking,
   publisher) and re-baseline the runtime budget for the render path.
