"""
Audit Orchestrator - Main entrypoint for the Agent Skill Marketplace.
Coordinates all specialized audit skills and produces the final JSON report.
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Get base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.dirname(BASE_DIR)

# Add script paths to sys.path so scripts can be imported cleanly
crawl_render_path = os.path.join(SKILLS_DIR, "crawl-render-audit", "scripts")
freshness_path = os.path.join(SKILLS_DIR, "freshness-corroboration", "scripts")
engagement_path = os.path.join(SKILLS_DIR, "engagement-audit", "scripts")

if crawl_render_path not in sys.path:
    sys.path.insert(0, crawl_render_path)
if freshness_path not in sys.path:
    sys.path.insert(0, freshness_path)
if engagement_path not in sys.path:
    sys.path.insert(0, engagement_path)

# Direct imports from the added script paths
from audit import audit_url
from consistency import analyze_freshness_consistency
from engagement import analyze_engagement


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def validate_url(url: str) -> str:
    """Validate and normalize input URL."""
    if not url:
        raise ValueError("URL cannot be empty")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    netloc = parsed.netloc.lower()
    if "." not in netloc and not netloc.startswith("localhost"):
        raise ValueError(f"Invalid URL: {url}")

    if url.endswith("/"):
        url = url[:-1]

    return url


def normalize_severity(severity: str) -> str:
    """Normalize severity level to standard values."""
    valid_severities = ["critical", "high", "medium", "low", "info"]
    severity_lower = str(severity).lower().strip()

    if severity_lower in valid_severities:
        return severity_lower

    severity_map = {
        "error": "high",
        "warning": "medium",
        "notice": "low",
        "debug": "info",
        "critical": "critical",
        "major": "high",
        "minor": "low",
    }

    return severity_map.get(severity_lower, "info")


def calculate_priority(finding: Dict[str, Any]) -> int:
    """Calculate priority score for a finding (1-100, higher = more important)."""
    severity_scores = {
        "critical": 90,
        "high": 70,
        "medium": 50,
        "low": 30,
        "info": 10,
    }

    base_score = severity_scores.get(finding.get("severity", "info"), 10)

    category_multipliers = {
        "html": 1.1,
        "orientation": 1.2,
        "navigation": 1.1,
        "identity": 1.0,
        "consistency": 0.9,
        "freshness": 0.8,
    }

    category = finding.get("category", "")
    multiplier = category_multipliers.get(category, 1.0)

    return min(100, int(base_score * multiplier))


def generate_finding_id(finding: Dict[str, Any]) -> str:
    """Generate a unique, deterministic ID for a finding."""
    existing_id = finding.get("id") or finding.get("check_id")
    if existing_id:
        return str(existing_id)

    key_fields = [
        str(finding.get("skill", "")),
        str(finding.get("category", "")),
        str(finding.get("title", finding.get("message", ""))),
        str(finding.get("location", "")),
    ]

    hash_input = "|".join(key_fields)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]

    return f"{finding.get('skill', 'unknown')}-{hash_value}"


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate findings based on content similarity."""
    seen = {}
    unique_findings = []

    for finding in findings:
        signature = f"{finding.get('category', '')}-{finding.get('title', finding.get('message', ''))}-{finding.get('location', '')}"

        if signature not in seen:
            seen[signature] = True
            if "id" not in finding:
                finding["id"] = generate_finding_id(finding)
            unique_findings.append(finding)

    return unique_findings


def normalize_finding(finding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize individual finding fields to conform to the Adobe Round 3 output schema.
    Guarantees 'id', 'title', 'severity', 'evidence', and 'suggested_action'.
    Preserves all extra fields.
    """
    norm = dict(finding)

    # 1. Normalize ID
    norm["id"] = generate_finding_id(finding)

    # 2. Normalize Title
    norm["title"] = (
        finding.get("title")
        or finding.get("message")
        or finding.get("name")
        or norm["id"]
    )

    # 3. Normalize Severity
    norm["severity"] = normalize_severity(finding.get("severity", "info"))

    # 4. Normalize Evidence
    norm["evidence"] = finding.get("evidence", "")

    # 5. Normalize Suggested Action (Map recommendation -> suggested_action)
    norm["suggested_action"] = (
        finding.get("suggested_action")
        or finding.get("recommendation")
        or finding.get("action")
        or ""
    )

    return norm


def orchestrate_audit(
    url: str, target_facts: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Run full multi-skill audit pipeline for a target URL and return Adobe-compliant report.
    """
    start_time = time.time()
    normalized_url = validate_url(url)
    audited_at = datetime.now(timezone.utc).isoformat()

    # Step 1: Execute primary crawl-render-audit pipeline
    crawl_render_result = audit_url(normalized_url, target_facts=target_facts)

    # Map output payload for downstream specialist skills
    http_data = crawl_render_result.get("http", {})
    raw_ext = crawl_render_result.get("raw_extraction", {})
    rend_data = crawl_render_result.get("rendering", {})
    json_ld = crawl_render_result.get("json_ld", [])

    crawl_data = {
        "url": normalized_url,
        "status_code": http_data.get("status", 0),
        "headers": http_data.get("headers", {}),
        "raw_html": http_data.get("raw_html", ""),
        "text": raw_ext.get("text", "") if isinstance(raw_ext, dict) else "",
        "word_count": raw_ext.get("word_count", 0) if isinstance(raw_ext, dict) else 0,
        "rendered_text": (
            rend_data.get("extracted_facts", {}).get("text", "")
            if rend_data.get("executed")
            else ""
        ),
        "rendered_word_count": rend_data.get("word_count", 0),
        "json_ld": json_ld,
        "extracted_facts": crawl_render_result.get("extracted_facts", {}),
        "pages": [
            {
                "url": normalized_url,
                "html": http_data.get("raw_html", ""),
                "text": raw_ext.get("text", "") if isinstance(raw_ext, dict) else "",
            }
        ],
    }

    # Step 2: Execute Freshness Corroboration Skill
    freshness_findings = []
    try:
        res = analyze_freshness_consistency(
            crawl_data, crawl_render_result.get("findings", [])
        )
        if isinstance(res, tuple):
            freshness_findings = res[1]
        elif isinstance(res, list):
            freshness_findings = res
        elif isinstance(res, dict):
            freshness_findings = res.get("findings", [])
    except Exception:
        freshness_findings = []

    # Step 3: Execute Engagement Audit Skill
    engagement_findings = []
    try:
        res = analyze_engagement(crawl_data, crawl_render_result.get("findings", []))
        if isinstance(res, tuple):
            engagement_findings = res[1]
        elif isinstance(res, list):
            engagement_findings = res
        elif isinstance(res, dict):
            engagement_findings = res.get("findings", [])
    except Exception:
        engagement_findings = []

    # Aggregate findings from all skills
    raw_findings: List[Dict[str, Any]] = []
    raw_findings.extend(crawl_render_result.get("findings", []))
    raw_findings.extend(freshness_findings)
    raw_findings.extend(engagement_findings)

    # Deduplicate and normalize findings
    deduped_findings = deduplicate_findings(raw_findings)
    normalized_findings = [normalize_finding(f) for f in deduped_findings]

    # Calculate summary counters dynamically
    summary = {
        "total_findings": len(normalized_findings),
        "critical": sum(1 for f in normalized_findings if f["severity"] == "critical"),
        "high": sum(1 for f in normalized_findings if f["severity"] == "high"),
        "medium": sum(1 for f in normalized_findings if f["severity"] == "medium"),
        "low": sum(1 for f in normalized_findings if f["severity"] == "low"),
        "info": sum(1 for f in normalized_findings if f["severity"] == "info"),
    }

    # Emit Adobe Round 3 top-level schema contract
    report = {
        "site": normalized_url,
        "audited_at": audited_at,
        "summary": summary,
        "findings": normalized_findings,
        "meta": {
            "target_url": normalized_url,
            "duration_seconds": round(time.time() - start_time, 2),
        },
        "details": {
            "crawl_render": crawl_render_result,
            "freshness": freshness_findings,
            "engagement": engagement_findings,
        },
    }

    return report


def run_audit(url: str, **kwargs) -> Dict[str, Any]:
    """CLI / Legacy entrypoint wrapper."""
    return orchestrate_audit(url)


def save_report(report: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Save audit report to JSON file."""
    if not output_path:
        parsed = urlparse(report.get("site", "audit"))
        domain = parsed.netloc.replace(".", "_") or "site"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"audit_report_{domain}_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run brand AI readiness audit")
    parser.add_argument("url", help="Target website URL or domain")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    try:
        report = run_audit(args.url)
        save_report(report, args.output)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)