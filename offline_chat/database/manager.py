"""Database connection manager for CRUD operations.

This module provides the DatabaseConnectionManager class which handles all
CRUD operations for database connections, including creation, listing,
updating, and deletion. It manages the centralized connection store at
~/.offline-chat/database_connections.json with secure file permissions.
"""

import json
import os
from pathlib import Path
from typing import Any

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.result import Result, Ok, Err
from offline_chat.database.validator import ConnectionValidator


class DatabaseConnectionManager:
    """Manages CRUD operations for database connections.
    
    This class provides a centralized interface for managing database
    connections. It handles:
    - Creating and validating new connections
    - Listing and retrieving existing connections
    - Updating connection parameters
    - Deleting connections (with referential integrity checks)
    - Resolving connection names to full configurations
    - Secure storage with proper file permissions
    
    The connection store is a JSON file with the following structure:
    {
        "version": "1.0",
        "connections": [...]
    }
    
    Attributes:
        store_path: Path to the connection store JSON file
    """
    
    def __init__(self, store_path: Path | None = None, agents_dir: Path | None = None):
        """Initialize manager with connection store path.
        
        Args:
            store_path: Path to connection store. Defaults to
                       ~/.offline-chat/database_connections.json
            agents_dir: Path to agents directory. Defaults to
                       ~/.offline-chat/agents or OFFLINE_CHAT_DATA_DIR/agents
        """
        if store_path is None:
            store_path = Path.home() / ".offline-chat" / "database_connections.json"
        
        self.store_path = Path(store_path)
        
        # Set agents directory
        if agents_dir is None:
            # Check if OFFLINE_CHAT_DATA_DIR environment variable is set
            import os
            env_data_dir = os.environ.get("OFFLINE_CHAT_DATA_DIR")
            if env_data_dir:
                self.agents_dir = Path(env_data_dir) / "agents"
            else:
                self.agents_dir = Path.home() / ".offline-chat" / "agents"
        else:
            self.agents_dir = Path(agents_dir)
        
        self._ensure_store_exists()
        self._set_secure_permissions()
    
    def _ensure_store_exists(self) -> None:
        """Create store file if it doesn't exist.
        
        This method ensures the connection store directory and file exist.
        If the file doesn't exist, it creates it with an empty connections
        list and version information.
        """
        # Create parent directory if it doesn't exist
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create store file with initial structure if it doesn't exist
        if not self.store_path.exists():
            initial_data = {
                "version": "1.0",
                "connections": []
            }
            self._save_store(initial_data)
    
    def _set_secure_permissions(self) -> None:
        """Set file permissions to 600 (owner read/write only).
        
        This method sets the connection store file permissions to 0o600,
        which restricts access to the owner only. This is important for
        security since the file contains database credentials.
        
        On Windows, this method attempts to set permissions but may not
        have the same effect as on Unix-like systems.
        """
        try:
            # Set permissions to 600 (owner read/write only)
            os.chmod(self.store_path, 0o600)
        except (OSError, PermissionError) as e:
            # Log warning but don't fail - permissions may not be supported
            # on all platforms (e.g., Windows)
            print(f"Warning: Could not set secure permissions on connection store: {e}")
    
    def _verify_permissions(self) -> None:
        """Verify that file permissions are secure (600).
        
        This method checks if the connection store file has secure permissions
        (0o600 - owner read/write only). If the permissions are too permissive,
        it displays a warning message to the user.
        
        On Windows, this check may not be meaningful as the permission model
        is different from Unix-like systems.
        """
        if not self.store_path.exists():
            return
        
        try:
            # Get current file permissions
            current_perms = os.stat(self.store_path).st_mode & 0o777
            
            # Check if permissions are exactly 600 (owner read/write only)
            # We consider 600 as secure
            if current_perms != 0o600:
                # Check if permissions are too permissive (group or others have access)
                if current_perms & 0o077:  # Check if group or others have any permissions
                    print(
                        f"WARNING: Connection store has insecure permissions ({oct(current_perms)}).\n"
                        f"Database credentials may be accessible to other users.\n"
                        f"Recommended: Set permissions to 600 (owner read/write only).\n"
                        f"Run: chmod 600 {self.store_path}"
                    )
        except (OSError, PermissionError) as e:
            # Silently ignore permission check errors (e.g., on Windows)
            pass
    
    def _load_store(self) -> dict[str, Any]:
        """Load connections from JSON file with validation.
        
        This method loads the connection store and validates its structure:
        1. Checks that the JSON is valid
        2. Validates required top-level fields (version, connections)
        3. Validates that connections is an array
        4. Validates each connection object has required fields
        
        Returns:
            Dictionary containing version and connections list.
            
        Raises:
            json.JSONDecodeError: If the file contains invalid JSON.
            FileNotFoundError: If the store file doesn't exist.
            ValueError: If the JSON structure is invalid.
        """
        # Verify permissions before loading
        self._verify_permissions()
        
        # Load JSON data
        try:
            with open(self.store_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Connection store contains invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
            )
        
        # Validate top-level structure
        if not isinstance(data, dict):
            raise ValueError(
                "Connection store must be a JSON object (dictionary), "
                f"but found {type(data).__name__}"
            )
        
        # Validate required top-level fields
        if "version" not in data:
            raise ValueError(
                "Connection store is missing required field 'version'"
            )
        
        if "connections" not in data:
            raise ValueError(
                "Connection store is missing required field 'connections'"
            )
        
        # Validate connections is an array
        if not isinstance(data["connections"], list):
            raise ValueError(
                f"Field 'connections' must be an array, but found {type(data['connections']).__name__}"
            )
        
        # Validate each connection object
        for i, conn in enumerate(data["connections"]):
            if not isinstance(conn, dict):
                raise ValueError(
                    f"Connection at index {i} must be an object (dictionary), "
                    f"but found {type(conn).__name__}"
                )
            
            # Check for required fields in connection object
            required_fields = ["name", "database_type"]
            missing_fields = [field for field in required_fields if field not in conn]
            
            if missing_fields:
                conn_name = conn.get("name", f"<unnamed at index {i}>")
                raise ValueError(
                    f"Connection '{conn_name}' is missing required fields: {', '.join(missing_fields)}"
                )
            
            # Validate database_type is a string
            if not isinstance(conn["database_type"], str):
                raise ValueError(
                    f"Connection '{conn['name']}' has invalid database_type: "
                    f"must be a string, but found {type(conn['database_type']).__name__}"
                )
            
            # Validate name is a string
            if not isinstance(conn["name"], str):
                raise ValueError(
                    f"Connection at index {i} has invalid name: "
                    f"must be a string, but found {type(conn['name']).__name__}"
                )
        
        return data
    
    def _save_store(self, data: dict[str, Any]) -> None:
        """Save connections to JSON file.
        
        Args:
            data: Dictionary containing version and connections list.
        """
        with open(self.store_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Ensure permissions are set after writing
        self._set_secure_permissions()
    
    def create_connection(self, connection: DatabaseConnection) -> Result[DatabaseConnection, str]:
        """Create a new database connection.
        
        This method validates and creates a new database connection in the store.
        It performs the following validations:
        1. Connection name is unique
        2. Connection name is in kebab-case format
        3. Database type is in the supported list
        
        Steps:
        1. Validate connection name is unique
        2. Validate connection name format (kebab-case)
        3. Validate database_type is in supported list
        4. Save to store
        5. Return success or error
        
        Args:
            connection: DatabaseConnection object to create
            
        Returns:
            Result with the created connection or error message
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> conn = DatabaseConnection(
            ...     name="prod-oracle",
            ...     database_type="oracle",
            ...     host="db.example.com",
            ...     port=1521,
            ...     service_name="PRODDB",
            ...     username="user",
            ...     password="pass"
            ... )
            >>> result = manager.create_connection(conn)
            >>> is_ok(result)
            True
        """
        # Supported database types
        SUPPORTED_DB_TYPES = ["oracle", "postgresql", "mysql", "sqlite"]
        
        # Validate connection name format (kebab-case)
        if not self._is_valid_kebab_case(connection.name):
            return Err(
                "Connection name must be in kebab-case format "
                "(lowercase letters, numbers, and hyphens only)"
            )
        
        # Validate database type
        if connection.database_type not in SUPPORTED_DB_TYPES:
            return Err(
                f"Invalid database type '{connection.database_type}'. "
                f"Supported types: {', '.join(SUPPORTED_DB_TYPES)}"
            )
        
        # Validate connection parameters based on database type
        validation_result = self._validate_connection(connection)
        from offline_chat.database.result import is_err, unwrap_err
        if is_err(validation_result):
            return Err(unwrap_err(validation_result))
        
        # Load existing connections
        try:
            store_data = self._load_store()
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            return Err(f"Failed to load connection store: {e}")
        
        # Validate connection name uniqueness
        existing_names = {conn["name"] for conn in store_data.get("connections", [])}
        if connection.name in existing_names:
            return Err(f"Connection '{connection.name}' already exists")
        
        # Add connection to store
        store_data["connections"].append(connection.to_dict())
        
        # Save to store
        try:
            self._save_store(store_data)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save connection: {e}")
        
        return Ok(connection)
    
    def list_connections(self) -> list[DatabaseConnection]:
        """List all database connections.
        
        This method loads all connections from the store and returns them
        as a list of DatabaseConnection objects. If the store cannot be
        loaded, an empty list is returned.
        
        Returns:
            List of all connections from store. Returns empty list if
            store cannot be loaded.
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> connections = manager.list_connections()
            >>> for conn in connections:
            ...     print(f"{conn.name}: {conn.database_type}")
        """
        try:
            store_data = self._load_store()
            connections = []
            
            for conn_dict in store_data.get("connections", []):
                try:
                    conn = DatabaseConnection.from_dict(conn_dict)
                    connections.append(conn)
                except (KeyError, ValueError) as e:
                    # Skip invalid connection entries
                    print(f"Warning: Skipping invalid connection: {e}")
                    continue
            
            return connections
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            # Return empty list if store cannot be loaded
            print(f"Warning: Could not load connections: {e}")
            return []
    
    def get_connection(self, name: str) -> Result[DatabaseConnection, str]:
        """Get a specific connection by name.
        
        This method looks up a connection by name in the store and returns
        it if found. If the connection doesn't exist, an error is returned.
        
        Args:
            name: Connection name to look up
            
        Returns:
            Result with the connection if found, or error message if not found
            or if the store cannot be loaded.
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> result = manager.get_connection("prod-oracle")
            >>> if is_ok(result):
            ...     conn = unwrap(result)
            ...     print(f"Found: {conn.name}")
            ... else:
            ...     print(f"Error: {unwrap_err(result)}")
        """
        try:
            store_data = self._load_store()
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            return Err(f"Failed to load connection store: {e}")
        
        # Search for connection by name
        for conn_dict in store_data.get("connections", []):
            if conn_dict.get("name") == name:
                try:
                    conn = DatabaseConnection.from_dict(conn_dict)
                    return Ok(conn)
                except (KeyError, ValueError) as e:
                    return Err(f"Invalid connection data for '{name}': {e}")
        
        # Connection not found
        return Err(f"Connection '{name}' not found")
    
    def update_connection(self, name: str, updates: dict[str, Any]) -> Result[DatabaseConnection, str]:
        """Update an existing connection.
        
        This method updates an existing database connection with new parameters.
        The connection name cannot be changed - to rename a connection, create
        a new one and delete the old one.
        
        Steps:
        1. Load existing connection
        2. Prevent name changes
        3. Apply updates to other fields
        4. Validate updated connection
        5. Save on success, preserve original on failure
        
        Args:
            name: Connection name to update
            updates: Dictionary of fields to update (name changes not allowed)
            
        Returns:
            Result with updated connection or error message
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> result = manager.update_connection(
            ...     "prod-oracle",
            ...     {"host": "new-host.example.com", "port": 1522}
            ... )
            >>> if is_ok(result):
            ...     print("Connection updated successfully")
        """
        # Check if trying to change name
        if "name" in updates and updates["name"] != name:
            return Err(
                "Cannot change connection name. Create a new connection instead."
            )
        
        # Load existing connection
        result = self.get_connection(name)
        from offline_chat.database.result import is_err, unwrap, unwrap_err
        
        if is_err(result):
            return Err(f"Connection '{name}' not found")
        
        existing_conn = unwrap(result)
        
        # Create updated connection by applying updates to existing connection
        conn_dict = existing_conn.to_dict()
        
        # Apply updates (excluding name)
        for key, value in updates.items():
            if key != "name":  # Explicitly prevent name changes
                conn_dict[key] = value
        
        # Update the updated_at timestamp
        from datetime import datetime
        conn_dict["updated_at"] = datetime.now().isoformat()
        
        # Create new connection object from updated dict
        try:
            updated_conn = DatabaseConnection.from_dict(conn_dict)
        except (KeyError, ValueError) as e:
            return Err(f"Invalid update parameters: {e}")
        
        # Validate database type hasn't changed to invalid value
        SUPPORTED_DB_TYPES = ["oracle", "postgresql", "mysql", "sqlite"]
        if updated_conn.database_type not in SUPPORTED_DB_TYPES:
            return Err(
                f"Invalid database type '{updated_conn.database_type}'. "
                f"Supported types: {', '.join(SUPPORTED_DB_TYPES)}"
            )
        
        # Validate updated connection parameters
        validation_result = self._validate_connection(updated_conn)
        if is_err(validation_result):
            return Err(unwrap_err(validation_result))
        
        # Load store and update the connection
        try:
            store_data = self._load_store()
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            return Err(f"Failed to load connection store: {e}")
        
        # Find and update the connection in the store
        connection_found = False
        for i, conn in enumerate(store_data.get("connections", [])):
            if conn.get("name") == name:
                store_data["connections"][i] = updated_conn.to_dict()
                connection_found = True
                break
        
        if not connection_found:
            return Err(f"Connection '{name}' not found in store")
        
        # Save updated store
        try:
            self._save_store(store_data)
        except (OSError, PermissionError) as e:
            # Preserve original on failure
            return Err(f"Failed to save updated connection: {e}")
        
        return Ok(updated_conn)
    
    def delete_connection(self, name: str) -> Result[None, str]:
        """Delete a connection if not in use.
        
        This method deletes a database connection from the store, but only
        if it is not currently referenced by any agents. This ensures
        referential integrity and prevents breaking agent configurations.
        
        Steps:
        1. Check if any agents reference this connection
        2. If in use, return error with agent list
        3. If not in use, remove from store
        4. Return success or error
        
        Args:
            name: Connection name to delete
            
        Returns:
            Result with None on success or error message on failure
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> result = manager.delete_connection("old-connection")
            >>> if is_ok(result):
            ...     print("Connection deleted successfully")
            ... else:
            ...     print(f"Error: {unwrap_err(result)}")
        """
        # Check if connection exists
        result = self.get_connection(name)
        from offline_chat.database.result import is_err
        
        if is_err(result):
            return Err(f"Connection '{name}' not found")
        
        # Check if any agents are using this connection
        agents_using = self.get_agents_using_connection(name)
        
        if agents_using:
            agent_list = ", ".join(agents_using)
            return Err(
                f"Cannot delete connection '{name}'. "
                f"Used by agents: {agent_list}"
            )
        
        # Load store and remove the connection
        try:
            store_data = self._load_store()
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            return Err(f"Failed to load connection store: {e}")
        
        # Find and remove the connection
        original_count = len(store_data.get("connections", []))
        store_data["connections"] = [
            conn for conn in store_data.get("connections", [])
            if conn.get("name") != name
        ]
        
        # Verify connection was removed
        if len(store_data["connections"]) == original_count:
            return Err(f"Connection '{name}' not found in store")
        
        # Save updated store
        try:
            self._save_store(store_data)
        except (OSError, PermissionError) as e:
            return Err(f"Failed to save connection store: {e}")
        
        return Ok(None)
    
    def resolve_connections(
        self, 
        assignments: list["AgentConnectionAssignment"]
    ) -> Result[list[tuple["DatabaseConnection", "AccessLevel", list[str] | None]], str]:
        """Resolve connection assignments to full configurations.
        
        This method takes a list of AgentConnectionAssignment objects and resolves
        each connection name to its full DatabaseConnection configuration. It also
        returns the access level and allowed tables for each connection.
        
        Steps:
        1. For each assignment, look up connection_name in store
        2. If any connection not found, return error
        3. Return list of tuples (DatabaseConnection, AccessLevel, allowed_tables)
        
        Args:
            assignments: List of AgentConnectionAssignment objects to resolve
            
        Returns:
            Result with list of tuples (connection, access_level, allowed_tables)
            or error message if any connection is not found
            
        Example:
            >>> from offline_chat.database.connection_assignment import AgentConnectionAssignment
            >>> from offline_chat.database.access_level import AccessLevel
            >>> manager = DatabaseConnectionManager()
            >>> assignments = [
            ...     AgentConnectionAssignment(
            ...         connection_name="prod-db",
            ...         access_level=AccessLevel.READ_ONLY
            ...     )
            ... ]
            >>> result = manager.resolve_connections(assignments)
            >>> if is_ok(result):
            ...     resolved = unwrap(result)
            ...     for conn, level, tables in resolved:
            ...         print(f"{conn.name}: {level.value}")
        """
        from offline_chat.database.connection_assignment import AgentConnectionAssignment
        from offline_chat.database.access_level import AccessLevel
        from offline_chat.database.result import is_err, unwrap, unwrap_err
        
        resolved = []
        missing_connections = []
        
        for assignment in assignments:
            # Look up the connection in the store
            result = self.get_connection(assignment.connection_name)
            
            if is_err(result):
                missing_connections.append(assignment.connection_name)
            else:
                connection = unwrap(result)
                resolved.append((
                    connection,
                    assignment.access_level,
                    assignment.allowed_tables
                ))
        
        # If any connections were not found, return error
        if missing_connections:
            if len(missing_connections) == 1:
                return Err(f"Connection '{missing_connections[0]}' not found")
            else:
                conn_list = "', '".join(missing_connections)
                return Err(f"Connections not found: '{conn_list}'")
        
        return Ok(resolved)
    
    def get_agents_using_connection(self, connection_name: str) -> list[str]:
        """Find all agents that reference a connection.
        
        This method scans all agent configurations to find which agents
        reference the specified connection. This is used to enforce
        referential integrity when deleting connections.
        
        Steps:
        1. Scan all agent configs in agents directory
        2. Check connection_assignments field for connection_name
        3. Return list of agent names
        
        Args:
            connection_name: Connection name to search for
            
        Returns:
            List of agent names using this connection.
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> agents = manager.get_agents_using_connection("prod-db")
            >>> if agents:
            ...     print(f"Connection used by: {', '.join(agents)}")
            ... else:
            ...     print("Connection not in use")
        """
        agents_using = []
        
        # If agents directory doesn't exist, return empty list
        if not self.agents_dir.exists():
            return []
        
        # Scan all subdirectories in agents directory
        try:
            for agent_dir in self.agents_dir.iterdir():
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
                    
                    # Check connection_assignments field
                    connection_assignments = config_data.get("connection_assignments", [])
                    
                    # Check if this connection is referenced
                    for assignment in connection_assignments:
                        if isinstance(assignment, dict):
                            if assignment.get("connection_name") == connection_name:
                                agents_using.append(config_data.get("name", agent_dir.name))
                                break
                    
                    # Also check legacy connection_references field for backward compatibility
                    connection_references = config_data.get("connection_references", [])
                    if connection_name in connection_references:
                        agent_name = config_data.get("name", agent_dir.name)
                        if agent_name not in agents_using:
                            agents_using.append(agent_name)
                    
                except (json.JSONDecodeError, KeyError, OSError) as e:
                    # Skip invalid config files
                    continue
        
        except (OSError, PermissionError):
            # If we can't read the agents directory, return empty list
            return []
        
        return agents_using
    
    def _is_valid_kebab_case(self, name: str) -> bool:
        """Check if a name is in valid kebab-case format.
        
        Valid kebab-case:
        - Contains only lowercase letters, numbers, and hyphens
        - Does not start or end with a hyphen
        - Is not empty
        
        Args:
            name: Name to validate
            
        Returns:
            True if name is valid kebab-case, False otherwise
            
        Example:
            >>> manager = DatabaseConnectionManager()
            >>> manager._is_valid_kebab_case("my-connection-1")
            True
            >>> manager._is_valid_kebab_case("MyConnection")
            False
            >>> manager._is_valid_kebab_case("-invalid")
            False
            >>> manager._is_valid_kebab_case("invalid-")
            False
            >>> manager._is_valid_kebab_case("")
            False
        """
        if not name:
            return False
        
        # Check if starts or ends with hyphen
        if name.startswith("-") or name.endswith("-"):
            return False
        
        # Check if contains only lowercase letters, numbers, and hyphens
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        return all(c in allowed_chars for c in name)
    
    def _validate_connection(self, connection: DatabaseConnection) -> Result[None, str]:
        """Validate connection parameters based on database type.
        
        This method calls the appropriate ConnectionValidator method based on
        the connection's database_type.
        
        Args:
            connection: DatabaseConnection to validate
            
        Returns:
            Result with None on success or error message on failure
        """
        if connection.database_type == "oracle":
            return ConnectionValidator.validate_oracle(connection)
        elif connection.database_type == "postgresql":
            return ConnectionValidator.validate_postgresql(connection)
        elif connection.database_type == "mysql":
            return ConnectionValidator.validate_mysql(connection)
        elif connection.database_type == "sqlite":
            return ConnectionValidator.validate_sqlite(connection)
        else:
            return Err(f"Unsupported database type: {connection.database_type}")

