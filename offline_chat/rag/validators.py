"""
Validation functions for RAG components.
"""

import re
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a valid URL format.

    A valid URL must:
    - Start with http:// or https://
    - Have a valid domain structure
    - Not contain invalid characters

    Args:
        url: String to validate as URL

    Returns:
        True if the URL is valid, False otherwise

    Examples:
        >>> is_valid_url("https://example.com")
        True
        >>> is_valid_url("not a url")
        False
        >>> is_valid_url("ftp://example.com")
        False
    """
    if not url or not isinstance(url, str):
        return False

    # Must start with http:// or https://
    if not url.startswith(("http://", "https://")):
        return False

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Must have a scheme (http/https)
        if parsed.scheme not in ("http", "https"):
            return False

        # Must have a network location (domain)
        if not parsed.netloc:
            return False

        # Check for invalid characters in domain (must be ASCII)
        # Domain should only contain alphanumeric, dots, hyphens, and colons (for ports)
        domain_pattern = r'^[a-zA-Z0-9\.\-:]+$'
        if not re.match(domain_pattern, parsed.netloc):
            return False

        # Extract domain without port
        domain = parsed.netloc.split(":")[0]

        # Domain cannot be just a dot or empty
        if not domain or domain == ".":
            return False

        # Domain cannot start or end with a dot
        if domain.startswith(".") or domain.endswith("."):
            return False

        # Domain cannot have consecutive dots
        if ".." in domain:
            return False

        # Domain should contain at least one dot or be localhost
        if "." not in domain and domain != "localhost":
            return False

        # If domain has dots, check each part is valid
        if "." in domain:
            parts = domain.split(".")
            for part in parts:
                # Each part must be non-empty
                if not part:
                    return False
                # Each part cannot start or end with hyphen
                if part.startswith("-") or part.endswith("-"):
                    return False

        return True

    except Exception:
        return False


def validate_knowledge_source_url(url: str) -> tuple[bool, str | None]:
    """
    Validate a URL for use as a knowledge source.

    This function provides detailed validation feedback for URLs being
    added as knowledge sources to an agent's RAG configuration.

    Args:
        url: URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if URL is valid, False otherwise
        - error_message: None if valid, error description if invalid

    Examples:
        >>> validate_knowledge_source_url("https://example.com/docs")
        (True, None)
        >>> validate_knowledge_source_url("not a url")
        (False, "Invalid URL format: must start with http:// or https://")
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url = url.strip()

    if not url:
        return False, "URL must be a non-empty string"

    # Check protocol
    if not url.startswith(("http://", "https://")):
        return False, "Invalid URL format: must start with http:// or https://"

    # Use the basic validator
    if not is_valid_url(url):
        return False, "Invalid URL format: malformed URL structure"

    return True, None
