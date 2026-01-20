"""Unit tests for AgentManager.migrate_inline_configs() method.

This module contains unit tests for the migrate_inline_configs() method
that orchestrates migration of multiple agents with inline database configs.
"""

import json
import tempfile
import pytest
from pathlib import Path

from offline_chat.manager import AgentManager
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.access_level import AccessLevel


# ============================================================================
# Helper Functions
# ============================================================================

def setup_test_environment():
    """Set up test environment with temporary directories and managers."""
    tmp_dir = Path(tempfile.mkdtemp())
    
    agents_dir = tmp_dir / "agents"
    history_dir = tmp_dir / "history"
    connections_file = tmp_dir / "connections.json"
    
    agents_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    
    db_manager = DatabaseConnectionManager(store_path=connections_file)
    agent_manager = AgentManager(
        agents_dir=agents_dir,
        history_dir=history_dir,
        db_manager=db_manager
    )
    
    return {
        "tmp_dir": tmp_dir,
        "agents_dir": agents_dir,
        "history_dir": history_dir,
        "connections_file": connections_file,
        "db_manager": db_manager,
        "agent_manager": agent_manager,
    }


def create_agent_with_inline_config(agents_dir: Path, agent_name: str, database_config: dict):
    """Create an agent config file with inline database_config."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
        "database_config": database_config
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def create_agent_with_connection_references(agents_dir: Path, agent_name: str, connection_refs: list[str]):
    """Create an agent config file with legacy connection_references."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
        "connection_references": connection_refs
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def create_agent_without_inline_config(agents_dir: Path, agent_name: str):
    """Create an agent config file without inline database_config."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


# ============================================================================
# Tests for migrate_inline_configs()
# ============================================================================

def test_migrate_inline_configs_no_agents():
    """Test migrate_inline_configs with no agents needing migration."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create some agents without inline configs
    create_agent_without_inline_config(env["agents_dir"], "agent1")
    create_agent_without_inline_config(env["agents_dir"], "agent2")
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Should return empty dict
    assert results == {}, "Should return empty dict when no agents need migration"


def test_migrate_inline_configs_single_agent():
    """Test migrate_inline_configs with a single agent."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    db_manager = env["db_manager"]
    
    # Create agent with inline config
    db_config = {
        "type": "sqlite",
        "file_path": "/tmp/test.db"
    }
    create_agent_with_inline_config(env["agents_dir"], "test-agent", db_config)
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Should return mapping with one entry
    assert len(results) == 1, "Should migrate one agent"
    assert "test-agent" in results, "Should include test-agent in results"
    assert results["test-agent"] == "test-agent-sqlite", "Should create connection with correct name"
    
    # Verify connection was created
    conn_result = db_manager.get_connection("test-agent-sqlite")
    from offline_chat.database.result import is_ok
    assert is_ok(conn_result), "Connection should exist in store"


def test_migrate_inline_configs_multiple_agents():
    """Test migrate_inline_configs with multiple agents."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    db_manager = env["db_manager"]
    
    # Create multiple agents with inline configs
    agents = [
        ("agent1", {"type": "sqlite", "file_path": "/tmp/agent1.db"}),
        ("agent2", {"type": "sqlite", "file_path": "/tmp/agent2.db"}),
        ("agent3", {"type": "sqlite", "file_path": "/tmp/agent3.db"}),
    ]
    
    for agent_name, db_config in agents:
        create_agent_with_inline_config(env["agents_dir"], agent_name, db_config)
    
    # Also create an agent without inline config
    create_agent_without_inline_config(env["agents_dir"], "agent4")
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Should migrate only the three agents with inline configs
    assert len(results) == 3, "Should migrate three agents"
    assert "agent1" in results
    assert "agent2" in results
    assert "agent3" in results
    assert "agent4" not in results, "Should not migrate agent without inline config"
    
    # Verify all connections were created
    from offline_chat.database.result import is_ok
    for agent_name, _ in agents:
        conn_name = f"{agent_name}-sqlite"
        conn_result = db_manager.get_connection(conn_name)
        assert is_ok(conn_result), f"Connection {conn_name} should exist"


def test_migrate_inline_configs_with_legacy_references():
    """Test migrate_inline_configs with legacy connection_references."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    db_manager = env["db_manager"]
    
    # Create connections first
    conn1 = DatabaseConnection(
        name="existing-conn1",
        database_type="sqlite",
        file_path="/tmp/conn1.db"
    )
    conn2 = DatabaseConnection(
        name="existing-conn2",
        database_type="sqlite",
        file_path="/tmp/conn2.db"
    )
    db_manager.create_connection(conn1)
    db_manager.create_connection(conn2)
    
    # Create agent with legacy connection_references
    create_agent_with_connection_references(
        env["agents_dir"],
        "legacy-agent",
        ["existing-conn1", "existing-conn2"]
    )
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Should migrate the agent
    assert len(results) == 1, "Should migrate one agent"
    assert "legacy-agent" in results
    assert results["legacy-agent"] == "migrated-references"
    
    # Verify agent config was updated
    config_path = env["agents_dir"] / "legacy-agent" / "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)
    
    assert "connection_references" not in config, "Should remove connection_references"
    assert "connection_assignments" in config, "Should add connection_assignments"
    assert len(config["connection_assignments"]) == 2, "Should have two assignments"


def test_migrate_inline_configs_error_handling():
    """Test migrate_inline_configs handles errors gracefully."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create one valid agent
    db_config1 = {
        "type": "sqlite",
        "file_path": "/tmp/valid.db"
    }
    create_agent_with_inline_config(env["agents_dir"], "valid-agent", db_config1)
    
    # Create one agent with invalid config (missing required fields)
    db_config2 = {
        "type": "postgresql",
        # Missing host, port, database, username, password
    }
    create_agent_with_inline_config(env["agents_dir"], "invalid-agent", db_config2)
    
    # Run migration - should handle error gracefully
    results = agent_manager.migrate_inline_configs()
    
    # Should migrate the valid agent but not the invalid one
    assert "valid-agent" in results, "Should migrate valid agent"
    assert "invalid-agent" not in results, "Should not migrate invalid agent"
    
    # Verify valid agent was migrated
    from offline_chat.database.result import is_ok
    conn_result = env["db_manager"].get_connection("valid-agent-sqlite")
    assert is_ok(conn_result), "Valid agent connection should exist"


def test_migrate_inline_configs_no_db_manager():
    """Test migrate_inline_configs when db_manager is not available."""
    env = setup_test_environment()
    
    # Create agent manager without db_manager
    agent_manager = AgentManager(
        agents_dir=env["agents_dir"],
        history_dir=env["history_dir"],
        db_manager=None  # No db_manager
    )
    
    # Create agent with inline config
    db_config = {
        "type": "sqlite",
        "file_path": "/tmp/test.db"
    }
    create_agent_with_inline_config(env["agents_dir"], "test-agent", db_config)
    
    # Run migration - should return empty dict
    results = agent_manager.migrate_inline_configs()
    
    assert results == {}, "Should return empty dict when db_manager is not available"


def test_migrate_inline_configs_mixed_scenarios():
    """Test migrate_inline_configs with mixed scenarios."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    db_manager = env["db_manager"]
    
    # Create connection for legacy reference
    conn = DatabaseConnection(
        name="shared-conn",
        database_type="sqlite",
        file_path="/tmp/shared.db"
    )
    db_manager.create_connection(conn)
    
    # Create various agents
    # 1. Agent with inline config
    create_agent_with_inline_config(
        env["agents_dir"],
        "inline-agent",
        {"type": "sqlite", "file_path": "/tmp/inline.db"}
    )
    
    # 2. Agent with legacy references
    create_agent_with_connection_references(
        env["agents_dir"],
        "legacy-agent",
        ["shared-conn"]
    )
    
    # 3. Agent without inline config (already migrated or new)
    create_agent_without_inline_config(env["agents_dir"], "modern-agent")
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Should migrate both inline and legacy agents
    assert len(results) == 2, "Should migrate two agents"
    assert "inline-agent" in results
    assert "legacy-agent" in results
    assert "modern-agent" not in results
    
    # Verify inline agent connection
    from offline_chat.database.result import is_ok
    conn_result = db_manager.get_connection("inline-agent-sqlite")
    assert is_ok(conn_result), "Inline agent connection should exist"


def test_migrate_inline_configs_preserves_other_fields():
    """Test that migration preserves other agent config fields."""
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create agent with inline config and other fields
    agent_dir = env["agents_dir"] / "test-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_dir / "config.json"
    original_config = {
        "name": "test-agent",
        "display_name": "Test Agent",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.8,
        "language": "English",
        "web_search_enabled": True,
        "mcp_servers": ["server1", "server2"],
        "guidelines": ["Guideline 1", "Guideline 2"],
        "database_config": {
            "type": "sqlite",
            "file_path": "/tmp/test.db"
        }
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(original_config, f, indent=2)
    
    # Run migration
    results = agent_manager.migrate_inline_configs()
    
    # Verify migration succeeded
    assert "test-agent" in results
    
    # Load updated config
    with open(config_path, "r") as f:
        updated_config = json.load(f)
    
    # Verify other fields are preserved
    assert updated_config["display_name"] == "Test Agent"
    assert updated_config["base_model"] == "llama3:latest"
    assert updated_config["system_prompt"] == "You are a test agent."
    assert updated_config["temperature"] == 0.8
    assert updated_config["language"] == "English"
    assert updated_config["web_search_enabled"] is True
    assert updated_config["mcp_servers"] == ["server1", "server2"]
    assert updated_config["guidelines"] == ["Guideline 1", "Guideline 2"]
    
    # Verify database_config is removed and connection_assignments is added
    assert "database_config" not in updated_config
    assert "connection_assignments" in updated_config
