"""
Unit tests for RAG validators.
"""

import pytest

from offline_chat.rag.validators import is_valid_url, validate_knowledge_source_url


class TestIsValidUrl:
    """Unit tests for is_valid_url function."""
    
    def test_valid_http_url(self):
        """Test that valid HTTP URLs are accepted."""
        assert is_valid_url("http://example.com")
        assert is_valid_url("http://www.example.com")
        assert is_valid_url("http://subdomain.example.com")
        assert is_valid_url("http://example.com/path")
        assert is_valid_url("http://example.com/path/to/resource")
    
    def test_valid_https_url(self):
        """Test that valid HTTPS URLs are accepted."""
        assert is_valid_url("https://example.com")
        assert is_valid_url("https://www.example.com")
        assert is_valid_url("https://subdomain.example.com")
        assert is_valid_url("https://example.com/path")
    
    def test_valid_url_with_port(self):
        """Test that URLs with ports are accepted."""
        assert is_valid_url("http://example.com:8080")
        assert is_valid_url("https://example.com:443")
        assert is_valid_url("http://localhost:3000")
    
    def test_localhost(self):
        """Test that localhost URLs are accepted."""
        assert is_valid_url("http://localhost")
        assert is_valid_url("https://localhost")
        assert is_valid_url("http://localhost:8080")
    
    def test_invalid_protocol(self):
        """Test that non-HTTP(S) protocols are rejected."""
        assert not is_valid_url("ftp://example.com")
        assert not is_valid_url("file:///path/to/file")
        assert not is_valid_url("ssh://example.com")
        assert not is_valid_url("mailto:user@example.com")
    
    def test_no_protocol(self):
        """Test that URLs without protocol are rejected."""
        assert not is_valid_url("example.com")
        assert not is_valid_url("www.example.com")
        assert not is_valid_url("example.com/path")
    
    def test_malformed_protocol(self):
        """Test that malformed protocols are rejected."""
        assert not is_valid_url("http//example.com")
        assert not is_valid_url("https:/example.com")
        assert not is_valid_url("http:example.com")
        assert not is_valid_url("://example.com")
    
    def test_no_domain(self):
        """Test that URLs without domain are rejected."""
        assert not is_valid_url("http://")
        assert not is_valid_url("https://")
        assert not is_valid_url("http:///path")
    
    def test_invalid_domain_format(self):
        """Test that invalid domain formats are rejected."""
        assert not is_valid_url("http://.")
        assert not is_valid_url("http://.com")
        assert not is_valid_url("http://example.")
        assert not is_valid_url("http://example..com")
        assert not is_valid_url("http://-example.com")
        assert not is_valid_url("http://example-.com")
    
    def test_empty_string(self):
        """Test that empty string is rejected."""
        assert not is_valid_url("")
    
    def test_whitespace_only(self):
        """Test that whitespace-only strings are rejected."""
        assert not is_valid_url("   ")
        assert not is_valid_url("\t")
        assert not is_valid_url("\n")
    
    def test_none_input(self):
        """Test that None input is rejected."""
        assert not is_valid_url(None)
    
    def test_non_string_input(self):
        """Test that non-string inputs are rejected."""
        assert not is_valid_url(123)
        assert not is_valid_url([])
        assert not is_valid_url({})
    
    def test_url_with_special_characters(self):
        """Test that URLs with invalid special characters are rejected."""
        assert not is_valid_url("http://example .com")
        assert not is_valid_url("http://example\ncom")
        assert not is_valid_url("http://example\tcom")
    
    def test_url_with_query_params(self):
        """Test that URLs with query parameters are accepted."""
        # Note: Query params might contain special chars, but domain should be valid
        assert is_valid_url("http://example.com?key=value")
        assert is_valid_url("https://example.com/path?key=value&other=123")
    
    def test_url_with_fragment(self):
        """Test that URLs with fragments are accepted."""
        assert is_valid_url("http://example.com#section")
        assert is_valid_url("https://example.com/path#anchor")


class TestValidateKnowledgeSourceUrl:
    """Unit tests for validate_knowledge_source_url function."""
    
    def test_valid_url_returns_true_and_no_error(self):
        """Test that valid URLs return (True, None)."""
        is_valid, error = validate_knowledge_source_url("https://example.com")
        assert is_valid is True
        assert error is None
        
        is_valid, error = validate_knowledge_source_url("http://docs.example.com/api")
        assert is_valid is True
        assert error is None
    
    def test_invalid_url_returns_false_and_error_message(self):
        """Test that invalid URLs return (False, error_message)."""
        is_valid, error = validate_knowledge_source_url("not a url")
        assert is_valid is False
        assert error is not None
        assert isinstance(error, str)
        assert len(error) > 0
    
    def test_empty_string_returns_error(self):
        """Test that empty string returns appropriate error."""
        is_valid, error = validate_knowledge_source_url("")
        assert is_valid is False
        assert error is not None
        assert "non-empty" in error.lower()
    
    def test_whitespace_only_returns_error(self):
        """Test that whitespace-only string returns appropriate error."""
        is_valid, error = validate_knowledge_source_url("   ")
        assert is_valid is False
        assert error is not None
        assert "non-empty" in error.lower()
    
    def test_none_returns_error(self):
        """Test that None input returns appropriate error."""
        is_valid, error = validate_knowledge_source_url(None)
        assert is_valid is False
        assert error is not None
        assert "string" in error.lower()
    
    def test_non_string_returns_error(self):
        """Test that non-string input returns appropriate error."""
        is_valid, error = validate_knowledge_source_url(123)
        assert is_valid is False
        assert error is not None
        assert "string" in error.lower()
    
    def test_wrong_protocol_returns_error(self):
        """Test that wrong protocol returns appropriate error."""
        is_valid, error = validate_knowledge_source_url("ftp://example.com")
        assert is_valid is False
        assert error is not None
        assert "http" in error.lower()
    
    def test_no_protocol_returns_error(self):
        """Test that missing protocol returns appropriate error."""
        is_valid, error = validate_knowledge_source_url("example.com")
        assert is_valid is False
        assert error is not None
        assert "http" in error.lower()
    
    def test_malformed_url_returns_error(self):
        """Test that malformed URLs return appropriate error."""
        is_valid, error = validate_knowledge_source_url("http://")
        assert is_valid is False
        assert error is not None
        
        is_valid, error = validate_knowledge_source_url("http://.")
        assert is_valid is False
        assert error is not None
    
    def test_url_with_leading_trailing_whitespace(self):
        """Test that URLs with whitespace are handled (stripped and validated)."""
        is_valid, error = validate_knowledge_source_url("  https://example.com  ")
        assert is_valid is True
        assert error is None
    
    def test_error_messages_are_descriptive(self):
        """Test that error messages provide useful information."""
        # No protocol
        _, error = validate_knowledge_source_url("example.com")
        assert "http" in error.lower() or "protocol" in error.lower()
        
        # Empty string
        _, error = validate_knowledge_source_url("")
        assert "empty" in error.lower() or "string" in error.lower()
        
        # Malformed
        _, error = validate_knowledge_source_url("http://")
        assert "invalid" in error.lower() or "malformed" in error.lower()
