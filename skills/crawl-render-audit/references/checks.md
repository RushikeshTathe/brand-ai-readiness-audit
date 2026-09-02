# Crawl / Render Audit Checks

## 1. HTTP Accessibility

### Checks
- HTTP status code validation
- Redirect chain analysis (301, 302, 307, 308)
- Content-Type header verification
- Request timeout handling
- SSL/TLS certificate validation

### Severity Rules
- **Critical**: 5xx errors, SSL failures
- **High**: 4xx errors (except 404 for missing pages)
- **Medium**: Excessive redirects (>3)
- **Low**: Missing Content-Type
- **Info**: Successful redirects

## 2. robots.txt

### Checks
- robots.txt availability
- User-agent directives
- Disallow rules for important paths
- Sitemap directive presence
- Crawl-delay settings

### Severity Rules
- **Critical**: Important content blocked by robots.txt
- **High**: Homepage or key pages blocked
- **Medium**: Sitemap not referenced
- **Low**: Aggressive crawl-delay
- **Info**: robots.txt present and valid

## 3. Sitemap

### Checks
- Sitemap.xml discovery (standard location, robots.txt reference)
- Sitemap accessibility (HTTP 200)
- XML validity
- URL count and freshness
- Last modification dates

### Severity Rules
- **High**: Sitemap exists but inaccessible
- **Medium**: Sitemap missing or invalid XML
- **Low**: Sitemap outdated (>30 days)
- **Info**: Sitemap valid and accessible

## 4. Conservative Crawling

### Configuration
- Same-domain only
- Configurable max_pages (default: 20)
- Configurable max_depth (default: 2)
- Request timeout (default: 10s)
- Rate limiting (default: 1s delay)
- URL normalization
- Duplicate removal
- Tracking parameter handling
- Loop prevention

### Behavior
- Respect robots.txt
- Only use GET requests
- No form submissions
- No authenticated areas
- Handle errors gracefully

## 5. HTML Inspection

### Checks
- Title tag presence and length
- Meta description presence and length
- Canonical URL
- H1/H2 heading structure
- Body text content
- Internal link analysis
- Image alt attributes
- OpenGraph tags
- Twitter Card tags
- Viewport meta tag

### Severity Rules
- **Critical**: Missing title, no H1
- **High**: Missing meta description, broken canonical
- **Medium**: Missing alt attributes, poor heading structure
- **Low**: Long title (>60 chars), long meta description (>160 chars)
- **Info**: Well-structured HTML

## 6. Machine-readable Content

### Checks
- JavaScript-rendered content detection
- Canvas element presence
- Hidden content (display:none, visibility:hidden)
- Lazy-loaded images
- Dynamic content markers

### Severity Rules
- **High**: Critical content only in JavaScript
- **Medium**: Content in canvas elements
- **Low**: Hidden navigation elements
- **Info**: Content available in HTML

## 7. Structured Data

### Checks
- JSON-LD detection
- Schema.org type identification
- Required properties validation
- Nested schema detection
- SameAs links

### Severity Rules
- **High**: Invalid JSON-LD syntax
- **Medium**: Missing required properties
- **Low**: Deprecated schema types
- **Info**: Valid structured data

## 8. Broken Links

### Checks
- Internal link validation
- Status code verification
- Redirect chain following
- Timeout handling
- Error classification

### Severity Rules
- **Critical**: 410 Gone for important pages
- **High**: Persistent 404 errors
- **Medium**: 5xx errors
- **Low**: Redirects to different content
- **Info**: Temporary failures
