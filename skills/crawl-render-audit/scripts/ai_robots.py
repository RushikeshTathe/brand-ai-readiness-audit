"""
AI-aware robots.txt parser (offline, RFC 9309 subset).

Task: robots.txt -> AI bot directives.
Research: "AI bot restrictions in robots.txt" is a STRONG signal, while
"presence of a robots.txt file" alone is rejected as a standalone check.

Healthline lesson: HTML accessibility and crawler governance are separate
layers — this module reports policy only, never HTML quality.

Distinguishes live conversational-search agents (ChatGPT-User,
PerplexityBot, Claude-Web...) from training crawlers (CCBot,
Google-Extended...) via the `kind` field, but flags both when they block
public target content.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

# AI crawler directory: token -> kind. `kind` is informational only.
AI_BOTS: Dict[str, str] = {
    "gptbot": "training-crawler",
    "chatgpt-user": "live-search-agent",
    "oai-searchbot": "live-search-agent",
    "claudebot": "training-crawler",
    "claude-web": "live-search-agent",
    "anthropic-ai": "training-crawler",
    "perplexitybot": "live-search-agent",
    "google-extended": "training-crawler",
    "googleother": "training-crawler",
    "bytespider": "training-crawler",
    "amazonbot": "live-search-agent",
    "applebot-extended": "training-crawler",
    "diffbot": "service-crawler",
    "ccbot": "training-crawler",
    "cohere-ai": "training-crawler",
    "meta-externalagent": "training-crawler",
    "mistralai-user": "live-search-agent",
    "youbot": "live-search-agent",
}

DEFAULT_TARGETS = ["/"]


def fetch_robots_txt(origin: str, timeout: int = 15,
                     user_agent: str = "BrandAuditBot/1.0") -> Dict:
    """Fetch /robots.txt; never raises. Returns {available, status, text, url, error}."""
    url = origin.rstrip("/") + "/robots.txt"
    out = {"available": False, "status": 0, "text": "", "url": url, "error": None}
    try:
        resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
        out["status"] = resp.status_code
        if resp.status_code == 200 and resp.text is not None:
            out["available"] = True
            out["text"] = resp.text[:200_000]
        else:
            out["error"] = f"http-{resp.status_code}"
    except requests.exceptions.Timeout:
        out["error"] = "timeout"
    except requests.exceptions.RequestException as e:
        out["error"] = f"request-error: {e}"
    return out


def parse_robots_txt(text: str) -> Dict:
    """Parse robots.txt into groups: [{agents:[...], allow:[...], disallow:[...]}].

    Handles repeated User-agent lines per group, comments, case-insensitive
    directives. `Allow`/`Disallow` values stored raw (path prefixes).
    Also collects `sitemaps` and `crawl_delays`.
    """
    groups: List[Dict] = []
    sitemaps: List[str] = []
    current: Optional[Dict] = None

    def new_group():
        return {"agents": [], "allow": [], "disallow": [], "crawl_delay": None}

    current = None
    for raw_line in (text or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            agent = value.lower()
            if current is None or (current["allow"] or current["disallow"] or current.get("crawl_delay") is not None):
                # Start new group when previous group already has rules and
                # we see another user-agent line (standard grouping).
                if current is not None and current["agents"]:
                    groups.append(current)
                current = new_group()
            if current is None:
                current = new_group()
            current["agents"].append(agent)
        elif field in ("allow", "disallow"):
            if current is None:
                current = new_group()
            if value or field == "disallow":
                # Empty Disallow means allow-all; keep as "" marker.
                current[field].append(value)
        elif field == "crawl-delay":
            if current is None:
                current = new_group()
            try:
                current["crawl_delay"] = float(value.split()[0])
            except ValueError:
                current["crawl_delay"] = value
        elif field == "sitemap":
            if value:
                sitemaps.append(value.split()[0])
    if current is not None and current["agents"]:
        groups.append(current)
    return {"groups": groups, "sitemaps": sitemaps}


def _group_matches_agent(group_agents: List[str], ua_token: str) -> bool:
    ua = ua_token.lower()
    for agent in group_agents:
        a = agent.lower().strip()
        if a == "*":
            return True
        # robots matching is prefix/substring-insensitive; use containment
        # so "perplexitybot/1.0" or "anthropic-ai" variants still match.
        if a and (a in ua or ua in a):
            return True
    return False


def _path_disallowed(rules: Dict, path: str) -> Optional[str]:
    """Longest-prefix match per RFC 9309 (Allow wins ties). Returns matched rule or None."""
    if not path.startswith("/"):
        path = "/" + path
    best_allow, best_disallow = -1, -1
    best_dis_rule = None
    for rule in rules.get("allow", []):
        r = rule.strip()
        if r and (path == r or path.startswith(r)):
            best_allow = max(best_allow, len(r))
    for rule in rules.get("disallow", []):
        r = rule.strip()
        if r == "":
            continue  # empty Disallow = allow all
        if r == "/" or path == r or path.startswith(r):
            if len(r) > best_disallow:
                best_disallow = len(r)
                best_dis_rule = r
    if best_dis_rule is not None and best_disallow >= best_allow:
        return best_dis_rule
    return None


def check_ai_access(robots_text: str, target_paths: Optional[List[str]] = None) -> Dict:
    """Evaluate AI bot access against target paths.

    Returns {
      "ai_directives_found": bool,
      "bots": {token: {"kind": str, "blocked_paths": [...], "matched_rule": str|None}},
      "blocked_bots": [tokens blocking >=1 target path],
      "sitemaps": [...],
      "note": str,
    }
    Never fails a site for missing robots.txt: empty text -> no directives.
    """
    targets = target_paths or DEFAULT_TARGETS
    parsed = parse_robots_txt(robots_text or "")
    wildcard_group = None
    for g in parsed["groups"]:
        if any(a.strip() == "*" for a in g["agents"]):
            wildcard_group = g
            break
    bots: Dict[str, Dict] = {}
    for token, kind in AI_BOTS.items():
        matched_rules: Optional[Dict] = None
        for g in parsed["groups"]:
            if _group_matches_agent(g["agents"], token):
                matched_rules = g
                break
        # Fall back to wildcard group if no explicit group.
        effective = matched_rules if matched_rules is not None else wildcard_group
        blocked_paths: List[str] = []
        matched_rule = None
        if effective is not None:
            for path in targets:
                hit = _path_disallowed(effective, path)
                if hit is not None:
                    blocked_paths.append(path)
                    matched_rule = hit
        bots[token] = {"kind": kind, "blocked_paths": blocked_paths, "matched_rule": matched_rule}
    blocked = [t for t, b in bots.items() if b["blocked_paths"]]
    return {
        "ai_directives_found": any(
            any(_group_matches_agent(g["agents"], t) for t in AI_BOTS) for g in parsed["groups"]
        ),
        "bots": bots,
        "blocked_bots": blocked,
        "sitemaps": parsed["sitemaps"],
        "note": "missing robots.txt means no AI directives found (not a failure)",
    }
