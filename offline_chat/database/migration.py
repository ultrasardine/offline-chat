"""Migration utilities for converting inline database configs to centralized connections.

This module provides functionality to migrate agents from the old inline database
configuration format to the new centralized connection management system. It handles:
- Detection of agents with inline database_config fields
- Detection of agents with legacy connection_references fields
- Creation of connections in the centralized store
- Updating agent configs to use connection_assignments
- Removal of deprecated fields

The migration process is designed to be safe and preserve original configurations
if any errors occur during migration.
"""

import json
from pathlib import Path
from typing import Any

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import Err, Ok, Result, is_err, unwrap_err


def detect_inline_configs(agents_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Detect agents with inline database configurations that need migration.

    This function scans all agent configuration files in the agents directory
    and identifies those that have either:
    1. A database_config field (old inline configuration)
    2. A connection_references field (legacy connection references without access control)

    Args:
        agents_dir: Path to the agents directory containing agent subdirectories

    Returns:
        List of tuples (agent_name, config_dict) for agents needing migration.
        Returns empty list if agents_dir doesn't exist or can't be read.

    Example:
        >>> agents_dir = Path("/home/user/.offline-chat/agents")
        >>> agents_to_migrate = detect_inline_configs(agents_dir)
        >>> for agent_name, config in agents_to_migrate:
        ...     print(f"Agent {agent_name} needs migration")
    """
    agents_to_migrate = []

    # If agents directory doesn't exist, return empty list
    if not agents_dir.exists():
        return []

    # Scan all subdirectories in agents directory
    try:
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            # Look for config.json in the agent directory
            config_path = agent_dir / "config.json"
            if not config_path.exists():
                continue

            # Load and parse the config
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                agent_name = config_data.get("name", agent_dir.name)

                # Check if agent has inline database_config
                has_database_config = config_data.get("database_config") is not None

                # Check if agent has legacy connection_references (without connection_assignments)
                has_legacy_references = (
                    config_data.get("connection_references") and
                    not config_data.get("connection_assignments")
                )

                # Add to migration list if either condition is true
                if has_database_config or has_legacy_references:
                    agents_to_migrate.append((agent_name, config_data))

            except (json.JSONDecodeError, KeyError, OSError) as e:
                # Skip invalid config files
                print(f"Warning: Skipping invalid config in {agent_dir}: {e}")
                continue

    except (OSError, PermissionError) as e:
        # If we can't read the agents directory, return empty list
        print(f"Warning: Could not scan agents directory: {e}")
        return []

    return agents_to_migrate


def migrate_agent(
    agent_name: str,
    config_data: dict[str, Any],
    config_path: Path,
    db_manager: DatabaseConnectionManager
) -> Result[str, str]:
    """Migrate a single agent from inline config to centralized connection.

    This function performs the following steps:
    1. If database_config exists, create a connection in the centralized store
    2. If connection_references exists, convert to connection_assignments with read-write access
    3. Update agent config with connection_assignment
    4. Remove database_config and connection_references fields
    5. Save updated config

    The connection name is generated as "{agent_name}-{database_type}".
    The access level is set to READ_WRITE for backward compatibility.

    Args:
        agent_name: Name of the agent to migrate
        config_data: Agent configuration dictionary
        config_path: Path to the agent's config.json file
        db_manager: DatabaseConnectionManager instance for creating connections

    Returns:
        Result with the created connection name on success, or error message on failure.
        If the agent only has connection_references (no database_config), returns
        "migrated-references" as the connection name.

    Example:
        >>> from pathlib import Path
        >>> manager = DatabaseConnectionManager()
        >>> config_path = Path("/home/user/.offline-chat/agents/my-agent/config.json")
        >>> config_data = {
        ...     "name": "my-agent",
        ...     "database_config": {
        ...         "type": "postgresql",
        ...         "host": "localhost",
        ...         "port": 5432,
        ...         "database": "mydb",
        ...         "username": "user",
        ...         "password": "pass"
        ...     }
        ... }
        >>> result = migrate_agent("my-agent", config_data, config_path, manager)
        >>> if is_ok(result):
        ...     print(f"Created connection: {unwrap(result)}")
    """
    connection_assignments = []
    created_connection_name = None

    # Step 1: Handle database_config if present
    if config_data.get("database_config"):
        database_config = config_data["database_config"]

        # Extract database type
        db_type = database_config.get("type")
        if not db_type:
            return Err(f"Agent '{agent_name}': database_config missing 'type' field")

        # Generate connection name
        connection_name = f"{agent_name}-{db_type}"

        # Create DatabaseConnection object from inline config
        try:
            connection = _create_connection_from_inline_config(
                connection_name,
                database_config
            )
        except ValueError as e:
            return Err(f"Agent '{agent_name}': Invalid database_config: {e}")

        # Create connection in store
        result = db_manager.create_connection(connection)
        if is_err(result):
            error_msg = unwrap_err(result)
            # If connection already exists, that's okay - we can reuse it
            if "already exists" not in error_msg:
                return Err(f"Agent '{agent_name}': Failed to create connection: {error_msg}")

        # Create connection assignment with read-write access
        assignment = AgentConnectionAssignment(
            connection_name=connection_name,
            access_level=AccessLevel.READ_WRITE,
            allowed_tables=None
        )
        connection_assignments.append(assignment)
        created_connection_name = connection_name

    # Step 2: Handle legacy connection_references if present
    if config_data.get("connection_references"):
        connection_references = config_data["connection_references"]

        # Convert each reference to a connection_assignment with read-write access
        for conn_ref in connection_references:
            # Check if this connection already exists in the store
            result = db_manager.get_connection(conn_ref)
            if is_err(result):
                # Connection doesn't exist - this is an error
                return Err(
                    f"Agent '{agent_name}': Referenced connection '{conn_ref}' not found. "
                    f"Please create this connection before migrating."
                )

            # Create assignment with read-write access for backward compatibility
            assignment = AgentConnectionAssignment(
                connection_name=conn_ref,
                access_level=AccessLevel.READ_WRITE,
                allowed_tables=None
            )
            connection_assignments.append(assignment)

        # If we only migrated references (no database_config), use a special marker
        if created_connection_name is None:
            created_connection_name = "migrated-references"

    # Step 3: Update agent config with connection_assignments
    config_data["connection_assignments"] = [
        assignment.to_dict() for assignment in connection_assignments
    ]

    # Step 4: Remove deprecated fields
    if "database_config" in config_data:
        del config_data["database_config"]
    if "connection_references" in config_data:
        del config_data["connection_references"]

    # Step 5: Save updated config
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except (OSError, PermissionError) as e:
        return Err(f"Agent '{agent_name}': Failed to save updated config: {e}")

    return Ok(created_connection_name)


def _create_connection_from_inline_config(
    connection_name: str,
    database_config: dict[str, Any]
) -> DatabaseConnection:
    """Create a DatabaseConnection object from inline database_config.

    This helper function converts the old inline database configuration format
    to a DatabaseConnection object suitable for the centralized store.

    Args:
        connection_name: Name for the new connection
        database_config: Dictionary containing inline database configuration

    Returns:
        DatabaseConnection object

    Raises:
        ValueError: If required fields are missing or invalid

    Example:
        >>> config = {
        ...     "type": "postgresql",
        ...     "host": "localhost",
        ...     "port": 5432,
        ...     "database": "mydb",
        ...     "username": "user",
        ...     "password": "pass"
        ... }
        >>> conn = _create_connection_from_inline_config("my-conn", config)
        >>> conn.database_type
        'postgresql'
    """
    db_type = database_config.get("type")
    if not db_type:
        raise ValueError("Missing 'type' field in database_config")

    # Map common field names
    connection = DatabaseConnection(
        name=connection_name,
        database_type=db_type,
        host=database_config.get("host"),
        port=database_config.get("port"),
        database=database_config.get("database"),
        service_name=database_config.get("service_name"),
        username=database_config.get("username"),
        password=database_config.get("password"),
        file_path=database_config.get("file_path"),
        additional_params=database_config.get("additional_params", {})
    )

    return connection
