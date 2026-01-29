"""Unit tests and property-based tests for ConnectionValidator."""

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database import (
    ConnectionValidator,
    DatabaseConnection,
    is_err,
    is_ok,
    unwrap_err,
)


class TestValidateOracle:
    """Tests for validate_oracle() method."""

    def test_validate_oracle_success(self):
        """Test validating a valid Oracle connection."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_ok(result), f"Expected Ok, got Err: {unwrap_err(result) if is_err(result) else ''}"

    def test_validate_oracle_missing_host(self):
        """Test that missing host field is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host=None,
            port=1521,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'host'" in error_msg
        assert "oracle" in error_msg

    def test_validate_oracle_missing_port(self):
        """Test that missing port field is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=None,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'port'" in error_msg

    def test_validate_oracle_missing_service_name(self):
        """Test that missing service_name field is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name=None,
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'service_name'" in error_msg

    def test_validate_oracle_missing_username(self):
        """Test that missing username field is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username=None,
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'username'" in error_msg

    def test_validate_oracle_missing_password(self):
        """Test that missing password field is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username="testuser",
            password=None
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'password'" in error_msg

    def test_validate_oracle_empty_string_fields(self):
        """Test that empty string fields are rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="",
            port=1521,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'host'" in error_msg

    def test_validate_oracle_invalid_port_zero(self):
        """Test that port 0 is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=0,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid port number" in error_msg

    def test_validate_oracle_invalid_port_negative(self):
        """Test that negative port is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=-1,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid port number" in error_msg

    def test_validate_oracle_invalid_port_too_large(self):
        """Test that port > 65535 is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=65536,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid port number" in error_msg

    def test_validate_oracle_wrong_database_type(self):
        """Test that wrong database type is rejected."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="postgresql",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_oracle(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid database type" in error_msg
        assert "postgresql" in error_msg


class TestValidatePostgreSQL:
    """Tests for validate_postgresql() method."""

    def test_validate_postgresql_success(self):
        """Test validating a valid PostgreSQL connection."""
        conn = DatabaseConnection(
            name="test-postgres",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_postgresql(conn)
        assert is_ok(result)

    def test_validate_postgresql_missing_host(self):
        """Test that missing host field is rejected."""
        conn = DatabaseConnection(
            name="test-postgres",
            database_type="postgresql",
            host=None,
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_postgresql(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'host'" in error_msg
        assert "postgresql" in error_msg

    def test_validate_postgresql_missing_database(self):
        """Test that missing database field is rejected."""
        conn = DatabaseConnection(
            name="test-postgres",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database=None,
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_postgresql(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'database'" in error_msg

    def test_validate_postgresql_invalid_port(self):
        """Test that invalid port is rejected."""
        conn = DatabaseConnection(
            name="test-postgres",
            database_type="postgresql",
            host="localhost",
            port=0,
            database="testdb",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_postgresql(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid port number" in error_msg


class TestValidateMySQL:
    """Tests for validate_mysql() method."""

    def test_validate_mysql_success(self):
        """Test validating a valid MySQL connection."""
        conn = DatabaseConnection(
            name="test-mysql",
            database_type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_mysql(conn)
        assert is_ok(result)

    def test_validate_mysql_missing_host(self):
        """Test that missing host field is rejected."""
        conn = DatabaseConnection(
            name="test-mysql",
            database_type="mysql",
            host=None,
            port=3306,
            database="testdb",
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_mysql(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'host'" in error_msg
        assert "mysql" in error_msg

    def test_validate_mysql_missing_database(self):
        """Test that missing database field is rejected."""
        conn = DatabaseConnection(
            name="test-mysql",
            database_type="mysql",
            host="localhost",
            port=3306,
            database=None,
            username="testuser",
            password="testpass"
        )

        result = ConnectionValidator.validate_mysql(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'database'" in error_msg


class TestValidateSQLite:
    """Tests for validate_sqlite() method."""

    def test_validate_sqlite_success(self):
        """Test validating a valid SQLite connection."""
        conn = DatabaseConnection(
            name="test-sqlite",
            database_type="sqlite",
            file_path="/path/to/database.db"
        )

        result = ConnectionValidator.validate_sqlite(conn)
        assert is_ok(result)

    def test_validate_sqlite_missing_file_path(self):
        """Test that missing file_path field is rejected."""
        conn = DatabaseConnection(
            name="test-sqlite",
            database_type="sqlite",
            file_path=None
        )

        result = ConnectionValidator.validate_sqlite(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'file_path'" in error_msg
        assert "sqlite" in error_msg

    def test_validate_sqlite_empty_file_path(self):
        """Test that empty file_path is rejected."""
        conn = DatabaseConnection(
            name="test-sqlite",
            database_type="sqlite",
            file_path=""
        )

        result = ConnectionValidator.validate_sqlite(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'file_path'" in error_msg

    def test_validate_sqlite_whitespace_file_path(self):
        """Test that whitespace-only file_path is rejected."""
        conn = DatabaseConnection(
            name="test-sqlite",
            database_type="sqlite",
            file_path="   "
        )

        result = ConnectionValidator.validate_sqlite(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Missing required field 'file_path'" in error_msg

    def test_validate_sqlite_wrong_database_type(self):
        """Test that wrong database type is rejected."""
        conn = DatabaseConnection(
            name="test-sqlite",
            database_type="mysql",
            file_path="/path/to/database.db"
        )

        result = ConnectionValidator.validate_sqlite(conn)
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid database type" in error_msg
        assert "mysql" in error_msg


class TestTestConnection:
    """Tests for test_connection() method."""

    def test_test_connection_placeholder(self):
        """Test that test_connection returns Ok (placeholder implementation)."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="sqlite",
            file_path="/path/to/db.db"
        )

        result = ConnectionValidator.test_connection(conn)
        assert is_ok(result), "Placeholder implementation should return Ok"


# Property-Based Tests

# Helper strategy for non-whitespace text
def non_whitespace_text(min_size=1, max_size=100):
    return st.text(
    min_size=min_size, max_size=max_size
).filter(lambda s: s.strip() != "")


@given(
    host=non_whitespace_text(min_size=1, max_size=100),
    port=st.integers(min_value=1, max_value=65535),
    service_name=non_whitespace_text(min_size=1, max_size=50),
    username=non_whitespace_text(min_size=1, max_size=50),
    password=non_whitespace_text(min_size=1, max_size=100)
)
@settings(max_examples=100, deadline=None)
def test_property_oracle_required_fields_validation(host, port, service_name, username, password):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.2, 8.3**

    For any Oracle connection with all required fields present and valid,
    validation should succeed.
    """
    conn = DatabaseConnection(
        name="test-oracle",
        database_type="oracle",
        host=host,
        port=port,
        service_name=service_name,
        username=username,
        password=password
    )

    result = ConnectionValidator.validate_oracle(conn)
    assert is_ok(result), f"Valid Oracle connection should pass validation, got: {unwrap_err(result) if is_err(result) else ''}"


@given(
    host=non_whitespace_text(min_size=1, max_size=100),
    port=st.integers(min_value=1, max_value=65535),
    database=non_whitespace_text(min_size=1, max_size=50),
    username=non_whitespace_text(min_size=1, max_size=50),
    password=non_whitespace_text(min_size=1, max_size=100)
)
@settings(max_examples=100, deadline=None)
def test_property_postgresql_required_fields_validation(host, port, database, username, password):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.4**

    For any PostgreSQL connection with all required fields present and valid,
    validation should succeed.
    """
    conn = DatabaseConnection(
        name="test-postgres",
        database_type="postgresql",
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )

    result = ConnectionValidator.validate_postgresql(conn)
    assert is_ok(result), f"Valid PostgreSQL connection should pass validation, got: {unwrap_err(result) if is_err(result) else ''}"


@given(
    host=non_whitespace_text(min_size=1, max_size=100),
    port=st.integers(min_value=1, max_value=65535),
    database=non_whitespace_text(min_size=1, max_size=50),
    username=non_whitespace_text(min_size=1, max_size=50),
    password=non_whitespace_text(min_size=1, max_size=100)
)
@settings(max_examples=100, deadline=None)
def test_property_mysql_required_fields_validation(host, port, database, username, password):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.5**

    For any MySQL connection with all required fields present and valid,
    validation should succeed.
    """
    conn = DatabaseConnection(
        name="test-mysql",
        database_type="mysql",
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )

    result = ConnectionValidator.validate_mysql(conn)
    assert is_ok(result), f"Valid MySQL connection should pass validation, got: {unwrap_err(result) if is_err(result) else ''}"


@given(
    file_path=non_whitespace_text(min_size=1, max_size=200)
)
@settings(max_examples=100, deadline=None)
def test_property_sqlite_required_fields_validation(file_path):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.6**

    For any SQLite connection with file_path present and non-empty (after stripping whitespace),
    validation should succeed.
    """
    conn = DatabaseConnection(
        name="test-sqlite",
        database_type="sqlite",
        file_path=file_path
    )

    result = ConnectionValidator.validate_sqlite(conn)
    assert is_ok(result), f"Valid SQLite connection should pass validation, got: {unwrap_err(result) if is_err(result) else ''}"


@given(
    missing_field=st.sampled_from(["host", "port", "service_name", "username", "password"])
)
@settings(max_examples=50, deadline=None)
def test_property_oracle_missing_required_field_fails(missing_field):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.2, 8.3**

    For any Oracle connection missing a required field, validation should fail
    with a descriptive error message.
    """
    # Create connection with all fields
    fields = {
        "name": "test-oracle",
        "database_type": "oracle",
        "host": "localhost",
        "port": 1521,
        "service_name": "TESTDB",
        "username": "user",
        "password": "pass"
    }

    # Set the missing field to None
    fields[missing_field] = None

    conn = DatabaseConnection(**fields)
    result = ConnectionValidator.validate_oracle(conn)

    assert is_err(result), f"Oracle connection missing '{missing_field}' should fail validation"
    error_msg = unwrap_err(result)
    assert "Missing required field" in error_msg
    assert missing_field in error_msg


@given(
    missing_field=st.sampled_from(["host", "port", "database", "username", "password"])
)
@settings(max_examples=50, deadline=None)
def test_property_postgresql_missing_required_field_fails(missing_field):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.4**

    For any PostgreSQL connection missing a required field, validation should fail
    with a descriptive error message.
    """
    fields = {
        "name": "test-postgres",
        "database_type": "postgresql",
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "user",
        "password": "pass"
    }

    fields[missing_field] = None

    conn = DatabaseConnection(**fields)
    result = ConnectionValidator.validate_postgresql(conn)

    assert is_err(result), f"PostgreSQL connection missing '{missing_field}' should fail validation"
    error_msg = unwrap_err(result)
    assert "Missing required field" in error_msg
    assert missing_field in error_msg


@given(
    missing_field=st.sampled_from(["host", "port", "database", "username", "password"])
)
@settings(max_examples=50, deadline=None)
def test_property_mysql_missing_required_field_fails(missing_field):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.5**

    For any MySQL connection missing a required field, validation should fail
    with a descriptive error message.
    """
    fields = {
        "name": "test-mysql",
        "database_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "user",
        "password": "pass"
    }

    fields[missing_field] = None

    conn = DatabaseConnection(**fields)
    result = ConnectionValidator.validate_mysql(conn)

    assert is_err(result), f"MySQL connection missing '{missing_field}' should fail validation"
    error_msg = unwrap_err(result)
    assert "Missing required field" in error_msg
    assert missing_field in error_msg


@given(
    port=st.integers()
)
@settings(max_examples=100, deadline=None)
def test_property_invalid_port_numbers_rejected(port):
    """
    **Property 4: Required Fields Validation by Database Type**
    **Validates: Requirements 2.4, 8.3, 8.4, 8.5**

    For any port number outside the valid range (1-65535), validation should fail.
    """
    # Skip valid ports
    if 1 <= port <= 65535:
        return

    conn = DatabaseConnection(
        name="test-conn",
        database_type="postgresql",
        host="localhost",
        port=port,
        database="testdb",
        username="user",
        password="pass"
    )

    result = ConnectionValidator.validate_postgresql(conn)
    assert is_err(result), f"Port {port} should be rejected"
    error_msg = unwrap_err(result)
    assert "Invalid port number" in error_msg


@given(
    db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"])
)
@settings(max_examples=50, deadline=None)
def test_property_error_message_quality(db_type):
    """
    **Property 27: Error Message Quality**
    **Validates: Requirements 8.7**

    For any failed connection validation, the error message should be non-empty
    and contain descriptive information about what failed.
    """
    # Create an invalid connection (missing required fields)
    conn = DatabaseConnection(
        name="test-conn",
        database_type=db_type
    )

    # Call appropriate validator
    if db_type == "oracle":
        result = ConnectionValidator.validate_oracle(conn)
    elif db_type == "postgresql":
        result = ConnectionValidator.validate_postgresql(conn)
    elif db_type == "mysql":
        result = ConnectionValidator.validate_mysql(conn)
    else:  # sqlite
        result = ConnectionValidator.validate_sqlite(conn)

    # Should fail validation
    assert is_err(result), f"Invalid {db_type} connection should fail validation"

    # Error message should be descriptive
    error_msg = unwrap_err(result)
    assert isinstance(error_msg, str), "Error message should be a string"
    assert len(error_msg) > 0, "Error message should not be empty"
    assert "Missing required field" in error_msg, "Error message should describe the problem"
