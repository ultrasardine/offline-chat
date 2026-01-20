"""CLI module for agent update operations.

This module provides interactive command-line functions for updating
existing agents, including managing database connections with access
control and guidelines management.

The CLI provides:
1. Agent selection for updates
2. Database connection management with access levels
3. Access level selection (read-only, read-write, table-specific)
4. Table selection for table-specific access
5. Display of current and available connections

Usage Example:
    >>> from cli.agent_update_menu import show_update_agent_menu
    >>> from offline_chat.manager import AgentManager
    >>> from offline_chat.database.manager import DatabaseConnectionManager
    >>>
    >>> agent_manager = AgentManager(db_manager=db_conn_manager)
    >>> db_manager = DatabaseConnectionManager()
    >>> show_update_agent_menu(agent_manager, db_manager)
"""

from typing import Optional

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_ok, unwrap, unwrap_err
from offline_chat.manager import AgentManager


def show_update_agent_menu(
    agent_manager: AgentManager,
    db_manager: DatabaseConnectionManager
) -> None:
    """Display agent update menu and handle agent selection.
    
    This is the main entry point for updating agents. It displays a list
    of available agents and allows the user to select one for updates.
    After selection, it shows update options including database connections.
    
    Args:
        agent_manager: AgentManager instance for agent operations
        db_manager: DatabaseConnectionManager instance for connection operations
        
    Example:
        >>> agent_manager = AgentManager(db_manager=db_conn_manager)
        >>> db_manager = DatabaseConnectionManager()
        >>> show_update_agent_menu(agent_manager, db_manager)
        
        Update Agent
        ========================================
        
        Available agents:
          1. data-analyst (Data Analyst)
          2. code-reviewer (Code Reviewer)
          0. Cancel
        
        Select agent to update: 1
        
        Update Options for: data-analyst
        ----------------------------------------
          1. Update database connections
          2. Back to main menu
    """
    while True:
        print("\n" + "=" * 40)
        print("Update Agent")
        print("=" * 40)
        
        # Get list of agents
        agents = agent_manager.list_agents()
        
        if not agents:
            print("\nNo agents available. Create one first!")
            return
        
        # Display agent list
        print("\nAvailable agents:")
        for i, agent in enumerate(agents, 1):
            print(f"  {i}. {agent.name} ({agent.display_name})")
        print("  0. Cancel")
        print()
        
        try:
            choice = input("Select agent to update: ").strip()
            
            if choice == "0":
                return
            
            try:
                idx = int(choice)
                if 1 <= idx <= len(agents):
                    selected_agent = agents[idx - 1]
                    _show_agent_update_options(
                        agent_manager,
                        db_manager,
                        selected_agent.name
                    )
                else:
                    print("\nInvalid selection. Please try again.")
            except ValueError:
                print("\nInvalid input. Please enter a number.")
                
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
            return


def _show_agent_update_options(
    agent_manager: AgentManager,
    db_manager: DatabaseConnectionManager,
    agent_name: str
) -> None:
    """Display update options for a specific agent.
    
    Args:
        agent_manager: AgentManager instance
        db_manager: DatabaseConnectionManager instance
        agent_name: Name of the agent to update
    """
    # Import guidelines menu here to avoid circular imports
    from guidelines_menu import show_guidelines_menu
    
    while True:
        print("\n" + "-" * 40)
        print(f"Update Options for: {agent_name}")
        print("-" * 40)
        print("  1. Update base model")
        print("  2. Update database connections")
        print("  3. Manage guidelines")
        print("  4. Back to agent selection")
        print()
        
        try:
            choice = input("Select option: ").strip()
            
            if choice == "1":
                update_base_model_flow(agent_manager, agent_name)
            elif choice == "2":
                update_database_connections_flow(agent_manager, db_manager, agent_name)
            elif choice == "3":
                show_guidelines_menu(agent_manager, agent_name)
            elif choice == "4":
                break
            else:
                print("\nInvalid option. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nReturning to agent selection...")
            break


def update_base_model_flow(
    agent_manager: AgentManager,
    agent_name: str
) -> None:
    """Interactive flow for updating an agent's base model.
    
    This function guides the user through changing the Ollama base model
    for an agent. It displays the current model, prompts for a new model,
    and updates both the agent configuration and regenerates the Ollama model.
    
    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent to update
        
    Example:
        >>> update_base_model_flow(agent_manager, "db-analyst")
        
        Update Base Model: db-analyst
        ========================================
        
        Current base model: llama3.1:latest
        
        Recommended models for tool calling:
          - llama3.2:latest (recommended)
          - mistral:latest (fast alternative)
          - qwen2.5:latest (best for tools)
        
        Enter new base model (or 'cancel' to abort): llama3.2:latest
        
        Updating base model... Done!
        Regenerating Ollama model... Done!
        
        ✓ Base model updated successfully.
    """
    print("\n" + "=" * 40)
    print(f"Update Base Model: {agent_name}")
    print("=" * 40)
    
    # Get agent
    agent = agent_manager.get_agent(agent_name)
    if agent is None:
        print(f"\nError: Agent '{agent_name}' not found.")
        return
    
    # Display current model
    print(f"\nCurrent base model: {agent.base_model}")
    
    # Show recommendations
    print("\nRecommended models for tool calling:")
    print("  - llama3.2:latest (recommended)")
    print("  - mistral:latest (fast alternative)")
    print("  - qwen2.5:latest (best for tools)")
    print("\nOther options:")
    print("  - llama3.1:latest (current, limited tool support)")
    print("  - llama3:latest (older version)")
    print()
    
    try:
        new_model = input("Enter new base model (or 'cancel' to abort): ").strip()
        
        if new_model.lower() == "cancel" or not new_model:
            print("\nUpdate cancelled.")
            return
        
        # Confirm the change
        print(f"\nChange base model from '{agent.base_model}' to '{new_model}'?")
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm != "y":
            print("\nUpdate cancelled.")
            return
        
        # Update the base model
        print("\nUpdating base model...", end=" ", flush=True)
        result = agent_manager.update_agent(agent_name, {"base_model": new_model})
        
        if is_ok(result):
            print("Done!")
            print(f"\n✓ Base model updated to '{new_model}' successfully.")
            print("\nNote: The agent will use the new model in the next chat session.")
            
            # Check if model exists in Ollama
            print("\nTip: Make sure the model is available in Ollama:")
            print(f"  ollama pull {new_model}")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")
            
    except KeyboardInterrupt:
        print("\n\nUpdate cancelled.")


def update_database_connections_flow(
    agent_manager: AgentManager,
    db_manager: DatabaseConnectionManager,
    agent_name: str
) -> None:
    """Interactive flow for updating agent database connections.
    
    This function guides the user through managing database connections
    for an agent:
    1. Displays currently assigned connections with access levels
    2. Displays available connections for assignment
    3. Allows adding connections with access level selection
    4. Allows removing connections
    
    Args:
        agent_manager: AgentManager instance
        db_manager: DatabaseConnectionManager instance
        agent_name: Name of the agent to update
        
    Example:
        >>> update_database_connections_flow(agent_manager, db_manager, "data-analyst")
        
        Manage Database Connections: data-analyst
        ========================================
        
        Currently Assigned Connections:
          1. prod-oracle (read-only)
          2. dev-postgres (table-specific-read-write: users, orders)
        
        Available Connections:
          3. staging-mysql (mysql)
          4. local-sqlite (sqlite)
        
        Options:
          a. Add connection
          r. Remove connection
          b. Back
        
        Select option: a
    """
    while True:
        print("\n" + "=" * 40)
        print(f"Manage Database Connections: {agent_name}")
        print("=" * 40)
        
        # Get agent
        agent = agent_manager.get_agent(agent_name)
        if agent is None:
            print(f"\nError: Agent '{agent_name}' not found.")
            return
        
        # Display currently assigned connections
        print("\nCurrently Assigned Connections:")
        if agent.connection_assignments:
            for i, assignment in enumerate(agent.connection_assignments, 1):
                access_info = assignment.access_level.value
                if assignment.allowed_tables:
                    tables_str = ", ".join(assignment.allowed_tables)
                    access_info = f"{access_info}: {tables_str}"
                print(f"  {i}. {assignment.connection_name} ({access_info})")
        else:
            print("  (none)")
        
        # Get all available connections
        all_connections = db_manager.list_connections()
        assigned_names = {a.connection_name for a in agent.connection_assignments}
        available_connections = [
            conn for conn in all_connections
            if conn.name not in assigned_names
        ]
        
        # Display available connections
        print("\nAvailable Connections:")
        if available_connections:
            start_idx = len(agent.connection_assignments) + 1
            for i, conn in enumerate(available_connections, start_idx):
                print(f"  {i}. {conn.name} ({conn.database_type})")
        else:
            print("  (none)")
        
        # Display options
        print("\nOptions:")
        print("  a. Add connection")
        if agent.connection_assignments:
            print("  r. Remove connection")
        print("  b. Back")
        print()
        
        try:
            choice = input("Select option: ").strip().lower()
            
            if choice == "a":
                if not available_connections:
                    print("\nNo available connections to add.")
                    print("All connections are already assigned to this agent.")
                    continue
                _add_connection_flow(
                    agent_manager,
                    db_manager,
                    agent_name,
                    available_connections
                )
            elif choice == "r":
                if not agent.connection_assignments:
                    print("\nNo connections to remove.")
                    continue
                _remove_connection_flow(agent_manager, agent_name, agent.connection_assignments)
            elif choice == "b":
                break
            else:
                print("\nInvalid option. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nReturning to update options...")
            break


def _add_connection_flow(
    agent_manager: AgentManager,
    db_manager: DatabaseConnectionManager,
    agent_name: str,
    available_connections: list
) -> None:
    """Flow for adding a connection to an agent.
    
    Args:
        agent_manager: AgentManager instance
        db_manager: DatabaseConnectionManager instance
        agent_name: Name of the agent
        available_connections: List of available DatabaseConnection objects
    """
    print("\n--- Add Database Connection ---")
    print("\nAvailable connections:")
    for i, conn in enumerate(available_connections, 1):
        print(f"  {i}. {conn.name} ({conn.database_type})")
    print("  0. Cancel")
    print()
    
    try:
        choice = input("Select connection to add: ").strip()
        
        if choice == "0":
            return
        
        idx = int(choice)
        if not (1 <= idx <= len(available_connections)):
            print("\nInvalid selection.")
            return
        
        selected_connection = available_connections[idx - 1]
        
        # Select access level
        access_level = select_access_level()
        if access_level is None:
            print("\nConnection addition cancelled.")
            return
        
        # Select allowed tables if table-specific access
        allowed_tables = None
        if access_level in (
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ):
            allowed_tables = select_allowed_tables(db_manager, selected_connection.name)
            if allowed_tables is None:
                print("\nConnection addition cancelled.")
                return
        
        # Assign the connection
        print("\nAssigning connection...", end=" ", flush=True)
        result = agent_manager.assign_connection(
            agent_name,
            selected_connection.name,
            access_level,
            allowed_tables
        )
        
        if is_ok(result):
            print("Done!")
            print(f"\n✓ Connection '{selected_connection.name}' assigned successfully.")
            if allowed_tables:
                print(f"  Access level: {access_level.value}")
                print(f"  Allowed tables: {', '.join(allowed_tables)}")
            else:
                print(f"  Access level: {access_level.value}")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")
            
    except ValueError:
        print("\nInvalid input.")
    except KeyboardInterrupt:
        print("\n\nConnection addition cancelled.")


def _remove_connection_flow(
    agent_manager: AgentManager,
    agent_name: str,
    connection_assignments: list
) -> None:
    """Flow for removing a connection from an agent.
    
    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent
        connection_assignments: List of AgentConnectionAssignment objects
    """
    print("\n--- Remove Database Connection ---")
    print("\nCurrently assigned connections:")
    for i, assignment in enumerate(connection_assignments, 1):
        access_info = assignment.access_level.value
        if assignment.allowed_tables:
            tables_str = ", ".join(assignment.allowed_tables)
            access_info = f"{access_info}: {tables_str}"
        print(f"  {i}. {assignment.connection_name} ({access_info})")
    print("  0. Cancel")
    print()
    
    try:
        choice = input("Select connection to remove: ").strip()
        
        if choice == "0":
            return
        
        idx = int(choice)
        if not (1 <= idx <= len(connection_assignments)):
            print("\nInvalid selection.")
            return
        
        selected_assignment = connection_assignments[idx - 1]
        
        # Confirm removal
        confirm = input(
            f"\nRemove connection '{selected_assignment.connection_name}'? (y/N): "
        ).strip().lower()
        
        if confirm != "y":
            print("\nRemoval cancelled.")
            return
        
        # Remove the connection
        print("\nRemoving connection...", end=" ", flush=True)
        result = agent_manager.remove_connection(agent_name, selected_assignment.connection_name)
        
        if is_ok(result):
            print("Done!")
            print(f"\n✓ Connection '{selected_assignment.connection_name}' removed successfully.")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")
            
    except ValueError:
        print("\nInvalid input.")
    except KeyboardInterrupt:
        print("\n\nConnection removal cancelled.")


def select_access_level() -> Optional[AccessLevel]:
    """Prompt user to select an access level.
    
    Displays a menu of available access levels and returns the user's
    selection. Returns None if the user cancels.
    
    Returns:
        Selected AccessLevel or None if cancelled
        
    Example:
        >>> access_level = select_access_level()
        
        Select Access Level
        ----------------------------------------
          1. read-only (SELECT queries only)
          2. read-write (SELECT, INSERT, UPDATE, DELETE)
          3. table-specific-read (SELECT on specific tables)
          4. table-specific-read-write (All operations on specific tables)
          0. Cancel
        
        Select access level: 1
    """
    print("\n" + "-" * 40)
    print("Select Access Level")
    print("-" * 40)
    print("  1. read-only (SELECT queries only)")
    print("  2. read-write (SELECT, INSERT, UPDATE, DELETE)")
    print("  3. table-specific-read (SELECT on specific tables)")
    print("  4. table-specific-read-write (All operations on specific tables)")
    print("  0. Cancel")
    print()
    
    try:
        choice = input("Select access level: ").strip()
        
        if choice == "0":
            return None
        elif choice == "1":
            return AccessLevel.READ_ONLY
        elif choice == "2":
            return AccessLevel.READ_WRITE
        elif choice == "3":
            return AccessLevel.TABLE_SPECIFIC_READ
        elif choice == "4":
            return AccessLevel.TABLE_SPECIFIC_READ_WRITE
        else:
            print("\nInvalid selection.")
            return None
            
    except ValueError:
        print("\nInvalid input.")
        return None


def select_allowed_tables(
    db_manager: DatabaseConnectionManager,
    connection_name: str
) -> Optional[list[str]]:
    """Prompt user to enter allowed tables for table-specific access.
    
    For table-specific access levels, this function prompts the user to
    enter a comma-separated list of table names that the agent is allowed
    to access.
    
    Args:
        db_manager: DatabaseConnectionManager instance (for future table discovery)
        connection_name: Name of the connection (for future table discovery)
        
    Returns:
        List of table names or None if cancelled
        
    Example:
        >>> tables = select_allowed_tables(db_manager, "prod-db")
        
        Specify Allowed Tables
        ----------------------------------------
        Enter table names (comma-separated): users, orders, products
        
        Allowed tables: users, orders, products
    """
    print("\n" + "-" * 40)
    print("Specify Allowed Tables")
    print("-" * 40)
    print("Enter table names separated by commas.")
    print("Example: users, orders, products")
    print()
    
    try:
        tables_input = input("Enter table names (comma-separated): ").strip()
        
        if not tables_input:
            print("\nError: At least one table name is required.")
            return None
        
        # Parse and clean table names
        tables = [t.strip() for t in tables_input.split(",")]
        tables = [t for t in tables if t]  # Remove empty strings
        
        if not tables:
            print("\nError: At least one table name is required.")
            return None
        
        # Display confirmation
        print(f"\nAllowed tables: {', '.join(tables)}")
        
        return tables
        
    except KeyboardInterrupt:
        print("\n\nTable selection cancelled.")
        return None
