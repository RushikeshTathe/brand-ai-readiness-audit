"""
Test finding normalization.
Tests for severity normalization, deduplication, and priority calculation.
"""

import pytest
import sys
import os

# Add the skills directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'audit-orchestrator', 'scripts'))

from orchestrator import (  # type: ignore
    normalize_severity,
    deduplicate_findings,
    calculate_priority,
    generate_finding_id
)


class TestSeverityNormalization:
    """Test severity normalization."""
    
    def test_standard_severities(self):
        """Standard severity values should pass through."""
        standard = ['critical', 'high', 'medium', 'low', 'info']
        for severity in standard:
            assert normalize_severity(severity) == severity
    
    def test_case_insensitive(self):
        """Severity normalization should be case insensitive."""
        assert normalize_severity("CRITICAL") == "critical"
        assert normalize_severity("High") == "high"
        assert normalize_severity("MEDIUM") == "medium"
    
    def test_common_aliases(self):
        """Common aliases should map correctly."""
        aliases = {
            'error': 'high',
            'warning': 'medium',
            'notice': 'low',
            'debug': 'info',
            'major': 'high',
            'minor': 'low'
        }
        
        for alias, expected in aliases.items():
            assert normalize_severity(alias) == expected, f"Alias {alias} should map to {expected}"
    
    def test_unknown_defaults_to_info(self):
        """Unknown severity should default to info."""
        unknown_severities = ['unknown', 'test', '', 'random']
        for severity in unknown_severities:
            assert normalize_severity(severity) == 'info'


class TestDeduplication:
    """Test finding deduplication."""
    
    def test_removes_exact_duplicates(self):
        """Exact duplicates should be removed."""
        findings = [
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com'},
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com'},
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com'}
        ]
        
        unique = deduplicate_findings(findings)
        assert len(unique) == 1
    
    def test_keeps_different_findings(self):
        """Different findings should all be kept."""
        findings = [
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com'},
            {'category': 'html', 'title': 'Missing description', 'location': 'http://example.com'},
            {'category': 'navigation', 'title': 'No navigation', 'location': 'http://example.com'}
        ]
        
        unique = deduplicate_findings(findings)
        assert len(unique) == 3
    
    def test_deduplication_across_pages(self):
        """Same issue on different pages should be kept."""
        findings = [
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com/page1'},
            {'category': 'html', 'title': 'Missing title', 'location': 'http://example.com/page2'}
        ]
        
        unique = deduplicate_findings(findings)
        assert len(unique) == 2
    
    def test_ids_are_unique_after_deduplication(self):
        """Finding IDs should be unique after deduplication."""
        findings = [
            {'skill': 'test', 'category': 'html', 'title': 'Issue 1', 'location': 'http://example.com'},
            {'skill': 'test', 'category': 'html', 'title': 'Issue 2', 'location': 'http://example.com'},
            {'skill': 'test', 'category': 'nav', 'title': 'Issue 3', 'location': 'http://example.com'}
        ]
        
        unique = deduplicate_findings(findings)
        ids = [f['id'] for f in unique]
        
        assert len(ids) == len(set(ids)), "Finding IDs should be unique"


class TestPriorityCalculation:
    """Test priority calculation."""
    
    def test_critical_higher_than_high(self):
        """Critical findings should have higher priority than high."""
        critical = calculate_priority({'severity': 'critical', 'category': 'other'})
        high = calculate_priority({'severity': 'high', 'category': 'other'})
        
        assert critical > high
    
    def test_high_higher_than_medium(self):
        """High findings should have higher priority than medium."""
        high = calculate_priority({'severity': 'high', 'category': 'other'})
        medium = calculate_priority({'severity': 'medium', 'category': 'other'})
        
        assert high > medium
    
    def test_medium_higher_than_low(self):
        """Medium findings should have higher priority than low."""
        medium = calculate_priority({'severity': 'medium', 'category': 'other'})
        low = calculate_priority({'severity': 'low', 'category': 'other'})
        
        assert medium > low
    
    def test_low_higher_than_info(self):
        """Low findings should have higher priority than info."""
        low = calculate_priority({'severity': 'low', 'category': 'other'})
        info = calculate_priority({'severity': 'info', 'category': 'other'})
        
        assert low > info
    
    def test_category_affects_priority(self):
        """Category should affect priority calculation."""
        html_priority = calculate_priority({'severity': 'medium', 'category': 'html'})
        other_priority = calculate_priority({'severity': 'medium', 'category': 'other'})
        
        # HTML category has 1.1x multiplier
        assert html_priority > other_priority
    
    def test_priority_in_bounds(self):
        """Priority should be between 1 and 100."""
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            for category in ['html', 'orientation', 'navigation', 'other']:
                priority = calculate_priority({'severity': severity, 'category': category})
                assert 1 <= priority <= 100, f"Priority {priority} out of bounds"


class TestFindingIdGeneration:
    """Test finding ID generation."""
    
    def test_id_format(self):
        """ID should have format: skill-hash."""
        finding = {
            'skill': 'crawl-render-audit',
            'category': 'html',
            'title': 'Missing title',
            'location': 'http://example.com'
        }
        
        finding_id = generate_finding_id(finding)
        assert '-' in finding_id
        assert finding_id.startswith('crawl-render-audit-')
    
    def test_id_length(self):
        """ID hash portion should be 8 characters."""
        finding = {
            'skill': 'test',
            'category': 'cat',
            'title': 'Title',
            'location': 'http://example.com'
        }
        
        finding_id = generate_finding_id(finding)
        parts = finding_id.split('-')
        assert len(parts[-1]) == 8
    
    def test_same_finding_same_id(self):
        """Same finding should produce same ID."""
        finding = {
            'skill': 'test',
            'category': 'cat',
            'title': 'Title',
            'location': 'http://example.com'
        }
        
        id1 = generate_finding_id(finding)
        id2 = generate_finding_id(finding)
        
        assert id1 == id2
    
    def test_different_finding_different_id(self):
        """Different findings should produce different IDs."""
        finding1 = {'skill': 'test', 'category': 'cat1', 'title': 'Title', 'location': 'http://example.com'}
        finding2 = {'skill': 'test', 'category': 'cat2', 'title': 'Title', 'location': 'http://example.com'}
        
        id1 = generate_finding_id(finding1)
        id2 = generate_finding_id(finding2)
        
        assert id1 != id2
