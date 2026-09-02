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

## How this tool browses the network

This is the key thing your team should understand: **the tool does the browsing, not the person running it.** When you (or your CI pipeline) run the script, the requests go out from *your* machine to the website you're auditing. This is read-only network access — the tool never writes to or changes the target site.

### What does the network layer actually do?

1. **Sends HTTP GET requests.** The crawler (`crawler.py`) uses the Python `requests` library to fetch pages. A GET request is exactly what your browser does when you type a URL — it asks the server for a page and receives the HTML back. The tool never uses POST/PUT/DELETE, never submits forms, and never touches authenticated (logged-in) areas.

2. **Identifies itself.** Every request includes a `User-Agent` header: `"BrandAuditBot/1.0"`. This tells the website "I am an automated auditor" so site operators can distinguish it from a human visitor or from malicious bots.

3. **Downloads then parses.** Once it gets the raw HTML, it parses it with `BeautifulSoup` to read things like the title, meta descriptions, headings, links, images, and structured data — without ever interacting with the page's JavaScript.

4. **Follows internal links.** It reads the links on each page and queues up the ones pointing to the *same domain*, so it can visit a few more relevant pages. By default it visits up to 20 pages, 2 levels deep.

### How it stays safe and polite

| Rule | Why |
|------|-----|
| **Read-only (GET only)** | It can never modify the target website |
| **Respects `robots.txt`** | It reads the site's robots.txt first and will not access any path the site blocks |
| **Same-domain only** | It never wanders to external sites — it only follows links within the domain being audited |
| **Delay between requests** | A built-in delay (default 1s) throttles it so it doesn't hammer the server |
| **Configurable limits** | `max_pages`, `max_depth`, `timeout`, and `delay` caps keep it conservative |
| **Loop prevention** | Tracks already-visited URLs and drops duplicates (fragments, tracking params like `utm_*`, `index.html`) so it doesn't crawl in circles |

### Where the network access actually happens

The browsing happens **on your machine at runtime** — it is *not* done by an external service or by an AI agent. If you run the orchestrator locally, your machine makes the requests. If you run it in CI/cloud, that machine makes the requests. The only external thing that ever happens is the standard HTTP request sent to, and the response received from, the audited website.

## Architecture

```
URL
 ↓
Validate & normalize URL
 ↓
Crawl/inspection (read-only HTTP)
 ↓
Shared audit context
 ↓
Specialized skills
 ↓
Findings
 ↓
Orchestrator
 ↓
Final JSON report
```

### Shared audit context

The most important design decision: all three skills share **one** crawl result instead of each skill re-downloading the website. The orchestrator crawls once, then builds a shared `audit_context` that every skill reads from. This keeps the network load low (one crawl, multiple analyses) and guarantees all skills see the same data.

```json
{
  "site": { "input_url", "normalized_url", "final_url", "domain" },
  "robots": { ... },
  "sitemap": { ... },
  "pages": [ ... ],
  "links": [ ... ],
  "structured_data": [ ... ],
  "metadata": [ ... ]
}
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

Default settings are conservative and directly control how much the tool browses the network:

| Setting | Default | Controls |
|---------|---------|----------|
| `max_pages` | 20 | Max pages fetched over the network |
| `max_depth` | 2 | How deep it follows internal links |
| `delay` | 1.0s | Pause between requests (rate limiting) |
| `timeout` | 10s | How long to wait for each response |
| `user_agent` | `BrandAuditBot/1.0` | Identifier sent with each request |

These can be configured via command-line flags or the Python API, and they keep the browsing conservative so the audited site is never overwhelmed.

## License

Adobe University Hackathon 2026
