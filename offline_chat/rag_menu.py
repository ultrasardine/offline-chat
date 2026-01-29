"""RAG management menu for Offline Chat application.

This module provides the RAG management interface for adding, re-indexing,
and listing knowledge sources for agents.
"""

from offline_chat.database.result import is_err, is_ok, unwrap, unwrap_err
from offline_chat.manager import AgentManager


def show_rag_menu(manager: AgentManager) -> None:
    """Display RAG management menu and handle user interactions.

    This menu allows users to:
    - Add knowledge sources to agents
    - Re-index existing knowledge sources
    - List knowledge sources for agents

    Args:
        manager: AgentManager instance for agent operations
    """
    while True:
        print("\n" + "=" * 40)
        print("RAG Knowledge Source Management")
        print("=" * 40)
        print("\n  1. Add knowledge source to agent")
        print("  2. Re-index knowledge source")
        print("  3. List knowledge sources for agent")
        print("  0. Back to main menu")
        print()

        try:
            choice = input("Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                _add_knowledge_source_flow(manager)
            elif choice == "2":
                _reindex_knowledge_source_flow(manager)
            elif choice == "3":
                _list_knowledge_sources_flow(manager)
            else:
                print("\nInvalid option. Please try again.")

        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
            break


def _add_knowledge_source_flow(manager: AgentManager) -> None:
    """Handle adding a knowledge source to an agent.

    Args:
        manager: AgentManager instance
    """
    print("\n" + "-" * 40)
    print("Add Knowledge Source")
    print("-" * 40)

    # List agents with RAG enabled
    agents = manager.list_agents()
    rag_agents = [agent for agent in agents if agent.rag_config and agent.rag_config.enabled]

    if not rag_agents:
        print("\nNo agents with RAG enabled found.")
        print("Create an agent with RAG enabled first.")
        return

    # Select agent
    print("\nAgents with RAG enabled:")
    for i, agent in enumerate(rag_agents, 1):
        print(f"  {i}. {agent.display_name} ({agent.name})")
    print("  0. Cancel")
    print()

    try:
        choice = input("Select agent: ").strip()
        idx = int(choice)

        if idx == 0:
            return

        if not (1 <= idx <= len(rag_agents)):
            print("\nInvalid selection.")
            return

        agent = rag_agents[idx - 1]

    except ValueError:
        print("\nInvalid input.")
        return

    # Select source type
    print("\nSource type:")
    print("  1. Web URL")
    print("  2. Database table")
    print("  0. Cancel")
    print()

    try:
        choice = input("Select source type: ").strip()

        if choice == "0":
            return
        elif choice == "1":
            source_type = "web"
        elif choice == "2":
            source_type = "database"
        else:
            print("\nInvalid selection.")
            return

    except ValueError:
        print("\nInvalid input.")
        return

    # Get identifier
    if source_type == "web":
        identifier = input("\nEnter URL: ").strip()
        if not identifier:
            print("\nURL cannot be empty.")
            return
    else:  # database
        identifier = input("\nEnter table name: ").strip()
        if not identifier:
            print("\nTable name cannot be empty.")
            return

    # Confirm ingestion
    ingest_input = input("\nIngest immediately? (Y/n): ").strip()
    ingest = ingest_input.lower() != "n"

    # Progress callback
    def progress_callback(message: str) -> None:
        print(f"  {message}")

    # Add knowledge source
    print()
    result = manager.add_knowledge_source(
        agent_name=agent.name,
        source_type=source_type,
        identifier=identifier,
        ingest=ingest,
        progress_callback=progress_callback if ingest else None,
    )

    if is_ok(result):
        if ingest:
            print("\nKnowledge source added and ingested successfully!")
        else:
            print("\nKnowledge source added. Run re-index to ingest content.")
    else:
        error_msg = unwrap_err(result)
        print(f"\nError: {error_msg}")


def _reindex_knowledge_source_flow(manager: AgentManager) -> None:
    """Handle re-indexing a knowledge source.

    Args:
        manager: AgentManager instance
    """
    print("\n" + "-" * 40)
    print("Re-index Knowledge Source")
    print("-" * 40)

    # List agents with RAG enabled
    agents = manager.list_agents()
    rag_agents = [agent for agent in agents if agent.rag_config and agent.rag_config.enabled]

    if not rag_agents:
        print("\nNo agents with RAG enabled found.")
        return

    # Select agent
    print("\nAgents with RAG enabled:")
    for i, agent in enumerate(rag_agents, 1):
        print(f"  {i}. {agent.display_name} ({agent.name})")
    print("  0. Cancel")
    print()

    try:
        choice = input("Select agent: ").strip()
        idx = int(choice)

        if idx == 0:
            return

        if not (1 <= idx <= len(rag_agents)):
            print("\nInvalid selection.")
            return

        agent = rag_agents[idx - 1]

    except ValueError:
        print("\nInvalid input.")
        return

    # List knowledge sources for this agent
    sources_result = manager.list_knowledge_sources(agent.name)

    if is_err(sources_result):
        error_msg = unwrap_err(sources_result)
        print(f"\nError: {error_msg}")
        return

    sources = unwrap(sources_result)

    if not sources:
        print(f"\nNo knowledge sources configured for '{agent.display_name}'.")
        return

    # Select source to re-index
    print(f"\nKnowledge sources for '{agent.display_name}':")
    for i, source in enumerate(sources, 1):
        status_indicator = {
            "active": "✓",
            "failed": "✗",
            "pending": "○",
        }.get(source.status, "?")

        print(f"  {i}. [{status_indicator}] {source.source_type}: {source.identifier}")
        if source.last_indexed:
            print(f"      Last indexed: {source.last_indexed.strftime('%Y-%m-%d %H:%M')}")
        if source.error_message:
            print(f"      Error: {source.error_message}")

    print("  0. Cancel")
    print()

    try:
        choice = input("Select source to re-index: ").strip()
        idx = int(choice)

        if idx == 0:
            return

        if not (1 <= idx <= len(sources)):
            print("\nInvalid selection.")
            return

        source = sources[idx - 1]

    except ValueError:
        print("\nInvalid input.")
        return

    # Confirm re-indexing
    confirm = input(f"\nRe-index '{source.identifier}'? (Y/n): ").strip()
    if confirm.lower() == "n":
        print("\nCancelled.")
        return

    # Progress callback
    def progress_callback(message: str) -> None:
        print(f"  {message}")

    # Re-index
    print()
    result = manager.reindex_knowledge_source(
        agent_name=agent.name,
        source_identifier=source.identifier,
        progress_callback=progress_callback,
    )

    if is_ok(result):
        print("\nKnowledge source re-indexed successfully!")
    else:
        error_msg = unwrap_err(result)
        print(f"\nError: {error_msg}")


def _list_knowledge_sources_flow(manager: AgentManager) -> None:
    """Handle listing knowledge sources for an agent.

    Args:
        manager: AgentManager instance
    """
    print("\n" + "-" * 40)
    print("List Knowledge Sources")
    print("-" * 40)

    # List agents with RAG enabled
    agents = manager.list_agents()
    rag_agents = [agent for agent in agents if agent.rag_config and agent.rag_config.enabled]

    if not rag_agents:
        print("\nNo agents with RAG enabled found.")
        return

    # Select agent
    print("\nAgents with RAG enabled:")
    for i, agent in enumerate(rag_agents, 1):
        print(f"  {i}. {agent.display_name} ({agent.name})")
    print("  0. Cancel")
    print()

    try:
        choice = input("Select agent: ").strip()
        idx = int(choice)

        if idx == 0:
            return

        if not (1 <= idx <= len(rag_agents)):
            print("\nInvalid selection.")
            return

        agent = rag_agents[idx - 1]

    except ValueError:
        print("\nInvalid input.")
        return

    # List knowledge sources
    sources_result = manager.list_knowledge_sources(agent.name)

    if is_err(sources_result):
        error_msg = unwrap_err(sources_result)
        print(f"\nError: {error_msg}")
        return

    sources = unwrap(sources_result)

    if not sources:
        print(f"\nNo knowledge sources configured for '{agent.display_name}'.")
        return

    # Display sources with details
    print("\n" + "=" * 40)
    print(f"Knowledge Sources for '{agent.display_name}'")
    print("=" * 40)

    for i, source in enumerate(sources, 1):
        status_indicator = {
            "active": "✓ Active",
            "failed": "✗ Failed",
            "pending": "○ Pending",
        }.get(source.status, "? Unknown")

        print(f"\n{i}. {source.source_type.upper()}: {source.identifier}")
        print(f"   Status: {status_indicator}")

        if source.last_indexed:
            print(f"   Last indexed: {source.last_indexed.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("   Last indexed: Never")

        if source.error_message:
            print(f"   Error: {source.error_message}")

    print("\n" + "=" * 40)
