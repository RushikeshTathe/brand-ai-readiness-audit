"""
Sitemap discovery (baseline only).

Task: origin/robots -> sitemap locations.
Per research README: sitemap existence / URL count are REJECTED as
standalone checks. This module only discovers locations and fetches them
for baseline context (used to resolve relative robots Sitemap lines).

It never emits pass/fail. Decision rules must not fail a site for
missing sitemap.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List
from urllib.parse import urljoin

import requests


def discover_sitemap_urls(robots_text: str, origin: str) -> List[str]:
    """Return ordered unique sitemap URLs from robots.txt + default location."""
    found: List[str] = []
    for line in (robots_text or "").splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            loc = line.split(":", 1)[1].strip().split()[0] if ":" in line else ""
            if loc:
                # Resolve relative sitemap paths against origin.
                found.append(urljoin(origin.rstrip("/") + "/", loc))
    default = urljoin(origin.rstrip("/") + "/", "/sitemap.xml")
    if default not in found:
        found.append(default)
    # De-duplicate preserving order.
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def fetch_sitemap(url: str, timeout: int = 15) -> Dict:
    """Fetch one sitemap URL; return baseline observation (never raises)."""
    result: Dict = {
        "url": url,
        "available": False,
        "status": 0,
        "content_type": "",
        "is_index": False,
        "locs": [],
        "count": 0,
        "error": None,
    }
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "BrandAuditBot/1.0"},
            timeout=timeout,
        )
        result["status"] = resp.status_code
        result["content_type"] = resp.headers.get("Content-Type", "")
        if resp.status_code != 200 or not resp.text:
            result["error"] = f"http-{resp.status_code}"
            return result
        try:
            root = ET.fromstring(resp.text.encode("utf-8", "ignore"))
        except ET.ParseError as e:
            result["error"] = f"xml-parse-error: {e}"
            return result
        tag = root.tag.lower()
        result["is_index"] = "sitemapindex" in tag
        # <loc> children of either <sitemap> or <url> entries.
        locs = [el.text.strip() for el in root.iter() if el.tag.lower().endswith("loc") and el.text and el.text.strip()]
        result["locs"] = locs[:5000]
        result["count"] = len(locs)
        result["available"] = True
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.RequestException as e:
        result["error"] = f"request-error: {e}"
    return result


def discover_and_fetch(robots_text: str, origin: str, timeout: int = 15) -> Dict:
    """Discover sitemap locations and fetch them; baseline context only."""
    urls = discover_sitemap_urls(robots_text, origin)
    fetched = [fetch_sitemap(u, timeout=timeout) for u in urls]
    return {"candidate_urls": urls, "sitemaps": fetched}
