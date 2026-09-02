"""
Page analysis module.
Analyzes HTML content for accessibility, SEO, and engagement issues.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def analyze_html_structure(soup: BeautifulSoup, url: str) -> Dict:
    """
    Analyze HTML structure and extract key elements.
    
    Args:
        soup: BeautifulSoup object
        url: Page URL
        
    Returns:
        Dictionary with HTML analysis
    """
    analysis = {
        'title': None,
        'title_length': 0,
        'meta_description': None,
        'meta_description_length': 0,
        'canonical': None,
        'h1_tags': [],
        'h2_tags': [],
        'h1_count': 0,
        'h2_count': 0,
        'images': [],
        'images_without_alt': 0,
        'links': [],
        'internal_links': 0,
        'external_links': 0,
        'broken_links': [],
        'open_graph': {},
        'twitter_cards': {},
        'viewport': None,
        'charset': None,
        'language': None
    }
    
    # Title
    if soup.title:
        analysis['title'] = soup.title.string.strip() if soup.title.string else ''
        analysis['title_length'] = len(analysis['title'])
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        analysis['meta_description'] = meta_desc.get('content', '').strip()
        analysis['meta_description_length'] = len(analysis['meta_description'])
    
    # Canonical URL
    canonical = soup.find('link', rel='canonical')
    if canonical:
        analysis['canonical'] = canonical.get('href')
    
    # Headings
    analysis['h1_tags'] = [h1.get_text(strip=True) for h1 in soup.find_all('h1')]
    analysis['h1_count'] = len(analysis['h1_tags'])
    analysis['h2_tags'] = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
    analysis['h2_count'] = len(analysis['h2_tags'])
    
    # Images
    images = soup.find_all('img')
    analysis['images'] = []
    analysis['images_without_alt'] = 0
    for img in images:
        src = img.get('src', '')
        alt = img.get('alt')
        if not alt or not alt.strip():
            analysis['images_without_alt'] += 1
        analysis['images'].append({
            'src': src,
            'alt': alt
        })
    
    # Links
    links = soup.find_all('a', href=True)
    base_domain = urlparse(url).netloc.lower()
    
    for link in links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Skip empty links and anchors
        if not href or href.startswith('#'):
            continue
        
        # Determine if internal or external
        try:
            parsed = urlparse(href)
            if parsed.netloc:
                is_internal = parsed.netloc.lower() == base_domain
            else:
                is_internal = True  # Relative URL
        except Exception:
            is_internal = True
        
        link_info = {
            'href': href,
            'text': text,
            'is_internal': is_internal
        }
        
        analysis['links'].append(link_info)
        if is_internal:
            analysis['internal_links'] += 1
        else:
            analysis['external_links'] += 1
    
    # OpenGraph
    og_tags = soup.find_all('meta', property=re.compile(r'^og:'))
    for og in og_tags:
        property_name = og.get('property', '').replace('og:', '')
        analysis['open_graph'][property_name] = og.get('content', '')
    
    # Twitter Cards
    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
    for twitter in twitter_tags:
        name = twitter.get('name', '').replace('twitter:', '')
        analysis['twitter_cards'][name] = twitter.get('content', '')
    
    # Viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        analysis['viewport'] = viewport.get('content')
    
    # Charset
    charset = soup.find('meta', charset=True)
    if charset:
        analysis['charset'] = charset.get('charset')
    
    # Language
    html_tag = soup.find('html')
    if html_tag:
        analysis['language'] = html_tag.get('lang')
    
    return analysis


def detect_accessibility_issues(analysis: Dict, url: str) -> List[Dict]:
    """
    Detect accessibility and SEO issues from HTML analysis.
    
    Args:
        analysis: HTML analysis dictionary
        url: Page URL
        
    Returns:
        List of findings
    """
    findings = []
    
    # Title issues
    if not analysis['title']:
        findings.append({
            'id': 'html-001',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'critical',
            'title': 'Missing page title',
            'description': 'Page does not have a title tag',
            'evidence': 'No <title> tag found',
            'location': url,
            'recommendation': 'Add a descriptive title tag'
        })
    elif analysis['title_length'] > 60:
        findings.append({
            'id': 'html-002',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'low',
            'title': 'Title too long',
            'description': f"Title is {analysis['title_length']} characters (recommended: 60 or less)",
            'evidence': f"Title: {analysis['title']}",
            'location': url,
            'recommendation': 'Shorten the title to 60 characters or less'
        })
    
    # Meta description issues
    if not analysis['meta_description']:
        findings.append({
            'id': 'html-003',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'high',
            'title': 'Missing meta description',
            'description': 'Page does not have a meta description',
            'evidence': 'No meta description found',
            'location': url,
            'recommendation': 'Add a compelling meta description (150-160 characters)'
        })
    elif analysis['meta_description_length'] > 160:
        findings.append({
            'id': 'html-004',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'low',
            'title': 'Meta description too long',
            'description': f"Meta description is {analysis['meta_description_length']} characters (recommended: 160 or less)",
            'evidence': f"Description: {analysis['meta_description'][:100]}...",
            'location': url,
            'recommendation': 'Shorten the meta description to 160 characters or less'
        })
    
    # H1 issues
    if analysis['h1_count'] == 0:
        findings.append({
            'id': 'html-005',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'critical',
            'title': 'Missing H1 heading',
            'description': 'Page does not have an H1 heading',
            'evidence': 'No H1 tags found',
            'location': url,
            'recommendation': 'Add a single, descriptive H1 heading'
        })
    elif analysis['h1_count'] > 1:
        findings.append({
            'id': 'html-006',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'medium',
            'title': 'Multiple H1 headings',
            'description': f"Page has {analysis['h1_count']} H1 headings",
            'evidence': f"H1 tags: {', '.join(analysis['h1_tags'][:3])}",
            'location': url,
            'recommendation': 'Use only one H1 heading per page'
        })
    
    # Image alt text issues
    if analysis['images_without_alt'] > 0:
        findings.append({
            'id': 'html-007',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'medium',
            'title': 'Images without alt text',
            'description': f"{analysis['images_without_alt']} images missing alt attributes",
            'evidence': f"Total images: {len(analysis['images'])}, Without alt: {analysis['images_without_alt']}",
            'location': url,
            'recommendation': 'Add descriptive alt text to all images'
        })
    
    # Canonical URL issues
    if not analysis['canonical']:
        findings.append({
            'id': 'html-008',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'medium',
            'title': 'Missing canonical URL',
            'description': 'Page does not have a canonical URL',
            'evidence': 'No canonical link tag found',
            'location': url,
            'recommendation': 'Add a canonical URL to prevent duplicate content issues'
        })
    
    # Viewport issues
    if not analysis['viewport']:
        findings.append({
            'id': 'html-009',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'medium',
            'title': 'Missing viewport meta tag',
            'description': 'Page does not have a viewport meta tag',
            'evidence': 'No viewport meta tag found',
            'location': url,
            'recommendation': 'Add viewport meta tag for mobile responsiveness'
        })
    
    # Language issues
    if not analysis['language']:
        findings.append({
            'id': 'html-010',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'low',
            'title': 'Missing language attribute',
            'description': 'HTML tag does not have a lang attribute',
            'evidence': 'No lang attribute on <html> tag',
            'location': url,
            'recommendation': 'Add lang attribute to specify page language'
        })
    
    # OpenGraph issues
    og_required = ['title', 'description', 'image']
    missing_og = [prop for prop in og_required if prop not in analysis['open_graph']]
    if missing_og:
        findings.append({
            'id': 'html-011',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'low',
            'title': 'Missing OpenGraph tags',
            'description': f"Missing OpenGraph properties: {', '.join(missing_og)}",
            'evidence': f"Found OG tags: {', '.join(analysis['open_graph'].keys())}",
            'location': url,
            'recommendation': 'Add OpenGraph tags for better social media sharing'
        })
    
    return findings


def detect_machine_readability_issues(soup: BeautifulSoup, url: str) -> List[Dict]:
    """
    Detect issues with machine-readable content.
    
    Args:
        soup: BeautifulSoup object
        url: Page URL
        
    Returns:
        List of findings
    """
    findings = []
    
    # Check for JavaScript-rendered content markers
    js_indicators = soup.find_all(attrs={'data-reactroot': True}) + \
                    soup.find_all(attrs={'id': '__next'}) + \
                    soup.find_all(attrs={'id': '__nuxt'}) + \
                    soup.find_all(attrs={'id': 'app'}) + \
                    soup.find_all(attrs={'id': 'root'})
    
    if js_indicators:
        findings.append({
            'id': 'machine-001',
            'skill': 'crawl-render-audit',
            'category': 'machine_readability',
            'severity': 'info',
            'title': 'JavaScript framework detected',
            'description': 'Page appears to use a JavaScript framework',
            'evidence': f"Found {len(js_indicators)} framework markers",
            'location': url,
            'recommendation': 'Ensure critical content is available in initial HTML'
        })
    
    # Check for canvas elements
    canvas_elements = soup.find_all('canvas')
    if canvas_elements:
        findings.append({
            'id': 'machine-002',
            'skill': 'crawl-render-audit',
            'category': 'machine_readability',
            'severity': 'medium',
            'title': 'Canvas elements detected',
            'description': f"Found {len(canvas_elements)} canvas elements",
            'evidence': 'Canvas elements may contain non-accessible content',
            'location': url,
            'recommendation': 'Provide text alternatives for canvas content'
        })
    
    # Check for hidden content
    hidden_elements = soup.find_all(attrs={'style': re.compile(r'display:\s*none|visibility:\s*hidden')})
    if len(hidden_elements) > 5:  # Some hidden content is normal
        findings.append({
            'id': 'machine-003',
            'skill': 'crawl-render-audit',
            'category': 'machine_readability',
            'severity': 'low',
            'title': 'Significant hidden content',
            'description': f"Found {len(hidden_elements)} hidden elements",
            'evidence': 'Hidden content may not be accessible to all users',
            'location': url,
            'recommendation': 'Review hidden content for accessibility'
        })
    
    return findings


def analyze_pages(context: Dict) -> List[Dict]:
    """
    Analyze all crawled pages and generate findings.
    
    Args:
        context: Audit context with page data
        
    Returns:
        List of findings
    """
    all_findings = []
    
    for page in context.get('pages', []):
        html = page.get('html', '')
        url = page.get('url', '')
        
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Store HTML analysis in context
        analysis = analyze_html_structure(soup, url)
        page['analysis'] = analysis
        
        # Detect HTML issues
        html_findings = detect_accessibility_issues(analysis, url)
        all_findings.extend(html_findings)
        
        # Detect machine readability issues
        machine_findings = detect_machine_readability_issues(soup, url)
        all_findings.extend(machine_findings)
    
    return all_findings
