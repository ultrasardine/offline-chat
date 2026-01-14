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

Web search usage:
    from offline_chat import WebSearchTool, WebFetchTool, SearchResult, DuckDuckGoProvider

    # Use web search tool
    search_tool = WebSearchTool()
    results = search_tool.execute("Python programming")

    # Use web fetch tool
    fetch_tool = WebFetchTool()
    content = fetch_tool.execute("https://example.com")

    # Use search provider directly
    provider = DuckDuckGoProvider(timeout=10)
    results = provider.search("Python programming", max_results=5)
"""

from offline_chat.agent import Agent
from offline_chat.cli import CLI, format_agent_message, format_user_message
from offline_chat.exceptions import (
    AgentExistsError,
    AgentNotFoundError,
    FetchError,
    FetchHTTPError,
    FetchTimeoutError,
    InvalidAgentNameError,
    MCPConfigError,
    OfflineChatError,
    OllamaCommandError,
    OllamaConnectionError,
    SearchConnectionError,
    SearchError,
    SearchTimeoutError,
)
from offline_chat.fetch import WebFetchTool
from offline_chat.history import ConversationHistory, HistoryStore, Message
from offline_chat.manager import (
    AgentManager,
    get_default_agents_dir,
    get_default_history_dir,
)
from offline_chat.mcp_client import MCPClient, MCPClientManager, convert_mcp_tool_to_ollama
from offline_chat.mcp_config import MCPServerConfig
from offline_chat.mcp_presets import (
    add_preset,
    get_all_available_presets,
    get_preset,
    load_presets,
    remove_preset,
    save_presets,
)
from offline_chat.search import DuckDuckGoProvider, SearchResult
from offline_chat.session import ChatSession
from offline_chat.tools import WebSearchTool

__all__ = [
    # Data models
    "Agent",
    "Message",
    "ConversationHistory",
    "MCPServerConfig",
    # MCP Client
    "MCPClient",
    "MCPClientManager",
    "convert_mcp_tool_to_ollama",
    # MCP Presets
    "load_presets",
    "save_presets",
    "add_preset",
    "remove_preset",
    "get_preset",
    "get_all_available_presets",
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
    # Web Search
    "SearchResult",
    "DuckDuckGoProvider",
    "WebSearchTool",
    "WebFetchTool",
    # Exceptions
    "OfflineChatError",
    "AgentNotFoundError",
    "AgentExistsError",
    "InvalidAgentNameError",
    "OllamaConnectionError",
    "OllamaCommandError",
    "SearchError",
    "SearchTimeoutError",
    "SearchConnectionError",
    "FetchError",
    "FetchTimeoutError",
    "FetchHTTPError",
    "MCPConfigError",
]

__version__ = "0.1.0"
