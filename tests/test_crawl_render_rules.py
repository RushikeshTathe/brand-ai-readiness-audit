"""
Counterexample review for crawl-render decision rules.

Encodes the 4 key cases from Adobe_R3_Audit_Research_README.md as
synthetic-signal tests (no network). A false positive = a failure finding
emitted where the research says none is warranted; a false negative =
a required finding missing.

Key cases: Dot & Key, Healthline, Nordstrom, Saraswat Bank.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'crawl-render-audit', 'scripts'))

from rules import apply_rules  # type: ignore
from ai_robots import check_ai_access, parse_robots_txt  # type: ignore
from waf_detector import detect_blockade  # type: ignore
from facts import compare_facts  # type: ignore
from text_extract import extract_text, expansion_stats  # type: ignore


def _base_signals(**over):
    sig = {
        "blockade": {"blocked": False, "kind": None, "signals": [], "status": 200},
        "ai_access": {"blocked_bots": [], "bots": {}},
        "fact_summary": {"total": 0, "in_raw": 0, "js_dependent": 0,
                         "jsonld_rescue": 0, "missing_everywhere": 0},
        "fact_matrix": [],
        "expansion": {"raw_words": 500, "rendered_words": 550, "abs_gain": 50,
                      "pct_gain": 10.0, "screening_triggered": False},
        "jsonld": {"objects_count": 0, "errors_count": 0},
        "render_ok": True,
    }
    sig.update(over)
    return sig


def _ids(findings):
    return [f["id"] for f in findings]


class TestDotAndKey:
    """Large expansion + price in JSON-LD => NO RENDER failure."""

    def test_jsonld_rescue_suppresses_csr_failure(self):
        facts = [{"key": "price", "value": "Rs. 495"}]
        raw_text = "Dot & Key Vitamin C moisturizer nav footer " * 20
        jsonld_blob = "product dot & key vitamin c moisturizer rs. 495 in stock"
        rendered_text = raw_text + " extra widgets reviews footer links " * 60
        res = compare_facts(facts, raw_text, jsonld_blob, rendered_text)
        assert res["summary"]["jsonld_rescue"] == 1
        assert res["summary"]["js_dependent"] == 0

        raw = extract_text("<html><body>" + raw_text + "</body></html>")
        ren = extract_text("<html><body>" + rendered_text + "</body></html>")
        exp = expansion_stats(raw, ren)
        assert exp["screening_triggered"]  # big expansion really happened

        findings = apply_rules(_base_signals(
            fact_summary=res["summary"], fact_matrix=res["matrix"],
            expansion=exp, render_ok=True,
            jsonld={"objects_count": 1, "errors_count": 0}))
        assert "RENDER-001" not in _ids(findings), "FP: expansion+JSON-LD must not fail"
        assert "SCHEMA-001" in _ids(findings)


class TestHealthline:
    """Strong raw HTML + AI bot block => POLICY fires, layers stay separate."""

    def test_policy_fires_despite_good_html(self):
        robots = "User-agent: PerplexityBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n"
        access = check_ai_access(robots, ["/"])
        assert "perplexitybot" in access["blocked_bots"]

        facts = [{"key": "symptom", "value": "migraine treatment options"}]
        blob = "migraine treatment options include rest and hydration"
        res = compare_facts(facts, blob, "", blob)
        assert res["summary"]["in_raw"] == 1

        findings = apply_rules(_base_signals(
            ai_access=access, fact_summary=res["summary"],
            fact_matrix=res["matrix"]))
        assert "POLICY-001" in _ids(findings), "FN: AI bot block must be flagged"
        assert "RENDER-001" not in _ids(findings)
        assert "ACCESS-001" not in _ids(findings)


class TestNordstrom:
    """403/WAF => ACCESS critical; CSR diagnosis skipped under blockade."""

    def test_blockade_suppresses_csr_diagnosis(self):
        html = "<html><head><title>Access Denied</title></head><body>Attention Required! captcha challenge __cf_bm</body></html>"
        blockade = detect_blockade(403, {"server": "cloudflare", "content-type": "text/html"}, html)
        assert blockade["blocked"] is True

        findings = apply_rules(_base_signals(
            blockade=blockade, render_ok=False,
            expansion={"raw_words": 50, "rendered_words": None, "abs_gain": None,
                       "pct_gain": None, "screening_triggered": False}))
        assert "ACCESS-001" in _ids(findings)
        assert findings[0]["severity"] == "critical"
        assert "RENDER-001" not in _ids(findings), "FP: no CSR claims under blockade"


class TestSaraswatBank:
    """Rendered growth but rate fact in static HTML => no JS dependency."""

    def test_static_fact_beats_word_counts(self):
        facts = [{"key": "fd-rate", "value": "7.10% p.a."}]
        raw_text = "Fixed deposit interest rates table 1 year 7.10% p.a. 5 years 7.50% p.a."
        rendered_text = raw_text + " online banking login widgets footer links " * 40
        res = compare_facts(facts, raw_text, "", rendered_text)
        assert res["summary"]["in_raw"] == 1
        assert res["summary"]["js_dependent"] == 0

        findings = apply_rules(_base_signals(
            fact_summary=res["summary"], fact_matrix=res["matrix"]))
        assert "RENDER-001" not in _ids(findings), "FP: word growth != fact dependency"


class TestTruePositiveCSR:
    """Fact only after rendering, absent raw+JSON-LD => RENDER-001 fires."""

    def test_genuine_js_dependency_flagged(self):
        facts = [{"key": "price", "value": "INR 2999"}]
        res = compare_facts(facts, "empty shell nav footer", "",
                            "product page price INR 2999 add to cart")
        assert res["summary"]["js_dependent"] == 1
        findings = apply_rules(_base_signals(
            fact_summary=res["summary"], fact_matrix=res["matrix"]))
        assert "RENDER-001" in _ids(findings)


class TestParserUnits:
    def test_allow_wins_and_empty_disallow(self):
        robots = ("User-agent: GPTBot\nDisallow: /\nAllow: /public/\n\n"
                  "User-agent: *\nDisallow:\n")
        access = check_ai_access(robots, ["/public/prices"])
        assert access["bots"]["gptbot"]["blocked_paths"] == []
        access2 = check_ai_access(robots, ["/private"])
        assert "/private" in access2["bots"]["gptbot"]["blocked_paths"]

    def test_missing_robots_is_not_a_failure(self):
        access = check_ai_access("", ["/"])
        assert access["blocked_bots"] == []
        findings = apply_rules(_base_signals(ai_access=access))
        assert "POLICY-001" not in _ids(findings)

    def test_429_is_rate_limited_blockade(self):
        b = detect_blockade(429, {"retry-after": "60"}, "slow down")
        assert b["blocked"] and b["kind"] == "rate-limited"

    def test_ok_page_not_blocked(self):
        b = detect_blockade(200, {"content-type": "text/html"},
                            "<html><head><title>Shop</title></head><body>hello</body></html>")
        assert b["blocked"] is False

    def test_expansion_screening_threshold(self):
        raw = {"word_count": 1000, "text": "", "char_count": 0}
        small = {"word_count": 1100, "text": "", "char_count": 0}
        assert expansion_stats(raw, small)["screening_triggered"] is False
        big = {"word_count": 1500, "text": "", "char_count": 0}
        assert expansion_stats(raw, big)["screening_triggered"] is True
