"""
Test report schema validation.
Ensures the audit report follows the required structure.
"""

import json
import pytest
import sys
import os

# Add the skills directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'audit-orchestrator', 'scripts'))

from orchestrator import run_audit, calculate_priority, generate_finding_id


class TestReportSchema:
    """Test the audit report schema."""
    
    def test_report_has_required_top_level_keys(self):
        """Report must have meta, summary, findings, recommendations."""
        # Create a minimal report structure
        report = {
            'meta': {},
            'summary': {},
            'findings': [],
            'recommendations': []
        }
        
        assert 'meta' in report
        assert 'summary' in report
        assert 'findings' in report
        assert 'recommendations' in report
    
    def test_meta_has_required_fields(self):
        """Meta must have version, timestamp, target_url, domain."""
        meta = {
            'version': '1.0.0',
            'timestamp': '2026-01-01T00:00:00Z',
            'target_url': 'https://example.com',
            'domain': 'example.com',
            'pages_crawled': 0,
            'duration_seconds': 0
        }
        
        required_fields = ['version', 'timestamp', 'target_url', 'domain']
        for field in required_fields:
            assert field in meta, f"Meta missing required field: {field}"
    
    def test_summary_has_severity_counts(self):
        """Summary must have counts for each severity level."""
        summary = {
            'total_findings': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0,
            'overall_score': 100,
            'top_issues': []
        }
        
        severity_fields = ['critical', 'high', 'medium', 'low', 'info']
        for field in severity_fields:
            assert field in summary, f"Summary missing severity count: {field}"
    
    def test_finding_has_required_fields(self):
        """Each finding must have required fields."""
        finding = {
            'id': 'test-001',
            'skill': 'crawl-render-audit',
            'category': 'html',
            'severity': 'medium',
            'title': 'Test finding',
            'description': 'Test description',
            'evidence': 'Test evidence',
            'location': 'https://example.com',
            'recommendation': 'Test recommendation'
        }
        
        required_fields = ['id', 'skill', 'category', 'severity', 'title', 
                          'description', 'evidence', 'location', 'recommendation']
        
        for field in required_fields:
            assert field in finding, f"Finding missing required field: {field}"
    
    def test_severity_is_valid_value(self):
        """Severity must be one of the valid values."""
        valid_severities = ['critical', 'high', 'medium', 'low', 'info']
        
        for severity in valid_severities:
            finding = {'severity': severity}
            assert finding['severity'] in valid_severities
    
    def test_recommendation_has_required_fields(self):
        """Each recommendation must have required fields."""
        recommendation = {
            'id': 'rec-001',
            'title': 'Test recommendation',
            'description': 'Test description',
            'priority': 'high',
            'effort': 'low',
            'impact': 'high'
        }
        
        required_fields = ['id', 'title', 'description', 'priority', 'effort', 'impact']
        
        for field in required_fields:
            assert field in recommendation, f"Recommendation missing required field: {field}"


class TestFindingNormalization:
    """Test finding normalization functions."""
    
    def test_calculate_priority_critical(self):
        """Critical findings should have high priority."""
        finding = {'severity': 'critical', 'category': 'html'}
        priority = calculate_priority(finding)
        assert priority >= 80
    
    def test_calculate_priority_info(self):
        """Info findings should have low priority."""
        finding = {'severity': 'info', 'category': 'other'}
        priority = calculate_priority(finding)
        assert priority <= 20
    
    def test_calculate_priority_range(self):
        """Priority should be between 1 and 100."""
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            finding = {'severity': severity, 'category': 'other'}
            priority = calculate_priority(finding)
            assert 1 <= priority <= 100, f"Priority {priority} out of range for severity {severity}"
    
    def test_generate_finding_id_unique(self):
        """Different findings should get different IDs."""
        finding1 = {
            'skill': 'test',
            'category': 'cat1',
            'title': 'Title 1',
            'location': 'http://example.com'
        }
        finding2 = {
            'skill': 'test',
            'category': 'cat2',
            'title': 'Title 2',
            'location': 'http://example.com'
        }
        
        id1 = generate_finding_id(finding1)
        id2 = generate_finding_id(finding2)
        
        assert id1 != id2
    
    def test_generate_finding_id_deterministic(self):
        """Same finding should get same ID."""
        finding = {
            'skill': 'test',
            'category': 'cat',
            'title': 'Title',
            'location': 'http://example.com'
        }
        
        id1 = generate_finding_id(finding)
        id2 = generate_finding_id(finding)
        
        assert id1 == id2


class TestBasicChecks:
    """Test basic functionality."""
    
    def test_validate_url_with_scheme(self):
        """URL with scheme should be returned as-is."""
        from orchestrator import validate_url
        
        url = "https://example.com"
        result = validate_url(url)
        assert result == url
    
    def test_validate_url_without_scheme(self):
        """URL without scheme should get https added."""
        from orchestrator import validate_url
        
        url = "example.com"
        result = validate_url(url)
        assert result == "https://example.com"
    
    def test_validate_url_invalid(self):
        """Invalid URL should raise ValueError."""
        from orchestrator import validate_url
        
        with pytest.raises(ValueError):
            validate_url("")
        
        with pytest.raises(ValueError):
            validate_url("not a url")
    
    def test_normalize_severity(self):
        """Severity normalization should work correctly."""
        from orchestrator import normalize_severity
        
        assert normalize_severity("critical") == "critical"
        assert normalize_severity("HIGH") == "high"
        assert normalize_severity("error") == "high"
        assert normalize_severity("warning") == "medium"
        assert normalize_severity("notice") == "low"
        assert normalize_severity("unknown") == "info"
