"""
Test report schema validation for Adobe Round 3 required contract.
"""

from datetime import datetime
import os
import sys

# Add skills directory to path
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "skills",
            "audit-orchestrator",
            "scripts",
        )
    ),
)

from orchestrator import (
    generate_finding_id,
    normalize_finding,
    normalize_severity,
    orchestrate_audit,
    validate_url,
)


class TestReportSchema:
    """Test the audit report schema compliance."""

    def test_report_has_required_top_level_keys(self):
        """Report must contain site, audited_at, summary, and findings."""
        report = orchestrate_audit("https://example.com")

        assert "site" in report
        assert report["site"] == "https://example.com"

        assert "audited_at" in report
        dt = datetime.fromisoformat(report["audited_at"])
        assert dt is not None

        assert "summary" in report
        summary = report["summary"]
        assert "total_findings" in summary
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary

        assert "findings" in report
        assert isinstance(report["findings"], list)

    def test_finding_has_required_fields(self):
        """Every finding in report must contain id, title, severity, evidence, suggested_action."""
        raw_finding = {
            "check_id": "TEST-001",
            "message": "Sample issue",
            "severity": "HIGH",
            "evidence": "Observed missing tag",
            "recommendation": "Add the missing tag",
            "custom_extra_field": "preserved_val",
        }

        normalized = normalize_finding(raw_finding)

        assert "id" in normalized
        assert normalized["id"] == "TEST-001"
        assert "title" in normalized
        assert normalized["title"] == "Sample issue"
        assert "severity" in normalized
        assert normalized["severity"] == "high"
        assert "evidence" in normalized
        assert normalized["evidence"] == "Observed missing tag"
        assert "suggested_action" in normalized
        assert normalized["suggested_action"] == "Add the missing tag"
        assert normalized["custom_extra_field"] == "preserved_val"

    def test_orchestrator_findings_schema(self):
        """Verify all findings produced in an actual audit meet the contract."""
        report = orchestrate_audit("https://example.com")

        for finding in report["findings"]:
            assert "id" in finding
            assert "title" in finding
            assert "severity" in finding
            assert "evidence" in finding
            assert "suggested_action" in finding

    def test_summary_counter_calculation(self):
        """Verify summary counters accurately reflect normalized findings."""
        report = orchestrate_audit("https://example.com")
        summary = report["summary"]
        findings = report["findings"]

        assert summary["total_findings"] == len(findings)
        assert summary["critical"] == sum(
            1 for f in findings if f["severity"] == "critical"
        )
        assert summary["high"] == sum(
            1 for f in findings if f["severity"] == "high"
        )
        assert summary["medium"] == sum(
            1 for f in findings if f["severity"] == "medium"
        )


class TestBasicChecks:
    """Test helper functions."""

    def test_validate_url(self):
        assert validate_url("example.com") == "https://example.com"

    def test_normalize_severity(self):
        assert normalize_severity("HIGH") == "high"
        assert normalize_severity("error") == "high"
        assert normalize_severity("warning") == "medium"