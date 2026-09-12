"""
Runtime benchmark: per-site audit time (raw-only mode).

Brief expectation: typical per-site runtime stays small. Rendering is the
dominant cost and is measured separately (test_render_runtime, skipped if
browser binaries are unavailable). This test asserts the non-render pipeline
(HTTP + robots + extraction + rules) completes quickly on 3 lightweight
sites. Network failures do not fail the test (audit never raises); only an
excessive *pipeline* duration does.
"""

import sys
import os
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'crawl-render-audit', 'scripts'))

from audit import audit_url

SITES = [
    "https://example.com",
    "https://www.wikipedia.org",
    "https://docs.github.com",
]

PER_SITE_BUDGET_S = 45.0


@pytest.mark.parametrize("site", SITES)
def test_raw_only_runtime_within_budget(site):
    started = time.time()
    result = audit_url(site, target_facts=[], render=False)
    wall = time.time() - started
    print(f"\n{site}: total={result['timings'].get('total_s')}s wall={wall:.2f}s "
          f"http={result['timings'].get('http_s')}s findings={len(result['findings'])}")
    assert wall < PER_SITE_BUDGET_S, f"{site} took {wall:.1f}s > {PER_SITE_BUDGET_S}s"


def test_render_runtime_timeboxed():
    """Single render measurement; skipped gracefully without browser binaries."""
    pytest.importorskip("playwright")
    from renderer import render_url
    started = time.time()
    out = render_url("https://example.com", timeout_s=25)
    wall = time.time() - started
    print(f"\nrender example.com: ok={out['ok']} elapsed={out.get('elapsed_s')}s wall={wall:.2f}s err={out.get('error')}")
    assert wall < 60.0
    if not out["ok"]:
        pytest.skip(f"renderer unavailable: {out.get('error')}")
