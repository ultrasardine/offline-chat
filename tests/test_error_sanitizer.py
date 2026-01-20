"""Unit tests for error message sanitization.

This module tests the error sanitization utilities that remove credentials
from error messages and logs to prevent credential exposure.
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.error_sanitizer import (
    sanitize_error_message,
    sanitize_connection_string,
    sanitize_dict,
)


class TestSanitizeErrorMessage:
    """Test suite for sanitize_error_message function."""

    def test_sanitize_with_password_in_error(self):
        """Error message containing password should have it masked."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123"
        )
        
        error = "Connection failed: password 'secret123' is invalid"
        sanitized = sanitize_error_message(error, conn)
        
        assert "secret123" not in sanitized
        assert "****" in sanitized
        assert "Connection failed" in sanitized

    def test_sanitize_without_connection_unchanged(self):
        """Error message without connection should remain unchanged."""
        error = "Connection timeout after 30 seconds"
        sanitized = sanitize_error_message(error)
        
        assert sanitized == error

    def test_sanitize_with_no_password_in_error(self):
        """Error message without password should remain unchanged."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123"
        )
        
        error = "Connection timeout after 30 seconds"
        sanitized = sanitize_error_message(error, conn)
        
        assert sanitized == error
        assert "secret123" not in sanitized

    def test_sanitize_multiple_occurrences(self):
        """Multiple occurrences of password should all be masked."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123"
        )
        
        error = "Error: secret123 failed, retry with secret123"
        sanitized = sanitize_error_message(error, conn)
        
        assert "secret123" not in sanitized
        assert sanitized.count("****") == 2

    def test_sanitize_with_additional_params_password(self):
        """Password in additional_params should be sanitized."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="ORCL",
            username="user",
            password="mainpass",
            additional_params={"db_password": "extrapass"}
        )
        
        error = "Failed with extrapass and mainpass"
        sanitized = sanitize_error_message(error, conn)
        
        assert "extrapass" not in sanitized
        assert "mainpass" not in sanitized
        assert "****" in sanitized

    def test_sanitize_with_token_in_additional_params(self):
        """Token in additional_params should be sanitized."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="pass123",
            additional_params={"api_token": "token456"}
        )
        
        error = "Authentication failed with token456"
        sanitized = sanitize_error_message(error, conn)
        
        assert "token456" not in sanitized
        assert "****" in sanitized

    def test_sanitize_with_additional_secrets(self):
        """Additional secrets parameter should be sanitized."""
        error = "API key abc123 is invalid"
        sanitized = sanitize_error_message(error, additional_secrets=["abc123"])
        
        assert "abc123" not in sanitized
        assert "****" in sanitized

    def test_sanitize_short_password_not_replaced(self):
        """Very short passwords (< 3 chars) should not be replaced to avoid false positives."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="ab"  # Too short
        )
        
        error = "Connection failed with ab"
        sanitized = sanitize_error_message(error, conn)
        
        # Short password should not be replaced (to avoid false positives)
        assert sanitized == error

    def test_sanitize_already_masked_password(self):
        """Already masked passwords should not be replaced."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="****"  # Already masked
        )
        
        error = "Connection failed with ****"
        sanitized = sanitize_error_message(error, conn)
        
        # Should remain unchanged
        assert sanitized == error

    def test_sanitize_longest_first(self):
        """Longer secrets should be replaced first to avoid partial replacements."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret",
            additional_params={"api_key": "secret123"}  # Contains "secret"
        )
        
        error = "Failed with secret123 and secret"
        sanitized = sanitize_error_message(error, conn)
        
        # Both should be masked
        assert "secret123" not in sanitized
        assert "secret" not in sanitized
        assert "****" in sanitized

    def test_sanitize_none_password(self):
        """Connection with None password should not cause errors."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="sqlite",
            file_path="/path/to/db.sqlite",
            password=None
        )
        
        error = "Connection failed"
        sanitized = sanitize_error_message(error, conn)
        
        assert sanitized == error

    def test_sanitize_empty_additional_params(self):
        """Empty additional_params should not cause errors."""
        conn = DatabaseConnection(
            name="test-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="mydb",
            username="user",
            password="secret123",
            additional_params={}
        )
        
        error = "Connection failed with secret123"
        sanitized = sanitize_error_message(error, conn)
        
        assert "secret123" not in sanitized
        assert "****" in sanitized


class TestSanitizeConnectionString:
    """Test suite for sanitize_connection_string function."""

    def test_sanitize_oracle_format(self):
        """Oracle connection string format should be sanitized."""
        conn_str = "user/secret123@localhost:1521/ORCL"
        sanitized = sanitize_connection_string(conn_str)
        
        assert "secret123" not in sanitized
        assert "user/****@localhost:1521/ORCL" == sanitized

    def test_sanitize_postgresql_url(self):
        """PostgreSQL URL format should be sanitized."""
        conn_str = "postgresql://user:secret@localhost:5432/mydb"
        sanitized = sanitize_connection_string(conn_str)
        
        assert "secret" not in sanitized
        assert "postgresql://user:****@localhost:5432/mydb" == sanitized

    def test_sanitize_mysql_url(self):
        """MySQL URL format should be sanitized."""
        conn_str = "mysql://user:password123@localhost:3306/mydb"
        sanitized = sanitize_connection_string(conn_str)
        
        assert "password123" not in sanitized
        assert "mysql://user:****@localhost:3306/mydb" == sanitized

    def test_sanitize_no_credentials(self):
        """Connection string without credentials should remain unchanged."""
        conn_str = "localhost:5432"
        sanitized = sanitize_connection_string(conn_str)
        
        assert sanitized == conn_str

    def test_sanitize_complex_password(self):
        """Complex password with special characters should be sanitized."""
        conn_str = "user/p@ssw0rd!#$@localhost:1521/ORCL"
        sanitized = sanitize_connection_string(conn_str)
        
        # The password (everything between / and @) should be masked
        assert "p@ssw0rd!#$" not in sanitized
        assert "****" in sanitized
        assert "user/" in sanitized
        assert "localhost:1521/ORCL" in sanitized

    def test_sanitize_multiple_at_signs(self):
        """Connection string with @ in password should be handled correctly."""
        conn_str = "postgresql://user:pass@word@localhost:5432/db"
        sanitized = sanitize_connection_string(conn_str)
        
        # Should mask the password part
        assert "pass@word" not in sanitized
        assert "****" in sanitized


class TestSanitizeDict:
    """Test suite for sanitize_dict function."""

    def test_sanitize_password_field(self):
        """Dictionary with password field should have it masked."""
        data = {
            "username": "user",
            "password": "secret",
            "host": "localhost"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["password"] == "****"
        assert sanitized["username"] == "user"
        assert sanitized["host"] == "localhost"

    def test_sanitize_token_field(self):
        """Dictionary with token field should have it masked."""
        data = {
            "api_token": "abc123",
            "host": "localhost"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["api_token"] == "****"
        assert sanitized["host"] == "localhost"

    def test_sanitize_multiple_sensitive_fields(self):
        """Dictionary with multiple sensitive fields should have all masked."""
        data = {
            "username": "user",
            "password": "secret",
            "api_key": "key123",
            "auth_token": "token456",
            "host": "localhost"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["password"] == "****"
        assert sanitized["api_key"] == "****"
        assert sanitized["auth_token"] == "****"
        assert sanitized["username"] == "user"
        assert sanitized["host"] == "localhost"

    def test_sanitize_none_values(self):
        """Dictionary with None values should remain None."""
        data = {
            "username": "user",
            "password": None,
            "host": "localhost"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["password"] is None
        assert sanitized["username"] == "user"

    def test_sanitize_empty_dict(self):
        """Empty dictionary should remain empty."""
        data = {}
        sanitized = sanitize_dict(data)
        
        assert sanitized == {}

    def test_sanitize_case_insensitive(self):
        """Sensitive field detection should be case-insensitive."""
        data = {
            "PASSWORD": "secret",
            "ApiKey": "key123",
            "Auth_Token": "token456"
        }
        
        sanitized = sanitize_dict(data)
        
        assert sanitized["PASSWORD"] == "****"
        assert sanitized["ApiKey"] == "****"
        assert sanitized["Auth_Token"] == "****"

    def test_sanitize_original_unchanged(self):
        """Original dictionary should not be modified."""
        data = {
            "username": "user",
            "password": "secret",
            "host": "localhost"
        }
        
        original_password = data["password"]
        sanitized = sanitize_dict(data)
        
        # Original should be unchanged
        assert data["password"] == original_password
        assert data["password"] == "secret"
        
        # Sanitized should be masked
        assert sanitized["password"] == "****"


# Property-based tests using Hypothesis

@given(
    password=st.text(min_size=3, max_size=50).filter(lambda s: s != "****"),
    error_template=st.sampled_from([
        "Connection failed: {}",
        "Authentication error with password {}",
        "Invalid credentials: {}",
        "Error: {} is not valid",
        "Failed to connect using {}"
    ])
)
@settings(max_examples=100)
def test_property_password_always_removed(password: str, error_template: str):
    """
    Feature: database-connection-management
    Property 24: Log Credential Sanitization
    
    For any password and error message containing that password,
    sanitizing the error should remove the password.
    
    Validates: Requirements 10.4, 10.5
    """
    conn = DatabaseConnection(
        name="test-db",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        username="user",
        password=password
    )
    
    error_message = error_template.format(password)
    sanitized = sanitize_error_message(error_message, conn)
    
    # The password should not appear in the sanitized message
    assert password not in sanitized
    # The mask should appear
    assert "****" in sanitized


@given(
    password=st.text(min_size=3, max_size=50).filter(lambda s: s != "****"),
    prefix=st.text(min_size=0, max_size=20),
    suffix=st.text(min_size=0, max_size=20)
)
@settings(max_examples=100)
def test_property_password_removed_with_context(password: str, prefix: str, suffix: str):
    """
    Feature: database-connection-management
    Property 24: Log Credential Sanitization
    
    For any password and surrounding text, the password should be removed
    regardless of context.
    
    Validates: Requirements 10.4, 10.5
    """
    # Skip if prefix or suffix contains the password (would make test ambiguous)
    assume(password not in prefix)
    assume(password not in suffix)
    
    conn = DatabaseConnection(
        name="test-db",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        username="user",
        password=password
    )
    
    error_message = f"{prefix}{password}{suffix}"
    sanitized = sanitize_error_message(error_message, conn)
    
    # The password should not appear
    assert password not in sanitized
    # The prefix and suffix should still be there
    if prefix:
        assert prefix in sanitized
    if suffix:
        assert suffix in sanitized


@given(
    error_message=st.text(min_size=0, max_size=200)
)
@settings(max_examples=100)
def test_property_no_connection_unchanged(error_message: str):
    """
    Feature: database-connection-management
    Property 24: Log Credential Sanitization
    
    For any error message without a connection object, the message
    should remain unchanged.
    
    Validates: Requirements 10.4, 10.5
    """
    sanitized = sanitize_error_message(error_message, None)
    assert sanitized == error_message


@given(
    username=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')
    )),
    password=st.text(
        min_size=3, max_size=50,
        alphabet=st.characters(blacklist_categories=('Zs', 'Zl', 'Zp', 'Cc'))
    ).filter(lambda s: s != "****" and "@" not in s and s.strip() == s),
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Ll', 'Nd'), whitelist_characters='.-'
    )),
    port=st.integers(min_value=1, max_value=65535),
    service=st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd')
    ))
)
@settings(max_examples=50)
def test_property_oracle_connection_string_sanitized(
    username: str, password: str, host: str, port: int, service: str
):
    """
    Feature: database-connection-management
    Property 24: Log Credential Sanitization
    
    For any Oracle connection string, the password should be masked.
    
    Validates: Requirements 10.4, 10.5
    """
    # Skip if password appears in other parts (would make test ambiguous)
    assume(password not in username)
    assume(password not in host)
    assume(password not in service)
    assume(password not in str(port))
    
    conn_str = f"{username}/{password}@{host}:{port}/{service}"
    sanitized = sanitize_connection_string(conn_str)
    
    # Password should not appear
    assert password not in sanitized
    # Username, host, port, and service should still be there
    assert username in sanitized
    assert host in sanitized
    assert str(port) in sanitized
    assert service in sanitized
    # Mask should appear
    assert "****" in sanitized


@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(min_size=0, max_size=50), st.none())
    )
)
@settings(max_examples=100)
def test_property_sanitize_dict_preserves_structure(data: dict):
    """
    Feature: database-connection-management
    Property 24: Log Credential Sanitization
    
    For any dictionary, sanitization should preserve all keys and
    only modify sensitive values.
    
    Validates: Requirements 10.4, 10.5
    """
    sanitized = sanitize_dict(data)
    
    # All keys should be preserved
    assert set(sanitized.keys()) == set(data.keys())
    
    # Non-sensitive values should be unchanged
    sensitive_patterns = [
        "password", "passwd", "pwd",
        "token", "secret", "key",
        "credential", "auth",
        "api_key", "apikey"
    ]
    
    for key, value in data.items():
        is_sensitive = any(pattern in key.lower() for pattern in sensitive_patterns)
        if not is_sensitive:
            # Non-sensitive values should be unchanged
            assert sanitized[key] == value
        elif value is not None:
            # Sensitive values should be masked
            assert sanitized[key] == "****"
        else:
            # None values should remain None
            assert sanitized[key] is None
