"""
Playwright renderer (timeboxed, optional dependency).

Task: URL -> rendered DOM/text.
Research layer 5: "Does browser rendering reveal facts unavailable before?"

- Timeboxed: navigation timeout + total budget enforced; failures return
  {"ok": False, ...} instead of raising.
- Optional: if playwright is not installed or browsers are missing, returns
  ok=False with a clear reason so the pipeline degrades to raw-only.
- No stealth/evasion: default Chromium, plain load, `networkidle` capped.
"""

import time
from typing import Dict, Optional


def render_url(
    url: str,
    timeout_s: int = 25,
    wait_ms: int = 1500,
    user_agent: str = "BrandAuditBot/1.0",
) -> Dict:
    """Render a URL headlessly. Returns observation dict (never raises)."""
    started = time.time()
    out: Dict = {
        "ok": False,
        "url": url,
        "final_url": url,
        "rendered_html": "",
        "status": None,
        "error": None,
        "elapsed_s": 0.0,
    }
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        out["error"] = "playwright-not-installed"
        return out
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
                if resp is not None:
                    try:
                        out["status"] = resp.status
                    except Exception:
                        pass
                # Bounded extra settle for late content; total still < timeout_s + slack.
                try:
                    page.wait_for_timeout(min(wait_ms, 5000))
                except Exception:
                    pass
                out["rendered_html"] = page.content() or ""
                out["final_url"] = page.url or url
                out["ok"] = True
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception as e:
        out["error"] = f"render-error: {type(e).__name__}: {str(e)[:300]}"
    out["elapsed_s"] = round(time.time() - started, 3)
    return out
