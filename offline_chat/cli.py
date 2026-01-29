"""Command-line interface for Offline Chat application.

This module provides the CLI class for terminal-based interaction
with the Offline Chat application.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from offline_chat.agent import Agent
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import Ok
from offline_chat.database_config_cli import configure_database_access
from offline_chat.database_menu import show_database_menu
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    MCPConfigError,
    OfflineChatError,
    OllamaConnectionError,
)
from offline_chat.manager import AgentManager
from offline_chat.mcp_config import MCPServerConfig
from offline_chat.mcp_presets import get_all_available_presets
from offline_chat.rag_menu import show_rag_menu
from offline_chat.session import ChatSession

logger = logging.getLogger(__name__)

# Add cli directory to path if not already there
cli_dir = Path(__file__).parent.parent / "cli"
if str(cli_dir) not in sys.path:
    sys.path.insert(0, str(cli_dir))

from agent_update_menu import show_update_agent_menu  # noqa: E402


def format_user_message(content: str) -> str:
    """Format a user message for display.

    Args:
        content: The message content.

    Returns:
        Formatted message string with "You:" prefix.
    """
    return f"You: {content}"


def format_agent_message(display_name: str, content: str) -> str:
    """Format an agent message for display.

    Args:
        display_name: The agent's display name.
        content: The message content.

    Returns:
        Formatted message string with agent name prefix.
    """
    return f"{display_name}: {content}"


class CLI:
    """Command-line interface for Offline Chat.

    This class provides a terminal-based interface for creating,
    listing, chatting with, and deleting AI agents.

    Attributes:
        manager: AgentManager instance for agent operations.
        session: ChatSession instance for chat operations.
    """

    MENU_OPTIONS = [
        "Create new agent",
        "List agents",
        "View agent details",
        "Chat with agent",
        "View conversation history",
        "Update agent",
        "Manage database connections",
        "Manage RAG knowledge sources",
        "Delete agent",
        "Exit",
    ]

    def __init__(
        self,
        manager: Optional[AgentManager] = None,
    ):
        """Initialize the CLI.

        Args:
            manager: Optional AgentManager instance. If not provided,
                creates a new one with default paths.
        """
        self.db_manager = DatabaseConnectionManager()
        self.manager = manager or AgentManager(db_manager=self.db_manager)
        self.session = ChatSession(self.manager)
        self._running = True

    def _run_migration_check(self) -> None:
        """Run migration check for agents with inline database configurations.

        This method is called automatically on application startup to migrate
        any agents with old-style inline database configurations to the new
        centralized connection management system.

        If any agents are migrated, displays the results to the user.
        """
        try:
            # Call the migration method
            migration_results = self.manager.migrate_inline_configs()

            # Display results if any agents were migrated
            if migration_results:
                print("\n" + "=" * 40)
                print("Database Configuration Migration")
                print("=" * 40)
                print(f"\nMigrated {len(migration_results)} agent(s) to centralized database connections:")

                for agent_name, connection_name in migration_results.items():
                    print(f"  • {agent_name} -> {connection_name}")

                print("\nYour agents now use the centralized connection management system.")
                print("You can manage connections via 'Manage database connections' menu.")
                print("=" * 40)
        except Exception as e:
            # Don't let migration errors prevent app startup
            print(f"\nWarning: Error during database configuration migration: {e}")
            print("The application will continue normally.")

    def run(self) -> None:
        """Start the CLI application.

        Main loop that displays the menu and handles user selections.
        Handles Ctrl+C gracefully.
        """
        print("\nWelcome to Offline Chat!")
        print("=" * 40)

        # Run migration check on startup
        self._run_migration_check()

        try:
            while self._running:
                choice = self.display_menu()

                if choice == 1:
                    self.create_agent_flow()
                elif choice == 2:
                    self.list_agents_flow()
                elif choice == 3:
                    self.view_agent_details_flow()
                elif choice == 4:
                    self.chat_flow()
                elif choice == 5:
                    self.view_history_flow()
                elif choice == 6:
                    self.update_agent_flow()
                elif choice == 7:
                    self.manage_database_connections_flow()
                elif choice == 8:
                    self.manage_rag_knowledge_sources_flow()
                elif choice == 9:
                    self.delete_agent_flow()
                elif choice == 10:
                    self._running = False
                    print("\nGoodbye!")
                else:
                    print("\nInvalid option. Please try again.")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            self._running = False

    def display_menu(self) -> int:
        """Display main menu and return selected option.

        Returns:
            The selected menu option (1-5), or 0 if invalid.
        """
        print("\n" + "-" * 40)
        print("Main Menu")
        print("-" * 40)

        for i, option in enumerate(self.MENU_OPTIONS, 1):
            print(f"  {i}. {option}")

        print()

        try:
            choice = input("Select option: ").strip()
            return int(choice)
        except ValueError:
            return 0

    def create_agent_flow(self) -> None:
        """Handle agent creation workflow.

        Prompts for all agent fields, validates input,
        and creates the agent.
        """
        print("\n" + "=" * 40)
        print("Create New Agent")
        print("=" * 40)

        try:
            # Prompt for agent name
            name = input("Agent name (kebab-case): ").strip()
            if not name:
                print("\nError: Agent name is required.")
                return

            # Prompt for display name
            display_name = input("Display name: ").strip()
            if not display_name:
                print("\nError: Display name is required.")
                return

            # Prompt for base model with default
            base_model = input("Base model [llama3:latest]: ").strip()
            if not base_model:
                base_model = "llama3:latest"

            # Prompt for system prompt
            system_prompt = input("Purpose/persona: ").strip()
            if not system_prompt:
                print("\nError: Purpose/persona is required.")
                return

            # Prompt for temperature with default
            temp_input = input("Temperature [0.7]: ").strip()
            if temp_input:
                try:
                    temperature = float(temp_input)
                    if not 0.0 <= temperature <= 1.0:
                        print("\nError: Temperature must be between 0.0 and 1.0.")
                        return
                except ValueError:
                    print("\nError: Invalid temperature value.")
                    return
            else:
                temperature = 0.7

            # Prompt for language with default
            language = input("Response language [English]: ").strip()
            if not language:
                language = "English"

            # Prompt for web search enabled (y/N)
            web_search_input = input("Enable web search? (y/N): ").strip()
            web_search_enabled = web_search_input.lower() == "y"

            # Prompt for MCP server configurations
            mcp_servers = self._prompt_mcp_servers()

            # Prompt for database configurations
            database_configs = configure_database_access(self.db_manager)

            # Combine MCP servers and database configs
            all_mcp_servers = mcp_servers + database_configs

            # Create the agent
            agent = Agent(
                name=name,
                display_name=display_name,
                base_model=base_model,
                system_prompt=system_prompt,
                temperature=temperature,
                language=language,
                web_search_enabled=web_search_enabled,
                mcp_servers=all_mcp_servers,
            )

            print("\nCreating agent...", end=" ", flush=True)
            self.manager.create_agent(agent)
            print("Done!")
            print(f"\nAgent '{display_name}' created successfully.")

        except InvalidAgentNameError as e:
            print(f"\nError: {e}")
        except AgentExistsError as e:
            print(f"\nError: {e}")
        except OfflineChatError as e:
            print(f"\nError: {e}")
        except KeyboardInterrupt:
            print("\n\nAgent creation cancelled.")

    def list_agents_flow(self) -> None:
        """Handle agent listing workflow.

        Displays all available agents with their details.
        """
        print("\n" + "=" * 40)
        print("Available Agents")
        print("=" * 40)

        agents = self.manager.list_agents()

        if not agents:
            print("\nNo agents available. Create one first!")
            return

        for agent in agents:
            # Truncate system prompt for display
            purpose = agent.system_prompt
            if len(purpose) > 50:
                purpose = purpose[:47] + "..."

            # Web search indicator
            web_search_status = "[Web Search]" if agent.web_search_enabled else ""

            # MCP servers indicator (non-database)
            mcp_status = ""
            if agent.mcp_servers:
                server_names = [s.name for s in agent.mcp_servers if not s.disabled]
                if server_names:
                    mcp_status = f"[MCP: {', '.join(server_names)}]"

            # Database connections indicator (new centralized system)
            db_status = ""
            if agent.connection_assignments:
                db_info = []
                for assignment in agent.connection_assignments:
                    result = self.db_manager.get_connection(assignment.connection_name)
                    if isinstance(result, Ok):
                        conn = result.value
                        access = assignment.access_level.value.replace('_', ' ').title()
                        db_info.append(f"{conn.database_type}:{conn.name}({access})")
                if db_info:
                    db_status = f"[DB: {', '.join(db_info)}]"
                else:
                    db_status = "[DB: connections not found]"
            elif agent.mcp_servers:
                # Backward compatibility: check for database-type MCP servers
                db_servers = [s for s in agent.mcp_servers
                             if hasattr(s, 'database_type') and s.database_type and not s.disabled]
                if db_servers:
                    db_info = [f"{s.database_type}:{s.name}" for s in db_servers]
                    db_status = f"[Databases: {', '.join(db_info)}]"

            print(f"\n  Name: {agent.name} {web_search_status} {mcp_status} {db_status}".rstrip())
            print(f"  Display: {agent.display_name}")
            print(f"  Model: {agent.base_model}")
            print(f"  Language: {agent.language}")
            print(f"  Purpose: {purpose}")
            print()

    def view_agent_details_flow(self) -> None:
        """Handle viewing detailed agent information workflow.

        Displays comprehensive agent details including database configurations
        with masked passwords.
        """
        print("\n" + "=" * 40)
        print("View Agent Details")
        print("=" * 40)

        agent = self._select_agent("Select agent to view details")
        if agent is None:
            return

        print("\n" + "=" * 40)
        print(f"Agent: {agent.display_name}")
        print("=" * 40)

        # Basic information
        print(f"\nName: {agent.name}")
        print(f"Display Name: {agent.display_name}")
        print(f"Base Model: {agent.base_model}")
        print(f"Temperature: {agent.temperature}")
        print(f"Language: {agent.language}")
        print(f"Web Search: {'Enabled' if agent.web_search_enabled else 'Disabled'}")
        print(f"Created: {agent.created_at.strftime('%Y-%m-%d %H:%M')}")

        # System prompt
        print("\nPurpose/Persona:")
        print(f"  {agent.system_prompt}")

        # Display MCP servers (non-database)
        if agent.mcp_servers:
            print("\nMCP Servers:")
            for server in agent.mcp_servers:
                status = "disabled" if server.disabled else "enabled"
                print(f"  - {server.name} ({status})")
                print(f"    Command: {server.command} {' '.join(server.args)}")
                if server.env:
                    print(f"    Environment: {len(server.env)} variable(s)")

        # Display database connections (new centralized system)
        if agent.connection_assignments:
            print("\nDatabase Connections:")

            for assignment in agent.connection_assignments:
                # Try to resolve the connection to get details
                result = self.db_manager.get_connection(assignment.connection_name)

                if isinstance(result, Ok):
                    conn = result.value
                    print(f"\n  Connection: {conn.name}")
                    print(f"  Type: {conn.database_type}")
                    print(f"  Access Level: {assignment.access_level.value}")

                    if assignment.allowed_tables:
                        print(f"  Allowed Tables: {', '.join(assignment.allowed_tables)}")

                    # Display connection details based on database type
                    if conn.database_type == "sqlite":
                        print(f"  Path: {conn.file_path}")
                    elif conn.database_type in ["postgresql", "mysql", "oracle"]:
                        if conn.host:
                            print(f"  Host: {conn.host}")
                        if conn.port:
                            print(f"  Port: {conn.port}")
                        if conn.database or conn.service_name:
                            db_name = conn.database or conn.service_name
                            print(f"  Database: {db_name}")
                        if conn.username:
                            print(f"  Username: {conn.username}")
                            print("  Password: ****")
                else:
                    # Connection not found in store
                    print(f"\n  Connection: {assignment.connection_name} [NOT FOUND]")
                    print(f"  Access Level: {assignment.access_level.value}")
                    if assignment.allowed_tables:
                        print(f"  Allowed Tables: {', '.join(assignment.allowed_tables)}")
        elif agent.mcp_servers:
            # Backward compatibility: check for database-type MCP servers
            db_servers = [s for s in agent.mcp_servers
                         if hasattr(s, 'database_type') and s.database_type and not s.disabled]
            if db_servers:
                print("\nDatabase Connections (Legacy):")
                for server in db_servers:
                    print(f"\n  Name: {server.name}")
                    print(f"  Type: {server.database_type}")
                    print(f"  Command: {server.command} {' '.join(server.args)}")

                    # Show type-specific details
                    if server.database_type == "oracle":
                        if hasattr(server, 'oracle_connection_name') and server.oracle_connection_name:
                            print(f"  Connection: {server.oracle_connection_name}")
                        if hasattr(server, 'database_user') and server.database_user:
                            print(f"  Username: {server.database_user}")
                            print("  Password: ****")
                    elif server.database_type == "sqlite":
                        if hasattr(server, 'database_path') and server.database_path:
                            print(f"  Path: {server.database_path}")
                    elif server.database_type in ["postgresql", "mysql"]:
                        if hasattr(server, 'database_host') and server.database_host:
                            print(f"  Host: {server.database_host}")
                        if hasattr(server, 'database_port') and server.database_port:
                            print(f"  Port: {server.database_port}")
                        if hasattr(server, 'database_name') and server.database_name:
                            print(f"  Database: {server.database_name}")
                        if hasattr(server, 'database_user') and server.database_user:
                            print(f"  Username: {server.database_user}")
                            print("  Password: ****")
            else:
                print("\nDatabase Connections: No database connections assigned")
        else:
            print("\nDatabase Connections: No database connections assigned")

        print("\n" + "=" * 40)

    def view_history_flow(self) -> None:
        """Handle viewing conversation history workflow.

        Allows user to select an agent and view its conversation history.
        """
        print("\n" + "=" * 40)
        print("View Conversation History")
        print("=" * 40)

        agent = self._select_agent("Select agent to view history")
        if agent is None:
            return

        history = self.manager.history_store.load(agent.name)

        if not history.messages:
            print(f"\nNo conversation history for '{agent.display_name}'.")
            return

        print(f"\n[{agent.display_name}] - {len(history.messages)} messages")
        print(f"Last updated: {history.last_updated.strftime('%Y-%m-%d %H:%M')}")
        print("-" * 40)

        for msg in history.messages:
            timestamp = msg.timestamp.strftime("%H:%M")
            if msg.role == "user":
                print(f"\n[{timestamp}] You: {msg.content}")
            else:
                print(f"\n[{timestamp}] {agent.display_name}: {msg.content}")

        print("\n" + "-" * 40)

    def _select_agent(self, prompt: str = "Select agent") -> Optional[Agent]:
        """Display agent list and let user select one.

        Args:
            prompt: The prompt to display.

        Returns:
            Selected Agent or None if cancelled.
        """
        agents = self.manager.list_agents()

        if not agents:
            print("\nNo agents available. Create one first!")
            return None

        print()
        for i, agent in enumerate(agents, 1):
            print(f"  {i}. {agent.display_name} ({agent.name})")

        print("  0. Cancel")
        print()

        try:
            choice = input(f"{prompt} (number): ").strip()
            idx = int(choice)

            if idx == 0:
                return None

            if 1 <= idx <= len(agents):
                return agents[idx - 1]

            print("\nInvalid selection.")
            return None

        except ValueError:
            print("\nInvalid input.")
            return None

    def _prompt_mcp_servers(self) -> list[MCPServerConfig]:
        """Prompt user for MCP server configurations.

        Shows available presets and allows selecting from them or
        adding custom configurations.

        Returns:
            List of MCPServerConfig objects.
        """
        mcp_servers: list[MCPServerConfig] = []

        add_mcp = input("\nAdd MCP servers? (y/N): ").strip()
        if add_mcp.lower() != "y":
            return mcp_servers

        print("\n" + "-" * 40)
        print("MCP Server Configuration")
        print("-" * 40)

        while True:
            # Show available presets
            presets = get_all_available_presets()

            print("\nAvailable MCP servers:")
            for i, (config, description) in enumerate(presets, 1):
                # Check if already added
                already_added = any(s.name == config.name for s in mcp_servers)
                status = " [added]" if already_added else ""
                print(f"  {i}. {config.name}{status}")
                print(f"     {description}")
                print(f"     Command: {config.command} {' '.join(config.args)}")

            print(f"\n  {len(presets) + 1}. Add custom MCP server")
            print("  0. Done adding servers")
            print()

            try:
                choice = input("Select option: ").strip()
                idx = int(choice)

                if idx == 0:
                    break

                if 1 <= idx <= len(presets):
                    preset_config, _ = presets[idx - 1]

                    # Check if already added
                    if any(s.name == preset_config.name for s in mcp_servers):
                        print(f"\n'{preset_config.name}' is already added.")
                        continue

                    # Allow customization of the preset
                    server = self._customize_preset(preset_config)
                    if server:
                        mcp_servers.append(server)
                        print(f"\nMCP server '{server.name}' added.")

                elif idx == len(presets) + 1:
                    # Custom server
                    server = self._prompt_single_mcp_server(len(mcp_servers) + 1)
                    if server:
                        mcp_servers.append(server)
                        print(f"\nMCP server '{server.name}' added.")

                else:
                    print("\nInvalid selection.")

            except ValueError:
                print("\nInvalid input.")

        return mcp_servers

    def _customize_preset(self, preset: MCPServerConfig) -> MCPServerConfig | None:
        """Allow user to customize a preset before adding.

        Args:
            preset: The preset configuration to customize.

        Returns:
            Customized MCPServerConfig or None if cancelled.
        """
        print(f"\n--- Configure '{preset.name}' ---")
        print(f"Command: {preset.command} {' '.join(preset.args)}")

        # For filesystem, prompt for path
        if preset.name == "filesystem":
            path = input("Directory path to allow access [~]: ").strip()
            if path:
                # Replace the last argument (path) with user's choice
                preset.args = preset.args[:-1] + [path]
            print(f"Updated: {preset.command} {' '.join(preset.args)}")

        # For servers that need tokens, prompt for them
        if preset.env:
            print("\nEnvironment variables needed:")
            for key, value in preset.env.items():
                if not value:  # Empty value means user needs to provide it
                    new_value = input(f"  {key}: ").strip()
                    if new_value:
                        preset.env[key] = new_value

        # Confirm
        confirm = input("\nAdd this server? (Y/n): ").strip()
        if confirm.lower() == "n":
            return None

        return preset

    def _prompt_single_mcp_server(self, index: int) -> Optional[MCPServerConfig]:
        """Prompt user for a single MCP server configuration.

        Args:
            index: The server index for display purposes.

        Returns:
            MCPServerConfig if valid input provided, None to cancel.
        """
        print(f"\n--- MCP Server {index} ---")

        # Prompt for server name
        name = input("Server name (e.g., fetch, filesystem): ").strip()
        if not name:
            print("Server name is required. Skipping MCP server.")
            return None

        # Prompt for command
        command = input("Command (e.g., uvx, npx): ").strip()
        if not command:
            print("Command is required. Skipping MCP server.")
            return None

        # Prompt for arguments
        args_input = input("Arguments (space-separated, e.g., mcp-server-fetch): ").strip()
        args = args_input.split() if args_input else []

        # Prompt for environment variables
        env: dict[str, str] = {}
        add_env = input("Add environment variables? (y/N): ").strip()
        if add_env.lower() == "y":
            print("Enter environment variables (KEY=VALUE format, empty line to finish):")
            while True:
                env_input = input("  ").strip()
                if not env_input:
                    break
                if "=" in env_input:
                    key, value = env_input.split("=", 1)
                    env[key.strip()] = value.strip()
                else:
                    print("  Invalid format. Use KEY=VALUE.")

        # Create and validate the config
        try:
            config = MCPServerConfig(
                name=name,
                command=command,
                args=args,
                env=env,
                disabled=False,
            )
            config.validate()
            return config
        except MCPConfigError as e:
            print(f"\nInvalid MCP configuration: {e}")
            return None

    def chat_flow(self) -> None:
        """Handle chat session workflow.

        Allows user to select an agent and start a conversation.
        Uses async methods when agent has MCP servers configured.
        """
        print("\n" + "=" * 40)
        print("Chat with Agent")
        print("=" * 40)

        agent = self._select_agent("Select agent to chat with")
        if agent is None:
            return

        # Check if agent has MCP servers - use async flow if so
        if agent.mcp_servers:
            self._chat_flow_async(agent)
        else:
            self._chat_flow_sync(agent)

    def _chat_flow_sync(self, agent: Agent) -> None:
        """Handle synchronous chat session (no MCP servers).

        Args:
            agent: The agent to chat with.
        """
        try:
            self.session.start(agent.name)
            display_name = self.session.get_display_name()

            # Track if we're showing a tool indicator
            self._tool_indicator_shown = False

            def tool_callback(tool_name: str) -> None:
                """Display indicator when a tool is called."""
                self._tool_indicator_shown = True
                if tool_name == "web_search":
                    print("\nSearching...", end="", flush=True)
                elif tool_name == "web_fetch":
                    print("\nFetching page...", end="", flush=True)

            # Set the tool callback on the session
            self.session.set_tool_callback(tool_callback)

            print(f"\n[{display_name}] - Commands: exit, clear")
            print("-" * 40)

            while True:
                try:
                    user_input = input("\nYou: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() == "exit":
                        print("\nSaving conversation...", end=" ", flush=True)
                        self.session.end()
                        print("Done!")
                        break

                    if user_input.lower() == "clear":
                        self.session.clear_history()
                        print("\nConversation history cleared.")
                        continue

                    # Reset tool indicator flag
                    self._tool_indicator_shown = False

                    # Send message and stream response
                    response_started = False
                    for chunk in self.session.send_message(user_input):
                        if not response_started:
                            # Clear indicator line and start response on new line
                            if self._tool_indicator_shown:
                                print()  # New line after indicator
                            print(f"\n{display_name}: ", end="", flush=True)
                            response_started = True
                        print(chunk, end="", flush=True)
                    print()

                    # Display source citations if available (RAG-enhanced response)
                    self._display_source_citations()

                except KeyboardInterrupt:
                    print("\n\nSaving conversation...", end=" ", flush=True)
                    self.session.end()
                    print("Done!")
                    break

        except AgentNotFoundError as e:
            print(f"\nError: {e}")
        except OllamaConnectionError as e:
            print(f"\nError: {e}")
            if self.session.is_active:
                self.session.end()
        except OfflineChatError as e:
            print(f"\nError: {e}")
            if self.session.is_active:
                self.session.end()

    def _chat_flow_async(self, agent: Agent) -> None:
        """Handle async chat session with MCP servers.

        Args:
            agent: The agent to chat with (has MCP servers configured).
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._chat_flow_async_impl(agent))
        except KeyboardInterrupt:
            print("\n\nGoodbye!")

    async def _chat_flow_async_impl(self, agent: Agent) -> None:
        """Async implementation of chat flow with MCP servers.

        Args:
            agent: The agent to chat with.
        """
        try:
            print("\nConnecting to MCP servers...", end=" ", flush=True)
            await self.session.start_async(agent.name)
            print("Done!")

            display_name = self.session.get_display_name()

            # Track if we're showing a tool indicator
            self._tool_indicator_shown = False

            def tool_callback(tool_name: str) -> None:
                """Display indicator when a tool is called."""
                self._tool_indicator_shown = True
                # Show tool name for MCP tools
                print(f"\nUsing tool: {tool_name}...", end="", flush=True)

            # Set the tool callback on the session
            self.session.set_tool_callback(tool_callback)

            # Show available MCP tools
            if self.session.has_mcp_tools:
                tool_count = len(self.session._mcp_manager.tool_registry)
                print(f"[{tool_count} MCP tool(s) available]")

            print(f"\n[{display_name}] - Commands: exit, clear")
            print("-" * 40)

            while True:
                try:
                    user_input = input("\nYou: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() == "exit":
                        print("\nSaving conversation...", end=" ", flush=True)
                        await self.session.end_async()
                        print("Done!")
                        break

                    if user_input.lower() == "clear":
                        self.session.clear_history()
                        print("\nConversation history cleared.")
                        continue

                    # Reset tool indicator flag
                    self._tool_indicator_shown = False

                    # Send message using async method
                    response_chunks = await self.session.send_message_async(user_input)

                    # Debug: Log response info
                    logger.debug(f"Received {len(response_chunks)} chunks, "
                               f"total chars: {sum(len(c) for c in response_chunks)}")

                    # Display response
                    if response_chunks:
                        if self._tool_indicator_shown:
                            print()  # New line after indicator
                        print(f"\n{display_name}: ", end="", flush=True)
                        for chunk in response_chunks:
                            print(chunk, end="", flush=True)
                        print()

                    # Display source citations if available (RAG-enhanced response)
                    self._display_source_citations()

                except KeyboardInterrupt:
                    print("\n\nSaving conversation...", end=" ", flush=True)
                    await self.session.end_async()
                    print("Done!")
                    break

        except AgentNotFoundError as e:
            print(f"\nError: {e}")
        except OllamaConnectionError as e:
            print(f"\nError: {e}")
            if self.session.is_active:
                await self.session.end_async()
        except OfflineChatError as e:
            print(f"\nError: {e}")
            if self.session.is_active:
                await self.session.end_async()

    def delete_agent_flow(self) -> None:
        """Handle agent deletion workflow.

        Allows user to select and delete an agent with confirmation.
        """
        print("\n" + "=" * 40)
        print("Delete Agent")
        print("=" * 40)

        agent = self._select_agent("Select agent to delete")
        if agent is None:
            return

        # Confirm deletion
        prompt = f"\nAre you sure you want to delete '{agent.display_name}'? (y/N): "
        confirm = input(prompt).strip()

        if confirm.lower() != "y":
            print("\nDeletion cancelled.")
            return

        try:
            print("\nDeleting agent...", end=" ", flush=True)
            self.manager.delete_agent(agent.name)
            print("Done!")
            print(f"\nAgent '{agent.display_name}' deleted successfully.")

        except AgentNotFoundError as e:
            print(f"\nError: {e}")
        except OfflineChatError as e:
            print(f"\nError: {e}")

    def update_agent_flow(self) -> None:
        """Handle agent update workflow.

        Displays the agent update menu which allows updating agent
        configuration including database connections and guidelines.
        """
        try:
            show_update_agent_menu(self.manager, self.db_manager)
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
        except OfflineChatError as e:
            print(f"\nError: {e}")

    def manage_database_connections_flow(self) -> None:
        """Handle database connection management workflow.

        Displays the database connection management menu which allows
        creating, listing, updating, and deleting database connections.
        """
        try:
            show_database_menu(self.db_manager)
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
        except OfflineChatError as e:
            print(f"\nError: {e}")

    def manage_rag_knowledge_sources_flow(self) -> None:
        """Handle RAG knowledge source management workflow.

        Displays the RAG management menu which allows adding, re-indexing,
        and listing knowledge sources for agents.
        """
        try:
            show_rag_menu(self.manager)
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...")
        except OfflineChatError as e:
            print(f"\nError: {e}")

    def _display_source_citations(self) -> None:
        """Display source citations for the last assistant message if available.

        This method checks if the last message in the conversation history
        has source citations (indicating a RAG-enhanced response) and displays
        them in a formatted way.
        """
        if not self.session.is_active or not self.session.history:
            return

        # Get the last message
        messages = self.session.history.messages
        if not messages:
            return

        last_message = messages[-1]

        # Check if it's an assistant message with sources
        if last_message.role != "assistant" or not last_message.sources:
            return

        # Display sources
        print("\n" + "-" * 40)
        print("Sources consulted:")
        for i, source in enumerate(last_message.sources, 1):
            print(f"  {i}. {source.format_for_display()}")
        print("-" * 40)
