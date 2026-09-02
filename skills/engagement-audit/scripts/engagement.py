"""
Engagement analysis module.
Analyzes first-screen orientation, navigation, and call-to-action effectiveness.
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def analyze_orientation(soup: BeautifulSoup, url: str) -> Dict:
    """
    Analyze first-screen orientation signals.
    
    Args:
        soup: BeautifulSoup object
        url: Page URL
        
    Returns:
        Dictionary with orientation analysis
    """
    orientation = {
        'has_h1': False,
        'h1_text': None,
        'has_subheading': False,
        'subheading_text': None,
        'has_value_proposition': False,
        'value_proposition_text': None,
        'has_primary_cta': False,
        'primary_cta_text': None,
        'has_navigation': False,
        'orientation_score': 0
    }
    
    # Check for H1
    h1 = soup.find('h1')
    if h1:
        orientation['has_h1'] = True
        orientation['h1_text'] = h1.get_text(strip=True)
    
    # Check for subheading (H2 or large text near H1)
    if h1:
        # Look for H2 immediately after H1
        h2 = soup.find('h2')
        if h2:
            orientation['has_subheading'] = True
            orientation['subheading_text'] = h2.get_text(strip=True)
        else:
            # Look for large paragraph or span near H1
            next_elements = h1.find_all_next(['p', 'span'], limit=3)
            for elem in next_elements:
                text = elem.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:
                    orientation['has_subheading'] = True
                    orientation['subheading_text'] = text
                    break
    
    # Check for value proposition in visible text
    # Look for common value proposition patterns
    value_patterns = [
        r'we (?:help|enable|provide|offer|deliver)',
        r'the (?:best|leading|top|#1)',
        r'(?:trusted|used|loved) by',
        r'save (?:time|money|effort)',
        r'(?:easy|fast|simple|powerful)',
        r'(?:free|instant|quick)',
    ]
    
    # Get visible text (excluding script/style)
    for script in soup(['script', 'style']):
        script.decompose()
    
    visible_text = soup.get_text()
    
    for pattern in value_patterns:
        if re.search(pattern, visible_text, re.IGNORECASE):
            orientation['has_value_proposition'] = True
            # Try to extract the sentence
            sentences = re.split(r'[.!?]+', visible_text)
            for sentence in sentences:
                if re.search(pattern, sentence, re.IGNORECASE):
                    orientation['value_proposition_text'] = sentence.strip()[:200]
                    break
            break
    
    # Check for primary CTA
    cta_patterns = [
        r'(?:get|start|try|sign up|learn more|contact|buy|shop|download|subscribe)',
        r'(?:free|demo|trial|quote|pricing)',
        r'(?:see|view|explore|discover)',
    ]
    
    # Look for buttons and links with CTA-like text
    buttons = soup.find_all(['button', 'a', 'input'], class_=re.compile(r'btn|button|cta', re.IGNORECASE))
    buttons.extend(soup.find_all('a', string=re.compile(r'(?:get|start|try|sign up|learn more|contact|buy|shop)', re.IGNORECASE)))
    
    if buttons:
        orientation['has_primary_cta'] = True
        orientation['primary_cta_text'] = buttons[0].get_text(strip=True)
    else:
        # Check for any links with CTA-like text
        links = soup.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            for pattern in cta_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    orientation['has_primary_cta'] = True
                    orientation['primary_cta_text'] = text
                    break
            if orientation['has_primary_cta']:
                break
    
    # Check for navigation
    nav = soup.find('nav') or soup.find(class_=re.compile(r'nav|menu', re.IGNORECASE))
    if nav:
        orientation['has_navigation'] = True
    
    # Calculate orientation score
    score = 0
    if orientation['has_h1']:
        score += 25
    if orientation['has_subheading']:
        score += 25
    if orientation['has_value_proposition']:
        score += 25
    if orientation['has_primary_cta']:
        score += 25
    
    orientation['orientation_score'] = score
    
    return orientation


def analyze_navigation(soup: BeautifulSoup, url: str) -> Dict:
    """
    Analyze navigation structure.
    
    Args:
        soup: BeautifulSoup object
        url: Page URL
        
    Returns:
        Dictionary with navigation analysis
    """
    navigation = {
        'has_nav_element': False,
        'nav_links': [],
        'nav_link_count': 0,
        'has_footer_nav': False,
        'footer_links': [],
        'has_search': False,
        'mobile_friendly': False
    }
    
    # Check for nav element
    nav = soup.find('nav')
    if nav:
        navigation['has_nav_element'] = True
        links = nav.find_all('a', href=True)
        navigation['nav_links'] = [
            {
                'text': link.get_text(strip=True),
                'href': link.get('href')
            }
            for link in links
        ]
        navigation['nav_link_count'] = len(links)
    
    # Check for navigation-like classes
    if not navigation['has_nav_element']:
        nav_classes = soup.find_all(class_=re.compile(r'nav|menu', re.IGNORECASE))
        for nav_elem in nav_classes:
            links = nav_elem.find_all('a', href=True)
            if links:
                navigation['has_nav_element'] = True
                navigation['nav_links'] = [
                    {
                        'text': link.get_text(strip=True),
                        'href': link.get('href')
                    }
                    for link in links
                ]
                navigation['nav_link_count'] = len(links)
                break
    
    # Check footer navigation
    footer = soup.find('footer') or soup.find(class_='footer')
    if footer:
        footer_links = footer.find_all('a', href=True)
        if footer_links:
            navigation['has_footer_nav'] = True
            navigation['footer_links'] = [
                {
                    'text': link.get_text(strip=True),
                    'href': link.get('href')
                }
                for link in footer_links
            ]
    
    # Check for search functionality
    search = soup.find('input', attrs={'type': 'search'}) or \
             soup.find('input', attrs={'name': 'q'}) or \
             soup.find('input', attrs={'name': 'search'}) or \
             soup.find(class_=re.compile(r'search', re.IGNORECASE))
    if search:
        navigation['has_search'] = True
    
    # Check viewport for mobile friendliness
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        navigation['mobile_friendly'] = True
    
    return navigation


def detect_orientation_issues(orientation: Dict, url: str) -> List[Dict]:
    """
    Detect orientation issues.
    
    Args:
        orientation: Orientation analysis dictionary
        url: Page URL
        
    Returns:
        List of findings
    """
    findings = []
    
    if not orientation['has_h1']:
        findings.append({
            'id': 'engage-001',
            'skill': 'engagement-audit',
            'category': 'orientation',
            'severity': 'critical',
            'title': 'No clear primary heading',
            'description': 'Page lacks an H1 heading for immediate orientation',
            'evidence': 'No H1 element found',
            'location': url,
            'recommendation': 'Add a clear H1 that communicates what the site offers'
        })
    
    if not orientation['has_subheading']:
        findings.append({
            'id': 'engage-002',
            'skill': 'engagement-audit',
            'category': 'orientation',
            'severity': 'high',
            'title': 'Missing subheading or tagline',
            'description': 'No supporting text to explain the value proposition',
            'evidence': 'No subheading or tagline found near H1',
            'location': url,
            'recommendation': 'Add a subheading that clarifies what you offer and for whom'
        })
    
    if not orientation['has_value_proposition']:
        findings.append({
            'id': 'engage-003',
            'skill': 'engagement-audit',
            'category': 'orientation',
            'severity': 'high',
            'title': 'Unclear value proposition',
            'description': 'No clear statement of benefits or value',
            'evidence': 'No value proposition patterns detected',
            'location': url,
            'recommendation': 'Clearly state what benefits visitors will get'
        })
    
    if not orientation['has_primary_cta']:
        findings.append({
            'id': 'engage-004',
            'skill': 'engagement-audit',
            'category': 'orientation',
            'severity': 'high',
            'title': 'Missing call-to-action',
            'description': 'No clear next step for visitors',
            'evidence': 'No CTA buttons or links found',
            'location': url,
            'recommendation': 'Add a prominent CTA that guides visitors to the next step'
        })
    
    return findings


def detect_navigation_issues(navigation: Dict, url: str) -> List[Dict]:
    """
    Detect navigation issues.
    
    Args:
        navigation: Navigation analysis dictionary
        url: Page URL
        
    Returns:
        List of findings
    """
    findings = []
    
    if not navigation['has_nav_element']:
        findings.append({
            'id': 'engage-005',
            'skill': 'engagement-audit',
            'category': 'navigation',
            'severity': 'critical',
            'title': 'No navigation found',
            'description': 'Website lacks navigation structure',
            'evidence': 'No nav element or navigation classes found',
            'location': url,
            'recommendation': 'Add clear navigation to help visitors find content'
        })
    elif navigation['nav_link_count'] < 3:
        findings.append({
            'id': 'engage-006',
            'skill': 'engagement-audit',
            'category': 'navigation',
            'severity': 'medium',
            'title': 'Limited navigation',
            'description': f"Only {navigation['nav_link_count']} navigation links found",
            'evidence': f"Navigation links: {', '.join([l['text'] for l in navigation['nav_links'][:3]])}",
            'location': url,
            'recommendation': 'Consider adding more navigation options for important sections'
        })
    
    if not navigation['has_footer_nav']:
        findings.append({
            'id': 'engage-007',
            'skill': 'engagement-audit',
            'category': 'navigation',
            'severity': 'low',
            'title': 'No footer navigation',
            'description': 'Website lacks footer navigation links',
            'evidence': 'No footer navigation found',
            'location': url,
            'recommendation': 'Add footer navigation with important links'
        })
    
    if not navigation['has_search']:
        findings.append({
            'id': 'engage-008',
            'skill': 'engagement-audit',
            'category': 'navigation',
            'severity': 'low',
            'title': 'No search functionality',
            'description': 'Website lacks search capability',
            'evidence': 'No search input found',
            'location': url,
            'recommendation': 'Consider adding search for content-heavy sites'
        })
    
    if not navigation['mobile_friendly']:
        findings.append({
            'id': 'engage-009',
            'skill': 'engagement-audit',
            'category': 'navigation',
            'severity': 'high',
            'title': 'Not mobile-friendly',
            'description': 'Missing viewport meta tag',
            'evidence': 'No viewport meta tag found',
            'location': url,
            'recommendation': 'Add viewport meta tag for mobile responsiveness'
        })
    
    return findings


def check_broken_navigation_links(navigation: Dict, url: str) -> List[Dict]:
    """
    Check for broken navigation links.
    
    Args:
        navigation: Navigation analysis dictionary
        url: Page URL
        
    Returns:
        List of findings
    """
    findings = []
    
    # This is a basic check - in a real implementation, you'd actually verify links
    # For now, we'll just check for obviously broken patterns
    
    all_links = navigation.get('nav_links', []) + navigation.get('footer_links', [])
    
    for link in all_links:
        href = link.get('href', '')
        text = link.get('text', '')
        
        # Check for obviously broken links
        if href in ['#', '#!', 'javascript:void(0)', 'javascript:;']:
            findings.append({
                'id': 'engage-010',
                'skill': 'engagement-audit',
                'category': 'navigation',
                'severity': 'medium',
                'title': 'Non-functional navigation link',
                'description': f"Link '{text}' points to a placeholder URL",
                'evidence': f"Link href: {href}",
                'location': url,
                'recommendation': 'Replace placeholder links with actual destinations'
            })
    
    return findings


def analyze_engagement(
    context: Dict,
    existing_findings: List[Dict]
) -> Tuple[Dict, List[Dict]]:
    """
    Analyze engagement across the website.
    
    Args:
        context: Audit context with page data
        existing_findings: Findings from other skills
        
    Returns:
        Tuple of (updated context, new findings)
    """
    new_findings = []
    
    # Analyze each page
    for page in context.get('pages', []):
        html = page.get('html', '')
        url = page.get('url', '')
        
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Analyze orientation
        orientation = analyze_orientation(soup, url)
        page['orientation'] = orientation
        
        # Detect orientation issues
        orientation_issues = detect_orientation_issues(orientation, url)
        new_findings.extend(orientation_issues)
        
        # Analyze navigation
        navigation = analyze_navigation(soup, url)
        page['navigation'] = navigation
        
        # Detect navigation issues
        navigation_issues = detect_navigation_issues(navigation, url)
        new_findings.extend(navigation_issues)
        
        # Check for broken navigation links
        broken_links = check_broken_navigation_links(navigation, url)
        new_findings.extend(broken_links)
    
    # Store summary in context
    if context['pages']:
        primary_page = context['pages'][0]
        context['engagement_summary'] = {
            'orientation_score': primary_page.get('orientation', {}).get('orientation_score', 0),
            'has_navigation': primary_page.get('navigation', {}).get('has_nav_element', False),
            'has_cta': primary_page.get('orientation', {}).get('has_primary_cta', False)
        }
    
    return context, new_findings
