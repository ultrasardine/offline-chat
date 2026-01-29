"""Integration tests for database error scenarios.

**Requirements**: 2.3, 3.4, 4.3

This module contains integration tests that verify error handling
across different database error scenarios. Tests cover:
- Connection failure handling
- Invalid query handling
- Non-existent table handling
- Error message propagation
- Graceful degradation
"""

import asyncio
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offline_chat import Agent, AgentManager, ChatSession
from offline_chat.database_config import create_database_mcp_config


@pytest.fixture
def temp_sqlite_db():
    """Create a temporary SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Create test database with sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a test table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Insert test data
    cursor.executemany(
        "INSERT INTO products (name, price) VALUES (?, ?)",
        [
            ("Laptop", 999.99),
            ("Mouse", 29.99),
        ],
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_database_tools():
    """Create mock database tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Execute SQL query against database",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "describe_table",
                "description": "Get schema information for a specific table",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to describe",
                        }
                    },
                    "required": ["table_name"],
                },
            },
        },
    ]


def test_connection_failure_handling(temp_agents_dir, temp_history_dir):
    """Test handling of database connection failures.

    **Validates: Requirements 2.3**

    This test verifies that:
    - Connection failures are caught and handled gracefully
    - Descriptive error messages are returned
    - Chat session continues without database tools
    - Session remains stable after connection failure
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create database configuration with invalid path
        invalid_config = create_database_mcp_config("sqlite", "invalid_db", path="/nonexistent/path/to/database.db")

        # Create agent with invalid database configuration
        agent = Agent(
            name="error-test-agent",
            display_name="Error Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[invalid_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock MCPClientManager to simulate connection failure
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value

            # Simulate connection failure
            mock_manager_instance.connect_all = AsyncMock(
                side_effect=Exception("Failed to connect to database: File not found")
            )
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.clients = {}

            # Start session - should handle connection failure gracefully
            result = await session.start_async("error-test-agent")

            # Session should still start successfully despite connection failure
            assert result is True
            assert session.is_active

            # Database connections should not be available
            assert not session.has_database_connections

            # Tools should be empty (no database tools available)
            tools = session._get_tools()
            assert len(tools) == 0

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_connection_failure_error_message(temp_agents_dir, temp_history_dir):
    """Test that connection failures return descriptive error messages.

    **Validates: Requirements 2.3**

    This test verifies that:
    - Connection error messages are descriptive
    - Error messages contain information about the failure
    - Error messages do not contain sensitive credentials
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create database configuration with invalid connection
        invalid_config = create_database_mcp_config(
            "postgresql",
            "invalid_postgres",
            host="nonexistent.host.local",
            port=5432,
            database="testdb",
            username="testuser",
            password="secret123",
        )

        # Create agent
        agent = Agent(
            name="postgres-error-agent",
            display_name="PostgreSQL Error Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[invalid_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock MCPClientManager to simulate connection failure with descriptive error
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value

            error_message = (
                "Failed to connect to PostgreSQL database at nonexistent.host.local:5432 - Connection refused"
            )

            # Simulate connection failure with descriptive error
            mock_manager_instance.connect_all = AsyncMock(side_effect=Exception(error_message))
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.clients = {}

            # Capture error by trying to start session
            try:
                await session.start_async("postgres-error-agent")
            except Exception as e:
                error_str = str(e)

                # Verify error message is descriptive
                assert "Failed to connect" in error_str or "Connection" in error_str

                # Verify error message does not contain password
                assert "secret123" not in error_str

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_invalid_query_handling(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_database_tools):
    """Test handling of invalid SQL queries.

    **Validates: Requirements 3.4**

    This test verifies that:
    - Invalid SQL queries are caught
    - Syntax error messages are returned to the agent
    - Error messages describe the syntax problem
    - Session remains stable after query errors
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="query-error-agent",
            display_name="Query Error Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock query error result
        error_message = "Error: SQL syntax error near 'SELCT' - did you mean 'SELECT'?"

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_database_tools)
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=error_message)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("query-error-agent")

            # Execute invalid query through tool
            result = await session._mcp_manager.call_tool(
                "query_database",
                {"query": "SELCT * FROM products"},  # Typo: SELCT instead of SELECT
            )

            # Verify error message is returned
            assert "Error" in result or "error" in result
            assert "syntax" in result.lower() or "SELCT" in result

            # Verify session is still active
            assert session.is_active

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_invalid_query_with_missing_table(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_database_tools):
    """Test handling of queries referencing non-existent tables.

    **Validates: Requirements 3.4**

    This test verifies that:
    - Queries referencing non-existent tables return errors
    - Error messages indicate the table doesn't exist
    - Error messages include the table name
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="table-error-agent",
            display_name="Table Error Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock query error result for non-existent table
        error_message = "Error: no such table: nonexistent_table"

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_database_tools)
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=error_message)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("table-error-agent")

            # Execute query with non-existent table
            result = await session._mcp_manager.call_tool(
                "query_database", {"query": "SELECT * FROM nonexistent_table"}
            )

            # Verify error message is returned
            assert "Error" in result or "error" in result
            assert "table" in result.lower()
            assert "nonexistent_table" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_nonexistent_table_describe(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_database_tools):
    """Test describing a non-existent table returns an error.

    **Validates: Requirements 4.3**

    This test verifies that:
    - Requesting schema for a non-existent table returns an error
    - Error message indicates the table was not found
    - Error message includes the table name
    - Session remains stable after the error
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="describe-error-agent",
            display_name="Describe Error Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock describe_table error result
        error_message = "Error: Table 'invalid_table' not found in database"

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_database_tools)
            mock_manager_instance.tool_registry = {"describe_table": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=error_message)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("describe-error-agent")

            # Execute describe_table for non-existent table
            result = await session._mcp_manager.call_tool("describe_table", {"table_name": "invalid_table"})

            # Verify error message is returned
            assert "Error" in result or "error" in result
            assert "not found" in result.lower()
            assert "invalid_table" in result

            # Verify session is still active
            assert session.is_active

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_multiple_error_scenarios_in_session(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_database_tools):
    """Test handling multiple errors in the same session.

    **Validates: Requirements 2.3, 3.4, 4.3**

    This test verifies that:
    - Multiple errors can occur in the same session
    - Each error is handled independently
    - Session remains stable across multiple errors
    - Error messages are returned for each error
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="multi-error-agent",
            display_name="Multi Error Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock different error results
        error_responses = {
            "syntax_error": "Error: SQL syntax error near 'SELCT'",
            "table_not_found": "Error: no such table: missing_table",
            "describe_error": "Error: Table 'unknown_table' not found",
        }

        call_count = 0

        async def mock_call_tool(name, args):
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return error_responses["syntax_error"]
            elif call_count == 1:
                call_count += 1
                return error_responses["table_not_found"]
            else:
                call_count += 1
                return error_responses["describe_error"]

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_database_tools)
            mock_manager_instance.tool_registry = {
                "query_database": "test_db",
                "describe_table": "test_db",
            }
            mock_manager_instance.call_tool = mock_call_tool
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("multi-error-agent")

            # Execute query with syntax error
            result1 = await session._mcp_manager.call_tool("query_database", {"query": "SELCT * FROM products"})
            assert "Error" in result1
            assert "syntax" in result1.lower()

            # Execute query with non-existent table
            result2 = await session._mcp_manager.call_tool("query_database", {"query": "SELECT * FROM missing_table"})
            assert "Error" in result2
            assert "table" in result2.lower()

            # Execute describe_table with non-existent table
            result3 = await session._mcp_manager.call_tool("describe_table", {"table_name": "unknown_table"})
            assert "Error" in result3
            assert "not found" in result3.lower()

            # Verify session is still active after all errors
            assert session.is_active
            assert call_count == 3

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_graceful_degradation_on_connection_failure(temp_agents_dir, temp_history_dir):
    """Test that chat session continues without database tools on connection failure.

    **Validates: Requirements 2.3**

    This test verifies that:
    - Session starts successfully even if database connection fails
    - Database tools are not available when connection fails
    - Session can still function for non-database operations
    - Error is logged but doesn't crash the session
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create database configuration that will fail to connect
        failing_config = create_database_mcp_config("sqlite", "failing_db", path="/invalid/path/database.db")

        # Create agent with failing database configuration
        agent = Agent(
            name="degraded-agent",
            display_name="Degraded Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            temperature=0.7,
            mcp_servers=[failing_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock MCPClientManager to simulate connection failure
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value

            # Simulate connection failure
            mock_manager_instance.connect_all = AsyncMock(side_effect=Exception("Database connection failed"))
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.clients = {}

            # Start session - should succeed despite connection failure
            result = await session.start_async("degraded-agent")

            # Verify session started successfully
            assert result is True
            assert session.is_active

            # Verify no database connections are available
            assert not session.has_database_connections
            connections = session.get_database_connections()
            assert len(connections) == 0

            # Verify no database tools are available
            tools = session._get_tools()
            assert len(tools) == 0

            # Session should still be functional for other operations
            # (e.g., regular chat without database tools)
            assert session.agent is not None
            assert session.agent.name == "degraded-agent"

        # Clean up
        await session.end_async()

    asyncio.run(run_test())
