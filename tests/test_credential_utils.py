"""Tests for credential masking utilities.

This module contains tests for credential masking and sanitization functions,
ensuring sensitive information is properly protected in displays and error messages.
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from offline_chat.credential_utils import (
    mask_password,
    sanitize_config_for_display,
    sanitize_error_message,
)
from offline_chat.mcp_config import MCPServerConfig


class TestPasswordMasking:
    """Property 21: Password masking in display.

    Feature: database-access, Property 21: Password masking in display
    **Validates: Requirements 5.2**

    For any agent configuration with database passwords, displaying the
    configuration should show masked passwords (e.g., "****") instead of
    actual values.
    """

    @settings(max_examples=100)
    @given(password=st.text(min_size=1, max_size=100).filter(lambda p: p not in "****"))
    def test_non_empty_passwords_masked(self, password: str):
        """Non-empty passwords should be masked as '****'."""
        masked = mask_password(password)
        assert masked == "****"
        # Only check if password not in masked if password isn't a substring of the mask
        if password not in "****":
            assert password not in masked

    def test_none_password_returns_none_string(self):
        """None password should return 'None' string."""
        masked = mask_password(None)
        assert masked == "None"

    @settings(max_examples=100)
    @given(
        name=st.text(
            min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s.strip()),
        password=st.text(
            min_size=2, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s != "****"),
    )
    def test_config_display_masks_database_password(self, name: str, password: str):
        """Database password in config should be masked for display."""
        # Skip if password is a substring of name or vice versa to avoid false positives
        assume(password not in name and name not in password)

        config = MCPServerConfig(
            name=name,
            command="sql",
            args=["-mcp"],
            database_type="oracle",
            database_password=password,
        )

        sanitized = sanitize_config_for_display(config)

        # The password field should be masked
        assert sanitized["database_password"] == "****"
        # The actual password should not appear as a value in the sanitized dict
        assert password not in sanitized.values()
        # Check nested env dict too
        if "env" in sanitized:
            assert password not in sanitized["env"].values()

    @settings(max_examples=100)
    @given(
        name=st.text(
            min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s.strip()),
        password=st.text(
            min_size=2, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s != "****"),
    )
    def test_config_display_masks_env_passwords(self, name: str, password: str):
        """Passwords in environment variables should be masked for display."""
        # Skip if password is a substring of name or vice versa to avoid false positives
        assume(password not in name and name not in password)

        config = MCPServerConfig(
            name=name, command="uvx", args=["postgres-mcp-server"], env={"PGPASSWORD": password}
        )

        sanitized = sanitize_config_for_display(config)

        # The password in env should be masked
        assert sanitized["env"]["PGPASSWORD"] == "****"
        # The actual password should not appear as a value in the sanitized dict
        assert password not in sanitized.values()
        assert password not in sanitized["env"].values()

    @settings(max_examples=50)
    @given(
        name=st.text(
            min_size=1, max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s.strip()),
        password=st.text(
            min_size=2, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ).filter(lambda s: s != "****"),
        env_key=st.sampled_from(
            [
                "PASSWORD",
                "PASSWD",
                "PWD",
                "SECRET",
                "TOKEN",
                "DB_PASSWORD",
                "API_SECRET",
                "AUTH_TOKEN",
            ]
        ),
    )
    def test_config_display_masks_various_password_env_keys(
        self, name: str, password: str, env_key: str
    ):
        """Various password-like environment variable keys should be masked."""
        # Skip if password is a substring of name or vice versa to avoid false positives
        assume(password not in name and name not in password)

        config = MCPServerConfig(
            name=name, command="uvx", args=["test-server"], env={env_key: password}
        )

        sanitized = sanitize_config_for_display(config)

        # The password in env should be masked
        assert sanitized["env"][env_key] == "****"
        # The actual password should not appear as a value in the sanitized dict
        assert password not in sanitized.values()
        assert password not in sanitized["env"].values()

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        value=st.text(min_size=1, max_size=100),
    )
    def test_config_display_preserves_non_password_env_vars(self, name: str, value: str):
        """Non-password environment variables should not be masked."""
        config = MCPServerConfig(
            name=name,
            command="uvx",
            args=["test-server"],
            env={"DATABASE_HOST": value, "PORT": "5432"},
        )

        sanitized = sanitize_config_for_display(config)

        assert sanitized["env"]["DATABASE_HOST"] == value
        assert sanitized["env"]["PORT"] == "5432"

    def test_config_without_password_unchanged(self):
        """Config without passwords should remain unchanged."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_type="oracle"
        )

        sanitized = sanitize_config_for_display(config)

        # Should have database_password key but with None value masked
        assert "database_password" not in sanitized or sanitized.get("database_password") is None


class TestCredentialExclusionFromErrorMessages:
    """Property 23: Credential exclusion from error messages.

    Feature: database-access, Property 23: Credential exclusion from error messages
    **Validates: Requirements 5.5**

    For any database configuration validation error, the error message should
    not contain password or other credential values.
    """

    @settings(max_examples=100)
    @given(
        password=st.text(min_size=1, max_size=100).filter(lambda p: p != "*" and "****" not in p),
        error_prefix=st.text(min_size=1, max_size=50),
    )
    def test_password_removed_from_error_message(self, password: str, error_prefix: str):
        """Passwords should be removed from error messages."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password=password
        )

        error_message = f"{error_prefix}: Connection failed with password {password}"
        sanitized = sanitize_error_message(error_message, config)

        # The original password should not appear in the sanitized message
        # (unless it's a substring of the mask, which we filter out)
        assert password not in sanitized
        assert "****" in sanitized

    @settings(max_examples=100)
    @given(
        password=st.text(min_size=1, max_size=100),
        error_template=st.sampled_from(
            [
                "Authentication failed: {}",
                "Invalid credentials: password={}",
                "Connection error with {}: timeout",
                "Failed to connect using {}",
            ]
        ),
    )
    def test_password_removed_from_various_error_formats(self, password: str, error_template: str):
        """Passwords should be removed from various error message formats."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password=password
        )

        error_message = error_template.format(password)
        sanitized = sanitize_error_message(error_message, config)

        assert password not in sanitized
        assert "****" in sanitized

    @settings(max_examples=50)
    @given(
        password=st.text(min_size=1, max_size=100),
        env_key=st.sampled_from(["PASSWORD", "PASSWD", "PWD", "SECRET", "TOKEN"]),
    )
    def test_env_password_removed_from_error_message(self, password: str, env_key: str):
        """Passwords from environment variables should be removed from error messages."""
        config = MCPServerConfig(
            name="test_db", command="uvx", args=["postgres-mcp-server"], env={env_key: password}
        )

        error_message = f"Connection failed: {env_key}={password} is invalid"
        sanitized = sanitize_error_message(error_message, config)

        assert password not in sanitized
        assert "****" in sanitized

    @settings(max_examples=50)
    @given(
        password=st.text(min_size=1, max_size=100),
        other_text=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    )
    def test_multiple_password_occurrences_removed(self, password: str, other_text: str):
        """All occurrences of password should be removed from error messages."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password=password
        )

        error_message = f"{other_text} {password} and again {password}"
        sanitized = sanitize_error_message(error_message, config)

        assert password not in sanitized
        assert sanitized.count("****") >= 2

    @settings(max_examples=50)
    @given(error_message=st.text(min_size=1, max_size=200))
    def test_error_without_config_unchanged(self, error_message: str):
        """Error messages without config should remain unchanged."""
        sanitized = sanitize_error_message(error_message, None)
        assert sanitized == error_message

    @settings(max_examples=50)
    @given(
        error_message=st.text(min_size=1, max_size=200),
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_error_without_password_in_config_unchanged(self, error_message: str, name: str):
        """Error messages with config but no password should remain unchanged."""
        config = MCPServerConfig(name=name, command="sql", args=["-mcp"], database_type="oracle")

        sanitized = sanitize_error_message(error_message, config)
        assert sanitized == error_message

    @settings(max_examples=50)
    @given(
        password=st.text(min_size=1, max_size=100),
        safe_text=st.text(min_size=1, max_size=100).filter(
            lambda s: s.strip() and "password" not in s.lower()
        ),
    )
    def test_non_password_text_preserved(self, password: str, safe_text: str):
        """Non-password text should be preserved in error messages."""
        # Skip if password is a substring of safe_text or vice versa to avoid false positives
        assume(password not in safe_text and safe_text not in password)

        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password=password
        )

        error_message = f"Error: {safe_text}"
        sanitized = sanitize_error_message(error_message, config)

        # Safe text should still be present
        assert safe_text in sanitized


class TestEdgeCases:
    """Unit tests for edge cases in credential masking."""

    def test_empty_string_password_masked(self):
        """Empty string passwords should be masked."""
        masked = mask_password("")
        assert masked == "****"

    def test_very_long_password_masked(self):
        """Very long passwords should be masked to same length."""
        long_password = "a" * 1000
        masked = mask_password(long_password)
        assert masked == "****"
        assert len(masked) == 4

    def test_password_with_special_chars_masked(self):
        """Passwords with special characters should be masked."""
        special_password = "p@$$w0rd!#%^&*()"
        masked = mask_password(special_password)
        assert masked == "****"

    def test_config_with_multiple_passwords_all_masked(self):
        """Config with both database_password and env passwords should mask all."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["postgres-mcp-server"],
            database_password="db_secret",
            env={"PGPASSWORD": "env_secret", "API_TOKEN": "api_secret"},
        )

        sanitized = sanitize_config_for_display(config)

        assert sanitized["database_password"] == "****"
        assert sanitized["env"]["PGPASSWORD"] == "****"
        assert sanitized["env"]["API_TOKEN"] == "****"
        assert "db_secret" not in str(sanitized)
        assert "env_secret" not in str(sanitized)
        assert "api_secret" not in str(sanitized)

    def test_case_insensitive_env_key_matching(self):
        """Environment key matching should be case-insensitive."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["test-server"],
            env={
                "password": "secret1",
                "Password": "secret2",
                "PASSWORD": "secret3",
                "db_PaSsWoRd": "secret4",
            },
        )

        sanitized = sanitize_config_for_display(config)

        # All should be masked
        assert sanitized["env"]["password"] == "****"
        assert sanitized["env"]["Password"] == "****"
        assert sanitized["env"]["PASSWORD"] == "****"
        assert sanitized["env"]["db_PaSsWoRd"] == "****"

    def test_partial_password_key_matches(self):
        """Partial matches of password keywords should be masked."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["test-server"],
            env={
                "MY_PASSWORD": "secret1",
                "DB_PASSWD": "secret2",
                "USER_PWD": "secret3",
                "API_SECRET_KEY": "secret4",
                "AUTH_TOKEN_VALUE": "secret5",
            },
        )

        sanitized = sanitize_config_for_display(config)

        # All should be masked because they contain password-like keywords
        assert sanitized["env"]["MY_PASSWORD"] == "****"
        assert sanitized["env"]["DB_PASSWD"] == "****"
        assert sanitized["env"]["USER_PWD"] == "****"
        assert sanitized["env"]["API_SECRET_KEY"] == "****"
        assert sanitized["env"]["AUTH_TOKEN_VALUE"] == "****"

    def test_error_message_with_no_password_match(self):
        """Error messages without password should remain unchanged."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password="secret123"
        )

        error_message = "Connection timeout after 30 seconds"
        sanitized = sanitize_error_message(error_message, config)

        assert sanitized == error_message

    def test_password_at_start_of_error_message(self):
        """Password at the start of error message should be removed."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password="secret123"
        )

        error_message = "secret123 is not a valid password"
        sanitized = sanitize_error_message(error_message, config)

        assert "secret123" not in sanitized
        assert sanitized.startswith("****")

    def test_password_at_end_of_error_message(self):
        """Password at the end of error message should be removed."""
        config = MCPServerConfig(
            name="test_db", command="sql", args=["-mcp"], database_password="secret123"
        )

        error_message = "Invalid password: secret123"
        sanitized = sanitize_error_message(error_message, config)

        assert "secret123" not in sanitized
        assert sanitized.endswith("****")

    def test_config_serialization_preserves_structure(self):
        """Sanitized config should preserve all non-password fields."""
        config = MCPServerConfig(
            name="test_db",
            command="sql",
            args=["-mcp", "-connection", "PROD"],
            env={"LANG": "en_US.UTF-8"},
            disabled=False,
            database_type="oracle",
            database_host="db.example.com",
            database_port=1521,
            database_name="ORCL",
            database_user="admin",
            database_password="secret",
        )

        sanitized = sanitize_config_for_display(config)

        # All non-password fields should be preserved
        assert sanitized["name"] == "test_db"
        assert sanitized["command"] == "sql"
        assert sanitized["args"] == ["-mcp", "-connection", "PROD"]
        assert sanitized["env"]["LANG"] == "en_US.UTF-8"
        assert sanitized["disabled"] is False
        assert sanitized["database_type"] == "oracle"
        assert sanitized["database_host"] == "db.example.com"
        assert sanitized["database_port"] == 1521
        assert sanitized["database_name"] == "ORCL"
        assert sanitized["database_user"] == "admin"
        # Only password should be masked
        assert sanitized["database_password"] == "****"
