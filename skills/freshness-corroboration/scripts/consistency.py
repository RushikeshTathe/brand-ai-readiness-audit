"""
Freshness and consistency analysis module.
Detects identity inconsistencies, cross-page conflicts, and stale content.
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ''
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Normalize common variations
    text = text.replace('&amp;', '&')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('\u00a0', ' ')  # Non-breaking space
    
    return text


def extract_entity_identity(context: Dict) -> Dict:
    """
    Extract entity identity information from crawled pages.
    
    Args:
        context: Audit context with page data
        
    Returns:
        Entity identity information
    """
    identity = {
        'organization_names': set(),
        'descriptions': set(),
        'locations': set(),
        'contact_info': {
            'emails': set(),
            'phones': set()
        },
        'logos': set(),
        'social_profiles': set(),
        'canonical_urls': set(),
        'domains': set()
    }
    
    for page in context.get('pages', []):
        html = page.get('html', '')
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract organization name from various sources
        # 1. From JSON-LD
        for json_ld in page.get('structured_data', []):
            if isinstance(json_ld, dict):
                if json_ld.get('@type') == 'Organization':
                    if 'name' in json_ld:
                        identity['organization_names'].add(normalize_text(json_ld['name']))
                    if 'url' in json_ld:
                        identity['canonical_urls'].add(json_ld['url'])
                    if 'logo' in json_ld:
                        identity['logos'].add(json_ld['logo'])
                    if 'sameAs' in json_ld:
                        if isinstance(json_ld['sameAs'], list):
                            identity['social_profiles'].update(json_ld['sameAs'])
                        else:
                            identity['social_profiles'].add(json_ld['sameAs'])
        
        # 2. From meta tags
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name:
            identity['organization_names'].add(normalize_text(og_site_name.get('content', '')))
        
        # 3. From title (often contains brand name)
        if soup.title and soup.title.string:
            title = soup.title.string
            # Common patterns: "Page Name - Brand" or "Brand | Page Name"
            for separator in [' - ', ' | ', ' :: ', ' • ']:
                if separator in title:
                    parts = title.split(separator)
                    # Take the part that looks like a brand name
                    for part in parts:
                        part = part.strip()
                        if len(part) < 30 and not part.startswith(('http', 'www')):
                            identity['organization_names'].add(normalize_text(part))
                    break
        
        # Extract description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            identity['descriptions'].add(normalize_text(meta_desc.get('content', '')))
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            identity['descriptions'].add(normalize_text(og_desc.get('content', '')))
        
        # Extract contact information
        text = soup.get_text()
        
        # Email patterns
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        identity['contact_info']['emails'].update(emails)
        
        # Phone patterns (various formats)
        phone_patterns = [
            r'[\+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{7,15}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            identity['contact_info']['phones'].update(phones)
        
        # Extract location
        # Look for address-like content
        address_patterns = [
            r'\d{1,5}\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Place|Pl|Way|Circle|Cir)\b',
            r'(?:Suite|Ste|Floor|Fl|Building|Bldg|Room|Rm)\s*\d+',
            r'[A-Z][a-z]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?',
        ]
        
        for pattern in address_patterns:
            addresses = re.findall(pattern, text)
            identity['locations'].update(addresses)
        
        # Extract canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            identity['canonical_urls'].add(canonical.get('href', ''))
        
        # Add domain
        domain = urlparse(page.get('url', '')).netloc
        if domain:
            identity['domains'].add(domain.lower())
    
    # Convert sets to lists for JSON serialization
    for key in identity:
        if isinstance(identity[key], set):
            identity[key] = list(identity[key])
        elif isinstance(identity[key], dict):
            for subkey in identity[key]:
                if isinstance(identity[key][subkey], set):
                    identity[key][subkey] = list(identity[key][subkey])
    
    return identity


def check_identity_consistency(identity: Dict, context: Dict) -> List[Dict]:
    """
    Check for identity inconsistencies.
    
    Args:
        identity: Entity identity information
        context: Audit context
        
    Returns:
        List of findings
    """
    findings = []
    
    # Check organization name consistency
    org_names = identity.get('organization_names', [])
    if len(org_names) > 1:
        # Filter out empty strings and very short names
        valid_names = [n for n in org_names if n and len(n) > 2]
        if len(valid_names) > 1:
            findings.append({
                'id': 'identity-001',
                'skill': 'freshness-corroboration',
                'category': 'identity',
                'severity': 'high',
                'title': 'Inconsistent organization names',
                'description': f"Found {len(valid_names)} different organization names",
                'evidence': f"Names found: {', '.join(valid_names[:5])}",
                'location': context['site']['domain'],
                'recommendation': 'Standardize organization name across all pages'
            })
    
    # Check canonical URL consistency
    canonical_urls = identity.get('canonical_urls', [])
    if len(canonical_urls) > 1:
        # Normalize and compare
        normalized_urls = set()
        for url in canonical_urls:
            if url:
                parsed = urlparse(url)
                normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
                normalized_urls.add(normalized)
        
        if len(normalized_urls) > 1:
            findings.append({
                'id': 'identity-002',
                'skill': 'freshness-corroboration',
                'category': 'identity',
                'severity': 'medium',
                'title': 'Inconsistent canonical URLs',
                'description': f"Found {len(normalized_urls)} different canonical URLs",
                'evidence': f"URLs: {', '.join(list(normalized_urls)[:3])}",
                'location': context['site']['domain'],
                'recommendation': 'Use consistent canonical URLs'
            })
    
    # Check social profile consistency
    social_profiles = identity.get('social_profiles', [])
    if social_profiles:
        # Group by platform
        platforms = {}
        for url in social_profiles:
            if url:
                parsed = urlparse(url)
                domain = parsed.netloc.lower().replace('www.', '')
                if domain not in platforms:
                    platforms[domain] = []
                platforms[domain].append(url)
        
        # Check for multiple profiles on same platform
        for platform, urls in platforms.items():
            if len(urls) > 1:
                findings.append({
                    'id': 'identity-003',
                    'skill': 'freshness-corroboration',
                    'category': 'identity',
                    'severity': 'low',
                    'title': f'Multiple {platform} profiles',
                    'description': f"Found {len(urls)} different {platform} profiles",
                    'evidence': f"URLs: {', '.join(urls[:3])}",
                    'location': context['site']['domain'],
                    'recommendation': f'Consolidate {platform} profiles'
                })
    
    return findings


def check_cross_page_consistency(context: Dict) -> List[Dict]:
    """
    Check for consistency across crawled pages.
    
    Args:
        context: Audit context with page data
        
    Returns:
        List of findings
    """
    findings = []
    
    # Collect facts from each page
    page_facts = []
    for page in context.get('pages', []):
        facts = {
            'url': page.get('url', ''),
            'title': page.get('title', ''),
            'meta_description': page.get('meta_description', ''),
            'h1': None,
            'prices': [],
            'dates': []
        }
        
        html = page.get('html', '')
        if html:
            soup = BeautifulSoup(html, 'lxml')
            
            # Get H1
            h1 = soup.find('h1')
            if h1:
                facts['h1'] = normalize_text(h1.get_text(strip=True))
            
            # Extract prices
            price_patterns = [
                r'\$\d+(?:\.\d{2})?',
                r'€\d+(?:\.\d{2})?',
                r'£\d+(?:\.\d{2})?',
                r'\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP)'
            ]
            text = soup.get_text()
            for pattern in price_patterns:
                prices = re.findall(pattern, text)
                facts['prices'].extend(prices)
            
            # Extract dates
            date_patterns = [
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
            ]
            for pattern in date_patterns:
                dates = re.findall(pattern, text, re.IGNORECASE)
                facts['dates'].extend(dates)
        
        page_facts.append(facts)
    
    # Compare prices across pages
    all_prices = {}
    for facts in page_facts:
        for price in facts['prices']:
            if price not in all_prices:
                all_prices[price] = []
            all_prices[price].append(facts['url'])
    
    # Check for price inconsistencies (same product different prices)
    # This is a simplified check - in reality you'd need product identification
    if len(all_prices) > 5:  # Only flag if many different prices
        findings.append({
            'id': 'consistency-001',
            'skill': 'freshness-corroboration',
            'category': 'consistency',
            'severity': 'medium',
            'title': 'Multiple price points detected',
            'description': f"Found {len(all_prices)} different price points across pages",
            'evidence': f"Sample prices: {', '.join(list(all_prices.keys())[:5])}",
            'location': context['site']['domain'],
            'recommendation': 'Verify pricing consistency across all pages'
        })
    
    return findings


def check_freshness_signals(context: Dict) -> List[Dict]:
    """
    Check for freshness signals and potential staleness.
    
    Args:
        context: Audit context with page data
        
    Returns:
        List of findings
    """
    findings = []
    current_year = datetime.now().year
    cutoff_date = datetime.now() - timedelta(days=365)
    
    for page in context.get('pages', []):
        html = page.get('html', '')
        url = page.get('url', '')
        
        if not html:
            continue
        
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text()
        
        # Check for old dates
        date_patterns = [
            (r'\b(20[0-2]\d)[/-](\d{1,2})[/-](\d{1,2})\b', 'ISO format'),
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](20[0-2]\d)\b', 'US format'),
        ]
        
        old_dates_found = []
        for pattern, format_name in date_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                try:
                    # Extract year
                    year_str = [g for g in groups if g and len(g) == 4 and g.startswith('20')][0]
                    year = int(year_str)
                    
                    if year < current_year - 1:  # More than 1 year old
                        old_dates_found.append(f"{match.group()} ({format_name})")
                except (ValueError, IndexError):
                    continue
        
        if old_dates_found:
            findings.append({
                'id': 'freshness-001',
                'skill': 'freshness-corroboration',
                'category': 'freshness',
                'severity': 'medium',
                'title': 'Potentially outdated dates',
                'description': f"Found {len(old_dates_found)} dates older than {current_year - 1}",
                'evidence': f"Dates found: {', '.join(old_dates_found[:3])}",
                'location': url,
                'recommendation': 'Review and update outdated content'
            })
        
        # Check for current year references
        if str(current_year) not in text and str(current_year - 1) not in text:
            findings.append({
                'id': 'freshness-002',
                'skill': 'freshness-corroboration',
                'category': 'freshness',
                'severity': 'low',
                'title': 'No recent year references',
                'description': f"Page does not reference {current_year} or {current_year - 1}",
                'evidence': f"Current year: {current_year}",
                'location': url,
                'recommendation': 'Update content to reference current year where appropriate'
            })
        
        # Check for copyright year
        copyright_match = re.search(r'©\s*(\d{4})', text)
        if copyright_match:
            copyright_year = int(copyright_match.group(1))
            if copyright_year < current_year:
                findings.append({
                    'id': 'freshness-003',
                    'skill': 'freshness-corroboration',
                    'category': 'freshness',
                    'severity': 'low',
                    'title': 'Outdated copyright year',
                    'description': f"Copyright year is {copyright_year}, current year is {current_year}",
                    'evidence': f"Copyright notice: {copyright_match.group()}",
                    'location': url,
                    'recommendation': 'Update copyright year to current year'
                })
        
        # Check for "last updated" or similar
        update_indicators = [
            'last updated',
            'last modified',
            'updated on',
            'edited on',
            'published on'
        ]
        
        for indicator in update_indicators:
            if indicator.lower() in text.lower():
                # Try to extract the date
                pattern = rf'{indicator}\s*[:\-]?\s*([A-Za-z]+\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{4}})'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Check if it's old
                    date_str = match.group(1)
                    # Simple year extraction
                    year_match = re.search(r'\d{4}', date_str)
                    if year_match:
                        year = int(year_match.group())
                        if year < current_year - 1:
                            findings.append({
                                'id': 'freshness-004',
                                'skill': 'freshness-corroboration',
                                'category': 'freshness',
                                'severity': 'medium',
                                'title': 'Content not updated recently',
                                'description': f"Last update indicator suggests content is from {year}",
                                'evidence': f"Found: {match.group()}",
                                'location': url,
                                'recommendation': 'Update content to reflect current information'
                            })
    
    return findings


def analyze_freshness_consistency(
    context: Dict,
    existing_findings: List[Dict]
) -> Tuple[Dict, List[Dict]]:
    """
    Analyze freshness and consistency across the website.
    
    Args:
        context: Audit context with page data
        existing_findings: Findings from other skills
        
    Returns:
        Tuple of (updated context, new findings)
    """
    new_findings = []
    
    # Extract entity identity
    identity = extract_entity_identity(context)
    context['entity_identity'] = identity
    
    # Check identity consistency
    identity_findings = check_identity_consistency(identity, context)
    new_findings.extend(identity_findings)
    
    # Check cross-page consistency
    consistency_findings = check_cross_page_consistency(context)
    new_findings.extend(consistency_findings)
    
    # Check freshness signals
    freshness_findings = check_freshness_signals(context)
    new_findings.extend(freshness_findings)
    
    # Add external corroboration placeholder
    context['external_corroboration'] = {
        'status': 'not_evaluated',
        'note': 'External corroboration not implemented in base version'
    }
    
    return context, new_findings
