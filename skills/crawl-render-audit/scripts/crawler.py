"""
Crawler module for conservative website crawling.
Implements same-domain crawling with configurable limits.
"""

import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from urllib.robotparser import RobotFileParser
from collections import deque
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup


# Tracking parameters to remove for URL normalization
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'fbclid', 'gclid', 'mc_cid', 'mc_eid', 'ref', 'source', 'medium',
    'campaign', 'term', 'content', '_ga', '_gl', 'hsa_cam', 'hsa_grp',
    'hsa_mt', 'hsa_src', 'hsa_ad', 'hsa_acc', 'hsa_net', 'hsa_ver',
    'hsa_la', 'hsa_ol', 'hsa_kw', 'hsa_tgt', 'hsa_cam_id', 'hsa_ad_id',
    'hsa_ad_set_id', 'hsa_net_id', 'hsa_ver_id', 'hsa_la_id', 'hsa_ol_id',
    'hsa_kw_id', 'hsa_tgt_id', 'hsa_cam_id', 'hsa_ad_id', 'hsa_ad_set_id',
    'hsa_net_id', 'hsa_ver_id', 'hsa_la_id', 'hsa_ol_id', 'hsa_kw_id',
    'hsa_tgt_id', 'hsa_cam_id', 'hsa_ad_id', 'hsa_ad_set_id', 'hsa_net_id',
    'hsa_ver_id', 'hsa_la_id', 'hsa_ol_id', 'hsa_kw_id', 'hsa_tgt_id',
    'hsa_cam_id', 'hsa_ad_id', 'hsa_ad_set_id', 'hsa_net_id', 'hsa_ver_id',
    'hsa_la_id', 'hsa_ol_id', 'hsa_kw_id', 'hsa_tgt_id'
}


class CrawlerConfig:
    """Configuration for the crawler."""
    
    def __init__(
        self,
        max_pages: int = 20,
        max_depth: int = 2,
        timeout: int = 10,
        delay: float = 1.0,
        user_agent: str = "BrandAuditBot/1.0"
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.delay = delay
        self.user_agent = user_agent


def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters and standardizing format."""
    parsed = urlparse(url)
    
    # Remove fragment
    parsed = parsed._replace(fragment='')
    
    # Remove tracking parameters
    query_params = parse_qs(parsed.query)
    cleaned_params = {
        k: v for k, v in query_params.items() 
        if k.lower() not in TRACKING_PARAMS
    }
    
    # Rebuild query string
    new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
    parsed = parsed._replace(query=new_query)
    
    # Normalize path (remove trailing slash for consistency, except root)
    path = parsed.path
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    
    # Remove index.html/htm variations
    path = re.sub(r'/index\.(html?|php)$', '', path, flags=re.IGNORECASE)
    
    parsed = parsed._replace(path=path)
    
    return urlunparse(parsed)


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the same domain."""
    return get_domain(url) == base_domain


def create_audit_context(url: str) -> Dict:
    """Create initial audit context."""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    
    return {
        "site": {
            "input_url": url,
            "normalized_url": normalized,
            "final_url": None,
            "domain": parsed.netloc.lower()
        },
        "robots": {
            "available": False,
            "content": None,
            "allows": [],
            "disallows": [],
            "sitemap_url": None
        },
        "sitemap": {
            "available": False,
            "urls": [],
            "last_modified": None
        },
        "pages": [],
        "links": [],
        "structured_data": [],
        "metadata": [],
        "text_signals": [],
        "render_signals": []
    }


def fetch_page(url: str, config: CrawlerConfig) -> Optional[Dict]:
    """Fetch a single page and extract basic information."""
    try:
        headers = {'User-Agent': config.user_agent}
        response = requests.get(
            url, 
            headers=headers, 
            timeout=config.timeout,
            allow_redirects=True
        )
        
        # Track redirect chain
        redirect_chain = []
        for resp in response.history:
            redirect_chain.append({
                'url': resp.url,
                'status': resp.status_code
            })
        
        # Parse content
        soup = BeautifulSoup(response.text, 'lxml') if response.text else None
        
        return {
            'url': url,
            'status_code': response.status_code,
            'final_url': response.url,
            'content_type': response.headers.get('Content-Type', ''),
            'headers': dict(response.headers),
            'html': response.text if response.text else '',
            'soup': soup,
            'redirect_chain': redirect_chain,
            'elapsed': response.elapsed.total_seconds()
        }
        
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'status_code': 0,
            'error': 'timeout',
            'final_url': url
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status_code': 0,
            'error': str(e),
            'final_url': url
        }


def extract_links(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    """Extract all links from a page."""
    links = []
    
    if not soup:
        return links
    
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        absolute_url = urljoin(base_url, href)
        normalized = normalize_url(absolute_url)
        
        links.append({
            'source': base_url,
            'target': normalized,
            'text': tag.get_text(strip=True),
            'is_internal': is_same_domain(normalized, get_domain(base_url))
        })
    
    return links


def crawl_website(
    url: str,
    config: Optional[CrawlerConfig] = None,
    robots_parser: Optional[RobotFileParser] = None
) -> Dict:
    """
    Crawl a website and populate audit context.
    
    Args:
        url: Starting URL
        config: Crawler configuration
        robots_parser: Pre-loaded robots.txt parser
        
    Returns:
        Populated audit context
    """
    if config is None:
        config = CrawlerConfig()
    
    context = create_audit_context(url)
    visited: Set[str] = set()
    queue: deque = deque([(normalize_url(url), 0)])
    
    while queue and len(context['pages']) < config.max_pages:
        current_url, depth = queue.popleft()
        
        # Skip if already visited or too deep
        if current_url in visited or depth > config.max_depth:
            continue
        
        # Check robots.txt
        if robots_parser and not robots_parser.can_fetch(config.user_agent, current_url):
            continue
        
        # Respect rate limiting
        time.sleep(config.delay)
        
        # Fetch page
        page_data = fetch_page(current_url, config)
        if not page_data:
            continue
        
        visited.add(current_url)
        
        # Update context with first successful page
        if not context['site']['final_url'] and page_data.get('final_url'):
            context['site']['final_url'] = page_data['final_url']
        
        # Store page data (without BeautifulSoup for JSON serialization)
        page_info = {
            'url': current_url,
            'status_code': page_data.get('status_code', 0),
            'final_url': page_data.get('final_url', current_url),
            'content_type': page_data.get('content_type', ''),
            'redirect_chain': page_data.get('redirect_chain', []),
            'error': page_data.get('error'),
            'elapsed': page_data.get('elapsed', 0),
            'html': page_data.get('html', '')
        }
        # Extract HTML metadata if available
        soup = page_data.get('soup')
        if soup:
            page_info['title'] = soup.title.string if soup.title else None
            page_info['meta_description'] = None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                page_info['meta_description'] = meta_desc.get('content')
            
            page_info['h1_count'] = len(soup.find_all('h1'))
            page_info['link_count'] = len(soup.find_all('a', href=True))
            page_info['image_count'] = len(soup.find_all('img'))
        
        context['pages'].append(page_info)
        
        # Extract and queue links
        if soup and page_data.get('status_code') == 200:
            links = extract_links(soup, current_url)
            context['links'].extend(links)
            
            # Add internal links to queue
            for link in links:
                if (link['is_internal'] and 
                    link['target'] not in visited and
                    depth + 1 <= config.max_depth):
                    queue.append((link['target'], depth + 1))
    
    return context
