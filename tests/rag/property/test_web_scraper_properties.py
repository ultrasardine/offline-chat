"""
Property-based tests for web scraper and URL validation.
"""

import pytest
from hypothesis import given, settings, strategies as st

from offline_chat.rag.validators import is_valid_url, validate_knowledge_source_url


# Strategy for generating invalid URL strings
@st.composite
def invalid_url_strategy(draw):
    """
    Generate strings that are NOT valid URLs.
    
    This includes:
    - Empty strings
    - Random text without protocol
    - URLs with wrong protocols (ftp, file, etc.)
    - URLs without domains
    - URLs with invalid characters
    - Malformed URLs
    """
    invalid_type = draw(st.sampled_from([
        "empty",
        "no_protocol",
        "wrong_protocol",
        "no_domain",
        "invalid_chars",
        "malformed",
        "whitespace_only",
        "protocol_only",
        "missing_slashes"
    ]))
    
    if invalid_type == "empty":
        return ""
    
    elif invalid_type == "whitespace_only":
        return draw(st.text(alphabet=" \t\n\r", min_size=1, max_size=10))
    
    elif invalid_type == "no_protocol":
        # Just domain-like text without protocol
        domain = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-"),
            min_size=3,
            max_size=30
        ))
        return f"example.com/{domain}"
    
    elif invalid_type == "wrong_protocol":
        # Use non-http(s) protocols
        protocol = draw(st.sampled_from(["ftp", "file", "ssh", "telnet", "mailto"]))
        domain = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters=".-"),
            min_size=3,
            max_size=30
        ))
        return f"{protocol}://example.com/{domain}"
    
    elif invalid_type == "no_domain":
        # Protocol but no domain
        protocol = draw(st.sampled_from(["http", "https"]))
        return f"{protocol}://"
    
    elif invalid_type == "protocol_only":
        # Just the protocol
        return draw(st.sampled_from(["http", "https", "http:", "https:"]))
    
    elif invalid_type == "missing_slashes":
        # Protocol without proper slashes
        protocol = draw(st.sampled_from(["http", "https"]))
        return f"{protocol}:example.com"
    
    elif invalid_type == "invalid_chars":
        # URLs with spaces or other invalid characters
        protocol = draw(st.sampled_from(["http", "https"]))
        invalid_text = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Zs", "Cc", "Cs")),
            min_size=1,
            max_size=10
        ))
        return f"{protocol}://example{invalid_text}.com"
    
    else:  # malformed
        # Various malformed patterns
        return draw(st.sampled_from([
            "http//example.com",  # Missing colon
            "https:/example.com",  # Missing slash
            "http:///example.com",  # Extra slash
            "https://",  # No domain
            "://example.com",  # No protocol
            "http://.",  # Just a dot
            "https://.com",  # Starts with dot
            "http://example.",  # Ends with dot
            "https://example..com",  # Double dot
            "http://-example.com",  # Starts with hyphen
            "https://example-.com",  # Ends with hyphen
        ]))


# Strategy for generating valid URL strings
@st.composite
def valid_url_strategy(draw):
    """
    Generate strings that ARE valid URLs.
    
    This includes:
    - http and https URLs
    - Various domain structures
    - URLs with paths, query params, fragments
    """
    protocol = draw(st.sampled_from(["http", "https"]))
    
    # Generate domain parts (ASCII lowercase letters and digits only)
    domain_parts = draw(st.lists(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
            min_size=1,
            max_size=15
        ).filter(lambda x: x and x[0] != "-" and x[-1] != "-" and x != "-"),
        min_size=2,
        max_size=4
    ))
    domain = ".".join(domain_parts)
    
    # Optionally add port
    port = ""
    if draw(st.booleans()):
        port = f":{draw(st.integers(min_value=1, max_value=65535))}"
    
    # Optionally add path
    path = ""
    if draw(st.booleans()):
        path_parts = draw(st.lists(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
                min_size=1,
                max_size=20
            ),
            min_size=1,
            max_size=5
        ))
        path = "/" + "/".join(path_parts)
    
    return f"{protocol}://{domain}{port}{path}"


@pytest.mark.property_test
class TestWebScraperProperties:
    """Property-based tests for web scraper and URL validation."""
    
    @given(invalid_url=invalid_url_strategy())
    @settings(max_examples=200, deadline=None)
    def test_url_validation_rejects_invalid_formats(self, invalid_url):
        """
        **Validates: Requirements 1.3**
        
        Property 2: URL Validation Rejects Invalid Formats
        
        For any string that is not a valid URL format, attempting to add it as a
        web knowledge source should be rejected by the validation logic.
        
        This property ensures that only properly formatted URLs can be added as
        knowledge sources, preventing errors during web scraping and maintaining
        data integrity in the RAG system.
        """
        # Test the basic URL validator
        is_valid = is_valid_url(invalid_url)
        
        # Invalid URLs should be rejected
        assert not is_valid, (
            f"Expected invalid URL to be rejected, but was accepted: {repr(invalid_url)}"
        )
        
        # Test the knowledge source validator
        is_valid_ks, error_message = validate_knowledge_source_url(invalid_url)
        
        # Should also be rejected by knowledge source validator
        assert not is_valid_ks, (
            f"Expected invalid URL to be rejected by knowledge source validator, "
            f"but was accepted: {repr(invalid_url)}"
        )
        
        # Should provide an error message
        assert error_message is not None, (
            f"Expected error message for invalid URL, but got None: {repr(invalid_url)}"
        )
        assert isinstance(error_message, str), (
            f"Expected error message to be a string, got {type(error_message)}"
        )
        assert len(error_message) > 0, (
            f"Expected non-empty error message for invalid URL: {repr(invalid_url)}"
        )
    
    @given(valid_url=valid_url_strategy())
    @settings(max_examples=100, deadline=None)
    def test_url_validation_accepts_valid_formats(self, valid_url):
        """
        Test that valid URLs are accepted by the validation logic.
        
        This is the inverse property - valid URLs should pass validation.
        This ensures the validator is not overly restrictive.
        """
        # Test the basic URL validator
        is_valid = is_valid_url(valid_url)
        
        # Valid URLs should be accepted
        assert is_valid, (
            f"Expected valid URL to be accepted, but was rejected: {repr(valid_url)}"
        )
        
        # Test the knowledge source validator
        is_valid_ks, error_message = validate_knowledge_source_url(valid_url)
        
        # Should also be accepted by knowledge source validator
        assert is_valid_ks, (
            f"Expected valid URL to be accepted by knowledge source validator, "
            f"but was rejected: {repr(valid_url)}"
        )
        
        # Should not have an error message
        assert error_message is None, (
            f"Expected no error message for valid URL, but got: {error_message}"
        )
    
    @given(url=st.text(min_size=0, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_url_validation_is_deterministic(self, url):
        """
        Test that URL validation is deterministic.
        
        For any input string, calling the validator multiple times should
        return the same result. This ensures consistency in validation.
        """
        # Call validator multiple times
        result1 = is_valid_url(url)
        result2 = is_valid_url(url)
        result3 = is_valid_url(url)
        
        # All results should be identical
        assert result1 == result2 == result3, (
            f"URL validation is not deterministic for: {repr(url)}"
        )
        
        # Same for knowledge source validator
        ks_result1 = validate_knowledge_source_url(url)
        ks_result2 = validate_knowledge_source_url(url)
        ks_result3 = validate_knowledge_source_url(url)
        
        assert ks_result1 == ks_result2 == ks_result3, (
            f"Knowledge source URL validation is not deterministic for: {repr(url)}"
        )
