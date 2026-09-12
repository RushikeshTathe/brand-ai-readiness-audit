# Adobe University Hackathon 2026 — Agent Skill Marketplace

## Research, Validation & Implementation Notes

This README records the research and validation completed before implementing the website-audit skills.

### Goal

The audit should not treat JavaScript, JSON-LD, robots.txt, or sitemaps as automatically good or bad. The goal is to detect measurable conditions that can explain why important website information may be difficult for automated retrieval systems to access or understand.

## 1. Key Learning

The strongest lesson from the 10-site sample is:

> **Target facts matter more than generic page metrics.**

Raw word count and rendered word count alone are weak signals. A large amount of text added after JavaScript can simply be navigation, widgets, footers, or other UI.

The implementation therefore follows a layered diagnostic approach:

1. Can the automated request reach the page?
2. Does crawler policy permit access?
3. Are important target facts present in the initial HTML?
4. Does raw JSON-LD provide a fallback?
5. Does browser rendering reveal facts that were unavailable before rendering?

## 2. Ten-Site Validation Dataset

| Site | Category |
|---|---|
| Wikipedia | Reference baseline |
| GitHub Docs | Developer documentation |
| Stripe Docs | Technical / fintech documentation |
| Zapier | B2B SaaS |
| Nordstrom | E-commerce |
| Healthline | Healthcare publisher |
| Coursera | EdTech |
| Prashant Corner | Local SMB catalog |
| Saraswat Bank | Regional banking |
| Dot & Key | D2C skincare / Shopify |

## 3. Signals Selected

### Strong signals

- WAF / HTTP 403 / 429 / bot challenge
- AI bot restrictions in `robots.txt`
- Important target facts in raw HTML
- Important target facts missing from raw HTML
- Important target facts available in raw JSON-LD

### Warning only

- Raw-vs-rendered word expansion

### Rejected as standalone checks

- Raw word count
- Rendered word count
- Sitemap existence
- Sitemap URL count
- Presence of a `robots.txt` file

## 4. Important JavaScript Rule

**JavaScript present ≠ JavaScript dependency.**

A page can use JavaScript for menus, analytics, tabs, or interactions while still delivering all important facts in raw HTML.

We only want to flag a meaningful dependency when:

```text
Important fact
    ↓
Missing from raw HTML
    ↓
Missing from raw JSON-LD
    ↓
Appears after browser rendering
```

## 5. Counterexamples

### Dot & Key

Large raw-to-rendered expansion was observed, but product price was available in JSON-LD.

**Lesson:** large DOM expansion alone must not produce a failure.

### Healthline

Strong raw HTML was observed, but an AI crawler policy restriction was present.

**Lesson:** HTML accessibility and crawler governance are separate layers.

### Nordstrom

Large raw-to-rendered expansion was associated with an HTTP 403/WAF challenge.

**Lesson:** check network access before diagnosing JavaScript dependency.

### Saraswat Bank

Rendered text increased, but the key interest-rate information was already present in a static HTML table.

**Lesson:** important fact availability is more useful than total word count.

## 6. Provisional Rules

1. **Edge Access Blockade** — 403/429 or WAF challenge prevents normal automated retrieval.
2. **Crawler Policy Restriction** — relevant AI user-agent is disallowed on public target content.
3. **Client-Side Rendering Fact Dependency** — important facts exist only after rendering and are absent from raw HTML and raw JSON-LD.
4. **Structured Data Fallback** — important facts are available in raw JSON-LD even when normal markup is dynamic.
5. **Word Expansion Screening** — >30% and >100 words is only a warning that triggers deeper inspection.

## 7. Finding Contract

Every skill should return a common finding format:

```json
{
  "id": "ACCESS-001",
  "title": "Important product facts are JS-dependent",
  "severity": "high",
  "evidence": {},
  "suggested_action": "...",
  "mechanism": "...",
  "priority": 1,
  "confidence": "high"
}
```

The official report requires `id`, `title`, `severity`, `evidence`, and `suggested_action`; the additional fields help the orchestrator explain mechanism, confidence, and remediation order.

## 8. Implementation Flow

```text
URL
 ↓
Direct HTTP request
 ↓
WAF / HTTP gate
 ↓
robots.txt policy
 ↓
Raw HTML extraction
 ↓
Target-fact check
 ↓
JSON-LD extraction
 ↓
Browser rendering
 ↓
Raw vs rendered comparison
 ↓
Target-fact comparison
 ↓
Finding generation
```

## 9. Research-to-Code Principle

The implementation should report **observations first and conclusions second**.

Do not automatically report:

- "Uses JavaScript"
- "Has a sitemap"
- "Has robots.txt"
- "Raw word count is low"
- "DOM expanded by X%"

as failures.

A finding needs concrete evidence and a defensible mechanism.

## 10. Explicit Non-Claims

We are **not** claiming:

- 30% + 100 words is a universal threshold.
- SPAs are invisible to every AI system.
- JSON-LD solves every AI discoverability problem.
- E-commerce platforms are inherently bad for AI retrieval.
- `robots.txt` permission guarantees indexing or retrieval.

## 11. Next Steps

1. Test the checks on 3–4 fresh websites.
2. Measure Playwright/browser-render runtime.
3. Validate target-fact comparison on different page types.
4. Re-test the counterexamples.
5. Freeze the `crawl-render-audit/SKILL.md`.
6. Connect it to the marketplace orchestrator.

## Files

- `Adobe_R3_Audit_Implementation_Workbook.xlsx` — implementation/research workbook.
- `Adobe_R3_Audit_Research_README.docx` — formatted research documentation.
