"""Property-based tests for sensitive field masking.

This module contains property-based tests using Hypothesis to verify universal
properties of sensitive field masking functionality.

Properties tested:
- Property 9: Sensitive Field Masking

**Validates: Requirements 3.3, 10.2, 10.3**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database.connection import DatabaseConnection

# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid connection names (kebab-case)
valid_connection_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=30).filter(
    lambda s: s[0] != "-" and s[-1] != "-" and "--" not in s and s[0] not in "0123456789"
)

# Database types
database_types = st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"])

# Non-empty text for sensitive fields
sensitive_text = st.text(min_size=1, max_size=100).filter(lambda s: s.strip() != "")

# Passwords (longer to avoid substring matches with common words)
password_text = st.text(
    min_size=8,
    max_size=100,
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="!@#$%^&*_-"),
).filter(
    lambda s: (
        s.strip() != ""
        and len(s) >= 8
        # Avoid passwords that are substrings of common field values
        and not any(word in s.lower() for word in ["localhost", "testdb", "database"])
        and not any(s.lower() in word for word in ["localhost", "testdb", "database", "connection"])
    )
)

# Host names
hostnames = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=".-_"), min_size=1, max_size=50
).filter(lambda s: s[0] not in ".-_" and s[-1] not in ".-_")

# Port numbers
ports = st.integers(min_value=1, max_value=65535)

# Sensitive keys for additional_params
sensitive_keys = st.sampled_from(
    [
        "password",
        "token",
        "api_key",
        "secret",
        "credential",
        "auth_token",
        "access_key",
        "private_key",
        "secret_key",
        "PASSWORD",
        "Token",
        "API_KEY",
        "Secret",
        "CREDENTIAL",
    ]
)

# Non-sensitive keys for additional_params
non_sensitive_keys = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=20
).filter(
    lambda s: not any(sensitive in s.lower() for sensitive in ["password", "token", "key", "secret", "credential"])
)


# ============================================================================
# Property 9: Sensitive Field Masking
# ============================================================================


@given(
    name=valid_connection_names,
    database_type=database_types,
    password=password_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_password_field_masking(name, database_type, password):
    """Property 9: Sensitive Field Masking (Password Field)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection with a password field, displaying the connection should
    mask the password with asterisks, and the actual password value should not
    appear in the masked output.
    """
    # Create a connection with a password
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        password=password,
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify password is masked
    assert masked["password"] == "********", f"Password should be masked with '********', got '{masked['password']}'"

    # Verify actual password does not appear in the password field
    assert masked["password"] != password, "Actual password should not appear in password field"

    # Verify password is not in sensitive string fields (but may appear in numbers, etc.)
    sensitive_string_fields = ["password", "username", "host", "database", "service_name", "file_path"]
    for key in sensitive_string_fields:
        value = masked.get(key)
        if isinstance(value, str) and value and len(password) > 1:  # Only check for passwords longer than 1 char
            assert password not in value or key == "password" and value == "********", (
                f"Password should not appear unmasked in field '{key}'"
            )


@given(
    name=valid_connection_names,
    database_type=database_types,
    sensitive_key=sensitive_keys,
    sensitive_value=sensitive_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_additional_params_sensitive_masking(name, database_type, sensitive_key, sensitive_value):
    """Property 9: Sensitive Field Masking (Additional Params - Sensitive)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection with sensitive fields in additional_params (containing
    'password', 'token', 'key', 'secret', 'credential'), the values should be
    masked with asterisks, and actual values should not appear in the output.
    """
    # Create a connection with sensitive additional params
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        additional_params={sensitive_key: sensitive_value},
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify sensitive value in additional_params is masked
    assert sensitive_key in masked["additional_params"], (
        f"Sensitive key '{sensitive_key}' should be present in masked output"
    )

    assert masked["additional_params"][sensitive_key] == "********", (
        f"Sensitive value for '{sensitive_key}' should be masked with '********'"
    )

    # Verify actual sensitive value does not appear unmasked in additional_params
    for key, value in masked["additional_params"].items():
        if key == sensitive_key:
            assert value == "********", f"Sensitive value for '{sensitive_key}' should be masked"
        elif isinstance(value, str) and len(sensitive_value) > 1:
            # Only check for values longer than 1 char to avoid false positives
            assert value != sensitive_value, "Sensitive value should not appear unmasked in additional_params"


@given(
    name=valid_connection_names,
    database_type=database_types,
    non_sensitive_key=non_sensitive_keys,
    non_sensitive_value=st.text(min_size=1, max_size=50),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_additional_params_non_sensitive_preserved(
    name, database_type, non_sensitive_key, non_sensitive_value
):
    """Property 9: Sensitive Field Masking (Additional Params - Non-Sensitive)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection with non-sensitive fields in additional_params, the
    values should be preserved as-is and not masked.
    """
    # Create a connection with non-sensitive additional params
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        additional_params={non_sensitive_key: non_sensitive_value},
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify non-sensitive value is preserved
    assert non_sensitive_key in masked["additional_params"], (
        f"Non-sensitive key '{non_sensitive_key}' should be present in masked output"
    )

    assert masked["additional_params"][non_sensitive_key] == non_sensitive_value, (
        f"Non-sensitive value should be preserved, expected '{non_sensitive_value}', "
        f"got '{masked['additional_params'][non_sensitive_key]}'"
    )


@given(
    name=valid_connection_names,
    database_type=database_types,
    password=sensitive_text,
    sensitive_params=st.dictionaries(keys=sensitive_keys, values=sensitive_text, min_size=1, max_size=5),
    non_sensitive_params=st.dictionaries(
        keys=non_sensitive_keys, values=st.text(min_size=1, max_size=50), min_size=1, max_size=5
    ),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_multiple_sensitive_fields_masking(
    name, database_type, password, sensitive_params, non_sensitive_params
):
    """Property 9: Sensitive Field Masking (Multiple Sensitive Fields)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection with multiple sensitive fields (password and multiple
    sensitive additional_params), all sensitive values should be masked while
    non-sensitive values are preserved.
    """
    # Combine sensitive and non-sensitive params
    all_params = {**sensitive_params, **non_sensitive_params}

    # Create a connection with multiple sensitive fields
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        password=password,
        additional_params=all_params,
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify password is masked
    assert masked["password"] == "********", "Password should be masked"

    # Verify actual password does not appear in password field
    assert masked["password"] != password, "Actual password should not appear in password field"

    # Verify all sensitive params are masked
    for key, value in sensitive_params.items():
        assert masked["additional_params"][key] == "********", f"Sensitive param '{key}' should be masked"
        # Verify the actual value is not the masked value
        assert value != "********" or masked["additional_params"][key] == "********", (
            f"Sensitive value for '{key}' should be masked"
        )

    # Verify all non-sensitive params are preserved
    for key, value in non_sensitive_params.items():
        assert masked["additional_params"][key] == value, f"Non-sensitive param '{key}' should be preserved"


@given(
    name=valid_connection_names,
    database_type=database_types,
    hostname=hostnames,
    port=ports,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_non_sensitive_fields_preserved(name, database_type, hostname, port):
    """Property 9: Sensitive Field Masking (Non-Sensitive Fields Preserved)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection, non-sensitive fields (name, database_type, host, port)
    should be preserved as-is in the masked output.
    """
    # Create a connection with non-sensitive fields
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        host=hostname if database_type != "sqlite" else None,
        port=port if database_type != "sqlite" else None,
        password="secret123",  # Add a password to ensure masking works
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify non-sensitive fields are preserved
    assert masked["name"] == name, f"Name should be preserved, expected '{name}', got '{masked['name']}'"

    assert masked["database_type"] == database_type, "Database type should be preserved"

    if database_type != "sqlite":
        assert masked["host"] == hostname, f"Host should be preserved, expected '{hostname}', got '{masked['host']}'"

        assert masked["port"] == port, f"Port should be preserved, expected {port}, got {masked['port']}"


@given(
    name=valid_connection_names,
    database_type=database_types,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_no_password_field_handling(name, database_type):
    """Property 9: Sensitive Field Masking (No Password Field)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection without a password field (password is None), the masked
    output should handle this gracefully without errors.
    """
    # Create a connection without a password
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        password=None,
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation (should not raise an error)
    masked = connection.mask_sensitive_fields()

    # Verify password field is None or not masked
    assert masked["password"] is None, f"Password should be None when not set, got '{masked['password']}'"


@given(
    name=valid_connection_names,
    database_type=database_types,
    password=st.just(""),  # Empty string password
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_9_empty_password_handling(name, database_type, password):
    """Property 9: Sensitive Field Masking (Empty Password)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any connection with an empty password string, the masked output should
    handle this gracefully (empty strings are falsy in Python).
    """
    # Create a connection with an empty password
    connection = DatabaseConnection(
        name=name,
        database_type=database_type,
        password=password,
        host="localhost" if database_type != "sqlite" else None,
        port=5432 if database_type != "sqlite" else None,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify empty password is not masked (since it's falsy)
    assert masked["password"] == "", f"Empty password should remain empty, got '{masked['password']}'"


@given(
    name=valid_connection_names,
    password=sensitive_text,
    username=st.text(min_size=1, max_size=50),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_oracle_connection_masking(name, password, username):
    """Property 9: Sensitive Field Masking (Oracle Connection)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any Oracle connection with password, the password should be masked
    while other Oracle-specific fields (service_name, username) are preserved.
    """
    # Create an Oracle connection
    connection = DatabaseConnection(
        name=name,
        database_type="oracle",
        host="oracle.example.com",
        port=1521,
        service_name="ORCL",
        username=username,
        password=password,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify password is masked
    assert masked["password"] == "********", "Password should be masked"

    # Verify actual password does not appear in password field
    assert masked["password"] != password, "Actual password should not appear in password field"

    # Verify non-sensitive Oracle fields are preserved
    assert masked["service_name"] == "ORCL", "Service name should be preserved"

    assert masked["username"] == username, "Username should be preserved"


@given(
    name=valid_connection_names,
    password=sensitive_text,
    database_name=st.text(min_size=1, max_size=50),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_postgresql_connection_masking(name, password, database_name):
    """Property 9: Sensitive Field Masking (PostgreSQL Connection)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any PostgreSQL connection with password, the password should be masked
    while other PostgreSQL-specific fields (database) are preserved.
    """
    # Create a PostgreSQL connection
    connection = DatabaseConnection(
        name=name,
        database_type="postgresql",
        host="postgres.example.com",
        port=5432,
        database=database_name,
        username="postgres",
        password=password,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify password is masked
    assert masked["password"] == "********", "Password should be masked"

    # Verify actual password does not appear in password field
    assert masked["password"] != password, "Actual password should not appear in password field"

    # Verify database name is preserved
    assert masked["database"] == database_name, "Database name should be preserved"


@given(
    name=valid_connection_names,
    file_path=st.text(min_size=1, max_size=100),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_9_sqlite_connection_no_password(name, file_path):
    """Property 9: Sensitive Field Masking (SQLite Connection)

    **Validates: Requirements 3.3, 10.2, 10.3**

    For any SQLite connection (which typically has no password), the masked
    output should preserve the file_path and handle the absence of password.
    """
    # Create a SQLite connection
    connection = DatabaseConnection(
        name=name,
        database_type="sqlite",
        file_path=file_path,
    )

    # Get masked representation
    masked = connection.mask_sensitive_fields()

    # Verify file_path is preserved
    assert masked["file_path"] == file_path, "File path should be preserved"

    # Verify password is None
    assert masked["password"] is None, "SQLite connection should have no password"
