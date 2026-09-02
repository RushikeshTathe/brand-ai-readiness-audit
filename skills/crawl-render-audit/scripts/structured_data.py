"""
Structured data analysis module.
Detects and validates Schema.org/JSON-LD structured data.
"""

import json
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


# Common Schema.org types and their typical use cases
SCHEMA_TYPES = {
    'Organization': 'Company/brand information',
    'LocalBusiness': 'Physical business location',
    'Product': 'Product information',
    'Offer': 'Product pricing/availability',
    'Article': 'News/blog articles',
    'BlogPosting': 'Blog posts',
    'BreadcrumbList': 'Navigation hierarchy',
    'WebSite': 'Website metadata',
    'FAQPage': 'Frequently asked questions',
    'HowTo': 'Instructional content',
    'Event': 'Events',
    'Recipe': 'Recipes',
    'Review': 'Reviews',
    'AggregateRating': 'Ratings summary',
    'Person': 'Individual information',
    'Place': 'Location information',
    'Event': 'Event details'
}


def extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract all JSON-LD structured data from a page.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of JSON-LD objects
    """
    json_ld_data = []
    
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            content = script.string
            if content:
                data = json.loads(content)
                
                # Handle both single objects and arrays
                if isinstance(data, list):
                    json_ld_data.extend(data)
                else:
                    json_ld_data.append(data)
                    
        except json.JSONDecodeError as e:
            # Invalid JSON-LD
            json_ld_data.append({
                '_error': True,
                '_error_message': str(e),
                '_raw': content[:200] if content else ''
            })
    
    return json_ld_data


def extract_microdata(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract Microdata structured data from a page.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of Microdata items
    """
    microdata_items = []
    
    for item in soup.find_all(attrs={'itemscope': True}):
        item_type = item.get('itemtype', '')
        if item_type:
            microdata_items.append({
                'type': item_type,
                'tag': item.name
            })
    
    return microdata_items


def validate_json_ld(data: Dict) -> List[str]:
    """
    Validate a JSON-LD object for common issues.
    
    Args:
        data: JSON-LD object
        
    Returns:
        List of validation issues
    """
    issues = []
    
    if not isinstance(data, dict):
        return ['Invalid JSON-LD structure']
    
    # Check for error flag
    if data.get('_error'):
        issues.append(f"Invalid JSON-LD syntax: {data.get('_error_message', 'Unknown error')}")
        return issues
    
    # Check for @context
    if '@context' not in data:
        issues.append('Missing @context property')
    elif not data['@context'].startswith('https://schema.org'):
        issues.append('Non-standard @context')
    
    # Check for @type
    if '@type' not in data:
        issues.append('Missing @type property')
    
    return issues


def analyze_schema_type(data: Dict, page_context: Dict = None) -> Dict:
    """
    Analyze a specific schema type for completeness and relevance.
    
    Args:
        data: JSON-LD object
        page_context: Optional page context for relevance checking
        
    Returns:
        Analysis results
    """
    schema_type = data.get('@type', 'Unknown')
    result = {
        'type': schema_type,
        'issues': [],
        'recommendations': [],
        'completeness': 0
    }
    
    # Common required properties by type
    required_props = {
        'Organization': ['name', 'url'],
        'Product': ['name', 'description'],
        'Article': ['headline', 'author', 'datePublished'],
        'BreadcrumbList': ['itemListElement'],
        'WebSite': ['name', 'url'],
        'FAQPage': ['mainEntity'],
        'LocalBusiness': ['name', 'address'],
        'Offer': ['price', 'priceCurrency', 'availability']
    }
    
    # Check required properties
    if schema_type in required_props:
        for prop in required_props[schema_type]:
            if prop not in data:
                result['issues'].append(f"Missing required property: {prop}")
                result['recommendations'].append(f"Add {prop} property")
    
    # Calculate completeness
    if schema_type in required_props:
        total = len(required_props[schema_type])
        found = sum(1 for prop in required_props[schema_type] if prop in data)
        result['completeness'] = int((found / total) * 100) if total > 0 else 0
    
    return result


def detect_structured_data_issues(structured_data: List[Dict], page_url: str) -> List[Dict]:
    """
    Detect issues with structured data.
    
    Args:
        structured_data: List of JSON-LD objects
        page_url: URL of the page being analyzed
        
    Returns:
        List of findings
    """
    findings = []
    
    if not structured_data:
        findings.append({
            'id': 'schema-001',
            'skill': 'crawl-render-audit',
            'category': 'structured_data',
            'severity': 'low',
            'title': 'No structured data found',
            'description': 'Page does not contain JSON-LD or Microdata',
            'evidence': 'No structured data detected',
            'location': page_url,
            'recommendation': 'Consider adding relevant structured data'
        })
        return findings
    
    # Analyze each JSON-LD object
    for i, data in enumerate(structured_data):
        issues = validate_json_ld(data)
        
        if issues:
            severity = 'high' if any('Invalid' in issue for issue in issues) else 'medium'
            findings.append({
                'id': f'schema-{i+1:03d}',
                'skill': 'crawl-render-audit',
                'category': 'structured_data',
                'severity': severity,
                'title': f'Structured data issue: {data.get("@type", "Unknown")}',
                'description': '; '.join(issues),
                'evidence': json.dumps(data, indent=2)[:500],
                'location': page_url,
                'recommendation': 'Fix structured data syntax and required properties'
            })
        else:
            # Analyze completeness
            analysis = analyze_schema_type(data)
            if analysis['issues']:
                findings.append({
                    'id': f'schema-{i+1:03d}',
                    'skill': 'crawl-render-audit',
                    'category': 'structured_data',
                    'severity': 'medium',
                    'title': f'Incomplete structured data: {analysis["type"]}',
                    'description': '; '.join(analysis['issues']),
                    'evidence': json.dumps(data, indent=2)[:500],
                    'location': page_url,
                    'recommendation': '; '.join(analysis['recommendations'])
                })
    
    return findings


def analyze_structured_data(context: Dict) -> Dict:
    """
    Analyze structured data across all crawled pages.
    
    Args:
        context: Audit context with page data
        
    Returns:
        Updated context with structured data analysis
    """
    all_structured_data = []
    all_findings = []
    
    for page in context.get('pages', []):
        html = page.get('html', '')
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract JSON-LD
        json_ld = extract_json_ld(soup)
        if json_ld:
            all_structured_data.extend(json_ld)
            
            # Store in page data
            page['structured_data'] = json_ld
            
            # Analyze for issues
            page_findings = detect_structured_data_issues(json_ld, page['url'])
            all_findings.extend(page_findings)
    
    context['structured_data'] = all_structured_data
    context['structured_data_findings'] = all_findings
    
    return context
