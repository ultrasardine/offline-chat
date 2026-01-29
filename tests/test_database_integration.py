"""Integration tests for database configuration in agent creation.

This module tests the integration of database configuration into the
agent creation workflow.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from offline_chat.agent import Agent
from offline_chat.cli import CLI
from offline_chat.database_config import create_database_mcp_config
from offline_chat.manager import AgentManager


def test_agent_creation_with_database_config():
    """Test that agents can be created with database configurations."""
    # Create a temporary directory for agent storage
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        agents_dir = data_dir / "agents"
        history_dir = data_dir / "history"

        agents_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        manager = AgentManager(agents_dir=str(agents_dir), history_dir=str(history_dir))

        # Create a SQLite database config
        db_config = create_database_mcp_config("sqlite", "test_db", path="/tmp/test.db")

        # Create an agent with database config
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent",
            temperature=0.7,
            mcp_servers=[db_config],
        )

        # Mock ollama.create to avoid actual model creation
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Verify agent was created
        loaded_agent = manager.get_agent("test-agent")
        assert loaded_agent is not None
        assert len(loaded_agent.mcp_servers) == 1
        assert loaded_agent.mcp_servers[0].database_type == "sqlite"
        assert loaded_agent.mcp_servers[0].database_path == "/tmp/test.db"


def test_agent_with_multiple_databases():
    """Test that agents can have multiple database configurations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        agents_dir = data_dir / "agents"
        history_dir = data_dir / "history"

        agents_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        manager = AgentManager(agents_dir=str(agents_dir), history_dir=str(history_dir))

        # Create multiple database configs
        sqlite_config = create_database_mcp_config("sqlite", "local_db", path="/tmp/local.db")

        postgres_config = create_database_mcp_config(
            "postgresql",
            "remote_db",
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass",
        )

        # Create an agent with multiple database configs
        agent = Agent(
            name="multi-db-agent",
            display_name="Multi DB Agent",
            base_model="llama3:latest",
            system_prompt="Agent with multiple databases",
            temperature=0.7,
            mcp_servers=[sqlite_config, postgres_config],
        )

        # Mock ollama.create
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Verify agent was created with both databases
        loaded_agent = manager.get_agent("multi-db-agent")
        assert loaded_agent is not None
        assert len(loaded_agent.mcp_servers) == 2

        # Check both database types are present
        db_types = {s.database_type for s in loaded_agent.mcp_servers}
        assert db_types == {"sqlite", "postgresql"}


def test_agent_with_mixed_mcp_and_database_servers():
    """Test that agents can have both regular MCP servers and database servers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        agents_dir = data_dir / "agents"
        history_dir = data_dir / "history"

        agents_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        manager = AgentManager(agents_dir=str(agents_dir), history_dir=str(history_dir))

        # Create a database config
        db_config = create_database_mcp_config("sqlite", "data_db", path="/tmp/data.db")

        # Create a regular MCP server config (from mcp_config)
        from offline_chat.mcp_config import MCPServerConfig

        regular_mcp = MCPServerConfig(name="fetch", command="uvx", args=["mcp-server-fetch"])

        # Create an agent with both types
        agent = Agent(
            name="mixed-agent",
            display_name="Mixed Agent",
            base_model="llama3:latest",
            system_prompt="Agent with mixed MCP servers",
            temperature=0.7,
            mcp_servers=[regular_mcp, db_config],
        )

        # Mock ollama.create
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)

        # Verify agent was created with both server types
        loaded_agent = manager.get_agent("mixed-agent")
        assert loaded_agent is not None
        assert len(loaded_agent.mcp_servers) == 2

        # Check that one is a database and one is not
        db_servers = [s for s in loaded_agent.mcp_servers if hasattr(s, "database_type") and s.database_type]
        regular_servers = [s for s in loaded_agent.mcp_servers if not (hasattr(s, "database_type") and s.database_type)]

        assert len(db_servers) == 1
        assert len(regular_servers) == 1
        assert db_servers[0].name == "data_db"
        assert regular_servers[0].name == "fetch"


def test_list_agents_displays_database_status():
    """Test that list_agents_flow displays database status correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        agents_dir = data_dir / "agents"
        history_dir = data_dir / "history"

        agents_dir.mkdir(parents=True)
        history_dir.mkdir(parents=True)

        manager = AgentManager(agents_dir=str(agents_dir), history_dir=str(history_dir))

        # Create agent with database
        db_config = create_database_mcp_config("sqlite", "test_db", path="/tmp/test.db")

        agent_with_db = Agent(
            name="db-agent",
            display_name="DB Agent",
            base_model="llama3:latest",
            system_prompt="Agent with database",
            temperature=0.7,
            mcp_servers=[db_config],
        )

        # Create agent without database
        agent_no_db = Agent(
            name="no-db-agent",
            display_name="No DB Agent",
            base_model="llama3:latest",
            system_prompt="Agent without database",
            temperature=0.7,
            mcp_servers=[],
        )

        # Mock ollama.create and create both agents
        with patch("offline_chat.manager.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent_with_db)
            manager.create_agent(agent_no_db)

        # Create CLI and capture output
        cli = CLI(manager=manager)

        # Mock print to capture output
        output_lines = []
        with patch("builtins.print") as mock_print:
            mock_print.side_effect = lambda *args, **kwargs: output_lines.append(" ".join(str(arg) for arg in args))
            cli.list_agents_flow()

        # Verify output contains database status
        output = "\n".join(output_lines)

        # Agent with database should show database info
        assert "sqlite:test_db" in output or "Databases:" in output

        # Agent without database should not show database indicator
        # (cleaner to show nothing than "No database access")
