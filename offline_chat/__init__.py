"""Offline Chat - Terminal-based chatbot application using local Ollama models.

This package provides tools for creating and interacting with personalized AI agents
powered by local Ollama models. Each agent has its own persona, purpose, and
persistent conversation history.

Usage as a library:
    from offline_chat import Agent, AgentManager, ChatSession

    # Create an agent manager
    manager = AgentManager()

    # Create a new agent
    agent = Agent(
        name="my-agent",
        display_name="My Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant."
    )
    manager.create_agent(agent)

    # Start a chat session
    session = ChatSession(manager)
    session.start("my-agent")
"""

from offline_chat.agent import Agent
from offline_chat.cli import CLI, format_agent_message, format_user_message
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    InvalidAgentNameError,
    OfflineChatError,
    OllamaCommandError,
    OllamaConnectionError,
)
from offline_chat.history import ConversationHistory, HistoryStore, Message
from offline_chat.manager import (
    AgentManager,
    get_default_agents_dir,
    get_default_history_dir,
)
from offline_chat.session import ChatSession

__all__ = [
    # Data models
    "Agent",
    "Message",
    "ConversationHistory",
    # Manager
    "AgentManager",
    "get_default_agents_dir",
    "get_default_history_dir",
    # Session
    "ChatSession",
    # Storage
    "HistoryStore",
    # CLI
    "CLI",
    "format_user_message",
    "format_agent_message",
    # Exceptions
    "OfflineChatError",
    "AgentNotFoundError",
    "AgentExistsError",
    "InvalidAgentNameError",
    "OllamaConnectionError",
    "OllamaCommandError",
]

__version__ = "0.1.0"
