"""Agent manager for Offline Chat application.

This module provides the AgentManager class for creating, listing,
retrieving, and deleting AI agents.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from offline_chat.agent import Agent
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    OllamaCommandError,
)
from offline_chat.history import HistoryStore

# Environment variable name for custom data directory
OFFLINE_CHAT_DATA_DIR_ENV = "OFFLINE_CHAT_DATA_DIR"
DEFAULT_DATA_SUBDIR = ".offline-chat"


def get_default_data_dir() -> Path:
    """Get the default data directory path.

    Returns the path from OFFLINE_CHAT_DATA_DIR environment variable if set,
    otherwise defaults to ~/.offline-chat.

    Returns:
        Path to the data directory.
    """
    env_path = os.environ.get(OFFLINE_CHAT_DATA_DIR_ENV)
    if env_path:
        return Path(env_path)
    return Path.home() / DEFAULT_DATA_SUBDIR


def get_default_agents_dir() -> Path:
    """Get the default agents directory path."""
    return get_default_data_dir() / "agents"


def get_default_history_dir() -> Path:
    """Get the default history directory path."""
    return get_default_data_dir() / "history"


class AgentManager:
    """Manages agent CRUD operations.

    This class handles creating, listing, retrieving, and deleting agents.
    It manages both the local file storage and Ollama model registration.

    Attributes:
        agents_dir: Path to the directory where agent configs are stored.
        history_store: HistoryStore instance for managing conversation history.
    """

    def __init__(
        self,
        agents_dir: Path | str | None = None,
        history_dir: Path | str | None = None,
    ):
        """Initialize the AgentManager.

        Args:
            agents_dir: Path to the directory for storing agent configurations.
                       Defaults to ~/.offline-chat/agents or OFFLINE_CHAT_DATA_DIR/agents.
            history_dir: Path to the directory for storing conversation history.
                        Defaults to ~/.offline-chat/history or OFFLINE_CHAT_DATA_DIR/history.
        """
        self.agents_dir = Path(agents_dir) if agents_dir else get_default_agents_dir()
        history_path = Path(history_dir) if history_dir else get_default_history_dir()
        self.history_store = HistoryStore(history_path)

        # Ensure directories exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.history_store.history_dir.mkdir(parents=True, exist_ok=True)

    def _get_agent_dir(self, name: str) -> Path:
        """Get the directory path for an agent.

        Args:
            name: The agent name.

        Returns:
            Path to the agent's directory.
        """
        return self.agents_dir / name

    def _get_config_path(self, name: str) -> Path:
        """Get the config file path for an agent.

        Args:
            name: The agent name.

        Returns:
            Path to the agent's config.json file.
        """
        return self._get_agent_dir(name) / "config.json"

    def _get_modelfile_path(self, name: str) -> Path:
        """Get the Modelfile path for an agent.

        Args:
            name: The agent name.

        Returns:
            Path to the agent's Modelfile.
        """
        return self._get_agent_dir(name) / "Modelfile"

    def agent_exists(self, name: str) -> bool:
        """Check if an agent exists.

        Args:
            name: The agent name to check.

        Returns:
            True if the agent exists, False otherwise.
        """
        config_path = self._get_config_path(name)
        return config_path.exists()

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a specific agent by name.

        Args:
            name: The agent name.

        Returns:
            Agent instance if found, None otherwise.
        """
        config_path = self._get_config_path(name)

        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Agent.from_dict(data)

    def create_agent(self, agent: Agent) -> bool:
        """Create a new agent with Ollama model registration.

        This method validates the agent name, saves the configuration and
        Modelfile, and registers the model with Ollama.

        Args:
            agent: The Agent instance to create.

        Returns:
            True if the agent was created successfully.

        Raises:
            InvalidAgentNameError: If the agent name is invalid.
            AgentExistsError: If an agent with the same name already exists.
            OllamaCommandError: If the Ollama create command fails.
        """
        # Validate agent name format
        if not agent.validate_name():
            raise InvalidAgentNameError(agent.name)

        # Check for existing agent
        if self.agent_exists(agent.name):
            raise AgentExistsError(agent.name)

        agent_dir = self._get_agent_dir(agent.name)
        config_path = self._get_config_path(agent.name)
        modelfile_path = self._get_modelfile_path(agent.name)

        try:
            # Create agent directory
            agent_dir.mkdir(parents=True, exist_ok=True)

            # Save config.json
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)

            # Save Modelfile
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(agent.to_modelfile())

            # Execute ollama create command
            result = subprocess.run(
                ["ollama", "create", agent.name, "-f", str(modelfile_path)],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise OllamaCommandError(f"ollama create {agent.name}", error_msg)

            return True

        except OllamaCommandError:
            # Clean up on Ollama failure
            self._cleanup_agent_files(agent.name)
            raise
        except Exception as e:
            # Clean up on any other failure
            self._cleanup_agent_files(agent.name)
            raise OllamaCommandError(f"ollama create {agent.name}", str(e))

    def _cleanup_agent_files(self, name: str) -> None:
        """Clean up agent files after a failed creation.

        Args:
            name: The agent name.
        """
        agent_dir = self._get_agent_dir(name)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

    def list_agents(self) -> list[Agent]:
        """List all available agents.

        Returns:
            List of Agent instances, empty list if no agents exist.
        """
        agents = []

        if not self.agents_dir.exists():
            return agents

        for agent_dir in self.agents_dir.iterdir():
            if agent_dir.is_dir():
                config_path = agent_dir / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        agents.append(Agent.from_dict(data))
                    except (json.JSONDecodeError, KeyError):
                        # Skip invalid config files
                        continue

        return agents

    def delete_agent(self, name: str) -> bool:
        """Delete an agent and its associated data.

        This method removes the Ollama model, deletes the agent directory,
        and removes the conversation history.

        Args:
            name: The agent name to delete.

        Returns:
            True if the agent was deleted successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
            OllamaCommandError: If the Ollama rm command fails.
        """
        # Check if agent exists
        if not self.agent_exists(name):
            raise AgentNotFoundError(name)

        # Execute ollama rm command
        result = subprocess.run(
            ["ollama", "rm", name],
            capture_output=True,
            text=True,
        )

        # Note: We continue with deletion even if ollama rm fails
        # because the model might not exist in Ollama but files do
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            # Only raise if it's not a "model not found" error
            if "not found" not in error_msg.lower():
                raise OllamaCommandError(f"ollama rm {name}", error_msg)

        # Delete agent directory
        agent_dir = self._get_agent_dir(name)
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

        # Delete history file
        self.history_store.delete(name)

        return True
