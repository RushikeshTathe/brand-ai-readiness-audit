# Crawl / Render Audit Skill

## Purpose
Determines whether important website information can be reached and understood by machines.

## Capabilities
1. **HTTP Accessibility** - Status codes, redirects, content types, request failures
2. **robots.txt Analysis** - Availability, crawl directives, blocked paths
3. **Sitemap Discovery** - Discovery, accessibility, validity, listed URLs
4. **Conservative Crawling** - Same-domain, configurable depth/pages, rate limiting
5. **HTML Inspection** - Title, meta, headings, links, images, structured data
6. **Machine-readable Content** - JavaScript rendering, hidden content detection
7. **Structured Data** - Schema.org/JSON-LD detection and validation
8. **Broken Links** - Internal link validation with proper error classification

## Input
- `url`: Target website URL
- `audit_context`: Shared audit context object

## Output
- Populated audit context with crawl data
- List of findings with severity levels

## Usage
```python
from scripts.crawler import crawl_website
from scripts.robots import check_robots
from scripts.structured_data import analyze_structured_data
from scripts.page_analysis import analyze_pages

# Crawl website
context = crawl_website(url, max_pages=20, max_depth=2)

# Check robots.txt
context = check_robots(context)

# Analyze structured data
context = analyze_structured_data(context)

# Analyze pages
findings = analyze_pages(context)
```

## Findings Format
```json
{
  "id": "crawl-001",
  "skill": "crawl-render-audit",
  "category": "accessibility",
  "severity": "critical|high|medium|low|info",
  "title": "Finding title",
  "description": "Detailed description",
  "evidence": "Concrete evidence",
  "location": "URL or path",
  "recommendation": "Specific fix"
}
```

## Configuration
- `max_pages`: Maximum pages to crawl (default: 20)
- `max_depth`: Maximum crawl depth (default: 2)
- `timeout`: Request timeout in seconds (default: 10)
- `delay`: Delay between requests in seconds (default: 1)
- `user_agent`: User agent string (default: "BrandAuditBot/1.0")
