# 🔍 Brand AI Readiness Audit — Agent Skill Marketplace

![Adobe Hackathon](https://img.shields.io/badge/ADOBE_HACKATHON-2026-lightgrey)
![Round 3](https://img.shields.io/badge/ROUND_3-SUBMISSION-red)
![Python](https://img.shields.io/badge/PYTHON-3.10+-blue)
![Format](https://img.shields.io/badge/FORMAT-agentskills.io-green)
![Safety](https://img.shields.io/badge/READ--ONLY-SAFE-blue)
![License](https://img.shields.io/badge/LICENSE-MIT-yellow)

---

## 📌 Executive Summary

AI assistants (ChatGPT, Perplexity, Claude, Google AI Overviews) increasingly answer questions by fetching, reading, and citing pages directly — not by matching keywords. When a page's key facts are locked behind client-side JavaScript, missing from structured data, blocked by an AI-specific `robots.txt` rule, or contradicted across the web, that brand becomes invisible or misrepresented to the systems now mediating discovery.

Existing tools cover only pieces of this: SEO auditors check tags but don't understand LLM rendering; AI-visibility trackers show *where* a brand is missing but not *why*; UX tools measure behavior but not machine readability. None connect an off-site discoverability failure to its on-site root cause with actual evidence.

**Brand AI Readiness Audit** is an Agent Skill Marketplace, in the [agentskills.io](https://agentskills.io) format, that audits any public website — one it has never seen — for both halves of the problem:

1. **AI Discoverability** — can an automated crawler reach the page, and can it extract the actual facts (not just detect that a page exists)?
2. **On-site Engagement** — once a visitor lands, can they orient immediately and find a next action?

Every finding carries concrete evidence and a stated mechanism (*why* this affects retrieval or engagement), not a generic score.

---

## 🏗️ Architecture

```
                              URL
                               │
                               ▼
                  ┌────────────────────────┐
                  │   audit-orchestrator    │   ← entrypoint
                  │  (composes all skills)  │
                  └────────────┬────────────┘
                               │
              ┌────────────────┼────────────────────┐
              ▼                ▼                     ▼
   ┌─────────────────┐ ┌───────────────────┐ ┌──────────────────┐
   │ crawl-render-    │ │ freshness-        │ │ engagement-audit │
   │ audit            │ │ corroboration     │ │                  │
   │                  │ │                   │ │                  │
   │ HTTP/edge access │ │ entity identity   │ │ first-screen     │
   │ robots.txt (AI   │ │ cross-page        │ │ orientation      │
   │  bot directives) │ │  consistency      │ │ navigation       │
   │ raw HTML facts   │ │ freshness signals │ │ call-to-action   │
   │ JSON-LD fallback │ │                   │ │  clarity         │
   │ rendered facts   │ │                   │ │                  │
   └────────┬─────────┘ └─────────┬─────────┘ └────────┬─────────┘
            └────────────────────┬┴────────────────────┘
                                  ▼
                normalize → deduplicate → severity summary
                                  │
                                  ▼
                  final report (site, audited_at,
                     summary, findings[])
```

`crawl-render-audit` runs first; its output (raw HTML, extracted text, JSON-LD facts, rendering result) is shared with the other two skills so the page is only fetched once.

| Skill | What it checks | Why it matters |
|---|---|---|
| **audit-orchestrator** *(entrypoint)* | Coordinates all skills, normalizes findings, emits the final report | Single point of composition — the only skill an agent needs to invoke |
| **crawl-render-audit** | HTTP/WAF access, AI-bot-specific `robots.txt` rules, raw HTML vs. JSON-LD vs. rendered fact comparison | Layer 1 of the problem: can a machine even reach and read the fact? |
| **freshness-corroboration** | Entity identity signals, cross-page consistency, stale-content detection | Layer 2: is the fact current, unambiguous, and internally consistent? |
| **engagement-audit** | First-screen orientation, navigation, CTA clarity | The other half of Round 3: does a visitor who *does* arrive stay? |

---

## ⚙️ Installation

```bash
pip install -r requirements.txt

# Optional — only needed for the JS-rendering check.
# This downloads the Chromium binary to Playwright's own cache;
# it is NOT part of this repo and should never be bundled into the submission zip.
playwright install chromium
```

If Chromium isn't installed, rendering is skipped gracefully — the pipeline falls back to raw-HTML + JSON-LD analysis rather than failing.

## ▶️ Usage

### Command line

```bash
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com
```

| Option | Description |
|---|---|
| `--output PATH` / `-o PATH` | Write the JSON report to a specific file (default: auto-named `audit_report_<domain>_<timestamp>.json`) |

### Python

```python
import sys, os
sys.path.insert(0, os.path.join("skills", "audit-orchestrator", "scripts"))
sys.path.insert(0, os.path.join("skills", "crawl-render-audit", "scripts"))
sys.path.insert(0, os.path.join("skills", "freshness-corroboration", "scripts"))
sys.path.insert(0, os.path.join("skills", "engagement-audit", "scripts"))

from orchestrator import run_audit

report = run_audit("https://example.com")
```

Skill folders use hyphens per the agentskills.io convention, so they aren't importable as a normal Python package path — each `scripts/` directory is added to `sys.path` directly, as shown above and in `demo_audit.py`.

---

## 📄 Output

Matches the required schema (`site`, `audited_at`, `summary`, `findings[]` with `id`/`title`/`severity`/`evidence`/`suggested_action`), plus extra fields for transparency:

```json
{
  "site": "https://example.com",
  "audited_at": "2026-09-13T09:05:06.05Z",
  "summary": {
    "total_findings": 10,
    "critical": 2,
    "high": 5,
    "medium": 0,
    "low": 3,
    "info": 0
  },
  "findings": [
    {
      "id": "ACCESS-001",
      "title": "Edge access blockade prevents automated retrieval",
      "severity": "critical",
      "evidence": { "status": 403, "kind": "http-block", "signals": ["..."] },
      "suggested_action": "Allow automated audit traffic or provide an accessible mirror...",
      "mechanism": "HTTP edge controls stop the retrieval chain before any content layer can be evaluated.",
      "priority": 1,
      "confidence": "high"
    }
  ],
  "meta": { "target_url": "https://example.com", "duration_seconds": 0.09 },
  "details": { "crawl_render": {}, "freshness": [], "engagement": [] }
}
```

`meta` and `details` are additive context; `summary` and every finding always carry the required fields.

---

## ✅ Testing

```bash
pytest tests/
```

70 tests, including regression cases against four real counterexamples that shaped the rules:

| Site | What it tests |
|---|---|
| Dot & Key | Large DOM expansion + price in JSON-LD → no false CSR failure |
| Healthline | Strong raw HTML + AI-bot `robots.txt` block → policy fires independently of HTML quality |
| Nordstrom | 403/WAF blockade → network access checked before diagnosing JS dependency |
| Saraswat Bank | Rendered growth, but fact already in a static HTML table → no false positive |

---

## 🔒 Safety & Scope

- **Read-only** — GET requests only; no login, no form submission, no state-changing action against any target site
- Respects `robots.txt`
- Rendering is timeboxed, sandboxed to a single page load, and skipped entirely under an access blockade
- No pretrained model weights bundled; no browser binaries in this repo (see Installation)

## 🚫 What we explicitly don't claim

- No universal threshold — the JS-expansion rule is a screening signal only, never a pass/fail verdict on its own
- SPAs are not assumed invisible to every AI system, nor is JSON-LD assumed to solve every discoverability gap
- `robots.txt` permission is not treated as a guarantee of indexing or retrieval

---

## Team Shastra Stack