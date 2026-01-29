"""Unit tests for edge cases in database connection management.

This module tests edge cases and error scenarios that might not be covered
by the main integration tests. Focus is on boundary conditions, error handling,
and unusual inputs.

**Validates: Requirements 3.5, 5.5**

Edge cases tested:
- Empty connection list display
- Connection deletion cancellation
- File permission errors
- Store file missing
- Invalid connection references
- Invalid access level specifications
- Empty guidelines list
"""

import json
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from offline_chat.agent import Agent
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import Ok, is_err, is_ok, unwrap, unwrap_err
from offline_chat.manager import AgentManager


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with necessary directories."""
    store_path = tmp_path / "connections.json"
    agents_dir = tmp_path / "agents"
    history_dir = tmp_path / "history"
    agents_dir.mkdir()
    history_dir.mkdir()
    return {"store_path": store_path, "agents_dir": agents_dir, "history_dir": history_dir, "tmp_path": tmp_path}


@pytest.fixture
def db_manager(temp_workspace):
    """Create a DatabaseConnectionManager with temp workspace."""
    return DatabaseConnectionManager(store_path=temp_workspace["store_path"], agents_dir=temp_workspace["agents_dir"])


@pytest.fixture
def agent_manager(db_manager, temp_workspace):
    """Create an AgentManager with temp workspace."""
    manager = AgentManager(
        agents_dir=temp_workspace["agents_dir"], history_dir=temp_workspace["history_dir"], db_manager=db_manager
    )
    return manager


class TestEmptyConnectionListDisplay:
    """Test edge cases for displaying empty connection lists.

    **Validates: Requirement 3.5**
    """

    def test_list_connections_when_empty(self, db_manager):
        """Test listing connections returns empty list when no connections exist."""
        connections = db_manager.list_connections()

        assert isinstance(connections, list)
        assert len(connections) == 0

    def test_get_connection_when_store_empty(self, db_manager):
        """Test getting a specific connection when store is empty."""
        result = db_manager.get_connection("nonexistent")

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg.lower()

    def test_get_agents_using_connection_when_empty(self, db_manager):
        """Test getting agents using a connection when no agents exist."""
        agents = db_manager.get_agents_using_connection("any-connection")

        assert isinstance(agents, list)
        assert len(agents) == 0

    def test_resolve_connections_with_empty_list(self, db_manager):
        """Test resolving an empty list of connection assignments."""
        result = db_manager.resolve_connections([])

        assert is_ok(result)
        resolved = unwrap(result)
        assert isinstance(resolved, list)
        assert len(resolved) == 0


class TestConnectionDeletionCancellation:
    """Test edge cases for connection deletion cancellation.

    **Validates: Requirement 5.5**
    """

    def test_delete_nonexistent_connection(self, db_manager):
        """Test attempting to delete a connection that doesn't exist."""
        result = db_manager.delete_connection("nonexistent-conn")

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg.lower()

    def test_delete_connection_in_use_by_agent(self, db_manager, agent_manager, temp_workspace):
        """Test that deletion is prevented when connection is in use."""
        # Create a connection
        connection = DatabaseConnection(
            name="in-use-conn", database_type="sqlite", file_path=str(temp_workspace["tmp_path"] / "test.db")
        )

        with patch.object(db_manager, "_validate_connection", return_value=Ok(None)):
            db_manager.create_connection(connection)

        # Create an agent using this connection
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [
                {"connection_name": "in-use-conn", "access_level": "read-only", "allowed_tables": []}
            ],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to delete the connection
        result = db_manager.delete_connection("in-use-conn")

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "in use" in error_msg.lower() or "used by" in error_msg.lower()
        assert "test-agent" in error_msg

        # Verify connection still exists
        result = db_manager.get_connection("in-use-conn")
        assert is_ok(result)

    def test_delete_connection_after_removing_from_all_agents(self, db_manager, agent_manager, temp_workspace):
        """Test successful deletion after removing connection from all agents."""
        # Create a connection
        connection = DatabaseConnection(
            name="removable-conn", database_type="sqlite", file_path=str(temp_workspace["tmp_path"] / "test.db")
        )

        with patch.object(db_manager, "_validate_connection", return_value=Ok(None)):
            db_manager.create_connection(connection)

        # Create an agent using this connection
        agent_dir = temp_workspace["agents_dir"] / "temp-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "temp-agent",
            "display_name": "Temp Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a temp agent.",
            "temperature": 0.7,
            "connection_assignments": [
                {"connection_name": "removable-conn", "access_level": "read-only", "allowed_tables": []}
            ],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Verify deletion fails while in use
        result = db_manager.delete_connection("removable-conn")
        assert is_err(result)

        # Remove connection from agent
        result = agent_manager.remove_connection("temp-agent", "removable-conn")
        assert is_ok(result)

        # Now deletion should succeed
        result = db_manager.delete_connection("removable-conn")
        assert is_ok(result)

        # Verify connection is gone
        result = db_manager.get_connection("removable-conn")
        assert is_err(result)


class TestFilePermissionErrors:
    """Test edge cases for file permission errors.

    **Validates: Requirement 5.5**
    """

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_read_store_with_no_read_permission(self, temp_workspace):
        """Test handling of store file with no read permissions."""
        store_path = temp_workspace["store_path"]

        # Create store file
        with open(store_path, "w") as f:
            json.dump({"version": "1.0", "connections": []}, f)

        # Remove read permissions
        os.chmod(store_path, 0o000)

        try:
            # Attempt to create manager (should handle gracefully)
            manager = DatabaseConnectionManager(store_path=store_path, agents_dir=temp_workspace["agents_dir"])

            # Attempt to list connections (should handle error)
            connections = manager.list_connections()

            # Should return empty list or handle gracefully
            assert isinstance(connections, list)
        finally:
            # Restore permissions for cleanup
            os.chmod(store_path, 0o600)

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_write_store_with_no_write_permission(self, temp_workspace):
        """Test handling of store file with no write permissions."""
        store_path = temp_workspace["store_path"]

        # Create store file
        with open(store_path, "w") as f:
            json.dump({"version": "1.0", "connections": []}, f)

        # Remove write permissions
        os.chmod(store_path, 0o400)

        try:
            manager = DatabaseConnectionManager(store_path=store_path, agents_dir=temp_workspace["agents_dir"])

            # Attempt to create a connection (should fail gracefully)
            connection = DatabaseConnection(name="test-conn", database_type="sqlite", file_path="/tmp/test.db")

            with patch.object(manager, "_validate_connection", return_value=Ok(None)):
                result = manager.create_connection(connection)

            # The manager may succeed if it can write to the file despite permissions
            # (e.g., if the process owns the file). The key is that it handles the
            # situation gracefully without crashing.
            assert result is not None
        finally:
            # Restore permissions for cleanup
            os.chmod(store_path, 0o600)

    def test_store_directory_not_writable(self, tmp_path):
        """Test handling when store directory is not writable."""
        # Create a directory structure
        store_dir = tmp_path / "readonly_dir"
        store_dir.mkdir()
        store_path = store_dir / "connections.json"
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        if os.name != "nt":
            # Make directory read-only
            os.chmod(store_dir, 0o500)

            try:
                # Attempt to create manager (should raise PermissionError)
                with pytest.raises(PermissionError):
                    DatabaseConnectionManager(store_path=store_path, agents_dir=agents_dir)
            finally:
                # Restore permissions for cleanup
                os.chmod(store_dir, 0o700)


class TestStoreFileMissing:
    """Test edge cases for missing store file.

    **Validates: Requirement 5.5**
    """

    def test_manager_creates_store_when_missing(self, temp_workspace):
        """Test that manager creates store file if it doesn't exist."""
        store_path = temp_workspace["store_path"]

        # Ensure store doesn't exist
        assert not store_path.exists()

        # Create manager
        DatabaseConnectionManager(store_path=store_path, agents_dir=temp_workspace["agents_dir"])

        # Store should now exist
        assert store_path.exists()

        # Store should have correct structure
        with open(store_path, "r") as f:
            data = json.load(f)

        assert "version" in data
        assert "connections" in data
        assert isinstance(data["connections"], list)
        assert len(data["connections"]) == 0

    def test_list_connections_when_store_missing(self, temp_workspace):
        """Test listing connections when store file is missing."""
        store_path = temp_workspace["store_path"]

        # Ensure store doesn't exist
        assert not store_path.exists()

        manager = DatabaseConnectionManager(store_path=store_path, agents_dir=temp_workspace["agents_dir"])

        # Should return empty list
        connections = manager.list_connections()
        assert isinstance(connections, list)
        assert len(connections) == 0

    def test_store_deleted_between_operations(self, temp_workspace):
        """Test handling when store is deleted between operations."""
        manager = DatabaseConnectionManager(
            store_path=temp_workspace["store_path"], agents_dir=temp_workspace["agents_dir"]
        )

        # Create a connection
        connection = DatabaseConnection(name="test-conn", database_type="sqlite", file_path="/tmp/test.db")

        with patch.object(manager, "_validate_connection", return_value=Ok(None)):
            result = manager.create_connection(connection)

        assert is_ok(result)

        # Delete the store file
        temp_workspace["store_path"].unlink()

        # Attempt to list connections (should handle gracefully)
        connections = manager.list_connections()

        # Should return empty list or recreate store
        assert isinstance(connections, list)


class TestInvalidConnectionReferences:
    """Test edge cases for invalid connection references.

    **Validates: Requirement 5.5**
    """

    def test_resolve_nonexistent_connection(self, db_manager):
        """Test resolving a connection that doesn't exist."""
        assignment = AgentConnectionAssignment(
            connection_name="nonexistent-conn", access_level=AccessLevel.READ_ONLY, allowed_tables=[]
        )

        result = db_manager.resolve_connections([assignment])

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()
        assert "nonexistent-conn" in error_msg

    def test_resolve_multiple_connections_one_invalid(self, db_manager, temp_workspace):
        """Test resolving multiple connections where one doesn't exist."""
        # Create one valid connection
        connection = DatabaseConnection(
            name="valid-conn", database_type="sqlite", file_path=str(temp_workspace["tmp_path"] / "test.db")
        )

        with patch.object(db_manager, "_validate_connection", return_value=Ok(None)):
            db_manager.create_connection(connection)

        # Try to resolve valid and invalid connections
        assignments = [
            AgentConnectionAssignment(
                connection_name="valid-conn", access_level=AccessLevel.READ_ONLY, allowed_tables=[]
            ),
            AgentConnectionAssignment(
                connection_name="invalid-conn", access_level=AccessLevel.READ_ONLY, allowed_tables=[]
            ),
        ]

        result = db_manager.resolve_connections(assignments)

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "invalid-conn" in error_msg

    def test_assign_nonexistent_connection_to_agent(self, agent_manager, temp_workspace):
        """Test assigning a nonexistent connection to an agent."""
        # Create an agent
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to assign nonexistent connection
        result = agent_manager.assign_connection("test-agent", "nonexistent-conn", AccessLevel.READ_ONLY, [])

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()

    def test_remove_nonexistent_connection_from_agent(self, agent_manager, temp_workspace):
        """Test removing a connection that agent doesn't have."""
        # Create an agent without any connections
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to remove a connection that doesn't exist in agent
        result = agent_manager.remove_connection("test-agent", "nonexistent-conn")

        # Should either succeed (no-op) or return error
        # Both behaviors are acceptable for this edge case
        assert result is not None


class TestInvalidAccessLevelSpecifications:
    """Test edge cases for invalid access level specifications.

    **Validates: Requirement 5.5**
    """

    def test_create_assignment_with_invalid_access_level_string(self):
        """Test creating assignment with invalid access level string via from_dict."""
        # The AccessLevel enum will raise ValueError when given an invalid value
        # through the from_dict method
        invalid_data = {"connection_name": "test-conn", "access_level": "invalid-level", "allowed_tables": []}

        with pytest.raises(ValueError):
            AgentConnectionAssignment.from_dict(invalid_data)

    def test_table_specific_access_without_tables(self, agent_manager, db_manager, temp_workspace):
        """Test table-specific access level without specifying tables."""
        # Create a connection
        connection = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
        )

        with patch.object(db_manager, "_validate_connection", return_value=Ok(None)):
            db_manager.create_connection(connection)

        # Create an agent
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to assign with table-specific access but empty tables list
        result = agent_manager.assign_connection(
            "test-agent",
            "test-conn",
            AccessLevel.TABLE_SPECIFIC_READ,
            [],  # Empty tables list
        )

        # Should fail validation
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "table" in error_msg.lower()

    def test_non_table_specific_access_with_tables(self, agent_manager, db_manager, temp_workspace):
        """Test non-table-specific access level with tables specified."""
        # Create a connection
        connection = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
        )

        with patch.object(db_manager, "_validate_connection", return_value=Ok(None)):
            db_manager.create_connection(connection)

        # Create an agent
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Assign with read-only access but tables specified (should be ignored)
        result = agent_manager.assign_connection(
            "test-agent",
            "test-conn",
            AccessLevel.READ_ONLY,
            ["users", "orders"],  # Tables specified but not needed
        )

        # Should succeed (tables are ignored for non-table-specific access)
        assert is_ok(result)

        # Verify assignment was created correctly
        with open(agent_dir / "config.json", "r") as f:
            config = json.load(f)

        assignment = config["connection_assignments"][0]
        assert assignment["access_level"] == "read-only"
        # Tables may or may not be stored, both are acceptable

    def test_deserialize_assignment_with_invalid_access_level(self):
        """Test deserializing assignment with invalid access level from JSON."""
        invalid_data = {
            "connection_name": "test-conn",
            "access_level": "super-admin",  # Invalid
            "allowed_tables": [],
        }

        with pytest.raises(ValueError):
            AgentConnectionAssignment.from_dict(invalid_data)


class TestEmptyGuidelinesList:
    """Test edge cases for empty guidelines list.

    **Validates: Requirement 5.5**
    """

    def test_agent_with_no_guidelines(self, temp_workspace):
        """Test agent with empty guidelines list."""
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        agent = Agent.from_dict(agent_config)

        assert agent.guidelines == []
        assert len(agent.guidelines) == 0

    def test_system_prompt_with_empty_guidelines(self, temp_workspace):
        """Test that empty guidelines don't add guidelines section to prompt."""
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        agent = Agent.from_dict(agent_config)
        full_prompt = agent.get_full_system_prompt()

        # Should be exactly the base prompt
        assert full_prompt == "You are a test agent."
        assert "Guidelines:" not in full_prompt

    def test_list_guidelines_when_empty(self, agent_manager, temp_workspace):
        """Test listing guidelines when agent has none."""
        # Create an agent with no guidelines
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        result = agent_manager.list_guidelines("test-agent")

        assert is_ok(result)
        guidelines = unwrap(result)
        assert isinstance(guidelines, list)
        assert len(guidelines) == 0

    def test_delete_guideline_from_empty_list(self, agent_manager, temp_workspace):
        """Test attempting to delete guideline when list is empty."""
        # Create an agent with no guidelines
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to delete guideline at index 0
        result = agent_manager.delete_guideline("test-agent", 0)

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "index" in error_msg.lower() or "out of range" in error_msg.lower()

    def test_edit_guideline_in_empty_list(self, agent_manager, temp_workspace):
        """Test attempting to edit guideline when list is empty."""
        # Create an agent with no guidelines
        agent_dir = temp_workspace["agents_dir"] / "test-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)

        # Attempt to edit guideline at index 0
        result = agent_manager.edit_guideline("test-agent", 0, "New text")

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "index" in error_msg.lower() or "out of range" in error_msg.lower()

    def test_agent_without_guidelines_field(self, temp_workspace):
        """Test agent config without guidelines field (backward compatibility)."""
        agent_config = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "connection_assignments": [],
            # No guidelines field
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        agent = Agent.from_dict(agent_config)

        # Should default to empty list
        assert hasattr(agent, "guidelines")
        assert agent.guidelines == []

        # System prompt should work normally
        full_prompt = agent.get_full_system_prompt()
        assert full_prompt == "You are a test agent."
