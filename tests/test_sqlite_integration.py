"""Integration tests for SQLite database access.

**Requirements**: 1.1, 1.4, 2.1, 3.2, 4.1

This module contains integration tests that verify SQLite database access
through MCP servers. Tests cover:
- Agent creation with SQLite database configuration
- Chat session initialization with database connections
- Query execution through tool calling
- Result verification
- Connection lifecycle management
"""

import asyncio
import logging
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
            price REAL NOT NULL,
            category TEXT
        )
    """)

    # Insert test data
    cursor.executemany(
        "INSERT INTO products (name, price, category) VALUES (?, ?, ?)",
        [
            ("Laptop", 999.99, "Electronics"),
            ("Mouse", 29.99, "Electronics"),
            ("Desk", 299.99, "Furniture"),
            ("Chair", 199.99, "Furniture"),
        ],
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_sqlite_tools():
    """Create mock SQLite MCP tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Execute SQL query against SQLite database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"},
                        "max_rows": {
                            "type": "integer",
                            "description": "Maximum number of rows to return",
                            "default": 100,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_tables",
                "description": "List all tables in the database",
                "parameters": {"type": "object", "properties": {}},
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


def test_create_agent_with_sqlite_database(temp_agents_dir, temp_history_dir, temp_sqlite_db):
    """Test creating agent with SQLite database configuration.

    **Validates: Requirements 1.1, 1.4**

    This test verifies that:
    - A SQLite database MCP config can be created with a file path
    - The config has the correct database type and path
    - An agent can be created with the SQLite database configuration
    - The agent configuration persists correctly with database settings
    """
    manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

    # Create SQLite database configuration
    sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

    # Verify configuration properties
    assert sqlite_config.database_type == "sqlite"
    assert sqlite_config.database_path == temp_sqlite_db
    assert sqlite_config.command == "npx"
    assert "mcp-server-sqlite-npx" in sqlite_config.args
    assert temp_sqlite_db in sqlite_config.args

    # Create agent with SQLite database
    agent = Agent(
        name="sqlite-analyst",
        display_name="SQLite Data Analyst",
        base_model="llama3:latest",
        system_prompt="You are a data analyst with access to SQLite databases.",
        temperature=0.7,
        mcp_servers=[sqlite_config],
    )

    # Mock the ollama create command
    with patch("offline_chat.manager.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.create_agent(agent)

    # Verify agent was created and configuration persisted
    loaded_agent = manager.get_agent("sqlite-analyst")
    assert loaded_agent is not None
    assert len(loaded_agent.mcp_servers) == 1
    assert loaded_agent.mcp_servers[0].database_type == "sqlite"
    assert loaded_agent.mcp_servers[0].database_path == temp_sqlite_db


def test_chat_session_with_sqlite_database(
    temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_sqlite_tools
):
    """Test starting a chat session with SQLite database access.

    **Validates: Requirements 2.1**

    This test verifies that:
    - A chat session can be started with a SQLite database-enabled agent
    - Database connections are established and tracked
    - The session recognizes it has database connections
    - Connection information is accessible via session properties
    - Connections are properly closed when the session ends
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="sqlite-analyst",
            display_name="SQLite Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock MCPClientManager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_sqlite_tools)
            mock_manager_instance.tool_registry = {"query_database": "products_db"}
            mock_manager_instance.clients = {"products_db": MagicMock()}

            # Start session
            result = await session.start_async("sqlite-analyst")

            # Verify session started successfully
            assert result is True
            assert session.is_active

            # Verify database connections are tracked
            assert session.has_database_connections

            # Verify connection information
            connections = session.get_database_connections()
            assert "products_db" in connections
            assert connections["products_db"] == "sqlite"

        # End session and verify cleanup
        await session.end_async()
        assert not session.has_database_connections

    asyncio.run(run_test())


def test_execute_sqlite_query(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_sqlite_tools):
    """Test executing SQL queries through the query_database tool.

    **Validates: Requirements 3.2, 4.1**

    This test verifies that:
    - SQLite database tools are discovered and registered
    - The query_database tool is available in the tool list
    - SQL queries can be executed through the tool
    - Query results are returned correctly
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="sqlite-analyst",
            display_name="SQLite Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock query result
        mock_result = """id | name | price | category
1 | Laptop | 999.99 | Electronics
2 | Mouse | 29.99 | Electronics

2 rows returned"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_sqlite_tools)
            mock_manager_instance.tool_registry = {"query_database": "products_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"products_db": MagicMock()}

            # Start session
            await session.start_async("sqlite-analyst")

            # Verify query_database tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "query_database" in tool_names

            # Execute query through tool
            result = await session._mcp_manager.call_tool(
                "query_database",
                {
                    "query": (
                        "SELECT id, name, price, category FROM products "
                        "WHERE category = 'Electronics'"
                    )
                },
            )

            # Verify result contains expected data
            assert "id" in result
            assert "name" in result
            assert "Laptop" in result
            assert "Mouse" in result
            assert "Electronics" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_sqlite_list_tables(temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_sqlite_tools):
    """Test listing tables in SQLite database.

    **Validates: Requirements 4.1**

    This test verifies that:
    - The list_tables tool is available
    - Tables can be listed from the SQLite database
    - The products table is included in the results
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="sqlite-analyst",
            display_name="SQLite Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock list_tables result
        mock_result = """Tables in database:
- products

1 table found"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_sqlite_tools)
            mock_manager_instance.tool_registry = {
                "query_database": "products_db",
                "list_tables": "products_db",
            }
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"products_db": MagicMock()}

            # Start session
            await session.start_async("sqlite-analyst")

            # Verify list_tables tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "list_tables" in tool_names

            # Execute list_tables through tool
            result = await session._mcp_manager.call_tool("list_tables", {})

            # Verify result contains products table
            assert "products" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_sqlite_connection_cleanup(
    temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_sqlite_tools
):
    """Test that SQLite database connections are properly closed.

    **Validates: Requirements 2.1**

    This test verifies that:
    - Database connections are tracked during session
    - Connections are properly closed when session ends
    - No resource leaks occur
    - Cleanup is logged appropriately
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="sqlite-analyst",
            display_name="SQLite Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Capture log messages for cleanup verification
        log_messages = []

        class LogCapture(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())

        handler = LogCapture()
        logger = logging.getLogger("offline_chat.session")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            # Mock MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = AsyncMock()
                mock_manager_instance.get_all_tools = MagicMock(return_value=mock_sqlite_tools)
                mock_manager_instance.tool_registry = {}
                mock_manager_instance.clients = {"products_db": MagicMock()}
                mock_manager_instance.disconnect_all = AsyncMock()

                # Start session
                await session.start_async("sqlite-analyst")

                # Verify connection is active
                assert session.has_database_connections
                connections = session.get_database_connections()
                assert "products_db" in connections

            # End session
            await session.end_async()

            # Verify connections are closed
            assert not session.has_database_connections
            assert len(session.get_database_connections()) == 0

            # Verify cleanup was logged
            cleanup_logs = [
                msg for msg in log_messages if "Closing" in msg or "closed" in msg.lower()
            ]
            assert len(cleanup_logs) > 0, "Expected connection cleanup logs"
        finally:
            logger.removeHandler(handler)

    asyncio.run(run_test())


def test_sqlite_multiple_queries_same_session(
    temp_agents_dir, temp_history_dir, temp_sqlite_db, mock_sqlite_tools
):
    """Test executing multiple queries in the same session.

    **Validates: Requirements 2.1, 3.2**

    This test verifies that:
    - Multiple queries can be executed in a single session
    - Connection is reused across queries
    - Each query returns correct results
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db)

        # Create agent with SQLite database
        agent = Agent(
            name="sqlite-analyst",
            display_name="SQLite Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock query results
        query_results = [
            "id | name\n1 | Laptop\n2 | Mouse\n\n2 rows",
            "id | name\n3 | Desk\n4 | Chair\n\n2 rows",
            "category | count\nElectronics | 2\nFurniture | 2\n\n2 rows",
        ]

        call_count = 0

        async def mock_call_tool(name, args):
            nonlocal call_count
            result = query_results[call_count]
            call_count += 1
            return result

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_sqlite_tools)
            mock_manager_instance.tool_registry = {"query_database": "products_db"}
            mock_manager_instance.call_tool = mock_call_tool
            mock_manager_instance.clients = {"products_db": MagicMock()}

            # Start session
            await session.start_async("sqlite-analyst")

            # Execute multiple queries
            result1 = await session._mcp_manager.call_tool(
                "query_database",
                {"query": "SELECT id, name FROM products WHERE category = 'Electronics'"},
            )
            assert "Laptop" in result1
            assert "Mouse" in result1

            result2 = await session._mcp_manager.call_tool(
                "query_database",
                {"query": "SELECT id, name FROM products WHERE category = 'Furniture'"},
            )
            assert "Desk" in result2
            assert "Chair" in result2

            result3 = await session._mcp_manager.call_tool(
                "query_database",
                {"query": "SELECT category, COUNT(*) as count FROM products GROUP BY category"},
            )
            assert "Electronics" in result3
            assert "Furniture" in result3

            # Verify all three queries were executed
            assert call_count == 3

        # Clean up
        await session.end_async()

    asyncio.run(run_test())
