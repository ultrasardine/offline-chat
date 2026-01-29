"""Interactive CLI for database configuration.

This module provides interactive command-line functions for configuring
database access for agents, including Oracle, PostgreSQL, MySQL, and SQLite.

The CLI guides users through the process of:
1. Selecting a database type (Oracle, PostgreSQL, MySQL, SQLite)
2. Providing connection details (with database-specific prompts)
3. Testing the connection before saving
4. Adding multiple databases to a single agent

Oracle Database Support:
    Oracle is the primary supported database, accessed through Oracle SQLcl's
    built-in MCP server. The CLI provides three connection methods:

    1. Existing SQLcl Connection (Recommended):
       - Reuses saved connections from ~/.sqlcl/connections.json
       - No need to re-enter credentials
       - Most secure as credentials are managed by SQLcl

    2. TNS Alias:
       - Uses TNS names from tnsnames.ora
       - Requires username and password
       - Convenient for environments with TNS configured

    3. Full Connection Details:
       - Prompts for host, port, service name, username, password
       - Creates connection string: user/pass@host:port/service
       - Most flexible but requires all details

Usage Example:
    >>> from offline_chat.database_config_cli import configure_database_access
    >>>
    >>> # Interactive configuration
    >>> configs = configure_database_access()
    >>>
    >>> # Returns list of MCPServerConfig objects
    >>> for config in configs:
    ...     print(f"Configured: {config.name} ({config.database_type})")

Integration with Agent Creation:
    This module is typically called during agent creation in the main CLI:

    >>> from offline_chat import Agent, AgentManager
    >>> from offline_chat.database_config_cli import configure_database_access
    >>>
    >>> # During agent creation
    >>> db_configs = configure_database_access()
    >>>
    >>> agent = Agent(
    ...     name="data-analyst",
    ...     display_name="Data Analyst",
    ...     base_model="llama3.1:latest",
    ...     system_prompt="You are a data analyst.",
    ...     temperature=0.7,
    ...     mcp_servers=db_configs  # Add database configurations
    ... )
    >>>
    >>> manager = AgentManager()
    >>> manager.create_agent(agent)

Connection Testing:
    All database configurations are tested before being saved. If a connection
    test fails, the user is prompted to either retry or skip that database.
    This ensures that only working configurations are saved to the agent.
"""

import json
import os
from getpass import getpass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from offline_chat.connection_validator import validate_database_connection
from offline_chat.database_config import create_database_mcp_config
from offline_chat.mcp_config import MCPServerConfig

if TYPE_CHECKING:
    from offline_chat.database.connection import DatabaseConnection
    from offline_chat.database.manager import DatabaseConnectionManager


def configure_database_access(
    db_manager: Optional["DatabaseConnectionManager"] = None,
) -> list[MCPServerConfig]:
    """Interactive CLI flow for configuring database access.

    Prompts the user to add one or more database configurations,
    either by selecting existing connections or creating new ones.
    Validates connections and returns the list of configurations.

    Args:
        db_manager: Optional DatabaseConnectionManager for accessing existing connections.

    Returns:
        List of database MCP server configurations.
    """
    configs: list[MCPServerConfig] = []

    add_db = input("\nAdd database access? (y/N): ").strip().lower()
    if add_db != "y":
        return configs

    print("\n" + "-" * 40)
    print("Database Configuration")
    print("-" * 40)

    while True:
        # Show option to use existing connection or create new
        use_existing = False
        if db_manager is not None:
            existing_connections = db_manager.list_connections()
            if existing_connections:
                print("\nOptions:")
                print("  1. Use existing database connection")
                print("  2. Create new database connection")
                print("  0. Done adding databases")
                print()

                try:
                    choice = input("Select option: ").strip()
                    if choice == "0":
                        break
                    elif choice == "1":
                        use_existing = True
                    elif choice == "2":
                        use_existing = False
                    else:
                        print("Invalid selection.")
                        continue
                except ValueError:
                    print("Invalid input.")
                    continue

        if use_existing and db_manager is not None:
            # Select from existing connections
            existing_connections = db_manager.list_connections()

            # Filter out already selected connections
            available_connections = [
                conn for conn in existing_connections if not any(c.name == conn.name for c in configs)
            ]

            if not available_connections:
                print("\nNo available connections. All existing connections have been added.")
                continue

            print("\nExisting database connections:")
            for i, conn in enumerate(available_connections, 1):
                print(f"  {i}. {conn.name} ({conn.database_type})")
            print("  0. Cancel")
            print()

            try:
                choice = input("Select connection: ").strip()
                if choice == "0":
                    continue

                idx = int(choice)
                if 1 <= idx <= len(available_connections):
                    selected_conn = available_connections[idx - 1]

                    # Convert DatabaseConnection to MCPServerConfig
                    config = _connection_to_mcp_config(selected_conn)
                    configs.append(config)
                    print(f"✓ Database '{selected_conn.name}' added successfully")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")

        else:
            # Create new connection
            db_type = select_database_type()
            if db_type is None:
                break

            db_name = input("\nDatabase connection name: ").strip()
            if not db_name:
                print("Database name is required. Skipping.")
                continue

            # Check if name already used
            if any(c.name == db_name for c in configs):
                print(f"Database '{db_name}' already added. Use a different name.")
                continue

            try:
                if db_type == "oracle":
                    config = configure_oracle(db_name)
                elif db_type == "sqlite":
                    config = configure_sqlite(db_name)
                elif db_type == "postgresql":
                    config = configure_postgresql(db_name)
                elif db_type == "mysql":
                    config = configure_mysql(db_name)
                else:
                    print(f"Unsupported database type: {db_type}")
                    continue

                if config is None:
                    continue

                # Test connection
                print("\nTesting connection...", end=" ", flush=True)
                success, error = validate_database_connection(config)

                if success:
                    print("Done!")
                    configs.append(config)
                    print(f"✓ Database '{db_name}' configured successfully")
                else:
                    print("Failed!")
                    print(f"\nConnection error: {error}")
                    retry = input("Skip this database? (Y/n): ").strip().lower()
                    if retry != "n":
                        print("Database configuration skipped.")
                        continue
                    # If user wants to retry, loop will continue

            except ValueError as e:
                print(f"\nConfiguration error: {e}")
                continue
            except KeyboardInterrupt:
                print("\n\nDatabase configuration cancelled.")
                break

        # Ask if user wants to add another database
        add_another = input("\nAdd another database? (y/N): ").strip().lower()
        if add_another != "y":
            break

    return configs


def _connection_to_mcp_config(conn: "DatabaseConnection") -> MCPServerConfig:
    """Convert a DatabaseConnection to an MCPServerConfig.

    Args:
        conn: DatabaseConnection object to convert.

    Returns:
        MCPServerConfig configured for the database connection.
    """
    if conn.database_type == "sqlite":
        return create_database_mcp_config("sqlite", conn.name, path=conn.file_path)
    elif conn.database_type == "oracle":
        # Oracle connections always use full connection details in DatabaseConnection
        return create_database_mcp_config(
            "oracle",
            conn.name,
            host=conn.host,
            port=conn.port,
            service_name=conn.service_name,
            username=conn.username,
            password=conn.password,
        )
    elif conn.database_type == "postgresql":
        return create_database_mcp_config(
            "postgresql",
            conn.name,
            host=conn.host,
            port=conn.port,
            database=conn.database,
            username=conn.username,
            password=conn.password,
        )
    elif conn.database_type == "mysql":
        return create_database_mcp_config(
            "mysql",
            conn.name,
            host=conn.host,
            port=conn.port,
            database=conn.database,
            username=conn.username,
            password=conn.password,
        )
    else:
        raise ValueError(f"Unsupported database type: {conn.database_type}")


def select_database_type() -> Optional[str]:
    """Prompt for database type selection.

    Oracle is shown first as the primary database type.

    Returns:
        Selected database type string, or None to cancel.
    """
    print("\nDatabase types:")
    print("  1. Oracle")
    print("  2. PostgreSQL")
    print("  3. MySQL")
    print("  4. SQLite")
    print("  0. Done adding databases")
    print()

    try:
        choice = input("Select database type: ").strip()
        idx = int(choice)

        if idx == 0:
            return None
        elif idx == 1:
            return "oracle"
        elif idx == 2:
            return "postgresql"
        elif idx == 3:
            return "mysql"
        elif idx == 4:
            return "sqlite"
        else:
            print("Invalid selection.")
            return None
    except ValueError:
        print("Invalid input.")
        return None


def configure_oracle(db_name: str) -> Optional[MCPServerConfig]:
    """Configure Oracle Database connection.

    First checks for existing SQLcl connections, then prompts for details.

    Args:
        db_name: Unique name for this database connection.

    Returns:
        MCPServerConfig for Oracle, or None if cancelled.
    """
    print("\n--- Oracle Database Configuration ---")

    # Check for existing SQLcl connections
    existing_connections = list_sqlcl_connections()

    if existing_connections:
        print("\nExisting SQLcl connections:")
        for i, conn in enumerate(existing_connections, 1):
            print(f"  {i}. {conn}")
        print(f"  {len(existing_connections) + 1}. Create new connection")
        print()

        try:
            choice = input(f"Select connection (1-{len(existing_connections) + 1}): ").strip()
            idx = int(choice)

            if 1 <= idx <= len(existing_connections):
                conn_name = existing_connections[idx - 1]
                return create_database_mcp_config("oracle", db_name, connection_name=conn_name)
        except ValueError:
            print("Invalid input. Creating new connection.")

    # Prompt for new connection details
    print("\nOracle Database Connection Details:")
    use_tns = input("Use TNS alias? (y/N): ").strip().lower() == "y"

    if use_tns:
        tns_name = input("TNS alias: ").strip()
        if not tns_name:
            print("TNS alias is required.")
            return None

        username = input("Username: ").strip()
        if not username:
            print("Username is required.")
            return None

        password = getpass("Password: ")

        return create_database_mcp_config("oracle", db_name, tns_name=tns_name, username=username, password=password)
    else:
        host = input("Host [localhost]: ").strip() or "localhost"
        port_input = input("Port [1521]: ").strip()
        port = int(port_input) if port_input else 1521

        service_name = input("Service name: ").strip()
        if not service_name:
            print("Service name is required.")
            return None

        username = input("Username: ").strip()
        if not username:
            print("Username is required.")
            return None

        password = getpass("Password: ")

        return create_database_mcp_config(
            "oracle",
            db_name,
            host=host,
            port=port,
            service_name=service_name,
            username=username,
            password=password,
        )


def list_sqlcl_connections() -> list[str]:
    """List available SQLcl connections.

    Reads the SQLcl connections.json file from the user's home directory
    to discover existing database connections.

    Returns:
        List of connection names from SQLcl configuration.
    """
    # SQLcl connections are typically stored in ~/.sqlcl/connections.json
    sqlcl_config_path = Path.home() / ".sqlcl" / "connections.json"

    if not sqlcl_config_path.exists():
        return []

    try:
        with open(sqlcl_config_path, "r") as f:
            connections_data = json.load(f)

        # Extract connection names from the JSON structure
        # The structure may vary, but typically it's a dict with connection names as keys
        if isinstance(connections_data, dict):
            return list(connections_data.keys())
        elif isinstance(connections_data, list):
            # If it's a list of connection objects
            return [conn.get("name", "") for conn in connections_data if "name" in conn]

        return []
    except (json.JSONDecodeError, IOError):
        return []


def configure_sqlite(db_name: str) -> Optional[MCPServerConfig]:
    """Configure SQLite database connection.

    Prompts for file path and validates it exists.

    Args:
        db_name: Unique name for this database connection.

    Returns:
        MCPServerConfig for SQLite, or None if cancelled.
    """
    print("\n--- SQLite Database Configuration ---")

    path = input("Database file path: ").strip()
    if not path:
        print("File path is required.")
        return None

    # Validate file exists
    if not validate_sqlite_path(path):
        print(f"Error: File '{path}' does not exist.")
        create = input("Create new database file? (y/N): ").strip().lower()
        if create != "y":
            return None
        # If user wants to create, we'll allow the path
        # (actual creation happens when MCP server starts)

    return create_database_mcp_config("sqlite", db_name, path=path)


def validate_sqlite_path(path: str) -> bool:
    """Validate that a SQLite database file path exists.

    Args:
        path: File path to validate.

    Returns:
        True if file exists, False otherwise.
    """
    return os.path.isfile(path)


def configure_postgresql(db_name: str) -> Optional[MCPServerConfig]:
    """Configure PostgreSQL database connection.

    Prompts for all connection parameters.

    Args:
        db_name: Unique name for this database connection.

    Returns:
        MCPServerConfig for PostgreSQL, or None if cancelled.
    """
    print("\n--- PostgreSQL Database Configuration ---")

    host = input("Host [localhost]: ").strip() or "localhost"
    port_input = input("Port [5432]: ").strip()
    port = int(port_input) if port_input else 5432

    database = input("Database name: ").strip()
    if not database:
        print("Database name is required.")
        return None

    username = input("Username: ").strip()
    if not username:
        print("Username is required.")
        return None

    password = getpass("Password: ")

    return create_database_mcp_config(
        "postgresql",
        db_name,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
    )


def configure_mysql(db_name: str) -> Optional[MCPServerConfig]:
    """Configure MySQL database connection.

    Prompts for all connection parameters.

    Args:
        db_name: Unique name for this database connection.

    Returns:
        MCPServerConfig for MySQL, or None if cancelled.
    """
    print("\n--- MySQL Database Configuration ---")

    host = input("Host [localhost]: ").strip() or "localhost"
    port_input = input("Port [3306]: ").strip()
    port = int(port_input) if port_input else 3306

    database = input("Database name: ").strip()
    if not database:
        print("Database name is required.")
        return None

    username = input("Username: ").strip()
    if not username:
        print("Username is required.")
        return None

    password = getpass("Password: ")

    return create_database_mcp_config(
        "mysql",
        db_name,
        host=host,
        port=port,
        database=database,
        username=username,
        password=password,
    )
