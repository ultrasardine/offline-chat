"""Integration tests for complete database connection management workflows.

This module tests end-to-end workflows that span multiple components:
- Connection lifecycle with agent assignment and access levels
- Multi-agent connection sharing with different access levels
- Migration from inline configs to centralized connections
- Error handling with corrupted store
- Guidelines management with system prompt generation
- Query validation with different access levels

**Validates: All Requirements**

These integration tests verify that all components work together correctly
in real-world scenarios, testing complete user workflows from start to finish.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.result import Ok, Err, is_ok, is_err, unwrap, unwrap_err
from offline_chat.database.access_validator import AccessLevelValidator
from offline_chat.agent import Agent
from offline_chat.manager import AgentManager


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with necessary directories."""
    store_path = tmp_path / "connections.json"
    agents_dir = tmp_path / "agents"
    history_dir = tmp_path / "history"
    agents_dir.mkdir()
    history_dir.mkdir()
    return {
        "store_path": store_path,
        "agents_dir": agents_dir,
        "history_dir": history_dir,
        "tmp_path": tmp_path
    }


@pytest.fixture
def db_manager(temp_workspace):
    """Create a DatabaseConnectionManager with temp workspace."""
    return DatabaseConnectionManager(
        store_path=temp_workspace["store_path"],
        agents_dir=temp_workspace["agents_dir"]
    )


@pytest.fixture
def agent_manager(db_manager, temp_workspace):
    """Create an AgentManager with temp workspace."""
    manager = AgentManager(
        agents_dir=temp_workspace["agents_dir"],
        history_dir=temp_workspace["history_dir"],
        db_manager=db_manager
    )
    return manager


class TestCompleteConnectionLifecycle:
    """Test complete connection lifecycle workflow.
    
    Workflow: Create connection → Assign to agent with access level → 
              Start session → Resolve → Delete
    
    **Validates: Requirements 2, 5, 6, 11, 12**
    """
    
    def test_full_lifecycle_with_read_only_access(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test complete lifecycle: create → assign with read-only → resolve → delete."""
        # Step 1: Create a SQLite connection
        connection = DatabaseConnection(
            name="test-sqlite",
            database_type="sqlite",
            file_path=str(temp_workspace["tmp_path"] / "test.db")
        )
        
        # Mock validation to avoid actual database connection
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.create_connection(connection)
        
        assert is_ok(result), f"Failed to create connection: {unwrap_err(result) if is_err(result) else ''}"
        created_conn = unwrap(result)
        assert created_conn.name == "test-sqlite"
        
        # Step 2: Create an agent
        agent_dir = temp_workspace["agents_dir"] / "data-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "data-agent",
            "display_name": "Data Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a data analyst.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Step 3: Assign connection to agent with read-only access
        result = agent_manager.assign_connection(
            "data-agent",
            "test-sqlite",
            AccessLevel.READ_ONLY,
            []
        )
        
        assert is_ok(result), f"Failed to assign connection: {unwrap_err(result) if is_err(result) else ''}"
        
        # Verify assignment was saved
        with open(agent_dir / "config.json", "r") as f:
            updated_config = json.load(f)
        
        assert len(updated_config["connection_assignments"]) == 1
        assignment = updated_config["connection_assignments"][0]
        assert assignment["connection_name"] == "test-sqlite"
        assert assignment["access_level"] == "read-only"
        
        # Step 4: Resolve connections (simulating session start)
        agent = Agent.from_dict(updated_config)
        result = db_manager.resolve_connections(agent.connection_assignments)
        
        assert is_ok(result), f"Failed to resolve connections: {unwrap_err(result) if is_err(result) else ''}"
        resolved = unwrap(result)
        assert len(resolved) == 1
        assert resolved[0][0].name == "test-sqlite"
        assert resolved[0][1] == AccessLevel.READ_ONLY
        
        # Step 5: Attempt to delete connection (should fail - in use)
        result = db_manager.delete_connection("test-sqlite")
        
        assert is_err(result), "Should not be able to delete connection in use"
        error_msg = unwrap_err(result)
        assert "used by" in error_msg.lower() or "in use" in error_msg.lower()
        assert "data-agent" in error_msg
        
        # Step 6: Remove connection from agent
        result = agent_manager.remove_connection("data-agent", "test-sqlite")
        
        assert is_ok(result), f"Failed to remove connection: {unwrap_err(result) if is_err(result) else ''}"
        
        # Step 7: Delete connection (should succeed now)
        result = db_manager.delete_connection("test-sqlite")
        
        assert is_ok(result), f"Failed to delete connection: {unwrap_err(result) if is_err(result) else ''}"
        
        # Verify connection is gone
        result = db_manager.get_connection("test-sqlite")
        assert is_err(result), "Connection should not exist after deletion"


    def test_full_lifecycle_with_table_specific_access(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test lifecycle with table-specific access level."""
        # Create connection
        connection = DatabaseConnection(
            name="analytics-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="analytics",
            username="analyst",
            password="secret123"
        )
        
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.create_connection(connection)
        
        assert is_ok(result)
        
        # Create agent
        agent_dir = temp_workspace["agents_dir"] / "report-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "report-agent",
            "display_name": "Report Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You generate reports.",
            "temperature": 0.5,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Assign with table-specific read access
        allowed_tables = ["sales", "customers", "products"]
        result = agent_manager.assign_connection(
            "report-agent",
            "analytics-db",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        assert is_ok(result)
        
        # Verify assignment includes allowed tables
        with open(agent_dir / "config.json", "r") as f:
            updated_config = json.load(f)
        
        assignment = updated_config["connection_assignments"][0]
        assert assignment["access_level"] == "table-specific-read"
        assert set(assignment["allowed_tables"]) == set(allowed_tables)
        
        # Resolve and verify
        agent = Agent.from_dict(updated_config)
        result = db_manager.resolve_connections(agent.connection_assignments)
        
        assert is_ok(result)
        resolved = unwrap(result)
        assert resolved[0][1] == AccessLevel.TABLE_SPECIFIC_READ
        assert set(resolved[0][2]) == set(allowed_tables)


class TestMultiAgentConnectionSharing:
    """Test connection sharing across multiple agents with different access levels.
    
    Workflow: Create connection → Assign to multiple agents with different 
              access levels → Update connection
    
    **Validates: Requirements 2, 4, 6, 12**
    """
    
    def test_shared_connection_different_access_levels(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test one connection shared by multiple agents with different access levels."""
        # Create a shared connection
        connection = DatabaseConnection(
            name="shared-db",
            database_type="mysql",
            host="db.example.com",
            port=3306,
            database="production",
            username="app_user",
            password="secure_pass"
        )
        
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.create_connection(connection)
        
        assert is_ok(result)
        
        # Create first agent with read-only access
        agent1_dir = temp_workspace["agents_dir"] / "viewer-agent"
        agent1_dir.mkdir()
        agent1_config = {
            "name": "viewer-agent",
            "display_name": "Viewer Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You view data.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent1_dir / "config.json", "w") as f:
            json.dump(agent1_config, f)
        
        result = agent_manager.assign_connection(
            "viewer-agent",
            "shared-db",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_ok(result)
        
        # Create second agent with read-write access
        agent2_dir = temp_workspace["agents_dir"] / "editor-agent"
        agent2_dir.mkdir()
        agent2_config = {
            "name": "editor-agent",
            "display_name": "Editor Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You edit data.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent2_dir / "config.json", "w") as f:
            json.dump(agent2_config, f)
        
        result = agent_manager.assign_connection(
            "editor-agent",
            "shared-db",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_ok(result)
        
        # Create third agent with table-specific access
        agent3_dir = temp_workspace["agents_dir"] / "limited-agent"
        agent3_dir.mkdir()
        agent3_config = {
            "name": "limited-agent",
            "display_name": "Limited Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You have limited access.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent3_dir / "config.json", "w") as f:
            json.dump(agent3_config, f)
        
        result = agent_manager.assign_connection(
            "limited-agent",
            "shared-db",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            ["orders", "inventory"]
        )
        assert is_ok(result)
        
        # Verify all agents are using the connection
        agents_using = db_manager.get_agents_using_connection("shared-db")
        assert len(agents_using) == 3
        assert set(agents_using) == {"viewer-agent", "editor-agent", "limited-agent"}
        
        # Update the connection (e.g., change host)
        updates = {"host": "new-db.example.com", "port": 3307}
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.update_connection("shared-db", updates)
        
        assert is_ok(result)
        updated_conn = unwrap(result)
        assert updated_conn.host == "new-db.example.com"
        assert updated_conn.port == 3307
        
        # Verify all agents can still resolve the updated connection
        for agent_name in ["viewer-agent", "editor-agent", "limited-agent"]:
            agent_dir = temp_workspace["agents_dir"] / agent_name
            with open(agent_dir / "config.json", "r") as f:
                config = json.load(f)
            
            agent = Agent.from_dict(config)
            result = db_manager.resolve_connections(agent.connection_assignments)
            
            assert is_ok(result)
            resolved = unwrap(result)
            assert resolved[0][0].host == "new-db.example.com"
            assert resolved[0][0].port == 3307


class TestMigrationWorkflow:
    """Test migration from inline configs to centralized connections.
    
    Workflow: Create agents with inline configs → Migrate → Verify
    
    **Validates: Requirements 9**
    """
    
    def test_migrate_inline_database_config(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test migration of agent with inline database_config."""
        # Create agent with old-style inline database config
        agent_dir = temp_workspace["agents_dir"] / "legacy-agent"
        agent_dir.mkdir()
        legacy_config = {
            "name": "legacy-agent",
            "display_name": "Legacy Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a legacy agent.",
            "temperature": 0.7,
            "database_config": {
                "type": "oracle",
                "host": "oracle.example.com",
                "port": 1521,
                "service_name": "ORCL",
                "username": "legacy_user",
                "password": "legacy_pass"
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(legacy_config, f)
        
        # Mock validation
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            # Run migration
            migrations = agent_manager.migrate_inline_configs()
        
        # Migration returns a dict, not a Result
        assert isinstance(migrations, dict)
        
        # Verify migration created a connection
        assert "legacy-agent" in migrations
        connection_name = migrations["legacy-agent"]
        assert connection_name == "legacy-agent-oracle"
        
        # Verify connection exists in store
        result = db_manager.get_connection(connection_name)
        assert is_ok(result)
        conn = unwrap(result)
        assert conn.database_type == "oracle"
        assert conn.host == "oracle.example.com"
        assert conn.service_name == "ORCL"
        
        # Verify agent config was updated
        with open(agent_dir / "config.json", "r") as f:
            updated_config = json.load(f)
        
        # database_config should be removed
        assert "database_config" not in updated_config
        
        # connection_assignments should be added with read-write access
        assert "connection_assignments" in updated_config
        assert len(updated_config["connection_assignments"]) == 1
        assignment = updated_config["connection_assignments"][0]
        assert assignment["connection_name"] == connection_name
        assert assignment["access_level"] == "read-write"


    def test_migrate_connection_references_to_assignments(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test migration of agent with old connection_references field."""
        # First create a connection in the store
        connection = DatabaseConnection(
            name="existing-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            db_manager.create_connection(connection)
        
        # Create agent with old-style connection_references
        agent_dir = temp_workspace["agents_dir"] / "old-style-agent"
        agent_dir.mkdir()
        old_config = {
            "name": "old-style-agent",
            "display_name": "Old Style Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are an old style agent.",
            "temperature": 0.7,
            "connection_references": ["existing-conn"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(old_config, f)
        
        # Run migration
        migrations = agent_manager.migrate_inline_configs()
        
        # Migration returns a dict
        assert isinstance(migrations, dict)
        
        # Verify agent config was updated
        with open(agent_dir / "config.json", "r") as f:
            updated_config = json.load(f)
        
        # connection_references should be removed
        assert "connection_references" not in updated_config
        
        # connection_assignments should be added
        assert "connection_assignments" in updated_config
        assert len(updated_config["connection_assignments"]) == 1
        assignment = updated_config["connection_assignments"][0]
        assert assignment["connection_name"] == "existing-conn"
        assert assignment["access_level"] == "read-write"


class TestCorruptedStoreErrorHandling:
    """Test error handling with corrupted connection store.
    
    Workflow: Corrupt store → Attempt operations → Verify error handling
    
    **Validates: Requirements 1.4, 10**
    """
    
    def test_corrupted_json_structure(self, db_manager, temp_workspace):
        """Test handling of corrupted JSON in connection store."""
        # Write invalid JSON to store
        with open(temp_workspace["store_path"], "w") as f:
            f.write("{ invalid json content }")
        
        # Attempt to list connections
        result = db_manager.list_connections()
        
        # Should return empty list with warning (graceful degradation)
        # The manager logs a warning but returns empty list
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_missing_connections_array(self, db_manager, temp_workspace):
        """Test handling of store missing 'connections' array."""
        # Write JSON without connections array
        with open(temp_workspace["store_path"], "w") as f:
            json.dump({"version": "1.0"}, f)
        
        # Attempt to list connections
        result = db_manager.list_connections()
        
        # Should handle gracefully - returns empty list with warning
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_malformed_connection_object(self, db_manager, temp_workspace):
        """Test handling of malformed connection object in store."""
        # Write store with malformed connection
        with open(temp_workspace["store_path"], "w") as f:
            json.dump({
                "version": "1.0",
                "connections": [
                    {
                        "name": "bad-conn",
                        # Missing required fields like database_type
                    }
                ]
            }, f)
        
        # Attempt to list connections
        result = db_manager.list_connections()
        
        # Should handle error gracefully - returns empty list with warning
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_recovery_after_corruption(self, db_manager, temp_workspace):
        """Test that system can recover after fixing corrupted store."""
        # Corrupt the store
        with open(temp_workspace["store_path"], "w") as f:
            f.write("{ bad json }")
        
        # Verify error handling (returns empty list with warning)
        result = db_manager.list_connections()
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Fix the store by recreating it
        with open(temp_workspace["store_path"], "w") as f:
            json.dump({
                "version": "1.0",
                "connections": []
            }, f)
        
        # Verify recovery
        result = db_manager.list_connections()
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Verify can create new connection
        connection = DatabaseConnection(
            name="recovery-test",
            database_type="sqlite",
            file_path="/tmp/test.db"
        )
        
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.create_connection(connection)
        
        assert is_ok(result)


class TestGuidelinesWithSystemPrompt:
    """Test guidelines management with system prompt generation.
    
    Workflow: Add/edit/delete guidelines → Verify system prompt generation
    
    **Validates: Requirements 13**
    """
    
    def test_guidelines_in_system_prompt(
        self,
        agent_manager,
        temp_workspace
    ):
        """Test that guidelines are properly included in system prompt."""
        # Create agent
        agent_dir = temp_workspace["agents_dir"] / "guided-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "guided-agent",
            "display_name": "Guided Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a helpful assistant.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Add guidelines
        guidelines = [
            "Always explain your reasoning",
            "Be concise and clear",
            "Ask for clarification when needed"
        ]
        
        for guideline in guidelines:
            result = agent_manager.add_guideline("guided-agent", guideline)
            assert is_ok(result)
        
        # Load agent and verify system prompt
        with open(agent_dir / "config.json", "r") as f:
            config = json.load(f)
        
        agent = Agent.from_dict(config)
        full_prompt = agent.get_full_system_prompt()
        
        # Verify base prompt is included
        assert "You are a helpful assistant." in full_prompt
        
        # Verify guidelines section is included
        assert "Guidelines:" in full_prompt
        
        # Verify all guidelines are included as bullet points
        for guideline in guidelines:
            assert guideline in full_prompt
            assert f"- {guideline}" in full_prompt
    
    def test_edit_guideline_updates_prompt(
        self,
        agent_manager,
        temp_workspace
    ):
        """Test that editing a guideline updates the system prompt."""
        # Create agent with guidelines
        agent_dir = temp_workspace["agents_dir"] / "edit-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "edit-agent",
            "display_name": "Edit Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are an assistant.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": ["Original guideline"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Edit the guideline
        result = agent_manager.edit_guideline("edit-agent", 0, "Updated guideline")
        assert is_ok(result)
        
        # Verify system prompt reflects the change
        with open(agent_dir / "config.json", "r") as f:
            config = json.load(f)
        
        agent = Agent.from_dict(config)
        full_prompt = agent.get_full_system_prompt()
        
        assert "Updated guideline" in full_prompt
        assert "Original guideline" not in full_prompt
    
    def test_delete_guideline_updates_prompt(
        self,
        agent_manager,
        temp_workspace
    ):
        """Test that deleting a guideline updates the system prompt."""
        # Create agent with multiple guidelines
        agent_dir = temp_workspace["agents_dir"] / "delete-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "delete-agent",
            "display_name": "Delete Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are an assistant.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [
                "First guideline",
                "Second guideline",
                "Third guideline"
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Delete the middle guideline
        result = agent_manager.delete_guideline("delete-agent", 1)
        assert is_ok(result)
        
        # Verify system prompt reflects the change
        with open(agent_dir / "config.json", "r") as f:
            config = json.load(f)
        
        agent = Agent.from_dict(config)
        full_prompt = agent.get_full_system_prompt()
        
        assert "First guideline" in full_prompt
        assert "Third guideline" in full_prompt
        assert "Second guideline" not in full_prompt
    
    def test_empty_guidelines_no_section(
        self,
        agent_manager,
        temp_workspace
    ):
        """Test that empty guidelines don't add a guidelines section."""
        # Create agent with no guidelines
        agent_dir = temp_workspace["agents_dir"] / "empty-agent"
        agent_dir.mkdir()
        agent_config = {
            "name": "empty-agent",
            "display_name": "Empty Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are an assistant.",
            "temperature": 0.7,
            "connection_assignments": [],
            "guidelines": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(agent_dir / "config.json", "w") as f:
            json.dump(agent_config, f)
        
        # Load agent and verify system prompt
        with open(agent_dir / "config.json", "r") as f:
            config = json.load(f)
        
        agent = Agent.from_dict(config)
        full_prompt = agent.get_full_system_prompt()
        
        # Should be exactly the base prompt
        assert full_prompt == "You are an assistant."
        assert "Guidelines:" not in full_prompt



class TestQueryValidationWithAccessLevels:
    """Test query validation with different access levels.
    
    Workflow: Query validation with different access levels
    
    **Validates: Requirements 12**
    """
    
    def test_read_only_access_validation(self):
        """Test query validation with read-only access."""
        validator = AccessLevelValidator()
        
        # SELECT queries should be allowed
        result = validator.validate_query(
            "SELECT * FROM users",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_ok(result)
        
        # INSERT queries should be rejected
        result = validator.validate_query(
            "INSERT INTO users (name) VALUES ('John')",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not allowed" in error_msg.lower()
        assert "read-only" in error_msg.lower()
        
        # UPDATE queries should be rejected
        result = validator.validate_query(
            "UPDATE users SET name = 'Jane' WHERE id = 1",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_err(result)
        
        # DELETE queries should be rejected
        result = validator.validate_query(
            "DELETE FROM users WHERE id = 1",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_err(result)
        
        # DDL queries should be rejected
        result = validator.validate_query(
            "CREATE TABLE test (id INT)",
            AccessLevel.READ_ONLY,
            []
        )
        assert is_err(result)
    
    def test_read_write_access_validation(self):
        """Test query validation with read-write access."""
        validator = AccessLevelValidator()
        
        # SELECT queries should be allowed
        result = validator.validate_query(
            "SELECT * FROM products",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_ok(result)
        
        # INSERT queries should be allowed
        result = validator.validate_query(
            "INSERT INTO products (name, price) VALUES ('Widget', 9.99)",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_ok(result)
        
        # UPDATE queries should be allowed
        result = validator.validate_query(
            "UPDATE products SET price = 10.99 WHERE id = 1",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_ok(result)
        
        # DELETE queries should be allowed
        result = validator.validate_query(
            "DELETE FROM products WHERE id = 1",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_ok(result)
        
        # DDL queries should be rejected
        result = validator.validate_query(
            "DROP TABLE products",
            AccessLevel.READ_WRITE,
            []
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not allowed" in error_msg.lower() or "ddl" in error_msg.lower()
    
    def test_table_specific_read_access_validation(self):
        """Test query validation with table-specific read access."""
        validator = AccessLevelValidator()
        allowed_tables = ["orders", "customers"]
        
        # SELECT on allowed table should succeed
        result = validator.validate_query(
            "SELECT * FROM orders",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_ok(result)
        
        result = validator.validate_query(
            "SELECT * FROM customers WHERE id = 1",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_ok(result)
        
        # SELECT on non-allowed table should fail
        result = validator.validate_query(
            "SELECT * FROM products",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not allowed" in error_msg.lower()
        assert "products" in error_msg
        
        # Write operations should fail even on allowed tables
        result = validator.validate_query(
            "INSERT INTO orders (total) VALUES (100)",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not allowed" in error_msg.lower()
    
    def test_table_specific_read_write_access_validation(self):
        """Test query validation with table-specific read-write access."""
        validator = AccessLevelValidator()
        allowed_tables = ["inventory", "shipments"]
        
        # SELECT on allowed table should succeed
        result = validator.validate_query(
            "SELECT * FROM inventory",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_ok(result)
        
        # INSERT on allowed table should succeed
        result = validator.validate_query(
            "INSERT INTO inventory (item, quantity) VALUES ('Widget', 100)",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_ok(result)
        
        # UPDATE on allowed table should succeed
        result = validator.validate_query(
            "UPDATE shipments SET status = 'delivered' WHERE id = 1",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_ok(result)
        
        # DELETE on allowed table should succeed
        result = validator.validate_query(
            "DELETE FROM inventory WHERE quantity = 0",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_ok(result)
        
        # Operations on non-allowed table should fail
        result = validator.validate_query(
            "SELECT * FROM products",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_err(result)
        
        result = validator.validate_query(
            "INSERT INTO products (name) VALUES ('Test')",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_err(result)
        
        # DDL should fail even on allowed tables
        result = validator.validate_query(
            "DROP TABLE inventory",
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        assert is_err(result)
    
    def test_complex_query_with_joins(self):
        """Test validation of complex queries with joins."""
        validator = AccessLevelValidator()
        allowed_tables = ["orders", "customers"]
        
        # Join with all allowed tables should succeed
        result = validator.validate_query(
            "SELECT o.*, c.name FROM orders o JOIN customers c ON o.customer_id = c.id",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_ok(result)
        
        # Join with non-allowed table should fail
        result = validator.validate_query(
            "SELECT o.*, p.name FROM orders o JOIN products p ON o.product_id = p.id",
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "products" in error_msg


class TestEndToEndIntegration:
    """Test complete end-to-end integration scenarios.
    
    **Validates: All Requirements**
    """
    
    def test_complete_workflow_multiple_agents_and_connections(
        self,
        db_manager,
        agent_manager,
        temp_workspace
    ):
        """Test a complete realistic workflow with multiple agents and connections."""
        # Step 1: Create multiple connections
        connections = [
            DatabaseConnection(
                name="prod-db",
                database_type="postgresql",
                host="prod.example.com",
                port=5432,
                database="production",
                username="prod_user",
                password="prod_pass"
            ),
            DatabaseConnection(
                name="dev-db",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="development",
                username="dev_user",
                password="dev_pass"
            ),
            DatabaseConnection(
                name="analytics-db",
                database_type="mysql",
                host="analytics.example.com",
                port=3306,
                database="analytics",
                username="analyst",
                password="analyst_pass"
            )
        ]
        
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            for conn in connections:
                result = db_manager.create_connection(conn)
                assert is_ok(result)
        
        # Step 2: Create multiple agents with different purposes
        agents_config = [
            {
                "name": "prod-viewer",
                "display_name": "Production Viewer",
                "system_prompt": "You view production data.",
                "connections": [("prod-db", AccessLevel.READ_ONLY, [])],
                "guidelines": ["Never modify production data", "Always verify queries"]
            },
            {
                "name": "dev-editor",
                "display_name": "Development Editor",
                "system_prompt": "You edit development data.",
                "connections": [("dev-db", AccessLevel.READ_WRITE, [])],
                "guidelines": ["Test queries before running", "Document changes"]
            },
            {
                "name": "analyst",
                "display_name": "Data Analyst",
                "system_prompt": "You analyze data.",
                "connections": [
                    ("prod-db", AccessLevel.TABLE_SPECIFIC_READ, ["sales", "customers"]),
                    ("analytics-db", AccessLevel.READ_WRITE, [])
                ],
                "guidelines": ["Explain your analysis", "Provide visualizations"]
            }
        ]
        
        for agent_cfg in agents_config:
            agent_dir = temp_workspace["agents_dir"] / agent_cfg["name"]
            agent_dir.mkdir()
            
            config = {
                "name": agent_cfg["name"],
                "display_name": agent_cfg["display_name"],
                "base_model": "llama3:latest",
                "system_prompt": agent_cfg["system_prompt"],
                "temperature": 0.7,
                "connection_assignments": [],
                "guidelines": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(agent_dir / "config.json", "w") as f:
                json.dump(config, f)
            
            # Assign connections
            for conn_name, access_level, allowed_tables in agent_cfg["connections"]:
                result = agent_manager.assign_connection(
                    agent_cfg["name"],
                    conn_name,
                    access_level,
                    allowed_tables
                )
                assert is_ok(result)
            
            # Add guidelines
            for guideline in agent_cfg["guidelines"]:
                result = agent_manager.add_guideline(agent_cfg["name"], guideline)
                assert is_ok(result)
        
        # Step 3: Verify all agents can resolve their connections
        for agent_cfg in agents_config:
            agent_dir = temp_workspace["agents_dir"] / agent_cfg["name"]
            with open(agent_dir / "config.json", "r") as f:
                config = json.load(f)
            
            agent = Agent.from_dict(config)
            result = db_manager.resolve_connections(agent.connection_assignments)
            
            assert is_ok(result)
            resolved = unwrap(result)
            assert len(resolved) == len(agent_cfg["connections"])
            
            # Verify system prompt includes guidelines
            full_prompt = agent.get_full_system_prompt()
            for guideline in agent_cfg["guidelines"]:
                assert guideline in full_prompt
        
        # Step 4: Update a shared connection
        updates = {"host": "new-prod.example.com"}
        with patch.object(db_manager, '_validate_connection', return_value=Ok(None)):
            result = db_manager.update_connection("prod-db", updates)
        
        assert is_ok(result)
        
        # Step 5: Verify agents using prod-db see the update
        for agent_name in ["prod-viewer", "analyst"]:
            agent_dir = temp_workspace["agents_dir"] / agent_name
            with open(agent_dir / "config.json", "r") as f:
                config = json.load(f)
            
            agent = Agent.from_dict(config)
            result = db_manager.resolve_connections(agent.connection_assignments)
            
            assert is_ok(result)
            resolved = unwrap(result)
            
            # Find prod-db in resolved connections
            prod_conn = next((r for r in resolved if r[0].name == "prod-db"), None)
            assert prod_conn is not None
            assert prod_conn[0].host == "new-prod.example.com"
        
        # Step 6: Try to delete a connection in use (should fail)
        result = db_manager.delete_connection("prod-db")
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "used by" in error_msg.lower() or "in use" in error_msg.lower()
        
        # Step 7: Remove connection from all agents
        for agent_name in ["prod-viewer", "analyst"]:
            result = agent_manager.remove_connection(agent_name, "prod-db")
            assert is_ok(result)
        
        # Step 8: Now deletion should succeed
        result = db_manager.delete_connection("prod-db")
        assert is_ok(result)
        
        # Step 9: Verify connection is gone
        result = db_manager.get_connection("prod-db")
        assert is_err(result)
