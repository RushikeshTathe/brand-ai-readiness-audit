"""
Runtime benchmark & short-circuit tests for crawl-render-audit pipeline.
"""

import os
import sys
import time
from unittest.mock import patch

import pytest

# Ensure skill scripts path is accessible
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "skills",
            "crawl-render-audit",
            "scripts",
        )
    ),
)

from audit import audit_url  # type: ignore

SITES = [
    "https://example.com",
    "https://www.wikipedia.org",
    "https://docs.github.com",
]

PER_SITE_BUDGET_S = 45.0


@pytest.mark.parametrize("site", SITES)
def test_raw_only_runtime_within_budget(site):
    """Assert non-render pipeline completes within budget on lightweight sites."""
    started = time.time()
    result = audit_url(site, target_facts=[], render=False)
    wall = time.time() - started
    print(
        f"\n{site}: total={result['timings'].get('total_s')}s wall={wall:.2f}s "
        f"http={result['timings'].get('http_s')}s findings={len(result['findings'])}"
    )
    assert wall < PER_SITE_BUDGET_S, f"{site} took {wall:.1f}s > {PER_SITE_BUDGET_S}s"


def test_render_runtime_timeboxed():
    """Single render measurement; skipped gracefully without browser binaries."""
    pytest.importorskip("playwright")
    from renderer import render_url  # type: ignore

    started = time.time()
    out = render_url("https://example.com", timeout_s=25)
    wall = time.time() - started
    print(
        f"\nrender example.com: ok={out['ok']} elapsed={out.get('elapsed_s')}s wall={wall:.2f}s err={out.get('error')}"
    )
    assert wall < 60.0
    if not out["ok"]:
        pytest.skip(f"renderer unavailable: {out.get('error')}")


def test_short_circuit_facts_in_raw_html():
    """Case 1: When target facts exist in raw HTML, rendering should be skipped."""
    raw_html = "<html><body><h1>Product Page</h1><p>Price is Rs. 495</p></body></html>"

    with patch("audit.fetch_url") as mock_fetch, patch("audit.render_url") as mock_render:
        mock_fetch.return_value = {
            "status": 200,
            "url": "https://example.com/item",
            "final_url": "https://example.com/item",
            "raw_html": raw_html,
            "headers": {"content-type": "text/html"},
            "error": None,
        }
        mock_render.return_value = {"ok": False, "rendered_html": "", "error": "render-skipped"}

        res = audit_url(
            "https://example.com/item",
            target_facts=[{"key": "price", "value": "Rs. 495"}],
            render=True,
        )

        mock_render.assert_not_called()
        assert res["signals"]["render_ok"] is False
        assert res["signals"]["render_error"] == "render-skipped-facts-resolved"

        js_findings = [
            f
            for f in res["findings"]
            if "CRA-JS" in str(f.get("id", "")) or "CRA-JS" in str(f.get("check_id", ""))
        ]
        assert len(js_findings) == 0


def test_render_invoked_when_facts_missing_pre_render():
    """Case 2: When target facts are absent pre-render, rendering must be attempted."""
    raw_html = "<html><body><h1>Loading...</h1></body></html>"
    rendered_html = "<html><body><h1>Product Page</h1><p>Price: Rs. 495</p></body></html>"

    with patch("audit.fetch_url") as mock_fetch, patch("audit.render_url") as mock_render:
        mock_fetch.return_value = {
            "status": 200,
            "url": "https://example.com/item",
            "final_url": "https://example.com/item",
            "raw_html": raw_html,
            "headers": {"content-type": "text/html"},
            "error": None,
        }
        mock_render.return_value = {
            "ok": True,
            "rendered_html": rendered_html,
            "error": None,
        }

        res = audit_url(
            "https://example.com/item",
            target_facts=[{"key": "price", "value": "Rs. 495"}],
            render=True,
        )

        mock_render.assert_called_once()
        assert res["signals"]["render_ok"] is True


def test_render_skipped_on_waf_blockade():
    """Case 3: When WAF blockade occurs, rendering must be skipped and blockade finding preserved."""
    waf_html = "<html><head><title>Access Denied</title></head><body>403 Forbidden - Akamai Bot Manager</body></html>"

    with patch("audit.fetch_url") as mock_fetch, patch("audit.render_url") as mock_render:
        mock_fetch.return_value = {
            "status": 403,
            "url": "https://example.com/item",
            "final_url": "https://example.com/item",
            "raw_html": waf_html,
            "headers": {"server": "AkamaiGHost"},
            "error": "HTTP 403",
        }
        mock_render.return_value = {"ok": False, "rendered_html": "", "error": "render-skipped"}

        res = audit_url(
            "https://example.com/item",
            target_facts=[{"key": "price", "value": "Rs. 495"}],
            render=True,
        )

        mock_render.assert_not_called()
        assert res["signals"]["render_ok"] is False
        assert res["signals"]["render_error"] == "render-skipped-blockade"

        # Check for blockade/access finding
        access_findings = [
            f
            for f in res["findings"]
            if any(k in str(f.get("id", "")) or k in str(f.get("check_id", "")) for k in ["WAF", "ACCESS", "BLOCK"])
        ]
        assert len(access_findings) > 0


def test_short_circuit_facts_in_jsonld():
    """Case 4: When target facts exist in raw JSON-LD, rendering is skipped."""
    raw_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org/",
          "@type": "Product",
          "name": "Vitamin C Gel",
          "offers": {
            "@type": "Offer",
            "price": "Rs. 495",
            "priceCurrency": "INR"
          }
        }
        </script>
      </head>
      <body><h1>Product Page</h1></body>
    </html>
    """

    with patch("audit.fetch_url") as mock_fetch, patch("audit.render_url") as mock_render:
        mock_fetch.return_value = {
            "status": 200,
            "url": "https://example.com/item",
            "final_url": "https://example.com/item",
            "raw_html": raw_html,
            "headers": {"content-type": "text/html"},
            "error": None,
        }
        mock_render.return_value = {"ok": False, "rendered_html": "", "error": "render-skipped"}

        res = audit_url(
            "https://example.com/item",
            target_facts=[{"key": "price", "value": "Rs. 495"}],
            render=True,
        )

        mock_render.assert_not_called()
        assert res["signals"]["render_ok"] is False
        assert res["signals"]["render_error"] == "render-skipped-facts-resolved"

        js_findings = [
            f
            for f in res["findings"]
            if "CRA-JS" in str(f.get("id", "")) or "CRA-JS" in str(f.get("check_id", ""))
        ]
        assert len(js_findings) == 0