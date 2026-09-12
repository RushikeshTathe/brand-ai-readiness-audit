"""
Direct HTTP fetch (baseline, provider-neutral).

Task: URL -> status, headers, raw HTML.
Layer 1 of the research flow: "Can the automated request reach the page?"

Design rules (from Adobe_R3_Audit_Research_README.md):
- Report observations first, conclusions second.
- Do NOT treat status codes alone as failures here; the WAF detector
  and decision rules interpret them.
- Read-only GET, fixed User-Agent, timeboxed per request.
- Must never raise on network failure: return an observation dict.

Stdlib + requests only.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests


DEFAULT_USER_AGENT = "BrandAuditBot/1.0"
DEFAULT_TIMEOUT = 15


def normalize_url(url: str) -> str:
    """Add scheme if missing and strip trailing slash (except root)."""
    url = (url or "").strip()
    if not url:
        raise ValueError("URL cannot be empty")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    if len(url) > 1 and url.endswith("/"):
        url = url[:-1]
    return url


def fetch_url(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    allow_redirects: bool = True,
    max_bytes: int = 3_000_000,
) -> Dict:
    """Fetch a URL with a plain GET and return raw observations.

    Returns dict with keys:
      url, final_url, status, headers, raw_html (truncated at max_bytes),
      redirect_chain, elapsed_s, error, content_type, truncated
    Never raises; transport errors are captured in `error`.
    """
    normalized = normalize_url(url)
    result: Dict = {
        "url": normalized,
        "final_url": normalized,
        "status": 0,
        "headers": {},
        "raw_html": "",
        "redirect_chain": [],
        "elapsed_s": 0.0,
        "error": None,
        "content_type": "",
        "truncated": False,
    }
    try:
        resp = requests.get(
            normalized,
            headers={"User-Agent": user_agent, "Accept": "text/html,*/*"},
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
        result["status"] = resp.status_code
        # Lowercase header keys for provider-neutral matching downstream.
        result["headers"] = {k.lower(): v for k, v in resp.headers.items()}
        result["final_url"] = resp.url
        result["content_type"] = resp.headers.get("Content-Type", "")
        try:
            result["elapsed_s"] = round(resp.elapsed.total_seconds(), 3)
        except Exception:
            result["elapsed_s"] = 0.0
        result["redirect_chain"] = [
            {"url": h.url, "status": h.status_code} for h in resp.history
        ]
        text = resp.text or ""
        if len(text.encode("utf-8", "ignore")) > max_bytes:
            # Truncate on character boundary (approx) to bound memory.
            text = text[: max_bytes // 2]
            result["truncated"] = True
        result["raw_html"] = text
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.SSLError as e:
        result["error"] = f"ssl-error: {e}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection-error: {e}"
    except requests.exceptions.RequestException as e:
        result["error"] = f"request-error: {e}"
    except ValueError as e:
        result["error"] = str(e)
    return result


def origin_of(url: str) -> str:
    """Return scheme://netloc for a URL (used for robots/sitemap lookup)."""
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return f"{parsed.scheme}://{parsed.netloc}"
