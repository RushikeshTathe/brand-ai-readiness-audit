---
name: freshness-corroboration
description: Audits whether a website's key facts are current, internally consistent, and unambiguously tied to a single identifiable entity - detecting stale dates/claims, cross-page inconsistencies, and missing entity-identity signals. Use this skill to diagnose why AI assistants might cite outdated or confused information about a brand.
license: MIT
---

# Freshness / Corroboration Skill

## Purpose
Investigates whether important brand facts are consistent, unambiguous, fresh, and well-represented.

## Capabilities
1. **Entity Identity** - Extract and validate brand identity information
2. **Cross-page Consistency** - Compare facts across crawled pages
3. **Freshness Signals** - Detect outdated content and stale information
4. **External Corroboration** - Architecture ready for future external validation

## Input
- `audit_context`: Shared audit context from crawl-render-audit
- `findings`: Existing findings from other skills

## Output
- Entity identity analysis
- Consistency findings
- Freshness findings
- Updated findings list

## Usage
```python
from scripts.consistency import analyze_freshness_consistency

# Analyze freshness and consistency
updated_context, findings = analyze_freshness_consistency(context, existing_findings)
```

## Findings Format
```json
{
  "id": "fresh-001",
  "skill": "freshness-corroboration",
  "category": "consistency|freshness|identity",
  "severity": "critical|high|medium|low|info",
  "title": "Finding title",
  "description": "Detailed description",
  "evidence": "Concrete evidence",
  "location": "URL or path",
  "recommendation": "Specific fix"
}
```

## Key Principles
- Normalize before comparing (whitespace, capitalization, punctuation)
- Only report meaningful conflicts, not superficial differences
- Do not assume old content is automatically wrong
- Report evidence suggesting potential staleness
- Do not fabricate external evidence
