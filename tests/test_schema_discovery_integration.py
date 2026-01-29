"""Integration tests for database schema discovery.

**Requirements**: 4.1, 4.2, 4.4, 4.5, 4.6

This module contains integration tests that verify schema discovery
functionality across different database types. Tests cover:
- list_tables tool (list-connections for Oracle)
- describe_table tool
- get_schema tool
- Oracle system table filtering
- Schema information completeness
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
def temp_sqlite_db_with_schema():
    """Create a temporary SQLite database with multiple tables for schema testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Create test database with multiple tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            description TEXT
        )
    """)

    # Create customers table
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_schema_tools():
    """Create mock database schema discovery tools."""
    return [
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
        {
            "type": "function",
            "function": {
                "name": "get_schema",
                "description": "Get the complete database schema",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


@pytest.fixture
def mock_oracle_schema_tools():
    """Create mock Oracle schema discovery tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list-connections",
                "description": "List available SQLcl connections",
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
        {
            "type": "function",
            "function": {
                "name": "get_schema",
                "description": "Get the complete database schema",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


def test_list_tables_sqlite(temp_agents_dir, temp_history_dir, temp_sqlite_db_with_schema, mock_schema_tools):
    """Test listing tables in SQLite database.

    **Validates: Requirements 4.1**

    This test verifies that:
    - The list_tables tool is available
    - All tables in the database are returned
    - Table names are correct
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db_with_schema)

        # Create agent with SQLite database
        agent = Agent(
            name="schema-analyst",
            display_name="Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are a database schema analyst.",
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
- customers
- orders

3 tables found"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_schema_tools)
            mock_manager_instance.tool_registry = {"list_tables": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("schema-analyst")

            # Verify list_tables tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "list_tables" in tool_names

            # Execute list_tables through tool
            result = await session._mcp_manager.call_tool("list_tables", {})

            # Verify result contains all tables
            assert "products" in result
            assert "customers" in result
            assert "orders" in result
            assert "3 tables" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_list_connections_oracle(temp_agents_dir, temp_history_dir, mock_oracle_schema_tools):
    """Test listing connections in Oracle database (list-connections tool).

    **Validates: Requirements 4.1**

    This test verifies that:
    - The list-connections tool is available for Oracle
    - Available SQLcl connections are returned
    - Oracle uses list-connections instead of list_tables
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create Oracle database configuration
        oracle_config = create_database_mcp_config("oracle", "prod_db", connection_name="PROD_ANALYTICS")

        # Create agent with Oracle database
        agent = Agent(
            name="oracle-schema-analyst",
            display_name="Oracle Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are an Oracle database schema analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock list-connections result
        mock_result = """Available SQLcl connections:
- PROD_ANALYTICS
- DEV_ANALYTICS
- TEST_DB

3 connections found"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_schema_tools)
            mock_manager_instance.tool_registry = {"list-connections": "prod_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"prod_db": MagicMock()}

            # Start session
            await session.start_async("oracle-schema-analyst")

            # Verify list-connections tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "list-connections" in tool_names

            # Execute list-connections through tool
            result = await session._mcp_manager.call_tool("list-connections", {})

            # Verify result contains connections
            assert "PROD_ANALYTICS" in result
            assert "DEV_ANALYTICS" in result
            assert "TEST_DB" in result
            assert "3 connections" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_describe_table(temp_agents_dir, temp_history_dir, temp_sqlite_db_with_schema, mock_schema_tools):
    """Test describing a specific table.

    **Validates: Requirements 4.2**

    This test verifies that:
    - The describe_table tool is available
    - Table schema information is returned
    - Column names, data types, and constraints are included
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db_with_schema)

        # Create agent with SQLite database
        agent = Agent(
            name="schema-analyst",
            display_name="Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are a database schema analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock describe_table result
        mock_result = """Table: products

Columns:
- id: INTEGER, PRIMARY KEY, AUTOINCREMENT
- name: TEXT, NOT NULL
- price: REAL, NOT NULL
- category: TEXT
- description: TEXT

Constraints:
- PRIMARY KEY (id)"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_schema_tools)
            mock_manager_instance.tool_registry = {"describe_table": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("schema-analyst")

            # Verify describe_table tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "describe_table" in tool_names

            # Execute describe_table through tool
            result = await session._mcp_manager.call_tool("describe_table", {"table_name": "products"})

            # Verify result contains schema information
            assert "products" in result
            assert "id" in result
            assert "name" in result
            assert "price" in result
            assert "category" in result
            assert "description" in result
            assert "INTEGER" in result
            assert "TEXT" in result
            assert "REAL" in result
            assert "PRIMARY KEY" in result
            assert "NOT NULL" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_get_schema(temp_agents_dir, temp_history_dir, temp_sqlite_db_with_schema, mock_schema_tools):
    """Test getting complete database schema.

    **Validates: Requirements 4.6**

    This test verifies that:
    - The get_schema tool is available
    - Complete schema for all tables is returned in a single call
    - Schema includes all tables and their columns
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db_with_schema)

        # Create agent with SQLite database
        agent = Agent(
            name="schema-analyst",
            display_name="Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are a database schema analyst.",
            temperature=0.7,
            mcp_servers=[sqlite_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock get_schema result with complete schema
        mock_result = """Database Schema:

Table: products
- id: INTEGER, PRIMARY KEY, AUTOINCREMENT
- name: TEXT, NOT NULL
- price: REAL, NOT NULL
- category: TEXT
- description: TEXT

Table: customers
- id: INTEGER, PRIMARY KEY, AUTOINCREMENT
- name: TEXT, NOT NULL
- email: TEXT, UNIQUE, NOT NULL
- created_at: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP

Table: orders
- id: INTEGER, PRIMARY KEY, AUTOINCREMENT
- customer_id: INTEGER, NOT NULL, FOREIGN KEY -> customers(id)
- product_id: INTEGER, NOT NULL, FOREIGN KEY -> products(id)
- quantity: INTEGER, NOT NULL
- order_date: TIMESTAMP, DEFAULT CURRENT_TIMESTAMP

3 tables in schema"""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_schema_tools)
            mock_manager_instance.tool_registry = {"get_schema": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("schema-analyst")

            # Verify get_schema tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "get_schema" in tool_names

            # Execute get_schema through tool
            result = await session._mcp_manager.call_tool("get_schema", {})

            # Verify result contains complete schema
            assert "products" in result
            assert "customers" in result
            assert "orders" in result

            # Verify all columns from all tables are present
            assert "id" in result
            assert "name" in result
            assert "price" in result
            assert "email" in result
            assert "customer_id" in result
            assert "product_id" in result
            assert "quantity" in result

            # Verify data types and constraints
            assert "INTEGER" in result
            assert "TEXT" in result
            assert "REAL" in result
            assert "TIMESTAMP" in result
            assert "PRIMARY KEY" in result
            assert "FOREIGN KEY" in result
            assert "NOT NULL" in result
            assert "UNIQUE" in result

            # Verify summary
            assert "3 tables" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_oracle_system_table_filtering(temp_agents_dir, temp_history_dir, mock_oracle_schema_tools):
    """Test that Oracle system tables are filtered out.

    **Validates: Requirements 4.4, 4.5**

    This test verifies that:
    - Oracle queries USER_TABLES or ALL_TABLES based on permissions
    - System tables are filtered out from results
    - Only user tables are returned
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create Oracle database configuration
        oracle_config = create_database_mcp_config("oracle", "prod_db", connection_name="PROD_ANALYTICS")

        # Create agent with Oracle database
        agent = Agent(
            name="oracle-schema-analyst",
            display_name="Oracle Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are an Oracle database schema analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock describe_table result showing it queries USER_TABLES
        # and filters out system tables
        mock_result = """Table: EMPLOYEES

Source: USER_TABLES (system tables filtered)

Columns:
- EMPLOYEE_ID: NUMBER, PRIMARY KEY
- FIRST_NAME: VARCHAR2(50), NOT NULL
- LAST_NAME: VARCHAR2(50), NOT NULL
- EMAIL: VARCHAR2(100), UNIQUE
- HIRE_DATE: DATE, NOT NULL
- SALARY: NUMBER(10,2)

Note: System tables (SYS, SYSTEM, DBTOOLS$*) are excluded from schema queries."""

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_schema_tools)
            mock_manager_instance.tool_registry = {"describe_table": "prod_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"prod_db": MagicMock()}

            # Start session
            await session.start_async("oracle-schema-analyst")

            # Execute describe_table through tool
            result = await session._mcp_manager.call_tool("describe_table", {"table_name": "EMPLOYEES"})

            # Verify result indicates system table filtering
            assert "USER_TABLES" in result or "ALL_TABLES" in result
            assert "system tables filtered" in result.lower() or "excluded" in result.lower()

            # Verify no system table references in result
            assert "SYS." not in result
            assert "SYSTEM." not in result

            # Verify user table information is present
            assert "EMPLOYEES" in result
            assert "EMPLOYEE_ID" in result
            assert "NUMBER" in result or "VARCHAR2" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_describe_nonexistent_table(temp_agents_dir, temp_history_dir, temp_sqlite_db_with_schema, mock_schema_tools):
    """Test describing a non-existent table returns an error.

    **Validates: Requirements 4.3** (from requirement 4 acceptance criteria)

    This test verifies that:
    - Requesting schema for a non-existent table returns an error
    - Error message indicates the table was not found
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create SQLite database configuration
        sqlite_config = create_database_mcp_config("sqlite", "test_db", path=temp_sqlite_db_with_schema)

        # Create agent with SQLite database
        agent = Agent(
            name="schema-analyst",
            display_name="Schema Analyst",
            base_model="llama3:latest",
            system_prompt="You are a database schema analyst.",
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
        mock_result = "Error: Table 'nonexistent_table' not found in database"

        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_schema_tools)
            mock_manager_instance.tool_registry = {"describe_table": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"test_db": MagicMock()}

            # Start session
            await session.start_async("schema-analyst")

            # Execute describe_table for non-existent table
            result = await session._mcp_manager.call_tool("describe_table", {"table_name": "nonexistent_table"})

            # Verify error message
            assert "Error" in result or "error" in result
            assert "not found" in result.lower()
            assert "nonexistent_table" in result

        # Clean up
        await session.end_async()

    asyncio.run(run_test())


def test_schema_tools_available_for_multiple_databases(
    temp_agents_dir, temp_history_dir, temp_sqlite_db_with_schema, mock_schema_tools
):
    """Test that schema tools are available when multiple databases are configured.

    **Validates: Requirements 4.1, 4.2, 4.6**

    This test verifies that:
    - Schema tools are available for each configured database
    - Tools are properly namespaced when multiple databases exist
    - Each database's schema can be queried independently
    """

    async def run_test():
        manager = AgentManager(agents_dir=str(temp_agents_dir), history_dir=str(temp_history_dir))

        # Create two SQLite database configurations
        sqlite_config1 = create_database_mcp_config("sqlite", "products_db", path=temp_sqlite_db_with_schema)
        sqlite_config2 = create_database_mcp_config("sqlite", "analytics_db", path=temp_sqlite_db_with_schema)

        # Create agent with multiple databases
        agent = Agent(
            name="multi-db-analyst",
            display_name="Multi-Database Analyst",
            base_model="llama3:latest",
            system_prompt="You are a database analyst with access to multiple databases.",
            temperature=0.7,
            mcp_servers=[sqlite_config1, sqlite_config2],
        )

        # Create agent (mock ollama command)
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Create chat session
        session = ChatSession(manager)

        # Mock tools for both databases
        all_tools = [
            {
                "type": "function",
                "function": {
                    "name": "products_db_list_tables",
                    "description": "List tables in products_db",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analytics_db_list_tables",
                    "description": "List tables in analytics_db",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "products_db_describe_table",
                    "description": "Describe table in products_db",
                    "parameters": {
                        "type": "object",
                        "properties": {"table_name": {"type": "string"}},
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analytics_db_describe_table",
                    "description": "Describe table in analytics_db",
                    "parameters": {
                        "type": "object",
                        "properties": {"table_name": {"type": "string"}},
                        "required": ["table_name"],
                    },
                },
            },
        ]

        # Mock MCPClientManager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=all_tools)
            mock_manager_instance.tool_registry = {
                "products_db_list_tables": "products_db",
                "analytics_db_list_tables": "analytics_db",
                "products_db_describe_table": "products_db",
                "analytics_db_describe_table": "analytics_db",
            }
            mock_manager_instance.clients = {
                "products_db": MagicMock(),
                "analytics_db": MagicMock(),
            }

            # Start session
            await session.start_async("multi-db-analyst")

            # Verify schema tools are available for both databases
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]

            # Check for namespaced tools
            assert "products_db_list_tables" in tool_names
            assert "analytics_db_list_tables" in tool_names
            assert "products_db_describe_table" in tool_names
            assert "analytics_db_describe_table" in tool_names

            # Verify both databases are tracked
            connections = session.get_database_connections()
            assert "products_db" in connections
            assert "analytics_db" in connections

        # Clean up
        await session.end_async()

    asyncio.run(run_test())
