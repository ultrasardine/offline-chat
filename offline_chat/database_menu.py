"""CLI module for database connection management.

This module provides interactive command-line functions for managing
centralized database connections. Users can create, list, update, and
delete database connections that can be shared across multiple agents.

The CLI provides:
1. Create connection flow - prompts for connection details and validates
2. List connections - displays all connections with masked credentials
3. Update connection flow - modifies existing connection parameters
4. Delete connection flow - removes connections with usage checks

Usage Example:
    >>> from offline_chat.database_menu import show_database_menu
    >>> from offline_chat.database.manager import DatabaseConnectionManager
    >>>
    >>> manager = DatabaseConnectionManager()
    >>> show_database_menu(manager)
"""

from getpass import getpass
from typing import Optional

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_ok, unwrap, unwrap_err


def show_database_menu(manager: DatabaseConnectionManager) -> None:
    """Display database connection management menu.
    
    This is the main entry point for database connection management.
    It displays a menu with options to create, list, update, delete
    connections, or return to the main menu.
    
    Args:
        manager: DatabaseConnectionManager instance for connection operations
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> show_database_menu(manager)
        
        Database Connection Management
        ----------------------------------------
          1. Create connection
          2. List connections
          3. Update connection
          4. Delete connection
          5. Back to main menu
    """
    while True:
        print("\n" + "-" * 40)
        print("Database Connection Management")
        print("-" * 40)
        print("  1. Create connection")
        print("  2. List connections")
        print("  3. Update connection")
        print("  4. Delete connection")
        print("  5. Back to main menu")
        print()
        
        try:
            choice = input("Select option: ").strip()
            
            if choice == "1":
                create_connection_flow(manager)
            elif choice == "2":
                list_connections_display(manager)
            elif choice == "3":
                update_connection_flow(manager)
            elif choice == "4":
                delete_connection_flow(manager)
            elif choice == "5":
                break
            else:
                print("\nInvalid option. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
            break


def create_connection_flow(manager: DatabaseConnectionManager) -> None:
    """Interactive flow for creating a new database connection.
    
    This function guides the user through creating a new database connection:
    1. Prompts for connection name (kebab-case)
    2. Prompts for database type (oracle, postgresql, mysql, sqlite)
    3. Prompts for database-specific connection parameters
    4. Validates the connection
    5. Saves to the connection store
    
    Args:
        manager: DatabaseConnectionManager instance
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> create_connection_flow(manager)
        
        Create New Database Connection
        ========================================
        Connection name (kebab-case): prod-oracle
        
        Database types:
          1. Oracle
          2. PostgreSQL
          3. MySQL
          4. SQLite
        
        Select database type: 1
        ...
    """
    print("\n" + "=" * 40)
    print("Create New Database Connection")
    print("=" * 40)
    
    try:
        # Prompt for connection name
        name = input("\nConnection name (kebab-case): ").strip()
        if not name:
            print("\nError: Connection name is required.")
            return
        
        # Prompt for database type
        db_type = _select_database_type()
        if db_type is None:
            print("\nConnection creation cancelled.")
            return
        
        # Prompt for database-specific parameters
        if db_type == "oracle":
            connection = _configure_oracle_connection(name)
        elif db_type == "postgresql":
            connection = _configure_postgresql_connection(name)
        elif db_type == "mysql":
            connection = _configure_mysql_connection(name)
        elif db_type == "sqlite":
            connection = _configure_sqlite_connection(name)
        else:
            print(f"\nError: Unsupported database type: {db_type}")
            return
        
        if connection is None:
            return
        
        # Create the connection
        print("\nCreating connection...", end=" ", flush=True)
        result = manager.create_connection(connection)
        
        if is_ok(result):
            print("Done!")
            print(f"\n✓ Connection '{name}' created successfully.")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")
            
    except KeyboardInterrupt:
        print("\n\nConnection creation cancelled.")


def list_connections_display(manager: DatabaseConnectionManager) -> None:
    """Display all database connections with masked credentials.
    
    This function lists all connections from the store, showing:
    - Connection name
    - Database type
    - Host/path information
    - Masked credentials (passwords shown as ****)
    - Agents using each connection
    
    Args:
        manager: DatabaseConnectionManager instance
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> list_connections_display(manager)
        
        Database Connections
        ========================================
        
        Connection: prod-oracle
        Type: oracle
        Host: db.example.com:1521
        Service: PRODDB
        Username: app_user
        Password: ****
        Used by: data-analyst, sales-agent
        ----------------------------------------
    """
    print("\n" + "=" * 40)
    print("Database Connections")
    print("=" * 40)
    
    connections = manager.list_connections()
    
    if not connections:
        print("\nNo connections available. Create one first!")
        return
    
    for conn in connections:
        # Get masked connection data for secure display
        masked = conn.mask_sensitive_fields()
        
        print(f"\nConnection: {masked['name']}")
        print(f"Type: {masked['database_type']}")
        
        # Display connection details based on type
        if masked['database_type'] == "oracle":
            if masked.get('host') and masked.get('port'):
                print(f"Host: {masked['host']}:{masked['port']}")
            if masked.get('service_name'):
                print(f"Service: {masked['service_name']}")
            if masked.get('username'):
                print(f"Username: {masked['username']}")
            if masked.get('password'):
                print(f"Password: {masked['password']}")
                
        elif masked['database_type'] in ("postgresql", "mysql"):
            if masked.get('host') and masked.get('port'):
                print(f"Host: {masked['host']}:{masked['port']}")
            if masked.get('database'):
                print(f"Database: {masked['database']}")
            if masked.get('username'):
                print(f"Username: {masked['username']}")
            if masked.get('password'):
                print(f"Password: {masked['password']}")
                
        elif masked['database_type'] == "sqlite":
            if masked.get('file_path'):
                print(f"Path: {masked['file_path']}")
        
        # Display any additional parameters (with sensitive fields masked)
        if masked.get('additional_params'):
            print("Additional parameters:")
            for key, value in masked['additional_params'].items():
                print(f"  {key}: {value}")
        
        # Show which agents are using this connection
        agents_using = manager.get_agents_using_connection(conn.name)
        if agents_using:
            print(f"Used by: {', '.join(agents_using)}")
        else:
            print("Used by: (none)")
        
        print("-" * 40)


def update_connection_flow(manager: DatabaseConnectionManager) -> None:
    """Interactive flow for updating an existing connection.
    
    This function guides the user through updating a connection:
    1. Lists available connections
    2. User selects connection to update
    3. Prompts for which parameters to update
    4. Validates the updated connection
    5. Saves changes
    
    Note: Connection name cannot be changed. To rename, create a new
    connection and delete the old one.
    
    Args:
        manager: DatabaseConnectionManager instance
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> update_connection_flow(manager)
        
        Update Database Connection
        ========================================
        
        Available connections:
          1. prod-oracle (oracle)
          2. dev-postgres (postgresql)
          0. Cancel
        
        Select connection to update: 1
        ...
    """
    print("\n" + "=" * 40)
    print("Update Database Connection")
    print("=" * 40)
    
    # Select connection to update
    connection = _select_connection(manager, "Select connection to update")
    if connection is None:
        return
    
    print(f"\nUpdating connection: {connection.name}")
    print(f"Type: {connection.database_type}")
    print("\nNote: Connection name cannot be changed.")
    print("Leave fields blank to keep current values.")
    
    try:
        updates = {}
        
        # Prompt for updates based on database type
        if connection.database_type == "oracle":
            updates = _prompt_oracle_updates(connection)
        elif connection.database_type == "postgresql":
            updates = _prompt_postgresql_updates(connection)
        elif connection.database_type == "mysql":
            updates = _prompt_mysql_updates(connection)
        elif connection.database_type == "sqlite":
            updates = _prompt_sqlite_updates(connection)
        
        if not updates:
            print("\nNo changes made.")
            return
        
        # Confirm update
        print("\nUpdating connection...", end=" ", flush=True)
        result = manager.update_connection(connection.name, updates)
        
        if is_ok(result):
            print("Done!")
            print(f"\n✓ Connection '{connection.name}' updated successfully.")
            
            # Notify about agents using this connection
            agents_using = manager.get_agents_using_connection(connection.name)
            if agents_using:
                print(f"\nNote: The following agents will use the updated connection:")
                for agent in agents_using:
                    print(f"  - {agent}")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")
            
    except KeyboardInterrupt:
        print("\n\nUpdate cancelled.")


def delete_connection_flow(manager: DatabaseConnectionManager) -> None:
    """Interactive flow for deleting a connection.
    
    This function guides the user through deleting a connection:
    1. Lists available connections
    2. User selects connection to delete
    3. Checks if connection is in use by any agents
    4. If in use, prevents deletion and shows which agents use it
    5. If not in use, confirms deletion with user
    6. Deletes the connection
    
    Args:
        manager: DatabaseConnectionManager instance
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> delete_connection_flow(manager)
        
        Delete Database Connection
        ========================================
        
        Available connections:
          1. prod-oracle (oracle)
          2. old-connection (postgresql)
          0. Cancel
        
        Select connection to delete: 2
        
        Are you sure you want to delete 'old-connection'? (y/N): y
        Deleting connection... Done!
    """
    print("\n" + "=" * 40)
    print("Delete Database Connection")
    print("=" * 40)
    
    # Select connection to delete
    connection = _select_connection(manager, "Select connection to delete")
    if connection is None:
        return
    
    # Check if connection is in use
    agents_using = manager.get_agents_using_connection(connection.name)
    
    if agents_using:
        print(f"\nError: Cannot delete connection '{connection.name}'.")
        print("The following agents are using this connection:")
        for agent in agents_using:
            print(f"  - {agent}")
        print("\nRemove the connection from these agents first.")
        return
    
    # Confirm deletion
    confirm = input(f"\nAre you sure you want to delete '{connection.name}'? (y/N): ").strip()
    
    if confirm.lower() != "y":
        print("\nDeletion cancelled.")
        return
    
    # Delete the connection
    print("\nDeleting connection...", end=" ", flush=True)
    result = manager.delete_connection(connection.name)
    
    if is_ok(result):
        print("Done!")
        print(f"\n✓ Connection '{connection.name}' deleted successfully.")
    else:
        print("Failed!")
        error = unwrap_err(result)
        print(f"\nError: {error}")


# Helper functions

def _select_database_type() -> Optional[str]:
    """Prompt for database type selection.
    
    Returns:
        Selected database type string, or None to cancel.
    """
    print("\nDatabase types:")
    print("  1. Oracle")
    print("  2. PostgreSQL")
    print("  3. MySQL")
    print("  4. SQLite")
    print("  0. Cancel")
    print()
    
    try:
        choice = input("Select database type: ").strip()
        
        if choice == "0":
            return None
        elif choice == "1":
            return "oracle"
        elif choice == "2":
            return "postgresql"
        elif choice == "3":
            return "mysql"
        elif choice == "4":
            return "sqlite"
        else:
            print("\nInvalid selection.")
            return None
    except ValueError:
        print("\nInvalid input.")
        return None


def _select_connection(
    manager: DatabaseConnectionManager,
    prompt: str = "Select connection"
) -> Optional[DatabaseConnection]:
    """Display connection list and let user select one.
    
    Args:
        manager: DatabaseConnectionManager instance
        prompt: The prompt to display
        
    Returns:
        Selected DatabaseConnection or None if cancelled
    """
    connections = manager.list_connections()
    
    if not connections:
        print("\nNo connections available. Create one first!")
        return None
    
    print("\nAvailable connections:")
    for i, conn in enumerate(connections, 1):
        print(f"  {i}. {conn.name} ({conn.database_type})")
    
    print("  0. Cancel")
    print()
    
    try:
        choice = input(f"{prompt} (number): ").strip()
        idx = int(choice)
        
        if idx == 0:
            return None
        
        if 1 <= idx <= len(connections):
            return connections[idx - 1]
        
        print("\nInvalid selection.")
        return None
        
    except ValueError:
        print("\nInvalid input.")
        return None


def _configure_oracle_connection(name: str) -> Optional[DatabaseConnection]:
    """Configure Oracle database connection parameters.
    
    Args:
        name: Connection name
        
    Returns:
        DatabaseConnection object or None if cancelled
    """
    print("\n--- Oracle Database Configuration ---")
    
    host = input("Host [localhost]: ").strip() or "localhost"
    
    port_input = input("Port [1521]: ").strip()
    try:
        port = int(port_input) if port_input else 1521
    except ValueError:
        print("\nError: Invalid port number.")
        return None
    
    service_name = input("Service name: ").strip()
    if not service_name:
        print("\nError: Service name is required.")
        return None
    
    username = input("Username: ").strip()
    if not username:
        print("\nError: Username is required.")
        return None
    
    password = getpass("Password: ")
    if not password:
        print("\nError: Password is required.")
        return None
    
    return DatabaseConnection(
        name=name,
        database_type="oracle",
        host=host,
        port=port,
        service_name=service_name,
        username=username,
        password=password
    )


def _configure_postgresql_connection(name: str) -> Optional[DatabaseConnection]:
    """Configure PostgreSQL database connection parameters.
    
    Args:
        name: Connection name
        
    Returns:
        DatabaseConnection object or None if cancelled
    """
    print("\n--- PostgreSQL Database Configuration ---")
    
    host = input("Host [localhost]: ").strip() or "localhost"
    
    port_input = input("Port [5432]: ").strip()
    try:
        port = int(port_input) if port_input else 5432
    except ValueError:
        print("\nError: Invalid port number.")
        return None
    
    database = input("Database name: ").strip()
    if not database:
        print("\nError: Database name is required.")
        return None
    
    username = input("Username: ").strip()
    if not username:
        print("\nError: Username is required.")
        return None
    
    password = getpass("Password: ")
    if not password:
        print("\nError: Password is required.")
        return None
    
    return DatabaseConnection(
        name=name,
        database_type="postgresql",
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )


def _configure_mysql_connection(name: str) -> Optional[DatabaseConnection]:
    """Configure MySQL database connection parameters.
    
    Args:
        name: Connection name
        
    Returns:
        DatabaseConnection object or None if cancelled
    """
    print("\n--- MySQL Database Configuration ---")
    
    host = input("Host [localhost]: ").strip() or "localhost"
    
    port_input = input("Port [3306]: ").strip()
    try:
        port = int(port_input) if port_input else 3306
    except ValueError:
        print("\nError: Invalid port number.")
        return None
    
    database = input("Database name: ").strip()
    if not database:
        print("\nError: Database name is required.")
        return None
    
    username = input("Username: ").strip()
    if not username:
        print("\nError: Username is required.")
        return None
    
    password = getpass("Password: ")
    if not password:
        print("\nError: Password is required.")
        return None
    
    return DatabaseConnection(
        name=name,
        database_type="mysql",
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )


def _configure_sqlite_connection(name: str) -> Optional[DatabaseConnection]:
    """Configure SQLite database connection parameters.
    
    Args:
        name: Connection name
        
    Returns:
        DatabaseConnection object or None if cancelled
    """
    print("\n--- SQLite Database Configuration ---")
    
    file_path = input("Database file path: ").strip()
    if not file_path:
        print("\nError: File path is required.")
        return None
    
    return DatabaseConnection(
        name=name,
        database_type="sqlite",
        file_path=file_path
    )


def _prompt_oracle_updates(connection: DatabaseConnection) -> dict:
    """Prompt for Oracle connection updates.
    
    Args:
        connection: Existing connection to update
        
    Returns:
        Dictionary of updates
    """
    updates = {}
    
    print(f"\nCurrent host: {connection.host}")
    host = input("New host (blank to keep): ").strip()
    if host:
        updates["host"] = host
    
    print(f"Current port: {connection.port}")
    port_input = input("New port (blank to keep): ").strip()
    if port_input:
        try:
            updates["port"] = int(port_input)
        except ValueError:
            print("Warning: Invalid port number, keeping current value.")
    
    print(f"Current service name: {connection.service_name}")
    service_name = input("New service name (blank to keep): ").strip()
    if service_name:
        updates["service_name"] = service_name
    
    print(f"Current username: {connection.username}")
    username = input("New username (blank to keep): ").strip()
    if username:
        updates["username"] = username
    
    change_password = input("Change password? (y/N): ").strip().lower()
    if change_password == "y":
        password = getpass("New password: ")
        if password:
            updates["password"] = password
    
    return updates


def _prompt_postgresql_updates(connection: DatabaseConnection) -> dict:
    """Prompt for PostgreSQL connection updates.
    
    Args:
        connection: Existing connection to update
        
    Returns:
        Dictionary of updates
    """
    updates = {}
    
    print(f"\nCurrent host: {connection.host}")
    host = input("New host (blank to keep): ").strip()
    if host:
        updates["host"] = host
    
    print(f"Current port: {connection.port}")
    port_input = input("New port (blank to keep): ").strip()
    if port_input:
        try:
            updates["port"] = int(port_input)
        except ValueError:
            print("Warning: Invalid port number, keeping current value.")
    
    print(f"Current database: {connection.database}")
    database = input("New database (blank to keep): ").strip()
    if database:
        updates["database"] = database
    
    print(f"Current username: {connection.username}")
    username = input("New username (blank to keep): ").strip()
    if username:
        updates["username"] = username
    
    change_password = input("Change password? (y/N): ").strip().lower()
    if change_password == "y":
        password = getpass("New password: ")
        if password:
            updates["password"] = password
    
    return updates


def _prompt_mysql_updates(connection: DatabaseConnection) -> dict:
    """Prompt for MySQL connection updates.
    
    Args:
        connection: Existing connection to update
        
    Returns:
        Dictionary of updates
    """
    updates = {}
    
    print(f"\nCurrent host: {connection.host}")
    host = input("New host (blank to keep): ").strip()
    if host:
        updates["host"] = host
    
    print(f"Current port: {connection.port}")
    port_input = input("New port (blank to keep): ").strip()
    if port_input:
        try:
            updates["port"] = int(port_input)
        except ValueError:
            print("Warning: Invalid port number, keeping current value.")
    
    print(f"Current database: {connection.database}")
    database = input("New database (blank to keep): ").strip()
    if database:
        updates["database"] = database
    
    print(f"Current username: {connection.username}")
    username = input("New username (blank to keep): ").strip()
    if username:
        updates["username"] = username
    
    change_password = input("Change password? (y/N): ").strip().lower()
    if change_password == "y":
        password = getpass("New password: ")
        if password:
            updates["password"] = password
    
    return updates


def _prompt_sqlite_updates(connection: DatabaseConnection) -> dict:
    """Prompt for SQLite connection updates.
    
    Args:
        connection: Existing connection to update
        
    Returns:
        Dictionary of updates
    """
    updates = {}
    
    print(f"\nCurrent file path: {connection.file_path}")
    file_path = input("New file path (blank to keep): ").strip()
    if file_path:
        updates["file_path"] = file_path
    
    return updates
