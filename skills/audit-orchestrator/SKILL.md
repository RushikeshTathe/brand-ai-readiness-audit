---
name: audit-orchestrator
description: Entrypoint skill for the brand AI-readiness audit marketplace. Accepts a website URL, invokes the crawl-render-audit, freshness-corroboration, and engagement-audit skills, then normalizes, deduplicates, and composes their findings into the single required audit report (site, audited_at, summary, findings). Use this skill when asked to audit a website for AI discoverability or on-site engagement problems.
license: MIT
---

# Audit Orchestrator Skill

## Purpose
The ONLY entrypoint for the Agent Skill Marketplace. Accepts a URL/domain and orchestrates all specialized audit skills to produce a structured JSON report.

## Responsibilities
1. Accept and validate URL/domain
2. Create audit context
3. Run crawl/render audit
4. Run freshness/corroboration audit
5. Run engagement audit
6. Collect and normalize findings
7. Deduplicate overlapping findings
8. Validate severity levels
9. Calculate priority scores
10. Add proactive recommendations
11. Produce final JSON report

## Input
- `url`: Target website URL or domain

## Output
- Structured JSON audit report

## Usage
```python
from scripts.orchestrator import run_audit

# Run complete audit
report = run_audit("https://example.com")

# Or with custom configuration
report = run_audit(
    url="https://example.com",
    max_pages=30,
    max_depth=3,
    timeout=15
)
```

## Report Structure
```json
{
  "meta": {
    "version": "1.0.0",
    "timestamp": "ISO-8601",
    "duration_seconds": 0,
    "target_url": "https://example.com",
    "pages_crawled": 0
  },
  "summary": {
    "total_findings": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0,
    "overall_score": 0,
    "top_issues": []
  },
  "findings": [],
  "recommendations": [],
  "audit_context": {}
}
```

## Configuration
- `max_pages`: Maximum pages to crawl (default: 20)
- `max_depth`: Maximum crawl depth (default: 2)
- `timeout`: Request timeout in seconds (default: 10)
- `delay`: Delay between requests (default: 1.0)
- `user_agent`: User agent string (default: "BrandAuditBot/1.0")
