"""Command-line interface for Offline Chat application.

This module provides the CLI class for terminal-based interaction
with the Offline Chat application.
"""

from typing import Optional

from offline_chat.agent import Agent
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    OfflineChatError,
    OllamaConnectionError,
)
from offline_chat.manager import AgentManager
from offline_chat.session import ChatSession


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
        "Chat with agent",
        "View conversation history",
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
        self.manager = manager or AgentManager()
        self.session = ChatSession(self.manager)
        self._running = True

    def run(self) -> None:
        """Start the CLI application.

        Main loop that displays the menu and handles user selections.
        Handles Ctrl+C gracefully.
        """
        print("\nWelcome to Offline Chat!")
        print("=" * 40)

        try:
            while self._running:
                choice = self.display_menu()

                if choice == 1:
                    self.create_agent_flow()
                elif choice == 2:
                    self.list_agents_flow()
                elif choice == 3:
                    self.chat_flow()
                elif choice == 4:
                    self.view_history_flow()
                elif choice == 5:
                    self.delete_agent_flow()
                elif choice == 6:
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

            # Create the agent
            agent = Agent(
                name=name,
                display_name=display_name,
                base_model=base_model,
                system_prompt=system_prompt,
                temperature=temperature,
                language=language,
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

            print(f"\n  Name: {agent.name}")
            print(f"  Display: {agent.display_name}")
            print(f"  Model: {agent.base_model}")
            print(f"  Language: {agent.language}")
            print(f"  Purpose: {purpose}")
            print()

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

    def chat_flow(self) -> None:
        """Handle chat session workflow.

        Allows user to select an agent and start a conversation.
        """
        print("\n" + "=" * 40)
        print("Chat with Agent")
        print("=" * 40)

        agent = self._select_agent("Select agent to chat with")
        if agent is None:
            return

        try:
            self.session.start(agent.name)
            display_name = self.session.get_display_name()

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

                    # Send message and stream response
                    print(f"\n{display_name}: ", end="", flush=True)
                    for chunk in self.session.send_message(user_input):
                        print(chunk, end="", flush=True)
                    print()

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
