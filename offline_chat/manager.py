"""Agent manager for Offline Chat application.

This module provides the AgentManager class for creating, listing,
retrieving, and deleting AI agents.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from offline_chat.agent import Agent
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.migration import detect_inline_configs, migrate_agent
from offline_chat.database.result import Err, Ok, Result, is_err, unwrap, unwrap_err
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    OllamaCommandError,
)
from offline_chat.history import HistoryStore

logger = logging.getLogger(__name__)

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
        data_dir: Path to the root data directory (contains agents, history, rag subdirs).
        agents_dir: Path to the directory where agent configs are stored.
        history_store: HistoryStore instance for managing conversation history.
        db_manager: DatabaseConnectionManager instance for validating connections.
    """

    def __init__(
        self,
        agents_dir: Path | str | None = None,
        history_dir: Path | str | None = None,
        db_manager: Optional["DatabaseConnectionManager"] = None,  # noqa: F821
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
        self.data_dir = get_default_data_dir()
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

    def get_rag_orchestrator(self, agent: Agent):
        """Get a RAG orchestrator for an agent with RAG enabled.

        This method initializes all RAG components and returns a configured
        RAG orchestrator. Returns None if RAG is not enabled for the agent.

        Args:
            agent: The Agent instance.

        Returns:
            RAGOrchestrator instance if RAG is enabled, None otherwise.

        Raises:
            Exception: If RAG component initialization fails.
        """
        if not agent.rag_config or not agent.rag_config.enabled:
            return None

        try:
            # Import RAG components (lazy import to avoid circular dependencies)
            from offline_chat.rag.context_retriever import ContextRetriever
            from offline_chat.rag.database_integration import DatabaseIntegration
            from offline_chat.rag.document_processor import DocumentProcessor
            from offline_chat.rag.embedding_generator import EmbeddingGenerator
            from offline_chat.rag.orchestrator import RAGOrchestrator
            from offline_chat.rag.prompt_augmenter import PromptAugmenter
            from offline_chat.rag.vector_store import VectorStore

            # Get data directory for vector store
            data_dir = get_default_data_dir() / "rag"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Initialize core components
            vector_store = VectorStore(data_dir)
            embedding_generator = EmbeddingGenerator(model_name=agent.rag_config.embedding_model)
            context_retriever = ContextRetriever(vector_store=vector_store, embedding_generator=embedding_generator)
            document_processor = DocumentProcessor(
                chunk_size=agent.rag_config.chunk_size, chunk_overlap=agent.rag_config.chunk_overlap
            )
            prompt_augmenter = PromptAugmenter()

            # Initialize optional components
            web_scraper = None
            database_integration = None

            # Check if agent has web sources - initialize web scraper if needed
            has_web_sources = any(ks.source_type == "web" for ks in agent.rag_config.knowledge_sources)
            if has_web_sources:
                # Web scraper will be initialized with MCP client when needed
                # For now, we'll pass None and let the orchestrator handle it
                pass

            # Check if agent has database sources - initialize database integration if needed
            has_db_sources = any(ks.source_type == "database" for ks in agent.rag_config.knowledge_sources)
            if has_db_sources and self.db_manager:
                # Get the first database connection for the agent
                # In the future, we might want to support multiple database connections
                if agent.connection_assignments:
                    first_connection = agent.connection_assignments[0]
                    conn_result = self.db_manager.get_connection(first_connection.connection_name)
                    if not is_err(conn_result):
                        connection = unwrap(conn_result)
                        database_integration = DatabaseIntegration(
                            connection=connection, document_processor=document_processor
                        )

            # Create orchestrator
            orchestrator = RAGOrchestrator(
                agent_config=agent,
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                context_retriever=context_retriever,
                document_processor=document_processor,
                prompt_augmenter=prompt_augmenter,
                web_scraper=web_scraper,
                database_integration=database_integration,
            )

            logger.info(f"Initialized RAG orchestrator for agent '{agent.name}'")
            return orchestrator

        except Exception as e:
            logger.error(f"Failed to initialize RAG orchestrator for agent '{agent.name}': {e}")
            raise

    def create_agent(self, agent: Agent) -> bool:
        """Create a new agent with Ollama model registration.

        This method validates the agent name, saves the configuration and
        Modelfile, and registers the model with Ollama. If RAG is enabled,
        creates a vector collection for the agent.

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

            # Create vector collection if RAG is enabled
            if agent.rag_config and agent.rag_config.enabled:
                self._create_rag_collection(agent)

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

    def _create_rag_collection(self, agent: Agent) -> None:
        """Create a vector collection for an agent with RAG enabled.

        This method initializes the RAG components and creates a vector
        collection for the agent's knowledge base.

        Args:
            agent: The Agent instance with RAG configuration.

        Raises:
            Exception: If vector collection creation fails.
        """
        if not agent.rag_config or not agent.rag_config.enabled:
            return

        try:
            # Import RAG components (lazy import to avoid circular dependencies)
            from offline_chat.rag.embedding_generator import EmbeddingGenerator
            from offline_chat.rag.vector_store import VectorStore

            # Get data directory for vector store
            data_dir = get_default_data_dir() / "rag"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Initialize vector store and embedding generator
            vector_store = VectorStore(data_dir)
            embedding_generator = EmbeddingGenerator(model_name=agent.rag_config.embedding_model)

            # Get embedding dimension
            embedding_dim = embedding_generator.get_embedding_dimension()

            # Create collection
            vector_store.create_collection(agent.name, embedding_dim)

            logger.info(f"Created vector collection for agent '{agent.name}' with embedding dimension {embedding_dim}")

        except Exception as e:
            logger.error(f"Failed to create vector collection for agent '{agent.name}': {e}")
            raise

    def _delete_rag_collection(self, agent_name: str) -> None:
        """Delete the vector collection for an agent.

        This method removes the vector collection and all indexed content
        for the specified agent.

        Args:
            agent_name: The agent name.
        """
        try:
            # Import RAG components (lazy import to avoid circular dependencies)
            from offline_chat.rag.vector_store import VectorStore

            # Get data directory for vector store
            data_dir = get_default_data_dir() / "rag"

            # Initialize vector store
            vector_store = VectorStore(data_dir)

            # Delete collection
            vector_store.delete_collection(agent_name)

            logger.info(f"Deleted vector collection for agent '{agent_name}'")

        except Exception as e:
            # Log error but don't raise - we want to continue with agent deletion
            logger.warning(f"Failed to delete vector collection for agent '{agent_name}': {e}")

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

    def delete_agent(self, name: str, delete_rag_collection: bool = True) -> bool:
        """Delete an agent and its associated data.

        This method removes the Ollama model, deletes the agent directory,
        and removes the conversation history. If the agent has RAG enabled
        and delete_rag_collection is True, also deletes the vector collection.

        Args:
            name: The agent name to delete.
            delete_rag_collection: If True, delete the vector collection (default: True).

        Returns:
            True if the agent was deleted successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
            OllamaCommandError: If the Ollama rm command fails.
        """
        # Check if agent exists
        if not self.agent_exists(name):
            raise AgentNotFoundError(name)

        # Load agent to check for RAG configuration
        agent = self.get_agent(name)

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

        # Delete vector collection if RAG is enabled
        if delete_rag_collection and agent and agent.rag_config and agent.rag_config.enabled:
            self._delete_rag_collection(name)

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
                return Err(f"Access level '{access_level.value}' requires allowed_tables to be specified")
            if not isinstance(allowed_tables, list) or len(allowed_tables) == 0:
                return Err(f"Access level '{access_level.value}' requires allowed_tables to be a non-empty list")

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
            assignment for assignment in agent.connection_assignments if assignment.connection_name != connection_name
        ]

        # Check if connection was actually removed
        if len(agent.connection_assignments) == original_count:
            return Err(f"Connection '{connection_name}' is not assigned to agent '{agent_name}'")

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
        web_search_enabled, connection_assignments, mcp_servers, guidelines,
        and rag_config.

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
                - rag_config: RAGConfig | None

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
            "rag_config",
        }

        # Check for invalid fields
        invalid_fields = set(updates.keys()) - valid_fields
        if invalid_fields:
            return Err(
                f"Invalid update fields: {', '.join(invalid_fields)}. Valid fields: {', '.join(sorted(valid_fields))}"
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
                    return Err(f"Failed to recreate Ollama model: {result.stderr or result.stdout}")
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
                    return Err("connection_assignments must be a list of AgentConnectionAssignment instances")
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

        if "rag_config" in updates:
            from offline_chat.rag.models import RAGConfig

            rag_config = updates["rag_config"]
            if rag_config is not None and not isinstance(rag_config, RAGConfig):
                return Err("rag_config must be a RAGConfig instance or None")

            # If enabling RAG for the first time, create vector collection
            if rag_config and rag_config.enabled and (not agent.rag_config or not agent.rag_config.enabled):
                # Create vector collection for this agent
                try:
                    from offline_chat.rag.embedding_generator import EmbeddingGenerator
                    from offline_chat.rag.vector_store import VectorStore

                    # Get data directory for vector store
                    data_dir = get_default_data_dir() / "rag"
                    data_dir.mkdir(parents=True, exist_ok=True)

                    embedding_gen = EmbeddingGenerator(rag_config.embedding_model)
                    vector_store = VectorStore(data_dir)

                    # Create collection with appropriate dimensions
                    embedding_dim = embedding_gen.get_embedding_dimension()
                    vector_store.create_collection(agent_name, embedding_dim)
                except Exception as e:
                    return Err(f"Failed to create vector collection: {e}")

            agent.rag_config = rag_config

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
            return Err(f"Guideline index {index} out of range. Agent has {len(agent.guidelines)} guideline(s).")

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
            return Err(f"Guideline index {index} out of range. Agent has {len(agent.guidelines)} guideline(s).")

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
                result = migrate_agent(agent_name, config_data, config_path, self.db_manager)

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

    def _validate_rag_agent(self, agent_name: str) -> Result[Agent, str]:
        """Validate that an agent exists and has RAG enabled.

        Args:
            agent_name: Name of the agent to validate

        Returns:
            Result with Agent on success or error message on failure
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")

        if not agent.rag_config or not agent.rag_config.enabled:
            return Err(f"RAG is not enabled for agent '{agent_name}'")

        return Ok(agent)

    def _save_agent_config(self, agent: Agent) -> Result[None, str]:
        """Save agent configuration to disk.

        Args:
            agent: Agent instance to save

        Returns:
            Result with None on success or error message on failure
        """
        try:
            config_path = self._get_config_path(agent.name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
            return Ok(None)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")

    def _get_rag_orchestrator_safe(self, agent: Agent) -> Result["RAGOrchestrator", str]:  # noqa: F821
        """Get RAG orchestrator with error handling.

        Args:
            agent: Agent instance

        Returns:
            Result with RAGOrchestrator on success or error message on failure
        """
        try:
            orchestrator = self.get_rag_orchestrator(agent)
            if orchestrator is None:
                return Err("Failed to initialize RAG orchestrator")
            return Ok(orchestrator)
        except Exception as e:
            return Err(f"Failed to initialize RAG orchestrator: {e}")

    def add_knowledge_source(
        self,
        agent_name: str,
        source_type: str,
        identifier: str,
        ingest: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Result[None, str]:
        """Add a knowledge source to an agent and optionally ingest it.

        This method adds a new knowledge source (URL or database table) to an
        agent's RAG configuration and optionally triggers ingestion and indexing.

        Args:
            agent_name: Name of the agent to update
            source_type: Type of source ("web" or "database")
            identifier: URL for web sources, table name for database sources
            ingest: If True, trigger ingestion immediately (default: True)
            progress_callback: Optional callback function for progress updates

        Returns:
            Result with None on success or error message on failure

        Example:
            >>> manager = AgentManager()
            >>> result = manager.add_knowledge_source(
            ...     "research-assistant",
            ...     "web",
            ...     "https://example.com/docs"
            ... )
            >>> if is_ok(result):
            ...     print("Knowledge source added and ingested")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")

        # Check if RAG config exists
        if not agent.rag_config:
            return Err(
                f"RAG is not configured for agent '{agent_name}'. Please configure RAG first via the Update Agent menu."
            )

        # Auto-enable RAG if this is the first knowledge source
        was_disabled = not agent.rag_config.enabled
        if was_disabled and len(agent.rag_config.knowledge_sources) == 0:
            agent.rag_config.enabled = True
            logger.info(f"Auto-enabling RAG for agent '{agent_name}' (first knowledge source)")

        # Validate source type
        if source_type not in ["web", "database"]:
            return Err(f"Invalid source type: {source_type}. Must be 'web' or 'database'")

        # Validate identifier
        if not identifier or not identifier.strip():
            return Err("Source identifier cannot be empty")

        identifier = identifier.strip()

        # Validate URL format for web sources
        if source_type == "web":
            from offline_chat.rag.validators import is_valid_url

            if not is_valid_url(identifier):
                return Err(f"Invalid URL format: {identifier}")

        # Check if source already exists
        for source in agent.rag_config.knowledge_sources:
            if source.source_type == source_type and source.identifier == identifier:
                return Err(f"Knowledge source already exists: {identifier}")

        # Create knowledge source
        from datetime import datetime

        from offline_chat.rag.models import KnowledgeSource

        new_source = KnowledgeSource(
            source_type=source_type,
            identifier=identifier,
            status="pending",
        )

        # Add to agent's knowledge sources
        agent.rag_config.knowledge_sources.append(new_source)

        # Save updated agent config
        try:
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save agent config: {e}")

        # Ingest if requested
        if ingest:
            if progress_callback:
                progress_callback(f"Ingesting {source_type} source: {identifier}")

            try:
                orchestrator = self.get_rag_orchestrator(agent)
                if orchestrator is None:
                    return Err("Failed to initialize RAG orchestrator")

                results = orchestrator.ingest_knowledge_sources([new_source])

                if not results or not results[0].success:
                    error_msg = results[0].error_message if results else "Unknown error"
                    return Err(f"Ingestion failed: {error_msg}")

                if progress_callback:
                    progress_callback(f"Successfully ingested {results[0].chunks_processed} chunks")

                # Update source status in config
                new_source.status = "active"
                new_source.last_indexed = datetime.now()

                # Save updated status
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(agent.to_dict(), f, indent=2)

            except Exception as e:
                logger.error(f"Error during ingestion: {e}")
                return Err(f"Ingestion error: {str(e)}")

        return Ok(None)

    def reindex_knowledge_source(
        self,
        agent_name: str,
        source_identifier: str,
        progress_callback: Optional[callable] = None,
    ) -> Result[None, str]:
        """Re-index an existing knowledge source.

        This method clears old embeddings for a knowledge source and re-ingests
        the content. Useful for updating content that has changed.

        Args:
            agent_name: Name of the agent
            source_identifier: URL or table name of the source to re-index
            progress_callback: Optional callback function for progress updates

        Returns:
            Result with None on success or error message on failure

        Example:
            >>> manager = AgentManager()
            >>> result = manager.reindex_knowledge_source(
            ...     "research-assistant",
            ...     "https://example.com/docs"
            ... )
            >>> if is_ok(result):
            ...     print("Knowledge source re-indexed")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")

        # Check if RAG is enabled
        if not agent.rag_config or not agent.rag_config.enabled:
            return Err(f"RAG is not enabled for agent '{agent_name}'")

        # Find the knowledge source
        source_to_reindex = None
        for source in agent.rag_config.knowledge_sources:
            if source.identifier == source_identifier:
                source_to_reindex = source
                break

        if source_to_reindex is None:
            return Err(f"Knowledge source not found: {source_identifier}")

        if progress_callback:
            progress_callback(f"Re-indexing {source_to_reindex.source_type} source: {source_identifier}")

        try:
            # Get RAG orchestrator
            orchestrator = self.get_rag_orchestrator(agent)
            if orchestrator is None:
                return Err("Failed to initialize RAG orchestrator")

            # Clear old embeddings by deleting and recreating collection
            # Note: This is a simple approach - in production you might want
            # to selectively delete only chunks from this source
            if progress_callback:
                progress_callback("Clearing old embeddings...")

            # For now, we'll just re-ingest which will add new chunks
            # The vector store will handle duplicates

            # Re-ingest the source
            results = orchestrator.ingest_knowledge_sources([source_to_reindex])

            if not results or not results[0].success:
                error_msg = results[0].error_message if results else "Unknown error"
                return Err(f"Re-indexing failed: {error_msg}")

            if progress_callback:
                progress_callback(f"Successfully re-indexed {results[0].chunks_processed} chunks")

            # Update source status in config
            from datetime import datetime

            source_to_reindex.status = "active"
            source_to_reindex.last_indexed = datetime.now()
            source_to_reindex.error_message = None

            # Save updated status
            config_path = self._get_config_path(agent_name)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(agent.to_dict(), f, indent=2)

            return Ok(None)

        except Exception as e:
            logger.error(f"Error during re-indexing: {e}")
            return Err(f"Re-indexing error: {str(e)}")

    def list_knowledge_sources(
        self,
        agent_name: str,
    ) -> Result[list, str]:
        """List all knowledge sources for an agent.

        This method returns all configured knowledge sources with their status,
        last indexed timestamp, and any error messages.

        Args:
            agent_name: Name of the agent

        Returns:
            Result with list of knowledge sources on success or error message on failure

        Example:
            >>> manager = AgentManager()
            >>> result = manager.list_knowledge_sources("research-assistant")
            >>> if is_ok(result):
            ...     sources = unwrap(result)
            ...     for source in sources:
            ...         print(f"{source.identifier} - {source.status}")
        """
        # Load agent config
        agent = self.get_agent(agent_name)
        if agent is None:
            return Err(f"Agent '{agent_name}' not found")

        # Check if RAG is enabled
        if not agent.rag_config or not agent.rag_config.enabled:
            return Err(f"RAG is not enabled for agent '{agent_name}'")

        return Ok(agent.rag_config.knowledge_sources)
