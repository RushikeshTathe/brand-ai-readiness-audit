# Brand AI Readiness Audit

A portable Agent Skill Marketplace that audits websites for AI discoverability and on-site engagement problems.

## Overview

This tool accepts a public website URL/domain and inspects it for:

1. **AI Discoverability Problems** - Can machines find and understand your content?
2. **On-site Engagement Problems** - Can visitors quickly understand and act?

The marketplace is **read-only** - it never modifies the target website.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
python skills/audit-orchestrator/scripts/orchestrator.py https://example.com
```

Options:
- `--max-pages N`: Maximum pages to crawl (default: 20)
- `--max-depth N`: Maximum crawl depth (default: 2)
- `--timeout N`: Request timeout in seconds (default: 10)
- `--delay N`: Delay between requests in seconds (default: 1.0)
- `--output PATH`: Output file path

### Python API

```python
from skills.audit_orchestrator.scripts.orchestrator import run_audit

report = run_audit("https://example.com")
```

## Architecture

```
URL
 ↓
Crawl/inspection
 ↓
Shared audit context
 ↓
Specialized skills
 ↓
Findings
 ↓
Orchestrator
 ↓
Final report
```

### Skills

1. **audit-orchestrator** (entrypoint) - Coordinates all skills and produces the final report
2. **crawl-render-audit** - Inspects HTTP accessibility, robots.txt, sitemaps, HTML, and structured data
3. **freshness-corroboration** - Detects inconsistencies and outdated content
4. **engagement-audit** - Evaluates orientation, navigation, and calls-to-action

## Output

The audit produces a structured JSON report:

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
  "recommendations": []
}
```

## Findings

Each finding includes:
- **id**: Unique identifier
- **skill**: Which skill detected it
- **category**: Category of issue
- **severity**: critical, high, medium, low, or info
- **title**: Brief description
- **description**: Detailed explanation
- **evidence**: Concrete evidence
- **location**: Where it was found
- **recommendation**: How to fix it

## Testing

```bash
pytest tests/
```

## Configuration

Default settings are conservative:
- Max 20 pages
- Max depth 2
- 1 second delay between requests
- 10 second timeout

These can be configured via command line or API.

## License

Adobe University Hackathon 2026
