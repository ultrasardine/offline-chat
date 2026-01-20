"""Unit tests for AgentManager.update_agent() method.

This module tests the update_agent functionality in AgentManager:
- Updating system_prompt
- Updating temperature
- Updating language
- Updating web_search_enabled
- Updating connection_assignments
- Updating mcp_servers
- Updating guidelines
- Validation of update fields
- Error handling
"""

import json
import pytest
from pathlib import Path

from offline_chat.agent import Agent
from offline_chat.database import AccessLevel, AgentConnectionAssignment
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_ok, is_err, unwrap, unwrap_err
from offline_chat.manager import AgentManager
from offline_chat.mcp_config import MCPServerConfig


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
        name="test-sqlite-1",
        database_type="sqlite",
        file_path=str(temp_dirs["connections_file"].parent / "test1.db")
    )
    conn2 = DatabaseConnection(
        name="test-sqlite-2",
        database_type="sqlite",
        file_path=str(temp_dirs["connections_file"].parent / "test2.db")
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
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        guidelines=["Be helpful", "Be concise"],
    )
    
    # Save agent config manually (skip Ollama registration for tests)
    agent_dir = agent_manager._get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_manager._get_config_path(agent.name)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(agent.to_dict(), f, indent=2)
    
    return agent


class TestUpdateAgentBasicFields:
    """Tests for updating basic agent fields."""
    
    def test_update_system_prompt(self, agent_manager, test_agent):
        """Test updating the system prompt."""
        new_prompt = "You are an updated test agent with new instructions."
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"system_prompt": new_prompt}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.system_prompt == new_prompt
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.system_prompt == new_prompt
    
    def test_update_temperature(self, agent_manager, test_agent):
        """Test updating the temperature."""
        new_temp = 0.3
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": new_temp}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == new_temp
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.temperature == new_temp
    
    def test_update_language(self, agent_manager, test_agent):
        """Test updating the language."""
        new_language = "Spanish"
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"language": new_language}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.language == new_language
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.language == new_language
    
    def test_update_web_search_enabled(self, agent_manager, test_agent):
        """Test updating web search enabled flag."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"web_search_enabled": True}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.web_search_enabled is True
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.web_search_enabled is True
    
    def test_update_multiple_fields(self, agent_manager, test_agent):
        """Test updating multiple fields at once."""
        updates = {
            "system_prompt": "New prompt",
            "temperature": 0.5,
            "language": "German",
            "web_search_enabled": True,
        }
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates=updates
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.system_prompt == "New prompt"
        assert updated_agent.temperature == 0.5
        assert updated_agent.language == "German"
        assert updated_agent.web_search_enabled is True
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.system_prompt == "New prompt"
        assert reloaded_agent.temperature == 0.5
        assert reloaded_agent.language == "German"
        assert reloaded_agent.web_search_enabled is True


class TestUpdateAgentGuidelines:
    """Tests for updating agent guidelines."""
    
    def test_update_guidelines(self, agent_manager, test_agent):
        """Test updating guidelines list."""
        new_guidelines = ["Always verify facts", "Provide sources", "Be thorough"]
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": new_guidelines}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.guidelines == new_guidelines
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.guidelines == new_guidelines
    
    def test_update_guidelines_empty_list(self, agent_manager, test_agent):
        """Test updating guidelines to empty list."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": []}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.guidelines == []
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.guidelines == []
    
    def test_update_guidelines_single_item(self, agent_manager, test_agent):
        """Test updating guidelines with single item."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": ["Only guideline"]}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.guidelines == ["Only guideline"]


class TestUpdateAgentConnectionAssignments:
    """Tests for updating connection assignments."""
    
    def test_update_connection_assignments(self, agent_manager, test_agent):
        """Test updating connection assignments."""
        assignments = [
            AgentConnectionAssignment(
                connection_name="test-sqlite-1",
                access_level=AccessLevel.READ_ONLY,
                allowed_tables=None
            ),
            AgentConnectionAssignment(
                connection_name="test-sqlite-2",
                access_level=AccessLevel.READ_WRITE,
                allowed_tables=None
            ),
        ]
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"connection_assignments": assignments}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert len(updated_agent.connection_assignments) == 2
        assert updated_agent.connection_assignments[0].connection_name == "test-sqlite-1"
        assert updated_agent.connection_assignments[1].connection_name == "test-sqlite-2"
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert len(reloaded_agent.connection_assignments) == 2
    
    def test_update_connection_assignments_empty(self, agent_manager, test_agent):
        """Test updating connection assignments to empty list."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"connection_assignments": []}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.connection_assignments == []
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.connection_assignments == []


class TestUpdateAgentMCPServers:
    """Tests for updating MCP servers."""
    
    def test_update_mcp_servers(self, agent_manager, test_agent):
        """Test updating MCP servers list."""
        mcp_servers = [
            MCPServerConfig(
                name="test-server",
                command="test-command",
                args=["arg1", "arg2"],
                env={"KEY": "value"}
            )
        ]
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"mcp_servers": mcp_servers}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert len(updated_agent.mcp_servers) == 1
        assert updated_agent.mcp_servers[0].name == "test-server"
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert len(reloaded_agent.mcp_servers) == 1
        assert reloaded_agent.mcp_servers[0].name == "test-server"
    
    def test_update_mcp_servers_empty(self, agent_manager, test_agent):
        """Test updating MCP servers to empty list."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"mcp_servers": []}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.mcp_servers == []


class TestUpdateAgentValidation:
    """Tests for validation in update_agent."""
    
    def test_update_nonexistent_agent(self, agent_manager):
        """Test updating a nonexistent agent fails."""
        result = agent_manager.update_agent(
            agent_name="nonexistent-agent",
            updates={"temperature": 0.5}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "not found" in error.lower()
    
    def test_update_invalid_field(self, agent_manager, test_agent):
        """Test updating an invalid field fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"invalid_field": "value"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "invalid" in error.lower()
        assert "invalid_field" in error.lower()
    
    def test_update_temperature_out_of_range_high(self, agent_manager, test_agent):
        """Test updating temperature above 1.0 fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 1.5}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "temperature" in error.lower()
        assert "between" in error.lower()
    
    def test_update_temperature_out_of_range_low(self, agent_manager, test_agent):
        """Test updating temperature below 0.0 fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": -0.1}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "temperature" in error.lower()
        assert "between" in error.lower()
    
    def test_update_temperature_wrong_type(self, agent_manager, test_agent):
        """Test updating temperature with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": "not a number"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "temperature" in error.lower()
        assert "number" in error.lower()
    
    def test_update_system_prompt_wrong_type(self, agent_manager, test_agent):
        """Test updating system_prompt with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"system_prompt": 123}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "system_prompt" in error.lower()
        assert "string" in error.lower()
    
    def test_update_language_wrong_type(self, agent_manager, test_agent):
        """Test updating language with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"language": 123}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "language" in error.lower()
        assert "string" in error.lower()
    
    def test_update_web_search_enabled_wrong_type(self, agent_manager, test_agent):
        """Test updating web_search_enabled with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"web_search_enabled": "yes"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "web_search_enabled" in error.lower()
        assert "boolean" in error.lower()
    
    def test_update_guidelines_wrong_type(self, agent_manager, test_agent):
        """Test updating guidelines with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": "not a list"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "guidelines" in error.lower()
        assert "list" in error.lower()
    
    def test_update_guidelines_non_string_items(self, agent_manager, test_agent):
        """Test updating guidelines with non-string items fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": ["valid", 123, "also valid"]}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "guidelines" in error.lower()
        assert "string" in error.lower()
    
    def test_update_connection_assignments_wrong_type(self, agent_manager, test_agent):
        """Test updating connection_assignments with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"connection_assignments": "not a list"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "connection_assignments" in error.lower()
        assert "list" in error.lower()
    
    def test_update_connection_assignments_wrong_item_type(self, agent_manager, test_agent):
        """Test updating connection_assignments with wrong item type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"connection_assignments": ["not an assignment"]}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "connection_assignments" in error.lower()
        assert "AgentConnectionAssignment" in error
    
    def test_update_mcp_servers_wrong_type(self, agent_manager, test_agent):
        """Test updating mcp_servers with wrong type fails."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"mcp_servers": "not a list"}
        )
        
        assert is_err(result)
        error = unwrap_err(result)
        assert "mcp_servers" in error.lower()
        assert "list" in error.lower()


class TestUpdateAgentEdgeCases:
    """Tests for edge cases in update_agent."""
    
    def test_update_with_empty_dict(self, agent_manager, test_agent):
        """Test updating with empty dict succeeds (no-op)."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        # Agent should be unchanged
        assert updated_agent.system_prompt == test_agent.system_prompt
        assert updated_agent.temperature == test_agent.temperature
    
    def test_update_temperature_boundary_zero(self, agent_manager, test_agent):
        """Test updating temperature to 0.0 succeeds."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 0.0}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == 0.0
    
    def test_update_temperature_boundary_one(self, agent_manager, test_agent):
        """Test updating temperature to 1.0 succeeds."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 1.0}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == 1.0
    
    def test_update_temperature_as_int(self, agent_manager, test_agent):
        """Test updating temperature with int value succeeds."""
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 1}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == 1.0
        assert isinstance(updated_agent.temperature, float)
    
    def test_update_preserves_other_fields(self, agent_manager, test_agent):
        """Test that updating one field preserves others."""
        original_prompt = test_agent.system_prompt
        original_language = test_agent.language
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 0.5}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == 0.5
        assert updated_agent.system_prompt == original_prompt
        assert updated_agent.language == original_language
    
    def test_update_same_value(self, agent_manager, test_agent):
        """Test updating to the same value succeeds."""
        original_temp = test_agent.temperature
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": original_temp}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.temperature == original_temp
    
    def test_update_with_very_long_system_prompt(self, agent_manager, test_agent):
        """Test updating with very long system prompt succeeds."""
        long_prompt = "A" * 10000
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"system_prompt": long_prompt}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert updated_agent.system_prompt == long_prompt
        
        # Verify persistence
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.system_prompt == long_prompt
    
    def test_update_with_many_guidelines(self, agent_manager, test_agent):
        """Test updating with many guidelines succeeds."""
        many_guidelines = [f"Guideline {i}" for i in range(100)]
        
        result = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": many_guidelines}
        )
        
        assert is_ok(result)
        updated_agent = unwrap(result)
        assert len(updated_agent.guidelines) == 100
        assert updated_agent.guidelines == many_guidelines


class TestUpdateAgentPersistence:
    """Tests for persistence of updates."""
    
    def test_multiple_updates_persist(self, agent_manager, test_agent):
        """Test that multiple sequential updates persist correctly."""
        # First update
        result1 = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"temperature": 0.3}
        )
        assert is_ok(result1)
        
        # Second update
        result2 = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"language": "French"}
        )
        assert is_ok(result2)
        
        # Third update
        result3 = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": ["New guideline"]}
        )
        assert is_ok(result3)
        
        # Verify all updates persisted
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.temperature == 0.3
        assert reloaded_agent.language == "French"
        assert reloaded_agent.guidelines == ["New guideline"]
    
    def test_update_overwrites_previous(self, agent_manager, test_agent):
        """Test that updates overwrite previous values."""
        # First update
        result1 = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": ["First", "Second"]}
        )
        assert is_ok(result1)
        
        # Second update overwrites
        result2 = agent_manager.update_agent(
            agent_name="test-agent",
            updates={"guidelines": ["Third"]}
        )
        assert is_ok(result2)
        
        # Verify only latest update persisted
        reloaded_agent = agent_manager.get_agent("test-agent")
        assert reloaded_agent.guidelines == ["Third"]
