"""
Test basic checks.
Tests for URL validation, crawler configuration, and HTML analysis.
"""

import pytest
import sys
import os

# Add the skills directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'audit-orchestrator', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'crawl-render-audit', 'scripts'))

from bs4 import BeautifulSoup
from orchestrator import validate_url  # type: ignore
from crawler import normalize_url, get_domain, is_same_domain, CrawlerConfig  # type: ignore
from page_analysis import analyze_html_structure  # type: ignore


class TestUrlValidation:
    """Test URL validation."""
    
    def test_valid_https_url(self):
        """Valid HTTPS URL should pass."""
        url = "https://example.com"
        result = validate_url(url)
        assert result == url
    
    def test_valid_http_url(self):
        """Valid HTTP URL should pass."""
        url = "http://example.com"
        result = validate_url(url)
        assert result == url
    
    def test_domain_without_scheme(self):
        """Domain without scheme should get https."""
        url = "example.com"
        result = validate_url(url)
        assert result == "https://example.com"
    
    def test_trailing_slash_removed(self):
        """Trailing slash should be removed."""
        url = "https://example.com/"
        result = validate_url(url)
        assert result == "https://example.com"
    
    def test_empty_url_raises_error(self):
        """Empty URL should raise ValueError."""
        with pytest.raises(ValueError):
            validate_url("")
    
    def test_invalid_url_raises_error(self):
        """Invalid URL should raise ValueError."""
        with pytest.raises(ValueError):
            validate_url("not a url")
    
    def test_url_with_path(self):
        """URL with path should be preserved."""
        url = "https://example.com/page"
        result = validate_url(url)
        assert result == url


class TestUrlNormalization:
    """Test URL normalization."""
    
    def test_remove_tracking_params(self):
        """Tracking parameters should be removed."""
        url = "https://example.com/page?utm_source=test&utm_medium=campaign&id=123"
        normalized = normalize_url(url)
        
        assert 'utm_source' not in normalized
        assert 'utm_medium' not in normalized
        assert 'id=123' in normalized
    
    def test_remove_fragment(self):
        """Fragment should be removed."""
        url = "https://example.com/page#section"
        normalized = normalize_url(url)
        
        assert '#' not in normalized
    
    def test_normalize_path(self):
        """Path should be normalized."""
        url = "https://example.com/page/"
        normalized = normalize_url(url)
        
        assert normalized == "https://example.com/page"
    
    def test_remove_index_html(self):
        """index.html should be removed."""
        url = "https://example.com/index.html"
        normalized = normalize_url(url)
        
        assert 'index.html' not in normalized


class TestDomainExtraction:
    """Test domain extraction."""
    
    def test_simple_domain(self):
        """Simple domain should be extracted."""
        url = "https://example.com"
        domain = get_domain(url)
        assert domain == "example.com"
    
    def test_www_domain(self):
        """www domain should be extracted."""
        url = "https://www.example.com"
        domain = get_domain(url)
        assert domain == "www.example.com"
    
    def test_domain_with_path(self):
        """Domain should be extracted without path."""
        url = "https://example.com/page"
        domain = get_domain(url)
        assert domain == "example.com"
    
    def test_case_insensitive(self):
        """Domain extraction should be case insensitive."""
        url = "https://EXAMPLE.COM"
        domain = get_domain(url)
        assert domain == "example.com"


class TestSameDomainCheck:
    """Test same domain checking."""
    
    def test_same_domain(self):
        """Same domain should return True."""
        url = "https://example.com/page"
        base = "example.com"
        assert is_same_domain(url, base) is True
    
    def test_different_domain(self):
        """Different domain should return False."""
        url = "https://other.com/page"
        base = "example.com"
        assert is_same_domain(url, base) is False
    
    def test_subdomain(self):
        """Subdomain should be treated as different."""
        url = "https://sub.example.com/page"
        base = "example.com"
        assert is_same_domain(url, base) is False


class TestCrawlerConfig:
    """Test crawler configuration."""
    
    def test_default_values(self):
        """Default configuration should have expected values."""
        config = CrawlerConfig()
        
        assert config.max_pages == 20
        assert config.max_depth == 2
        assert config.timeout == 10
        assert config.delay == 1.0
    
    def test_custom_values(self):
        """Custom configuration should override defaults."""
        config = CrawlerConfig(
            max_pages=50,
            max_depth=5,
            timeout=30,
            delay=2.0
        )
        
        assert config.max_pages == 50
        assert config.max_depth == 5
        assert config.timeout == 30
        assert config.delay == 2.0
    
    def test_user_agent(self):
        """User agent should be configurable."""
        config = CrawlerConfig(user_agent="CustomBot/1.0")
        assert config.user_agent == "CustomBot/1.0"


class TestHtmlAnalysis:
    """Test HTML analysis functions."""
    
    def test_analyze_html_structure(self):
        """HTML structure analysis should extract key elements."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="Test description">
            <link rel="canonical" href="https://example.com">
            <meta property="og:title" content="OG Title">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Main Heading</h1>
            <h2>Subheading</h2>
            <img src="image.jpg" alt="Test image">
            <a href="/page">Link</a>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'lxml')
        analysis = analyze_html_structure(soup, "https://example.com")
        
        assert analysis['title'] == "Test Page Title"
        assert analysis['meta_description'] == "Test description"
        assert analysis['canonical'] == "https://example.com"
        assert analysis['h1_count'] == 1
        assert analysis['h2_count'] == 1
        assert analysis['images_without_alt'] == 0
        assert analysis['viewport'] is not None
    
    def test_missing_title_detected(self):
        """Missing title should be detected."""
        html = "<html><body><h1>Content</h1></body></html>"
        soup = BeautifulSoup(html, 'lxml')
        analysis = analyze_html_structure(soup, "https://example.com")
        
        assert analysis['title'] is None
        assert analysis['title_length'] == 0
    
    def test_images_without_alt(self):
        """Images without alt text should be counted."""
        html = """
        <html><body>
            <img src="img1.jpg" alt="Has alt">
            <img src="img2.jpg">
            <img src="img3.jpg">
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        analysis = analyze_html_structure(soup, "https://example.com")
        
        assert analysis['images_without_alt'] == 2
