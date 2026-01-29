"""Unit tests for AgentManager connection assignment methods.

This module tests the connection assignment functionality in AgentManager:
- assign_connection() method
- remove_connection() method
- Validation of connection names
- Validation of allowed_tables for table-specific access
- Error handling
"""

import json

import pytest

from offline_chat.agent import Agent
from offline_chat.database import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_err, is_ok, unwrap_err
from offline_chat.manager import AgentManager


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for agents, history, and connections."""
    agents_dir = tmp_path / "agents"
    history_dir = tmp_path / "history"
    connections_file = tmp_path / "connections.json"

    agents_dir.mkdir()
    history_dir.mkdir()

    return {
        "agents_dir": agents_dir,
        "history_dir": history_dir,
        "connections_file": connections_file,
    }


@pytest.fixture
def db_manager(temp_dirs):
    """Create a DatabaseConnectionManager with test connections."""
    manager = DatabaseConnectionManager(store_path=temp_dirs["connections_file"])

    # Create test connections
    conn1 = DatabaseConnection(
        name="test-sqlite-1", database_type="sqlite", file_path=str(temp_dirs["connections_file"].parent / "test1.db")
    )
    conn2 = DatabaseConnection(
        name="test-sqlite-2", database_type="sqlite", file_path=str(temp_dirs["connections_file"].parent / "test2.db")
    )

    manager.create_connection(conn1)
    manager.create_connection(conn2)

    return manager


@pytest.fixture
def agent_manager(temp_dirs, db_manager):
    """Create an AgentManager with DatabaseConnectionManager."""
    return AgentManager(
        agents_dir=temp_dirs["agents_dir"],
        history_dir=temp_dirs["history_dir"],
        db_manager=db_manager,
    )


@pytest.fixture
def test_agent(agent_manager):
    """Create a test agent."""
    agent = Agent(
        name="test-agent",
        display_name="Test Agent",
        base_model="llama3:latest",
        system_prompt="You are a test agent.",
    )

    # Save agent config manually (skip Ollama registration for tests)
    agent_dir = agent_manager._get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)

    config_path = agent_manager._get_config_path(agent.name)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(agent.to_dict(), f, indent=2)

    return agent


class TestAssignConnection:
    """Tests for AgentManager.assign_connection() method."""

    def test_assign_connection_read_only(self, agent_manager, test_agent):
        """Test assigning a connection with read-only access."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )

        assert is_ok(result)

        # Verify assignment was saved
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].connection_name == "test-sqlite-1"
        assert agent.connection_assignments[0].access_level == AccessLevel.READ_ONLY
        assert agent.connection_assignments[0].allowed_tables is None

    def test_assign_connection_read_write(self, agent_manager, test_agent):
        """Test assigning a connection with read-write access."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_WRITE,
        )

        assert is_ok(result)

        # Verify assignment
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].access_level == AccessLevel.READ_WRITE

    def test_assign_connection_table_specific_read(self, agent_manager, test_agent):
        """Test assigning a connection with table-specific read access."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users", "orders"],
        )

        assert is_ok(result)

        # Verify assignment
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert agent.connection_assignments[0].allowed_tables == ["users", "orders"]

    def test_assign_connection_table_specific_read_write(self, agent_manager, test_agent):
        """Test assigning a connection with table-specific read-write access."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["products", "inventory"],
        )

        assert is_ok(result)

        # Verify assignment
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE
        assert agent.connection_assignments[0].allowed_tables == ["products", "inventory"]

    def test_assign_multiple_connections(self, agent_manager, test_agent):
        """Test assigning multiple connections to an agent."""
        # Assign first connection
        result1 = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )
        assert is_ok(result1)

        # Assign second connection
        result2 = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-2",
            access_level=AccessLevel.READ_WRITE,
        )
        assert is_ok(result2)

        # Verify both assignments
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 2

        conn_names = {a.connection_name for a in agent.connection_assignments}
        assert "test-sqlite-1" in conn_names
        assert "test-sqlite-2" in conn_names

    def test_assign_connection_updates_existing(self, agent_manager, test_agent):
        """Test that assigning an already-assigned connection updates it."""
        # Assign with read-only
        result1 = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )
        assert is_ok(result1)

        # Update to read-write
        result2 = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_WRITE,
        )
        assert is_ok(result2)

        # Verify only one assignment exists with updated access level
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].connection_name == "test-sqlite-1"
        assert agent.connection_assignments[0].access_level == AccessLevel.READ_WRITE

    def test_assign_connection_nonexistent_connection(self, agent_manager, test_agent):
        """Test that assigning a nonexistent connection fails."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="nonexistent-db",
            access_level=AccessLevel.READ_ONLY,
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "not found" in error.lower()

    def test_assign_connection_nonexistent_agent(self, agent_manager):
        """Test that assigning to a nonexistent agent fails."""
        result = agent_manager.assign_connection(
            agent_name="nonexistent-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "agent" in error.lower()
        assert "not found" in error.lower()

    def test_assign_connection_table_specific_without_tables(self, agent_manager, test_agent):
        """Test that table-specific access without allowed_tables fails."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=None,
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "allowed_tables" in error.lower()
        assert "require" in error.lower()  # "requires" contains "require"

    def test_assign_connection_table_specific_with_empty_tables(self, agent_manager, test_agent):
        """Test that table-specific access with empty allowed_tables fails."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=[],
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "allowed_tables" in error.lower()
        assert "non-empty" in error.lower()

    def test_assign_connection_without_db_manager(self, temp_dirs, test_agent):
        """Test that assigning without a db_manager fails gracefully."""
        # Create manager without db_manager
        manager = AgentManager(
            agents_dir=temp_dirs["agents_dir"],
            history_dir=temp_dirs["history_dir"],
            db_manager=None,
        )

        # Copy test agent to this manager's directory
        agent_dir = manager._get_agent_dir("test-agent")
        agent_dir.mkdir(parents=True, exist_ok=True)
        config_path = manager._get_config_path("test-agent")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(test_agent.to_dict(), f, indent=2)

        result = manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "DatabaseConnectionManager" in error


class TestRemoveConnection:
    """Tests for AgentManager.remove_connection() method."""

    def test_remove_connection_success(self, agent_manager, test_agent):
        """Test successfully removing a connection."""
        # First assign a connection
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )

        # Verify it was assigned
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1

        # Remove the connection
        result = agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
        )

        assert is_ok(result)

        # Verify it was removed
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 0

    def test_remove_connection_from_multiple(self, agent_manager, test_agent):
        """Test removing one connection when multiple are assigned."""
        # Assign two connections
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-2",
            access_level=AccessLevel.READ_WRITE,
        )

        # Remove one connection
        result = agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
        )

        assert is_ok(result)

        # Verify only one remains
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].connection_name == "test-sqlite-2"

    def test_remove_connection_not_assigned(self, agent_manager, test_agent):
        """Test removing a connection that is not assigned fails."""
        result = agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "not assigned" in error.lower()

    def test_remove_connection_nonexistent_agent(self, agent_manager):
        """Test removing from a nonexistent agent fails."""
        result = agent_manager.remove_connection(
            agent_name="nonexistent-agent",
            connection_name="test-sqlite-1",
        )

        assert is_err(result)
        error = unwrap_err(result)
        assert "agent" in error.lower()
        assert "not found" in error.lower()

    def test_remove_all_connections(self, agent_manager, test_agent):
        """Test removing all connections from an agent."""
        # Assign two connections
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-2",
            access_level=AccessLevel.READ_WRITE,
        )

        # Remove both
        result1 = agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
        )
        result2 = agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-2",
        )

        assert is_ok(result1)
        assert is_ok(result2)

        # Verify all removed
        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments) == 0


class TestConnectionAssignmentPersistence:
    """Tests for persistence of connection assignments."""

    def test_assignment_persists_across_loads(self, agent_manager, test_agent):
        """Test that assignments persist when agent is reloaded."""
        # Assign a connection
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users", "orders"],
        )

        # Reload the agent
        agent = agent_manager.get_agent("test-agent")

        # Verify assignment persisted
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].connection_name == "test-sqlite-1"
        assert agent.connection_assignments[0].access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert agent.connection_assignments[0].allowed_tables == ["users", "orders"]

    def test_removal_persists_across_loads(self, agent_manager, test_agent):
        """Test that removal persists when agent is reloaded."""
        # Assign and then remove
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )
        agent_manager.remove_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
        )

        # Reload the agent
        agent = agent_manager.get_agent("test-agent")

        # Verify removal persisted
        assert len(agent.connection_assignments) == 0

    def test_update_persists_across_loads(self, agent_manager, test_agent):
        """Test that updates persist when agent is reloaded."""
        # Assign with read-only
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.READ_ONLY,
        )

        # Update to table-specific
        agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["products"],
        )

        # Reload the agent
        agent = agent_manager.get_agent("test-agent")

        # Verify update persisted
        assert len(agent.connection_assignments) == 1
        assert agent.connection_assignments[0].access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE
        assert agent.connection_assignments[0].allowed_tables == ["products"]


class TestConnectionAssignmentEdgeCases:
    """Tests for edge cases in connection assignment."""

    def test_assign_with_single_table(self, agent_manager, test_agent):
        """Test assigning with a single allowed table."""
        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users"],
        )

        assert is_ok(result)

        agent = agent_manager.get_agent("test-agent")
        assert agent.connection_assignments[0].allowed_tables == ["users"]

    def test_assign_with_many_tables(self, agent_manager, test_agent):
        """Test assigning with many allowed tables."""
        tables = [f"table_{i}" for i in range(50)]

        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=tables,
        )

        assert is_ok(result)

        agent = agent_manager.get_agent("test-agent")
        assert len(agent.connection_assignments[0].allowed_tables) == 50

    def test_assign_preserves_table_order(self, agent_manager, test_agent):
        """Test that table order is preserved."""
        tables = ["zebra", "apple", "banana"]

        result = agent_manager.assign_connection(
            agent_name="test-agent",
            connection_name="test-sqlite-1",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=tables,
        )

        assert is_ok(result)

        agent = agent_manager.get_agent("test-agent")
        assert agent.connection_assignments[0].allowed_tables == ["zebra", "apple", "banana"]
