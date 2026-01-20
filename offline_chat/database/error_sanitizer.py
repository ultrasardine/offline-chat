"""Utilities for sanitizing error messages to remove credentials.

This module provides functions to sanitize error messages and logs by removing
sensitive credentials such as passwords, tokens, and other secrets. This ensures
that error messages displayed to users or written to logs do not expose
sensitive information.
"""

import re
from typing import Any

from offline_chat.database.connection import DatabaseConnection


def sanitize_error_message(
    error_message: str,
    connection: DatabaseConnection | None = None,
    additional_secrets: list[str] | None = None
) -> str:
    """Remove credentials from error messages.

    This function scans error messages for potential credential exposure and
    replaces any found credentials with masked values (****). It can extract
    credentials from a DatabaseConnection object and also accepts additional
    secrets to sanitize.

    Args:
        error_message: The error message to sanitize.
        connection: Optional DatabaseConnection to extract credentials from.
        additional_secrets: Optional list of additional secret strings to sanitize.

    Returns:
        Sanitized error message with credentials replaced by ****.

    Examples:
        >>> from offline_chat.database.connection import DatabaseConnection
        >>> conn = DatabaseConnection(
        ...     name="test-db",
        ...     database_type="postgresql",
        ...     host="localhost",
        ...     port=5432,
        ...     database="mydb",
        ...     username="user",
        ...     password="secret123"
        ... )
        >>> error = "Connection failed: password 'secret123' is invalid"
        >>> sanitized = sanitize_error_message(error, conn)
        >>> "secret123" in sanitized
        False
        >>> "****" in sanitized
        True

        >>> # Without connection, message is unchanged
        >>> error = "Connection timeout"
        >>> sanitize_error_message(error)
        'Connection timeout'

        >>> # With additional secrets
        >>> error = "API key abc123 is invalid"
        >>> sanitize_error_message(error, additional_secrets=["abc123"])
        'API key **** is invalid'
    """
    sanitized = error_message

    # Collect all secrets to sanitize
    secrets_to_sanitize = []

    # Extract secrets from connection if provided
    if connection is not None:
        # Add password if present
        if connection.password:
            secrets_to_sanitize.append(connection.password)

        # Add secrets from additional_params
        if connection.additional_params:
            sensitive_keys = ["password", "token", "key", "secret", "credential", "api_key"]
            for key, value in connection.additional_params.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    if value and isinstance(value, str):
                        secrets_to_sanitize.append(value)

    # Add any additional secrets provided
    if additional_secrets:
        secrets_to_sanitize.extend(additional_secrets)

    # Filter out secrets that are too short or are already masked
    # Short secrets (< 3 chars) are likely to cause false positives
    secrets_to_sanitize = [
        secret for secret in secrets_to_sanitize
        if isinstance(secret, str) and len(secret) >= 3 and secret != "****"
    ]

    # Sort by length (longest first) to avoid partial replacements
    secrets_to_sanitize.sort(key=len, reverse=True)

    # Replace each secret with ****
    for secret in secrets_to_sanitize:
        if secret in sanitized:
            sanitized = sanitized.replace(secret, "****")

    return sanitized


def sanitize_connection_string(connection_string: str) -> str:
    """Sanitize a database connection string by masking credentials.

    This function uses regex patterns to identify and mask credentials in
    common connection string formats.

    Supported formats:
    - Oracle: user/password@host:port/service
    - PostgreSQL: postgresql://user:password@host:port/database
    - MySQL: mysql://user:password@host:port/database
    - Generic: protocol://user:password@host

    Args:
        connection_string: The connection string to sanitize.

    Returns:
        Sanitized connection string with password masked.

    Examples:
        >>> # Oracle format
        >>> conn_str = "user/secret123@localhost:1521/ORCL"
        >>> sanitized = sanitize_connection_string(conn_str)
        >>> "secret123" in sanitized
        False
        >>> "user/****@localhost:1521/ORCL" == sanitized
        True

        >>> # PostgreSQL format
        >>> conn_str = "postgresql://user:secret@localhost:5432/mydb"
        >>> sanitized = sanitize_connection_string(conn_str)
        >>> "secret" in sanitized
        False
        >>> "postgresql://user:****@localhost:5432/mydb" == sanitized
        True

        >>> # No credentials
        >>> conn_str = "localhost:5432"
        >>> sanitize_connection_string(conn_str)
        'localhost:5432'
    """
    sanitized = connection_string

    # Pattern 1: Oracle format (user/password@host)
    # Matches: user/password@host:port/service
    # The password part is everything between / and the last @
    oracle_pattern = r'([a-zA-Z0-9_]+)/(.+?)@'
    sanitized = re.sub(oracle_pattern, r'\1/****@', sanitized)

    # Pattern 2: URL format (protocol://user:password@host)
    # Matches: postgresql://user:password@host, mysql://user:password@host, etc.
    url_pattern = r'([a-zA-Z][a-zA-Z0-9+.-]*://[^:]+):([^@\s]+)@'
    sanitized = re.sub(url_pattern, r'\1:****@', sanitized)

    return sanitized


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary by masking sensitive fields.

    This function creates a copy of the dictionary with sensitive fields
    (identified by key names) masked with ****.

    Args:
        data: Dictionary to sanitize.

    Returns:
        New dictionary with sensitive fields masked.

    Examples:
        >>> data = {
        ...     "username": "user",
        ...     "password": "secret",
        ...     "host": "localhost",
        ...     "api_token": "abc123"
        ... }
        >>> sanitized = sanitize_dict(data)
        >>> sanitized["password"]
        '****'
        >>> sanitized["api_token"]
        '****'
        >>> sanitized["username"]
        'user'
        >>> sanitized["host"]
        'localhost'
    """
    sanitized = data.copy()

    # List of sensitive key patterns
    sensitive_patterns = [
        "password", "passwd", "pwd",
        "token", "secret", "key",
        "credential", "auth",
        "api_key", "apikey"
    ]

    # Mask sensitive fields
    for key in sanitized:
        if any(pattern in key.lower() for pattern in sensitive_patterns):
            if sanitized[key] is not None:
                sanitized[key] = "****"

    return sanitized
