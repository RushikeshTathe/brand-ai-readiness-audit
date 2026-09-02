"""
Robots.txt analysis module.
Checks availability, directives, and potential issues.
"""

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import Dict, List, Optional


def fetch_robots_txt(base_url: str, user_agent: str = "BrandAuditBot/1.0") -> Dict:
    """
    Fetch and parse robots.txt.
    
    Args:
        base_url: Base URL of the website
        user_agent: User agent to check rules for
        
    Returns:
        Dictionary with robots.txt information
    """
    robots_url = urljoin(base_url, '/robots.txt')
    
    result = {
        'available': False,
        'url': robots_url,
        'content': None,
        'allows': [],
        'disallows': [],
        'sitemap_url': None,
        'crawl_delay': None,
        'error': None
    }
    
    try:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.read()
        
        result['available'] = True
        result['parser'] = parser
        
        # Try to get raw content for analysis
        try:
            import requests
            response = requests.get(robots_url, timeout=10, 
                                  headers={'User-Agent': user_agent})
            if response.status_code == 200:
                result['content'] = response.text
                result['raw_lines'] = response.text.splitlines()
        except Exception:
            pass
        
        # Extract sitemap URL from robots.txt
        if result.get('raw_lines'):
            for line in result['raw_lines']:
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    result['sitemap_url'] = sitemap_url
                    break
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def analyze_robots_directives(robots_data: Dict, important_paths: List[str] = None) -> List[Dict]:
    """
    Analyze robots.txt directives for potential issues.
    
    Args:
        robots_data: robots.txt data from fetch_robots_txt
        important_paths: List of important paths to check
        
    Returns:
        List of findings
    """
    findings = []
    
    if not robots_data.get('available'):
        findings.append({
            'id': 'robots-001',
            'skill': 'crawl-render-audit',
            'category': 'robots',
            'severity': 'medium',
            'title': 'robots.txt not available',
            'description': f"Could not access robots.txt at {robots_data.get('url')}",
            'evidence': robots_data.get('error', 'Unknown error'),
            'location': robots_data.get('url'),
            'recommendation': 'Ensure robots.txt is accessible at the standard location'
        })
        return findings
    
    # Check if important paths are blocked
    if important_paths and 'parser' in robots_data:
        parser = robots_data['parser']
        for path in important_paths:
            full_url = urljoin(robots_data['url'].replace('/robots.txt', '/'), path)
            if not parser.can_fetch(robots_data.get('user_agent', '*'), full_url):
                findings.append({
                    'id': 'robots-002',
                    'skill': 'crawl-render-audit',
                    'category': 'robots',
                    'severity': 'high',
                    'title': f'Important path blocked: {path}',
                    'description': f"robots.txt blocks access to important path: {path}",
                    'evidence': f"Path {path} is disallowed in robots.txt",
                    'location': full_url,
                    'recommendation': 'Review robots.txt to ensure important content is accessible'
                })
    
    # Check for aggressive crawl-delay
    if robots_data.get('crawl_delay'):
        delay = float(robots_data['crawl_delay'])
        if delay > 10:
            findings.append({
                'id': 'robots-003',
                'skill': 'crawl-render-audit',
                'category': 'robots',
                'severity': 'low',
                'title': 'Aggressive crawl-delay',
                'description': f"robots.txt specifies a crawl-delay of {delay} seconds",
                'evidence': f"Crawl-delay: {delay}",
                'location': robots_data.get('url'),
                'recommendation': 'Consider reducing crawl-delay for better accessibility'
            })
    
    # Check if sitemap is referenced
    if not robots_data.get('sitemap_url'):
        findings.append({
            'id': 'robots-004',
            'skill': 'crawl-render-audit',
            'category': 'robots',
            'severity': 'low',
            'title': 'No sitemap reference in robots.txt',
            'description': 'robots.txt does not reference a sitemap',
            'evidence': 'No Sitemap directive found',
            'location': robots_data.get('url'),
            'recommendation': 'Add Sitemap directive to help crawlers discover content'
        })
    
    return findings


def check_robots(context: Dict) -> Dict:
    """
    Check robots.txt and update audit context.
    
    Args:
        context: Audit context dictionary
        
    Returns:
        Updated audit context
    """
    base_url = f"https://{context['site']['domain']}"
    
    # Fetch robots.txt
    robots_data = fetch_robots_txt(base_url)
    context['robots'] = {
        'available': robots_data.get('available', False),
        'content': robots_data.get('content'),
        'allows': robots_data.get('allows', []),
        'disallows': robots_data.get('disallows', []),
        'sitemap_url': robots_data.get('sitemap_url'),
        'crawl_delay': robots_data.get('crawl_delay'),
        'error': robots_data.get('error'),
        'raw_lines': robots_data.get('raw_lines', [])
    }
    
    # Store parser for use by crawler
    if 'parser' in robots_data:
        context['robots']['parser'] = robots_data['parser']
    
    # Analyze directives
    important_paths = ['/', '/about', '/contact', '/products', '/services']
    context['robots']['findings'] = analyze_robots_directives(robots_data, important_paths)
    
    return context
