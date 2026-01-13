"""Tests for AgentManager.

This module contains property-based tests and unit tests for the AgentManager class.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import Agent, AgentExistsError, AgentManager, AgentNotFoundError


# Strategy for generating valid kebab-case names
def valid_kebab_case_strategy():
    """Generate valid kebab-case strings."""
    segment = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=1,
        max_size=10,
    )
    return st.lists(segment, min_size=1, max_size=3).map(lambda parts: "-".join(parts))


# Strategy for generating valid Agent objects
def valid_agent_strategy():
    """Generate valid Agent objects for property testing."""
    return st.builds(
        Agent,
        name=valid_kebab_case_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama", "llama2"]),
        system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestAgentUniquenessConstraint:
    """Property 2: Agent Uniqueness Constraint.

    Feature: offline-chat, Property 2: Agent Uniqueness Constraint
    Validates: Requirements 1.3

    For any agent that has been successfully created, attempting to create
    another agent with the same name SHALL fail and the original agent
    SHALL remain unchanged.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_duplicate_agent_creation_fails(self, agent: Agent):
        """Creating an agent with the same name twice should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Mock ollama create to succeed
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                # First creation should succeed
                result = manager.create_agent(agent)
                assert result is True

                # Get the original agent data
                original = manager.get_agent(agent.name)
                assert original is not None

                # Second creation with same name should fail
                duplicate = Agent(
                    name=agent.name,  # Same name
                    display_name="Different Display Name",
                    base_model="mistral",
                    system_prompt="Different prompt",
                    temperature=0.5,
                )

                try:
                    manager.create_agent(duplicate)
                    assert False, "Expected AgentExistsError"
                except AgentExistsError as e:
                    assert e.name == agent.name

                # Original agent should remain unchanged
                after = manager.get_agent(agent.name)
                assert after is not None
                assert after.name == original.name
                assert after.display_name == original.display_name
                assert after.base_model == original.base_model
                assert after.system_prompt == original.system_prompt


class TestAgentDeletionCompleteness:
    """Property 7: Agent Deletion Completeness.

    Feature: offline-chat, Property 7: Agent Deletion Completeness
    Validates: Requirements 4.3, 4.4

    For any agent that is successfully deleted, the agent directory
    (data/agents/{name}/) SHALL not exist AND the history file
    (data/history/{name}.json) SHALL not exist AND listing agents
    SHALL not include that agent.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_deletion_removes_all_artifacts(self, agent: Agent):
        """Deleting an agent should remove all associated files and data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Mock ollama commands
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                # Create the agent
                manager.create_agent(agent)

                # Create a history file to simulate conversation
                history_file = history_dir / f"{agent.name}.json"
                history_file.parent.mkdir(parents=True, exist_ok=True)
                history_data = (
                    '{"agent_name": "'
                    + agent.name
                    + '", "messages": [], "last_updated": "2025-01-13T10:00:00"}'
                )
                history_file.write_text(history_data)

                # Verify agent exists before deletion
                assert manager.agent_exists(agent.name)
                agent_dir = agents_dir / agent.name
                assert agent_dir.exists()
                assert history_file.exists()

                # Delete the agent
                result = manager.delete_agent(agent.name)
                assert result is True

                # Verify agent directory is gone
                assert not agent_dir.exists()

                # Verify history file is gone
                assert not history_file.exists()

                # Verify agent is not in list
                agents = manager.list_agents()
                agent_names = [a.name for a in agents]
                assert agent.name not in agent_names

                # Verify agent_exists returns False
                assert not manager.agent_exists(agent.name)

    def test_delete_nonexistent_agent_raises_error(self):
        """Deleting a non-existent agent should raise AgentNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            try:
                manager.delete_agent("nonexistent-agent")
                assert False, "Expected AgentNotFoundError"
            except AgentNotFoundError as e:
                assert e.name == "nonexistent-agent"


class TestAgentManagerBasicOperations:
    """Unit tests for basic AgentManager operations."""

    def test_agent_exists_returns_false_for_nonexistent(self):
        """agent_exists should return False for non-existent agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )
            assert manager.agent_exists("nonexistent") is False

    def test_get_agent_returns_none_for_nonexistent(self):
        """get_agent should return None for non-existent agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )
            assert manager.get_agent("nonexistent") is None

    def test_list_agents_returns_empty_list_when_no_agents(self):
        """list_agents should return empty list when no agents exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )
            agents = manager.list_agents()
            assert agents == []

    def test_create_agent_saves_config_and_modelfile(self):
        """create_agent should save config.json and Modelfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                manager.create_agent(agent)

                # Verify files exist
                config_path = agents_dir / "test-agent" / "config.json"
                modelfile_path = agents_dir / "test-agent" / "Modelfile"

                assert config_path.exists()
                assert modelfile_path.exists()

                # Verify config content
                import json

                with open(config_path) as f:
                    config = json.load(f)
                assert config["name"] == "test-agent"
                assert config["display_name"] == "Test Agent"

                # Verify Modelfile content
                modelfile_content = modelfile_path.read_text()
                assert "FROM llama3:latest" in modelfile_content
                assert "SYSTEM" in modelfile_content
                assert "PARAMETER temperature 0.7" in modelfile_content

    def test_list_agents_returns_all_created_agents(self):
        """list_agents should return all created agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agents_to_create = [
                Agent(
                    name="agent-1",
                    display_name="Agent One",
                    base_model="llama3:latest",
                    system_prompt="First agent",
                ),
                Agent(
                    name="agent-2",
                    display_name="Agent Two",
                    base_model="mistral",
                    system_prompt="Second agent",
                ),
            ]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                for agent in agents_to_create:
                    manager.create_agent(agent)

            listed = manager.list_agents()
            listed_names = {a.name for a in listed}

            assert len(listed) == 2
            assert "agent-1" in listed_names
            assert "agent-2" in listed_names
