"""Unit tests for access level validation integration in ChatSession.

This module tests that the AccessLevelValidator is properly integrated into
the query execution flow in ChatSession._execute_tool_async().

Feature: database-connection-management
Task: 7.3 Integrate AccessLevelValidator into query execution flow
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offline_chat.agent import Agent
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.history import HistoryStore
from offline_chat.manager import AgentManager
from offline_chat.mcp_config import MCPServerConfig
from offline_chat.session import ChatSession


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for agents and history."""
    agents_dir = tmp_path / "agents"
    history_dir = tmp_path / "history"
    agents_dir.mkdir()
    history_dir.mkdir()
    return agents_dir, history_dir


def test_read_only_access_blocks_write_queries(temp_dirs):
    """Test that read-only access blocks INSERT/UPDATE/DELETE queries.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query executed")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to execute a DELETE query (should be blocked)
            result = await session._execute_tool_async("query_database", {"query": "DELETE FROM users WHERE id = 1"})

            # Verify the query was blocked
            assert "Access denied" in result
            assert "not permitted" in result

            # Verify the actual database tool was NOT called
            mock_manager_instance.call_tool.assert_not_called()

    asyncio.run(run_test())


def test_read_only_access_allows_select_queries(temp_dirs):
    """Test that read-only access allows SELECT queries.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query results")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Execute a SELECT query (should be allowed)
            result = await session._execute_tool_async("query_database", {"query": "SELECT * FROM users"})

            # Verify the query was allowed
            assert result == "Query results"

            # Verify the actual database tool WAS called
            mock_manager_instance.call_tool.assert_called_once_with("query_database", {"query": "SELECT * FROM users"})

    asyncio.run(run_test())


def test_table_specific_access_blocks_disallowed_tables(temp_dirs):
    """Test that table-specific access blocks queries on disallowed tables.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with table-specific read access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db",
                    access_level=AccessLevel.TABLE_SPECIFIC_READ,
                    allowed_tables=["users", "orders"],
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query results")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to query a disallowed table (should be blocked)
            result = await session._execute_tool_async("query_database", {"query": "SELECT * FROM admin_secrets"})

            # Verify the query was blocked
            assert "Access denied" in result
            assert "not in allowed list" in result

            # Verify the actual database tool was NOT called
            mock_manager_instance.call_tool.assert_not_called()

    asyncio.run(run_test())


def test_non_query_tools_not_validated(temp_dirs):
    """Test that non-query tools (like list_tables) are not validated.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"list_tables": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="users, orders, products")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Execute a non-query tool (should not be validated)
            result = await session._execute_tool_async("list_tables", {})

            # Verify the tool was executed without validation
            assert result == "users, orders, products"

            # Verify the actual database tool WAS called
            mock_manager_instance.call_tool.assert_called_once_with("list_tables", {})

    asyncio.run(run_test())


def test_read_write_access_allows_write_queries(temp_dirs):
    """Test that read-write access allows INSERT/UPDATE/DELETE queries.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-write access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_WRITE, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="1 row updated")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Execute an UPDATE query (should be allowed)
            result = await session._execute_tool_async(
                "query_database", {"query": "UPDATE users SET name = 'John' WHERE id = 1"}
            )

            # Verify the query was allowed
            assert result == "1 row updated"

            # Verify the actual database tool WAS called
            mock_manager_instance.call_tool.assert_called_once()

    asyncio.run(run_test())


def test_table_specific_access_allows_allowed_tables(temp_dirs):
    """Test that table-specific access allows queries on allowed tables.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with table-specific read access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db",
                    access_level=AccessLevel.TABLE_SPECIFIC_READ,
                    allowed_tables=["users", "orders"],
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query results")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Query an allowed table (should succeed)
            result = await session._execute_tool_async("query_database", {"query": "SELECT * FROM users"})

            # Verify the query was allowed
            assert result == "Query results"

            # Verify the actual database tool WAS called
            mock_manager_instance.call_tool.assert_called_once()

    asyncio.run(run_test())


def test_table_specific_read_write_allows_write_on_allowed_tables(temp_dirs):
    """Test that table-specific read-write allows write operations on allowed tables.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with table-specific read-write access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db",
                    access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
                    allowed_tables=["users", "orders"],
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="1 row inserted")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Execute an INSERT on allowed table (should succeed)
            result = await session._execute_tool_async(
                "query_database", {"query": "INSERT INTO users (name) VALUES ('Alice')"}
            )

            # Verify the query was allowed
            assert result == "1 row inserted"

            # Verify the actual database tool WAS called
            mock_manager_instance.call_tool.assert_called_once()

    asyncio.run(run_test())


def test_table_specific_read_write_blocks_write_on_disallowed_tables(temp_dirs):
    """Test that table-specific read-write blocks write operations on disallowed tables.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with table-specific read-write access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db",
                    access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
                    allowed_tables=["users", "orders"],
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="1 row deleted")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to DELETE from disallowed table (should be blocked)
            result = await session._execute_tool_async(
                "query_database", {"query": "DELETE FROM admin_secrets WHERE id = 1"}
            )

            # Verify the query was blocked
            assert "Access denied" in result
            assert "not in allowed list" in result

            # Verify the actual database tool was NOT called
            mock_manager_instance.call_tool.assert_not_called()

    asyncio.run(run_test())


def test_error_message_contains_access_level_info(temp_dirs):
    """Test that error messages contain helpful information about access level.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock()
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to execute an INSERT query (should be blocked)
            result = await session._execute_tool_async(
                "query_database", {"query": "INSERT INTO users (name) VALUES ('Bob')"}
            )

            # Verify the error message is descriptive
            assert "Access denied" in result
            assert "not permitted" in result or "not allowed" in result

    asyncio.run(run_test())


def test_multiple_connections_with_different_access_levels(temp_dirs):
    """Test that an agent can have multiple connections with different access levels.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with multiple connections
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="readonly_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                ),
                AgentConnectionAssignment(
                    connection_name="readwrite_db", access_level=AccessLevel.READ_WRITE, allowed_tables=None
                ),
            ],
            mcp_servers=[
                MCPServerConfig(name="readonly_db", command="test", args=[], database_type="sqlite"),
                MCPServerConfig(name="readwrite_db", command="test", args=[], database_type="sqlite"),
            ],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "readonly_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query executed")
            mock_manager_instance.clients = {"readonly_db": MagicMock(), "readwrite_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["readonly_db"] = "sqlite"
            session._database_connections["readwrite_db"] = "sqlite"

            # Try to DELETE on readonly_db (should be blocked)
            result = await session._execute_tool_async("query_database", {"query": "DELETE FROM users WHERE id = 1"})

            # Verify the query was blocked
            assert "Access denied" in result

            # Now try the same query on readwrite_db (should succeed)
            mock_manager_instance.tool_registry = {"query_database": "readwrite_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="1 row deleted")

            result = await session._execute_tool_async("query_database", {"query": "DELETE FROM users WHERE id = 1"})

            # Verify the query was allowed
            assert result == "1 row deleted"

    asyncio.run(run_test())


def test_agent_without_connection_assignments(temp_dirs):
    """Test that agents without connection assignments don't cause errors.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent without connection assignments
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[],  # Empty
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value="Query results")
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to execute a query (should not crash, but may not validate)
            result = await session._execute_tool_async("query_database", {"query": "SELECT * FROM users"})

            # The query should execute (no validation without assignment)
            # This is expected behavior - if no assignment, no validation
            assert result == "Query results"

    asyncio.run(run_test())


def test_query_with_different_parameter_names(temp_dirs):
    """Test that validation works with different SQL parameter names (sql, query, statement).

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"run-sql": "test_db"}
            mock_manager_instance.call_tool = AsyncMock()
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Test with "sql" parameter name
            result = await session._execute_tool_async("run-sql", {"sql": "DELETE FROM users"})
            assert "Access denied" in result

            # Test with "statement" parameter name
            result = await session._execute_tool_async("run-sql", {"statement": "UPDATE users SET name = 'test'"})
            assert "Access denied" in result

    asyncio.run(run_test())


def test_namespaced_tool_names(temp_dirs):
    """Test that validation works with namespaced tool names (e.g., db_name_run_sql).

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with read-only access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db", access_level=AccessLevel.READ_ONLY, allowed_tables=None
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            # Namespaced tool name
            mock_manager_instance.tool_registry = {"test_db_run_sql": "test_db"}
            mock_manager_instance.call_tool = AsyncMock()
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Execute a DELETE query with namespaced tool name (should be blocked)
            result = await session._execute_tool_async("test_db_run_sql", {"sql": "DELETE FROM users WHERE id = 1"})

            # Verify the query was blocked
            assert "Access denied" in result

            # Verify the actual database tool was NOT called
            mock_manager_instance.call_tool.assert_not_called()

    asyncio.run(run_test())


def test_table_specific_read_blocks_write_operations(temp_dirs):
    """Test that table-specific-read blocks all write operations even on allowed tables.

    **Validates: Requirements 12.7, 12.8**
    """

    async def run_test():
        agents_dir, history_dir = temp_dirs
        manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)
        history_store = HistoryStore(history_dir=history_dir)

        # Create agent with table-specific read access
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            connection_assignments=[
                AgentConnectionAssignment(
                    connection_name="test_db",
                    access_level=AccessLevel.TABLE_SPECIFIC_READ,
                    allowed_tables=["users", "orders"],
                )
            ],
            mcp_servers=[MCPServerConfig(name="test_db", command="test", args=[], database_type="sqlite")],
        )

        # Save agent
        agent_dir = agents_dir / agent.name
        agent_dir.mkdir()
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent.to_dict(), f)

        # Create session
        session = ChatSession(manager, history_store)

        # Mock MCP manager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=[])
            mock_manager_instance.tool_registry = {"query_database": "test_db"}
            mock_manager_instance.call_tool = AsyncMock()
            mock_manager_instance.clients = {"test_db": MagicMock()}

            await session.start_async("test-agent")

            # Track database connections
            session._database_connections["test_db"] = "sqlite"

            # Try to UPDATE an allowed table (should be blocked - read-only)
            result = await session._execute_tool_async(
                "query_database", {"query": "UPDATE users SET name = 'test' WHERE id = 1"}
            )

            # Verify the query was blocked
            assert "Access denied" in result
            assert "not permitted" in result or "not allowed" in result

            # Verify the actual database tool was NOT called
            mock_manager_instance.call_tool.assert_not_called()

    asyncio.run(run_test())
