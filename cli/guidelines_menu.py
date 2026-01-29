"""CLI module for agent guidelines management.

This module provides interactive command-line functions for managing
agent guidelines. Guidelines are behavioral rules that are added to
the agent's system prompt.

The CLI provides:
1. Add new guidelines
2. Edit existing guidelines
3. Delete guidelines
4. List all guidelines with indices

Usage Example:
    >>> from cli.guidelines_menu import show_guidelines_menu
    >>> from offline_chat.manager import AgentManager
    >>>
    >>> agent_manager = AgentManager()
    >>> show_guidelines_menu(agent_manager, "data-analyst")
"""

from offline_chat.database.result import is_ok, unwrap, unwrap_err
from offline_chat.manager import AgentManager


def show_guidelines_menu(agent_manager: AgentManager, agent_name: str) -> None:
    """Display guidelines management menu for an agent.

    This is the main entry point for managing agent guidelines. It displays
    a menu with options to add, edit, delete, list guidelines, or go back.

    Args:
        agent_manager: AgentManager instance for agent operations
        agent_name: Name of the agent to manage guidelines for

    Example:
        >>> agent_manager = AgentManager()
        >>> show_guidelines_menu(agent_manager, "data-analyst")

        Manage Guidelines: data-analyst
        ========================================

        Options:
          1. Add guideline
          2. Edit guideline
          3. Delete guideline
          4. List guidelines
          5. Back

        Select option: _
    """
    while True:
        print("\n" + "=" * 40)
        print(f"Manage Guidelines: {agent_name}")
        print("=" * 40)
        print("\nOptions:")
        print("  1. Add guideline")
        print("  2. Edit guideline")
        print("  3. Delete guideline")
        print("  4. List guidelines")
        print("  5. Back")
        print()

        try:
            choice = input("Select option: ").strip()

            if choice == "1":
                add_guideline_flow(agent_manager, agent_name)
            elif choice == "2":
                edit_guideline_flow(agent_manager, agent_name)
            elif choice == "3":
                delete_guideline_flow(agent_manager, agent_name)
            elif choice == "4":
                list_guidelines_display(agent_manager, agent_name)
            elif choice == "5":
                break
            else:
                print("\nInvalid option. Please try again.")

        except KeyboardInterrupt:
            print("\n\nReturning to previous menu...")
            break


def add_guideline_flow(agent_manager: AgentManager, agent_name: str) -> None:
    """Interactive flow for adding a guideline to an agent.

    This function prompts the user to enter guideline text and adds it
    to the agent's guidelines list.

    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent to add guideline to

    Example:
        >>> add_guideline_flow(agent_manager, "data-analyst")

        --- Add Guideline ---

        Enter guideline text (or press Enter to cancel):
        > Always explain your SQL queries before executing them

        Adding guideline... Done!

        ✓ Guideline added successfully.
    """
    print("\n--- Add Guideline ---")
    print("\nEnter guideline text (or press Enter to cancel):")

    try:
        guideline_text = input("> ").strip()

        if not guideline_text:
            print("\nGuideline addition cancelled.")
            return

        # Add the guideline
        print("\nAdding guideline...", end=" ", flush=True)
        result = agent_manager.add_guideline(agent_name, guideline_text)

        if is_ok(result):
            print("Done!")
            print("\n✓ Guideline added successfully.")
        else:
            print("Failed!")
            error = unwrap_err(result)
            print(f"\nError: {error}")

    except KeyboardInterrupt:
        print("\n\nGuideline addition cancelled.")


def edit_guideline_flow(agent_manager: AgentManager, agent_name: str) -> None:
    """Interactive flow for editing an existing guideline.

    This function displays the current guidelines, prompts the user to
    select one by index, and allows them to modify the text.

    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent to edit guideline for

    Example:
        >>> edit_guideline_flow(agent_manager, "data-analyst")

        --- Edit Guideline ---

        Current Guidelines:
          1. Always explain your SQL queries
          2. Never modify production data

        Select guideline to edit (or 0 to cancel): 1

        Current text: Always explain your SQL queries

        Enter new text (or press Enter to cancel):
        > Always provide detailed explanations for SQL queries

        Updating guideline... Done!

        ✓ Guideline updated successfully.
    """
    print("\n--- Edit Guideline ---")

    # Get current guidelines
    result = agent_manager.list_guidelines(agent_name)
    if not is_ok(result):
        error = unwrap_err(result)
        print(f"\nError: {error}")
        return

    guidelines = unwrap(result)

    if not guidelines:
        print("\nNo guidelines to edit. Add some first!")
        return

    # Display guidelines
    print("\nCurrent Guidelines:")
    for i, guideline in enumerate(guidelines, 1):
        print(f"  {i}. {guideline}")
    print()

    try:
        choice = input("Select guideline to edit (or 0 to cancel): ").strip()

        if choice == "0":
            print("\nEdit cancelled.")
            return

        try:
            idx = int(choice)
            if not (1 <= idx <= len(guidelines)):
                print("\nInvalid selection.")
                return

            # Convert to 0-based index
            guideline_index = idx - 1

            # Show current text
            print(f"\nCurrent text: {guidelines[guideline_index]}")
            print("\nEnter new text (or press Enter to cancel):")

            new_text = input("> ").strip()

            if not new_text:
                print("\nEdit cancelled.")
                return

            # Update the guideline
            print("\nUpdating guideline...", end=" ", flush=True)
            result = agent_manager.edit_guideline(agent_name, guideline_index, new_text)

            if is_ok(result):
                print("Done!")
                print("\n✓ Guideline updated successfully.")
            else:
                print("Failed!")
                error = unwrap_err(result)
                print(f"\nError: {error}")

        except ValueError:
            print("\nInvalid input. Please enter a number.")

    except KeyboardInterrupt:
        print("\n\nEdit cancelled.")


def delete_guideline_flow(agent_manager: AgentManager, agent_name: str) -> None:
    """Interactive flow for deleting a guideline from an agent.

    This function displays the current guidelines, prompts the user to
    select one by index, confirms the deletion, and removes it.

    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent to delete guideline from

    Example:
        >>> delete_guideline_flow(agent_manager, "data-analyst")

        --- Delete Guideline ---

        Current Guidelines:
          1. Always explain your SQL queries
          2. Never modify production data

        Select guideline to delete (or 0 to cancel): 2

        Delete guideline: "Never modify production data"? (y/N): y

        Deleting guideline... Done!

        ✓ Guideline deleted successfully.
    """
    print("\n--- Delete Guideline ---")

    # Get current guidelines
    result = agent_manager.list_guidelines(agent_name)
    if not is_ok(result):
        error = unwrap_err(result)
        print(f"\nError: {error}")
        return

    guidelines = unwrap(result)

    if not guidelines:
        print("\nNo guidelines to delete.")
        return

    # Display guidelines
    print("\nCurrent Guidelines:")
    for i, guideline in enumerate(guidelines, 1):
        print(f"  {i}. {guideline}")
    print()

    try:
        choice = input("Select guideline to delete (or 0 to cancel): ").strip()

        if choice == "0":
            print("\nDeletion cancelled.")
            return

        try:
            idx = int(choice)
            if not (1 <= idx <= len(guidelines)):
                print("\nInvalid selection.")
                return

            # Convert to 0-based index
            guideline_index = idx - 1

            # Confirm deletion
            guideline_text = guidelines[guideline_index]
            confirm = input(f'\nDelete guideline: "{guideline_text}"? (y/N): ').strip().lower()

            if confirm != "y":
                print("\nDeletion cancelled.")
                return

            # Delete the guideline
            print("\nDeleting guideline...", end=" ", flush=True)
            result = agent_manager.delete_guideline(agent_name, guideline_index)

            if is_ok(result):
                print("Done!")
                print("\n✓ Guideline deleted successfully.")
            else:
                print("Failed!")
                error = unwrap_err(result)
                print(f"\nError: {error}")

        except ValueError:
            print("\nInvalid input. Please enter a number.")

    except KeyboardInterrupt:
        print("\n\nDeletion cancelled.")


def list_guidelines_display(agent_manager: AgentManager, agent_name: str) -> None:
    """Display all guidelines for an agent with indices.

    This function retrieves and displays all guidelines for the specified
    agent, numbered with 1-based indices for user reference.

    Args:
        agent_manager: AgentManager instance
        agent_name: Name of the agent to list guidelines for

    Example:
        >>> list_guidelines_display(agent_manager, "data-analyst")

        Guidelines for: data-analyst
        ----------------------------------------

        1. Always explain your SQL queries before executing them
        2. Never modify production data without explicit confirmation
        3. Provide data visualizations when appropriate

        Total: 3 guideline(s)
    """
    print("\n" + "-" * 40)
    print(f"Guidelines for: {agent_name}")
    print("-" * 40)

    # Get guidelines
    result = agent_manager.list_guidelines(agent_name)
    if not is_ok(result):
        error = unwrap_err(result)
        print(f"\nError: {error}")
        return

    guidelines = unwrap(result)

    if not guidelines:
        print("\nNo guidelines defined for this agent.")
        return

    # Display guidelines
    print()
    for i, guideline in enumerate(guidelines, 1):
        print(f"{i}. {guideline}")

    print(f"\nTotal: {len(guidelines)} guideline(s)")
