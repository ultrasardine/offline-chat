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
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.migration import detect_inline_configs, migrate_agent
from offline_chat.database.result import Result, Ok, Err, is_err, unwrap_err, unwrap
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
        db_manager: DatabaseConnectionManager instance for validating connections.
    """

    def __init__(
        self,
        agents_dir: Path | str | None = None,
        history_dir: Path | str | None = None,
        db_manager: Optional["DatabaseConnectionManager"] = None,
    ):
        """Initialize the AgentManager.

        Args:
            agents_dir: Path to the directory for storing agent configurations.
                       Defaults to ~/.offline-chat/agents or OFFLINE_CHAT_DATA_DIR/agents.
            history_dir: Path to the directory for storing conversation history.
                        Defaults to ~/.offline-chat/history or OFFLINE_CHAT_DATA_DIR/history.
            db_manager: DatabaseConnectionManager instance for validating connections.
                       If None, connection assignment methods will not be available.
        """
        self.agents_dir = Path(agents_dir) if agents_dir else get_default_agents_dir()
        history_path = Path(history_dir) if history_dir else get_default_history_dir()
        self.history_store = HistoryStore(history_path)
        self.db_manager = db_manager

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

    def assign_connection(
        self,
        agent_name: str,
        connection_name: str,
        access_level: AccessLevel,
        allowed_tables: list[str] | None = None,
    ) -> Result[None, str]:
        """Assign a database connection to an agent with access control.
        
        This method assigns a database connection to an agent with a specified
        access level. For table-specific access levels, allowed_tables must be
        provided.
        
        Steps:
        1. Validate connection name exists in the connection store
        2. Validate allowed_tables if table-specific access level
        3. Load agent config
        4. Create AgentConnectionAssignment
        5. Add to connection_assignments (or update if already exists)
        6. Save agent config
        
        Args:
            agent_name: Name of the agent to update
            connection_name: Name of the connection to assign
            access_level: Access level for this connection
            allowed_tables: List of allowed tables (required for table-specific access)
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = AgentManager(db_manager=db_conn_manager)
            >>> result = manager.assign_connection(
            ...     "data-analyst",
            ...     "prod-db",
            ...     AccessLevel.READ_ONLY
            ... )
            >>> if is_ok(result):
            ...     print("Connection assigned successfully")
        """
        # Check if db_manager is available
        if self.db_manager is None:
            return Err("DatabaseConnectionManager not available")
        
        # Validate connection exists
        conn_result = self.db_manager.get_connection(connection_name)
        if is_err(conn_result):
            return Err(f"Connection '{connection_name}' not found")
        
        # Validate allowed_tables for table-specific access levels
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE):
            if allowed_tables is None:
                return Err(
                    f"Access level '{access_level.value}' requires allowed_tables to be specified"
                )
            if not isinstance(allowed_tables, list) or len(allowed_tables) == 0:
                return Err(
                    f"Access level '{access_level.value}' requires allowed_tables to be a non-empty list"
                )
        
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Create new assignment
        new_assignment = AgentConnectionAssignment(
            connection_name=connection_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        
        # Check if connection is already assigned and update it, otherwise add new
        existing_index = None
        for i, assignment in enumerate(agent.connection_assignments):
            if assignment.connection_name == connection_name:
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing assignment
            agent.connection_assignments[existing_index] = new_assignment
        else:
            # Add new assignment
            agent.connection_assignments.append(new_assignment)
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(None)
    
    def remove_connection(
        self,
        agent_name: str,
        connection_name: str,
    ) -> Result[None, str]:
        """Remove a connection assignment from an agent.
        
        This method removes a database connection assignment from an agent's
        configuration. If the connection is not assigned to the agent, an
        error is returned.
        
        Args:
            agent_name: Name of the agent to update
            connection_name: Name of the connection to remove
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = AgentManager(db_manager=db_conn_manager)
            >>> result = manager.remove_connection("data-analyst", "prod-db")
            >>> if is_ok(result):
            ...     print("Connection removed successfully")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Find and remove the connection assignment
        original_count = len(agent.connection_assignments)
        agent.connection_assignments = [
            assignment for assignment in agent.connection_assignments
            if assignment.connection_name != connection_name
        ]
        
        # Check if connection was actually removed
        if len(agent.connection_assignments) == original_count:
            return Err(
                f"Connection '{connection_name}' is not assigned to agent '{agent_name}'"
            )
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(None)
    
    def update_agent(
        self,
        agent_name: str,
        updates: dict,
    ) -> Result[Agent, str]:
        """Update an existing agent configuration.
        
        This method updates an agent's configuration with the provided updates.
        Supports updating: base_model, system_prompt, temperature, language,
        web_search_enabled, connection_assignments, mcp_servers, and guidelines.
        
        The agent name cannot be changed. To rename an agent, create a new one
        and delete the old one.
        
        Args:
            agent_name: Name of the agent to update
            updates: Dictionary of fields to update. Valid keys:
                - base_model: str (Ollama model name, e.g., "llama3.2:latest")
                - system_prompt: str
                - temperature: float (0.0-1.0)
                - language: str
                - web_search_enabled: bool
                - connection_assignments: list[AgentConnectionAssignment]
                - mcp_servers: list[MCPServerConfig]
                - guidelines: list[str]
                
        Returns:
            Result with updated Agent on success or error message on failure
            
        Example:
            >>> manager = AgentManager()
            >>> result = manager.update_agent(
            ...     "data-analyst",
            ...     {"base_model": "llama3.2:latest", "temperature": 0.5}
            ... )
            >>> if is_ok(result):
            ...     agent = unwrap(result)
            ...     print(f"Updated agent: {agent.display_name}")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Validate and apply updates
        valid_fields = {
            "base_model",
            "system_prompt",
            "temperature",
            "language",
            "web_search_enabled",
            "connection_assignments",
            "mcp_servers",
            "guidelines",
        }
        
        # Check for invalid fields
        invalid_fields = set(updates.keys()) - valid_fields
        if invalid_fields:
            return Err(
                f"Invalid update fields: {', '.join(invalid_fields)}. "
                f"Valid fields: {', '.join(sorted(valid_fields))}"
            )
        
        # Apply updates
        if "base_model" in updates:
            if not isinstance(updates["base_model"], str):
                return Err("base_model must be a string")
            if not updates["base_model"].strip():
                return Err("base_model cannot be empty")
            agent.base_model = updates["base_model"].strip()
            
            # Regenerate Modelfile with new base model
            try:
                modelfile_path = self._get_modelfile_path(agent_name)
                with open(modelfile_path, "w", encoding="utf-8") as f:
                    f.write(agent.to_modelfile())
                
                # Recreate the Ollama model with new base
                result = subprocess.run(
                    ["ollama", "create", agent_name, "-f", str(modelfile_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                
                if result.returncode != 0:
                    return Err(
                        f"Failed to recreate Ollama model: {result.stderr or result.stdout}"
                    )
            except (OSError, PermissionError) as e:
                return Err(f"Failed to update Modelfile: {e}")
        
        if "system_prompt" in updates:
            if not isinstance(updates["system_prompt"], str):
                return Err("system_prompt must be a string")
            agent.system_prompt = updates["system_prompt"]
        
        if "temperature" in updates:
            temp = updates["temperature"]
            if not isinstance(temp, (int, float)):
                return Err("temperature must be a number")
            if not 0.0 <= temp <= 1.0:
                return Err("temperature must be between 0.0 and 1.0")
            agent.temperature = float(temp)
        
        if "language" in updates:
            if not isinstance(updates["language"], str):
                return Err("language must be a string")
            agent.language = updates["language"]
        
        if "web_search_enabled" in updates:
            if not isinstance(updates["web_search_enabled"], bool):
                return Err("web_search_enabled must be a boolean")
            agent.web_search_enabled = updates["web_search_enabled"]
        
        if "connection_assignments" in updates:
            if not isinstance(updates["connection_assignments"], list):
                return Err("connection_assignments must be a list")
            # Validate all items are AgentConnectionAssignment instances
            for item in updates["connection_assignments"]:
                if not isinstance(item, AgentConnectionAssignment):
                    return Err(
                        "connection_assignments must be a list of AgentConnectionAssignment instances"
                    )
            agent.connection_assignments = updates["connection_assignments"]
        
        if "mcp_servers" in updates:
            if not isinstance(updates["mcp_servers"], list):
                return Err("mcp_servers must be a list")
            agent.mcp_servers = updates["mcp_servers"]
        
        if "guidelines" in updates:
            if not isinstance(updates["guidelines"], list):
                return Err("guidelines must be a list")
            # Validate all items are strings
            for item in updates["guidelines"]:
                if not isinstance(item, str):
                    return Err("guidelines must be a list of strings")
            agent.guidelines = updates["guidelines"]
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(agent)
    
    def add_guideline(
        self,
        agent_name: str,
        guideline: str,
    ) -> Result[None, str]:
        """Add a guideline to an agent.
        
        This method appends a new guideline to the agent's guidelines list.
        The guideline text must be non-empty.
        
        Args:
            agent_name: Name of the agent to update
            guideline: Guideline text to add (must be non-empty)
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = AgentManager()
            >>> result = manager.add_guideline(
            ...     "data-analyst",
            ...     "Always explain your SQL queries before executing them"
            ... )
            >>> if is_ok(result):
            ...     print("Guideline added successfully")
        """
        # Validate guideline text
        if not isinstance(guideline, str):
            return Err("Guideline must be a string")
        if not guideline.strip():
            return Err("Guideline text cannot be empty")
        
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Add guideline
        agent.guidelines.append(guideline)
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(None)
    
    def edit_guideline(
        self,
        agent_name: str,
        index: int,
        new_text: str,
    ) -> Result[None, str]:
        """Edit an existing guideline.
        
        This method replaces the guideline at the specified index with new text.
        The index must be valid (0-based) and the new text must be non-empty.
        
        Args:
            agent_name: Name of the agent to update
            index: Index of the guideline to edit (0-based)
            new_text: New guideline text (must be non-empty)
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = AgentManager()
            >>> result = manager.edit_guideline(
            ...     "data-analyst",
            ...     0,
            ...     "Always provide detailed explanations for SQL queries"
            ... )
            >>> if is_ok(result):
            ...     print("Guideline updated successfully")
        """
        # Validate new text
        if not isinstance(new_text, str):
            return Err("Guideline text must be a string")
        if not new_text.strip():
            return Err("Guideline text cannot be empty")
        
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Validate index
        if not isinstance(index, int):
            return Err("Index must be an integer")
        if index < 0 or index >= len(agent.guidelines):
            return Err(
                f"Guideline index {index} out of range. "
                f"Agent has {len(agent.guidelines)} guideline(s)."
            )
        
        # Update guideline
        agent.guidelines[index] = new_text
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(None)
    
    def delete_guideline(
        self,
        agent_name: str,
        index: int,
    ) -> Result[None, str]:
        """Delete a guideline from an agent.
        
        This method removes the guideline at the specified index from the
        agent's guidelines list. The index must be valid (0-based).
        
        Args:
            agent_name: Name of the agent to update
            index: Index of the guideline to delete (0-based)
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = AgentManager()
            >>> result = manager.delete_guideline("data-analyst", 0)
            >>> if is_ok(result):
            ...     print("Guideline deleted successfully")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        # Validate index
        if not isinstance(index, int):
            return Err("Index must be an integer")
        if index < 0 or index >= len(agent.guidelines):
            return Err(
                f"Guideline index {index} out of range. "
                f"Agent has {len(agent.guidelines)} guideline(s)."
            )
        
        # Delete guideline
        agent.guidelines.pop(index)
        
        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")
        
        return Ok(None)
    
    def list_guidelines(
        self,
        agent_name: str,
    ) -> Result[list[str], str]:
        """List all guidelines for an agent.
        
        This method returns all guidelines for the specified agent in order.
        If the agent has no guidelines, an empty list is returned.
        
        Args:
            agent_name: Name of the agent to query
            
        Returns:
            Result with list of guidelines on success or error message on failure
            
        Example:
            >>> manager = AgentManager()
            >>> result = manager.list_guidelines("data-analyst")
            >>> if is_ok(result):
            ...     guidelines = unwrap(result)
            ...     for i, guideline in enumerate(guidelines):
            ...         print(f"{i}. {guideline}")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")
        
        return Ok(agent.guidelines)
    
    def migrate_inline_configs(self) -> dict[str, str]:
        """Migrate agents with inline database configs to centralized system.
        
        This method scans all agent configurations and migrates those with:
        1. Inline database_config fields (old format)
        2. Legacy connection_references fields (without access control)
        
        For each agent with inline configuration:
        - Creates a connection in the centralized store (name: {agent}-{db_type})
        - Updates agent config with connection_assignment (read-write access)
        - Removes deprecated database_config and connection_references fields
        
        The migration is designed to be safe and handle errors gracefully:
        - Errors are logged but don't stop migration of other agents
        - Original configurations are preserved if migration fails
        - Returns mapping of successfully migrated agents
        
        Returns:
            Dictionary mapping agent names to created connection names.
            For agents with only connection_references (no database_config),
            the value will be "migrated-references".
            
        Example:
            >>> manager = AgentManager(db_manager=db_conn_manager)
            >>> results = manager.migrate_inline_configs()
            >>> for agent_name, connection_name in results.items():
            ...     print(f"Migrated {agent_name} -> {connection_name}")
        """
        # Check if db_manager is available
        if self.db_manager is None:
            print("Warning: DatabaseConnectionManager not available, skipping migration")
            return {}
        
        # Step 1: Detect agents with inline configs
        agents_to_migrate = detect_inline_configs(self.agents_dir)
        
        if not agents_to_migrate:
            # No agents need migration
            return {}
        
        # Step 2: Migrate each agent
        migration_results = {}
        
        for agent_name, config_data in agents_to_migrate:
            # Get the config file path
            config_path = self._get_config_path(agent_name)
            
            # Step 3: Call migrate_agent for this agent
            try:
                result = migrate_agent(
                    agent_name,
                    config_data,
                    config_path,
                    self.db_manager
                )
                
                # Step 4: Handle result
                if is_err(result):
                    # Log error but continue with other agents
                    error_msg = unwrap_err(result)
                    print(f"Warning: Failed to migrate agent '{agent_name}': {error_msg}")
                else:
                    # Success - add to results
                    connection_name = unwrap(result)
                    migration_results[agent_name] = connection_name
                    print(f"Successfully migrated agent '{agent_name}' -> connection '{connection_name}'")
                    
            except Exception as e:
                # Catch any unexpected errors and continue
                print(f"Warning: Unexpected error migrating agent '{agent_name}': {e}")
                continue
        
        # Step 5: Return mapping of successfully migrated agents
        return migration_results
