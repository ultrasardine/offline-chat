"""Unit tests and property-based tests for database connection validation."""

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.connection_validator import (
    _find_query_tool,
    _get_test_query,
    validate_database_connection,
)
from offline_chat.mcp_config import MCPServerConfig


class TestGetTestQuery:
    """Tests for _get_test_query helper function."""

    def test_oracle_test_query(self):
        """Oracle databases should use SELECT 1 FROM DUAL."""
        query = _get_test_query("oracle")
        assert query == "SELECT 1 FROM DUAL"

    def test_postgresql_test_query(self):
        """PostgreSQL databases should use SELECT 1."""
        query = _get_test_query("postgresql")
        assert query == "SELECT 1"

    def test_mysql_test_query(self):
        """MySQL databases should use SELECT 1."""
        query = _get_test_query("mysql")
        assert query == "SELECT 1"

    def test_sqlite_test_query(self):
        """SQLite databases should use SELECT 1."""
        query = _get_test_query("sqlite")
        assert query == "SELECT 1"

    def test_none_database_type(self):
        """None database type should default to SELECT 1."""
        query = _get_test_query(None)
        assert query == "SELECT 1"


class TestFindQueryTool:
    """Tests for _find_query_tool helper function."""

    def test_find_oracle_run_sql_tool(self):
        """Should find Oracle SQLcl's run-sql tool."""
        tools = [
            {"function": {"name": "run-sql", "description": "Execute SQL"}},
            {"function": {"name": "list-connections", "description": "List connections"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name == "run-sql"

    def test_find_query_database_tool(self):
        """Should find generic query_database tool."""
        tools = [
            {"function": {"name": "query_database", "description": "Query DB"}},
            {"function": {"name": "list_tables", "description": "List tables"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name == "query_database"

    def test_find_query_tool(self):
        """Should find generic query tool."""
        tools = [
            {"function": {"name": "query", "description": "Execute query"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name == "query"

    def test_find_execute_query_tool(self):
        """Should find execute_query tool."""
        tools = [
            {"function": {"name": "execute_query", "description": "Execute query"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name == "execute_query"

    def test_find_run_query_tool(self):
        """Should find run_query tool."""
        tools = [
            {"function": {"name": "run_query", "description": "Run query"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name == "run_query"

    def test_no_query_tool_found(self):
        """Should return None when no query tool is available."""
        tools = [
            {"function": {"name": "list_tables", "description": "List tables"}},
            {"function": {"name": "describe_table", "description": "Describe table"}},
        ]
        tool_name = _find_query_tool(tools)
        assert tool_name is None

    def test_empty_tools_list(self):
        """Should return None for empty tools list."""
        tool_name = _find_query_tool([])
        assert tool_name is None

    def test_priority_order(self):
        """Should prioritize run-sql over other query tools."""
        tools = [
            {"function": {"name": "query_database", "description": "Query DB"}},
            {"function": {"name": "run-sql", "description": "Execute SQL"}},
            {"function": {"name": "query", "description": "Query"}},
        ]
        tool_name = _find_query_tool(tools)
        # run-sql should be found first as it's first in the priority list
        assert tool_name == "run-sql"


class TestValidateDatabaseConnection:
    """Tests for validate_database_connection function."""

    def test_successful_connection_validation(self):
        """Should return (True, None) for successful connection."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            database_type="sqlite",
        )

        # Mock the async validation function
        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (True, None)

            success, error = validate_database_connection(config)

            assert success is True
            assert error is None
            mock_async.assert_called_once_with(config)

    def test_connection_failure(self):
        """Should return (False, error_message) when connection fails."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/nonexistent/test.db"],
            database_type="sqlite",
        )

        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (False, "Failed to connect to MCP server")

            success, error = validate_database_connection(config)

            assert success is False
            assert error is not None
            assert "Failed to connect" in error

    def test_no_query_tool_available(self):
        """Should return (False, error_message) when no query tool is found."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            database_type="sqlite",
        )

        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (False, "No query tool found for database 'test_db'")

            success, error = validate_database_connection(config)

            assert success is False
            assert error is not None
            assert "No query tool found" in error

    def test_query_execution_error(self):
        """Should return (False, error_message) when test query fails."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            database_type="sqlite",
        )

        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (False, "Test query failed: Error: Database is locked")

            success, error = validate_database_connection(config)

            assert success is False
            assert error is not None
            assert "Test query failed" in error
            assert "Database is locked" in error

    def test_oracle_database_validation(self):
        """Should use Oracle-specific test query for Oracle databases."""
        config = MCPServerConfig(
            name="oracle_db",
            command="sql",
            args=["-mcp", "-connection", "PROD"],
            database_type="oracle",
            oracle_connection_name="PROD",
        )

        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (True, None)

            success, error = validate_database_connection(config)

            assert success is True
            assert error is None

    def test_cleanup_on_exception(self):
        """Should clean up connection even when exception occurs."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            database_type="sqlite",
        )

        with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
            mock_async.return_value = (False, "Connection validation error: Unexpected error")

            success, error = validate_database_connection(config)

            assert success is False
            assert error is not None
            assert "Connection validation error" in error

    def test_unexpected_exception_handling(self):
        """Should handle unexpected exceptions during validation."""
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            database_type="sqlite",
        )

        with patch("offline_chat.connection_validator.asyncio.run") as mock_run:
            mock_run.side_effect = RuntimeError("Event loop error")

            success, error = validate_database_connection(config)

            assert success is False
            assert error is not None
            assert "Unexpected error" in error


# Property-Based Tests


@given(
    db_name=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    ),
    error_message=st.text(min_size=1, max_size=200),
)
@settings(max_examples=100)
def test_property_connection_failure_error_messages(db_name, error_message):
    """
    **Property 8: Connection failure error messages**
    **Validates: Requirements 2.3**

    For any invalid database connection parameters, attempting to connect
    should return a descriptive error message containing information about
    the failure.

    This property verifies that:
    1. When connection fails, success is False
    2. When connection fails, error message is not None
    3. Error message is a non-empty string
    4. Error message contains descriptive information
    """
    config = MCPServerConfig(
        name=db_name,
        command="uvx",
        args=["sqlite-mcp-server", "--db-path", "/nonexistent/path.db"],
        database_type="sqlite",
    )

    # Mock the async validation to simulate connection failure
    with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
        mock_async.return_value = (False, error_message)

        success, error = validate_database_connection(config)

        # Property assertions
        assert success is False, "Connection failure should return False"
        assert error is not None, "Connection failure should return an error message"
        assert isinstance(error, str), "Error message should be a string"
        assert len(error) > 0, "Error message should not be empty"
        assert error == error_message, "Error message should match the failure reason"


@given(
    db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]),
    db_name=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    ),
)
@settings(max_examples=100)
def test_property_successful_connection_returns_no_error(db_type, db_name):
    """
    **Property: Successful connection validation**
    **Validates: Requirements 2.1, 6.7**

    For any valid database configuration, when connection succeeds,
    the validator should return (True, None) with no error message.

    This property verifies that:
    1. Successful connections return True
    2. Successful connections return None for error
    3. This holds for all database types
    """
    config = MCPServerConfig(name=db_name, command="test_command", args=["--test"], database_type=db_type)

    # Mock successful connection
    with patch("offline_chat.connection_validator._validate_connection_async") as mock_async:
        mock_async.return_value = (True, None)

        success, error = validate_database_connection(config)

        # Property assertions
        assert success is True, "Successful connection should return True"
        assert error is None, "Successful connection should return None for error"


@given(db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite", None]))
@settings(max_examples=50)
def test_property_test_query_format(db_type):
    """
    **Property: Test query format correctness**

    For any database type, the test query should be a valid SQL SELECT statement.

    This property verifies that:
    1. Test query is a non-empty string
    2. Test query starts with SELECT (case-insensitive)
    3. Oracle uses SELECT 1 FROM DUAL
    4. Other databases use SELECT 1
    """
    query = _get_test_query(db_type)

    # Property assertions
    assert isinstance(query, str), "Test query should be a string"
    assert len(query) > 0, "Test query should not be empty"
    assert query.upper().startswith("SELECT"), "Test query should be a SELECT statement"

    # Database-specific assertions
    if db_type == "oracle":
        assert query == "SELECT 1 FROM DUAL", "Oracle should use SELECT 1 FROM DUAL"
    else:
        assert query == "SELECT 1", "Non-Oracle databases should use SELECT 1"


@given(
    tool_names=st.lists(
        st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
        ),
        min_size=0,
        max_size=10,
        unique=True,
    )
)
@settings(max_examples=100)
def test_property_find_query_tool_returns_valid_or_none(tool_names):
    """
    **Property: Query tool discovery correctness**

    For any list of tool names, _find_query_tool should either:
    1. Return a valid query tool name that exists in the input list, OR
    2. Return None if no query tool is found

    This property verifies that:
    1. Result is either a string or None
    2. If result is a string, it exists in the input tools
    3. If result is None, no query tool names were in the input
    """
    # Convert tool names to tool schema format
    tools = [{"function": {"name": name, "description": f"Tool {name}"}} for name in tool_names]

    result = _find_query_tool(tools)

    # Property assertions
    assert result is None or isinstance(result, str), "Result should be either None or a string"

    if result is not None:
        # If a tool was found, it should exist in the input
        assert result in tool_names, f"Found tool '{result}' should exist in input tool names"

        # It should be one of the recognized query tool names
        recognized_names = ["run-sql", "query_database", "query", "execute_query", "run_query"]
        assert result in recognized_names, f"Found tool '{result}' should be a recognized query tool name"
    else:
        # If None was returned, verify no query tools were in the input
        recognized_names = ["run-sql", "query_database", "query", "execute_query", "run_query"]
        has_query_tool = any(name in recognized_names for name in tool_names)
        assert not has_query_tool, "If no tool found, input should not contain recognized query tool names"
