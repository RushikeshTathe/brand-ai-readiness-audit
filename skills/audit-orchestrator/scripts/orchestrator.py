"""
Audit Orchestrator - Main entrypoint for the Agent Skill Marketplace.
Coordinates all specialized audit skills and produces the final JSON report.
"""

import json
import sys
import os
import time
import hashlib
import importlib.util
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


def load_module_from_path(module_name: str, file_path: str):
    """Load a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Get the base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.dirname(BASE_DIR)

# Load skill modules
crawl_render_path = os.path.join(SKILLS_DIR, 'crawl-render-audit', 'scripts')
freshness_path = os.path.join(SKILLS_DIR, 'freshness-corroboration', 'scripts')
engagement_path = os.path.join(SKILLS_DIR, 'engagement-audit', 'scripts')

# Add to path
sys.path.insert(0, crawl_render_path)
sys.path.insert(0, freshness_path)
sys.path.insert(0, engagement_path)

# Import modules
from crawler import crawl_website, CrawlerConfig, normalize_url, get_domain
from robots import check_robots
from structured_data import analyze_structured_data
from page_analysis import analyze_pages
from consistency import analyze_freshness_consistency
from engagement import analyze_engagement


def validate_url(url: str) -> str:
    """
    Validate and normalize input URL.
    
    Args:
        url: Input URL or domain
        
    Returns:
        Normalized URL
        
    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Parse and validate
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    
    # Basic netloc sanity: valid domains need a dot or localhost
    netloc = parsed.netloc.lower()
    if '.' not in netloc and not netloc.startswith('localhost'):
        raise ValueError(f"Invalid URL: {url}")
    
    # Remove trailing slash for consistency
    if url.endswith('/'):
        url = url[:-1]
    
    return url


def calculate_priority(finding: Dict) -> int:
    """
    Calculate priority score for a finding (1-100, higher = more important).
    
    Args:
        finding: Finding dictionary
        
    Returns:
        Priority score
    """
    severity_scores = {
        'critical': 90,
        'high': 70,
        'medium': 50,
        'low': 30,
        'info': 10
    }
    
    base_score = severity_scores.get(finding.get('severity', 'info'), 10)
    
    # Adjust based on category
    category_multipliers = {
        'html': 1.1,
        'orientation': 1.2,
        'navigation': 1.1,
        'identity': 1.0,
        'consistency': 0.9,
        'freshness': 0.8
    }
    
    category = finding.get('category', '')
    multiplier = category_multipliers.get(category, 1.0)
    
    return min(100, int(base_score * multiplier))


def generate_finding_id(finding: Dict) -> str:
    """
    Generate a unique, deterministic ID for a finding.
    
    Args:
        finding: Finding dictionary
        
    Returns:
        Unique finding ID
    """
    # Create a hash based on key fields
    key_fields = [
        finding.get('skill', ''),
        finding.get('category', ''),
        finding.get('title', ''),
        finding.get('location', '')
    ]
    
    hash_input = '|'.join(key_fields)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    return f"{finding.get('skill', 'unknown')}-{hash_value}"


def deduplicate_findings(findings: List[Dict]) -> List[Dict]:
    """
    Remove duplicate findings based on content similarity.
    
    Args:
        findings: List of findings
        
    Returns:
        Deduplicated list
    """
    seen = {}
    unique_findings = []
    
    for finding in findings:
        # Generate a signature for comparison
        signature = f"{finding.get('category', '')}-{finding.get('title', '')}-{finding.get('location', '')}"
        
        if signature not in seen:
            seen[signature] = True
            # Ensure unique ID
            finding['id'] = generate_finding_id(finding)
            unique_findings.append(finding)
    
    return unique_findings


def normalize_severity(severity: str) -> str:
    """
    Normalize severity level to standard values.
    
    Args:
        severity: Severity string
        
    Returns:
        Normalized severity
    """
    valid_severities = ['critical', 'high', 'medium', 'low', 'info']
    severity_lower = severity.lower().strip()
    
    if severity_lower in valid_severities:
        return severity_lower
    
    # Map common variations
    severity_map = {
        'error': 'high',
        'warning': 'medium',
        'notice': 'low',
        'debug': 'info',
        'critical': 'critical',
        'major': 'high',
        'minor': 'low'
    }
    
    return severity_map.get(severity_lower, 'info')


def generate_recommendations(findings: List[Dict]) -> List[Dict]:
    """
    Generate proactive recommendations based on findings.
    
    Args:
        findings: List of findings
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    # Group findings by category
    categories = {}
    for finding in findings:
        category = finding.get('category', 'other')
        if category not in categories:
            categories[category] = []
        categories[category].append(finding)
    
    # Generate recommendations for each category
    if 'html' in categories:
        html_findings = categories['html']
        if any(f.get('severity') in ['critical', 'high'] for f in html_findings):
            recommendations.append({
                'id': 'rec-html-001',
                'title': 'Fix critical HTML issues',
                'description': 'Address missing titles, meta descriptions, and H1 headings',
                'priority': 'high',
                'effort': 'low',
                'impact': 'high'
            })
    
    if 'orientation' in categories:
        orientation_findings = categories['orientation']
        if any(f.get('severity') in ['critical', 'high'] for f in orientation_findings):
            recommendations.append({
                'id': 'rec-orientation-001',
                'title': 'Clarify value proposition',
                'description': 'Add clear headings, subheadings, and calls-to-action',
                'priority': 'high',
                'effort': 'medium',
                'impact': 'high'
            })
    
    if 'navigation' in categories:
        nav_findings = categories['navigation']
        if any(f.get('severity') in ['critical', 'high'] for f in nav_findings):
            recommendations.append({
                'id': 'rec-nav-001',
                'title': 'Improve navigation structure',
                'description': 'Add clear navigation and footer links',
                'priority': 'medium',
                'effort': 'medium',
                'impact': 'medium'
            })
    
    if 'freshness' in categories:
        freshness_findings = categories['freshness']
        if any(f.get('severity') in ['medium', 'high'] for f in freshness_findings):
            recommendations.append({
                'id': 'rec-freshness-001',
                'title': 'Update outdated content',
                'description': 'Review and update old dates, pricing, and statistics',
                'priority': 'medium',
                'effort': 'low',
                'impact': 'medium'
            })
    
    if 'structured_data' in categories:
        schema_findings = categories['structured_data']
        if len(schema_findings) > 2:
            recommendations.append({
                'id': 'rec-schema-001',
                'title': 'Add structured data',
                'description': 'Implement JSON-LD for key content types',
                'priority': 'medium',
                'effort': 'medium',
                'impact': 'medium'
            })
    
    return recommendations


def calculate_overall_score(findings: List[Dict]) -> int:
    """
    Calculate overall site score (0-100).
    
    Args:
        findings: List of findings
        
    Returns:
        Overall score
    """
    if not findings:
        return 100
    
    # Start with perfect score and deduct
    score = 100
    
    severity_deductions = {
        'critical': 20,
        'high': 10,
        'medium': 5,
        'low': 2,
        'info': 0
    }
    
    for finding in findings:
        severity = finding.get('severity', 'info')
        score -= severity_deductions.get(severity, 0)
    
    return max(0, min(100, score))


def run_audit(
    url: str,
    max_pages: int = 20,
    max_depth: int = 2,
    timeout: int = 10,
    delay: float = 1.0,
    user_agent: str = "BrandAuditBot/1.0"
) -> Dict:
    """
    Run a complete audit on a website.
    
    Args:
        url: Target website URL
        max_pages: Maximum pages to crawl
        max_depth: Maximum crawl depth
        timeout: Request timeout in seconds
        delay: Delay between requests
        user_agent: User agent string
        
    Returns:
        Complete audit report
    """
    start_time = time.time()
    
    # Validate and normalize URL
    normalized_url = validate_url(url)
    domain = get_domain(normalized_url)
    
    print(f"Starting audit for: {normalized_url}")
    print(f"Domain: {domain}")
    print(f"Configuration: max_pages={max_pages}, max_depth={max_depth}")
    
    # Create crawler config
    config = CrawlerConfig(
        max_pages=max_pages,
        max_depth=max_depth,
        timeout=timeout,
        delay=delay,
        user_agent=user_agent
    )
    
    # Step 1: Crawl website
    print("\n[1/4] Crawling website...")
    context = crawl_website(normalized_url, config)
    
    # Step 2: Check robots.txt
    print("[2/4] Analyzing robots.txt...")
    context = check_robots(context)
    
    # Step 3: Analyze structured data
    print("[3/4] Analyzing structured data...")
    context = analyze_structured_data(context)
    
    # Step 4: Analyze pages
    print("[4/4] Analyzing pages...")
    crawl_findings = analyze_pages(context)
    
    # Step 5: Freshness and consistency audit
    print("\n[5/6] Running freshness/consistency audit...")
    context, freshness_findings = analyze_freshness_consistency(context, crawl_findings)
    
    # Step 6: Engagement audit
    print("[6/6] Running engagement audit...")
    context, engagement_findings = analyze_engagement(context, crawl_findings)
    
    # Collect all findings
    all_findings = crawl_findings + freshness_findings + engagement_findings
    
    # Normalize severities
    for finding in all_findings:
        finding['severity'] = normalize_severity(finding.get('severity', 'info'))
    
    # Deduplicate
    all_findings = deduplicate_findings(all_findings)
    
    # Calculate priority
    for finding in all_findings:
        finding['priority'] = calculate_priority(finding)
    
    # Sort by priority (highest first)
    all_findings.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    # Generate recommendations
    recommendations = generate_recommendations(all_findings)
    
    # Calculate summary
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    for finding in all_findings:
        severity = finding.get('severity', 'info')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    duration = time.time() - start_time
    
    # Build final report
    report = {
        'meta': {
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'duration_seconds': round(duration, 2),
            'target_url': normalized_url,
            'domain': domain,
            'pages_crawled': len(context.get('pages', []))
        },
        'summary': {
            'total_findings': len(all_findings),
            'critical': severity_counts['critical'],
            'high': severity_counts['high'],
            'medium': severity_counts['medium'],
            'low': severity_counts['low'],
            'info': severity_counts['info'],
            'overall_score': calculate_overall_score(all_findings),
            'top_issues': [
                {
                    'title': f.get('title'),
                    'severity': f.get('severity'),
                    'priority': f.get('priority')
                }
                for f in all_findings[:5]
            ]
        },
        'findings': all_findings,
        'recommendations': recommendations,
        'audit_context': {
            'site': context.get('site', {}),
            'robots': {
                'available': context.get('robots', {}).get('available', False),
                'sitemap_url': context.get('robots', {}).get('sitemap_url')
            },
            'sitemap': {
                'available': context.get('sitemap', {}).get('available', False)
            },
            'entity_identity': context.get('entity_identity', {}),
            'engagement_summary': context.get('engagement_summary', {})
        }
    }
    
    print(f"\nAudit complete in {duration:.2f} seconds")
    print(f"Found {len(all_findings)} findings")
    print(f"Overall score: {report['summary']['overall_score']}/100")
    
    return report


def save_report(report: Dict, output_path: str = None) -> str:
    """
    Save audit report to JSON file.
    
    Args:
        report: Audit report dictionary
        output_path: Output file path (optional)
        
    Returns:
        Path to saved file
    """
    if not output_path:
        domain = report['meta']['domain'].replace('.', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"audit_report_{domain}_{timestamp}.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Report saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run brand AI readiness audit')
    parser.add_argument('url', help='Target website URL or domain')
    parser.add_argument('--max-pages', type=int, default=20, help='Maximum pages to crawl')
    parser.add_argument('--max-depth', type=int, default=2, help='Maximum crawl depth')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    try:
        report = run_audit(
            url=args.url,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            timeout=args.timeout,
            delay=args.delay
        )
        
        output_path = save_report(report, args.output)
        
        # Print summary
        print("\n" + "="*60)
        print("AUDIT SUMMARY")
        print("="*60)
        print(f"Target: {report['meta']['target_url']}")
        print(f"Pages crawled: {report['meta']['pages_crawled']}")
        print(f"Duration: {report['meta']['duration_seconds']}s")
        print(f"Overall score: {report['summary']['overall_score']}/100")
        print(f"\nFindings by severity:")
        print(f"  Critical: {report['summary']['critical']}")
        print(f"  High: {report['summary']['high']}")
        print(f"  Medium: {report['summary']['medium']}")
        print(f"  Low: {report['summary']['low']}")
        print(f"  Info: {report['summary']['info']}")
        print("="*60)
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
