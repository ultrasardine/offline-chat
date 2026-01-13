"""Chat session for Offline Chat application.

This module provides the ChatSession class for managing conversations
with AI agents, including message handling and history persistence.
"""

from datetime import datetime
from typing import Iterator, Optional

import ollama

from offline_chat.agent import Agent
from offline_chat.exceptions import AgentNotFoundError, OllamaConnectionError
from offline_chat.history import ConversationHistory, HistoryStore, Message
from offline_chat.manager import AgentManager


class ChatSession:
    """Manages a chat session with an AI agent.

    This class handles starting and ending chat sessions, sending messages,
    receiving streaming responses, and managing conversation history.

    Attributes:
        manager: AgentManager instance for agent operations.
        history_store: HistoryStore instance for history persistence.
        agent: The current agent (set after start()).
        history: The current conversation history (set after start()).
    """

    def __init__(
        self,
        manager: AgentManager,
        history_store: Optional[HistoryStore] = None,
    ):
        """Initialize the ChatSession.

        Args:
            manager: AgentManager instance for agent operations.
            history_store: Optional HistoryStore instance. If not provided,
                uses the manager's history_store.
        """
        self.manager = manager
        self.history_store = history_store or manager.history_store
        self.agent: Optional[Agent] = None
        self.history: Optional[ConversationHistory] = None

    def start(self, agent_name: str) -> bool:
        """Start a chat session with the specified agent.

        Loads the agent configuration and existing conversation history.

        Args:
            agent_name: The name of the agent to chat with.

        Returns:
            True if the session started successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
        """
        # Load the agent
        self.agent = self.manager.get_agent(agent_name)
        if self.agent is None:
            raise AgentNotFoundError(agent_name)

        # Load existing conversation history
        self.history = self.history_store.load(agent_name)

        return True

    def end(self) -> None:
        """End the session and save history.

        Saves the current conversation history to persistent storage.
        """
        if self.history is not None:
            self.history.last_updated = datetime.now()
            self.history_store.save(self.history)

        # Clear session state
        self.agent = None
        self.history = None

    def send_message(self, content: str) -> Iterator[str]:
        """Send a message and yield response chunks.

        Appends the user message to history, sends it to Ollama,
        streams the response, and appends the assistant response to history.

        Args:
            content: The message content to send.

        Yields:
            Response chunks as they are received from Ollama.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
            RuntimeError: If no session is active.
        """
        if self.agent is None or self.history is None:
            raise RuntimeError("No active session. Call start() first.")

        # Append user message to history
        user_message = Message(
            role="user",
            content=content,
            timestamp=datetime.now(),
        )
        self.history.messages.append(user_message)

        # Build messages list for Ollama
        messages = [{"role": msg.role, "content": msg.content} for msg in self.history.messages]

        # Send to Ollama with streaming
        try:
            stream = ollama.chat(
                model=self.agent.name,
                messages=messages,
                stream=True,
            )

            # Collect full response while yielding chunks
            full_response = ""
            for chunk in stream:
                chunk_content = chunk.get("message", {}).get("content", "")
                full_response += chunk_content
                yield chunk_content

            # Append assistant response to history
            assistant_message = Message(
                role="assistant",
                content=full_response,
                timestamp=datetime.now(),
            )
            self.history.messages.append(assistant_message)

        except Exception as e:
            # Check for connection errors
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str or "connect" in error_str:
                raise OllamaConnectionError()
            raise

    def clear_history(self) -> None:
        """Clear the conversation history.

        Resets the messages list and updates the last_updated timestamp.

        Raises:
            RuntimeError: If no session is active.
        """
        if self.history is None:
            raise RuntimeError("No active session. Call start() first.")

        self.history.messages = []
        self.history.last_updated = datetime.now()

    @property
    def is_active(self) -> bool:
        """Check if a session is currently active.

        Returns:
            True if a session is active, False otherwise.
        """
        return self.agent is not None and self.history is not None

    def get_display_name(self) -> str:
        """Get the display name of the current agent.

        Returns:
            The agent's display name, or empty string if no session is active.
        """
        if self.agent is None:
            return ""
        return self.agent.display_name
