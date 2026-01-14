"""Chat session for Offline Chat application.

This module provides the ChatSession class for managing conversations
with AI agents, including message handling and history persistence.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

import ollama

from offline_chat.agent import Agent
from offline_chat.exceptions import AgentNotFoundError, OllamaConnectionError
from offline_chat.fetch import WebFetchTool
from offline_chat.history import ConversationHistory, HistoryStore, Message
from offline_chat.manager import AgentManager
from offline_chat.mcp_client import MCPClientManager
from offline_chat.tools import WebSearchTool


class ChatSession:
    """Manages a chat session with an AI agent.

    This class handles starting and ending chat sessions, sending messages,
    receiving streaming responses, and managing conversation history.
    Supports tool calling for web search, web fetch, and MCP server capabilities.

    Attributes:
        manager: AgentManager instance for agent operations.
        history_store: HistoryStore instance for history persistence.
        agent: The current agent (set after start()).
        history: The current conversation history (set after start()).
        custom_tools: Optional list of custom tools to use.
    """

    def __init__(
        self,
        manager: AgentManager,
        history_store: Optional[HistoryStore] = None,
        tools: Optional[list] = None,
    ):
        """Initialize the ChatSession.

        Args:
            manager: AgentManager instance for agent operations.
            history_store: Optional HistoryStore instance. If not provided,
                uses the manager's history_store.
            tools: Optional list of tools to use regardless of agent config.
        """
        self.manager = manager
        self.history_store = history_store or manager.history_store
        self.custom_tools = tools
        self.agent: Optional[Agent] = None
        self.history: Optional[ConversationHistory] = None
        self._web_search_tool: Optional[WebSearchTool] = None
        self._web_fetch_tool: Optional[WebFetchTool] = None
        self._mcp_manager: Optional[MCPClientManager] = None
        self._on_tool_call: Optional[Callable[[str], None]] = None

    def start(self, agent_name: str) -> bool:
        """Start a chat session with the specified agent.

        Loads the agent configuration and existing conversation history.
        For agents with MCP servers, use start_async() instead.

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

    async def start_async(self, agent_name: str) -> bool:
        """Start a chat session with async MCP server connections.

        Loads the agent configuration, existing conversation history,
        and connects to any configured MCP servers.

        Args:
            agent_name: The name of the agent to chat with.

        Returns:
            True if the session started successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
        """
        # Load the agent and history using sync method
        self.start(agent_name)

        # Connect to MCP servers if configured
        if self.agent and self.agent.mcp_servers:
            self._mcp_manager = MCPClientManager(self.agent.mcp_servers)
            await self._mcp_manager.connect_all()

        return True

    def set_tool_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for tool call notifications.

        Args:
            callback: Function called with tool name when a tool is invoked.
        """
        self._on_tool_call = callback

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get tools to register with Ollama.

        Returns custom tools if provided, MCP tools if configured,
        web search and fetch tools if agent.web_search_enabled is True,
        or empty list otherwise.

        Returns:
            List of tool schemas.
        """
        if self.custom_tools:
            return [t.get_tool_schema() for t in self.custom_tools]

        tools: list[dict[str, Any]] = []

        # Add MCP tools if available
        if self._mcp_manager:
            tools.extend(self._mcp_manager.get_all_tools())

        # Add web search tools if enabled
        if self.agent and self.agent.web_search_enabled:
            if self._web_search_tool is None:
                self._web_search_tool = WebSearchTool()
            if self._web_fetch_tool is None:
                self._web_fetch_tool = WebFetchTool()
            tools.append(self._web_search_tool.get_tool_schema())
            tools.append(self._web_fetch_tool.get_tool_schema())

        return tools

    def _get_system_prompt(self) -> str:
        """Get the system prompt, enhanced with tool usage instructions if tools are available.

        Returns:
            The system prompt string.
        """
        if self.agent is None:
            return ""

        base_prompt = self.agent.system_prompt
        tools = self._get_tools()

        if not tools:
            return base_prompt

        # Build tool usage instructions
        tool_names = [t["function"]["name"] for t in tools]
        tool_list = ", ".join(tool_names)

        tool_instructions = (
            f"\n\nYou have access to the following tools: {tool_list}. "
            "When you need current or up-to-date information, USE these tools. "
            "IMPORTANT: When a tool returns results, you MUST use that information "
            "to answer the user's question. Do NOT ignore tool results or claim you "
            "don't have information when tools have provided it. Base your response "
            "on the tool results."
        )

        return base_prompt + tool_instructions

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name (synchronous).

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        if self._on_tool_call:
            self._on_tool_call(name)

        if name == "web_search":
            tool = self._web_search_tool or WebSearchTool()
            # Ensure max_results is an integer (model may pass it as string)
            if "max_results" in arguments:
                arguments["max_results"] = int(arguments["max_results"])
            return tool.execute(**arguments)
        elif name == "web_fetch":
            tool = self._web_fetch_tool or WebFetchTool()
            return tool.execute(**arguments)

        return f"Unknown tool: {name}"

    async def _execute_tool_async(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute tool, routing to MCP or built-in handlers.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        if self._on_tool_call:
            self._on_tool_call(name)

        # Check MCP tools first
        if self._mcp_manager and name in self._mcp_manager.tool_registry:
            return await self._mcp_manager.call_tool(name, arguments)

        # Fall back to built-in tools
        return self._execute_tool(name, arguments)

    def end(self) -> None:
        """End the session and save history.

        Saves the current conversation history to persistent storage.
        For sessions with MCP servers, use end_async() instead.
        """
        if self.history is not None:
            self.history.last_updated = datetime.now()
            self.history_store.save(self.history)

        # Clear session state
        self.agent = None
        self.history = None
        self._mcp_manager = None

    async def end_async(self) -> None:
        """End session and disconnect MCP servers.

        Saves the current conversation history and disconnects
        from all MCP servers.
        """
        # Disconnect MCP servers
        if self._mcp_manager:
            await self._mcp_manager.disconnect_all()

        # Save history and clear state using sync method
        self.end()

    def send_message(self, content: str) -> Iterator[str]:
        """Send a message and yield response chunks.

        Implements agent loop for tool calling. Appends the user message to
        history, sends it to Ollama, handles tool calls if any, and streams
        the final response. Only user messages and final assistant responses
        are persisted to history.

        For sessions with MCP tools, use send_message_async() instead.

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

        # Build messages list for Ollama with enhanced system prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._get_system_prompt()}
        ]
        messages.extend(
            {"role": msg.role, "content": msg.content}
            for msg in self.history.messages
        )

        tools = self._get_tools()

        # Agent loop - continue until no more tool calls
        try:
            while True:
                if not tools:
                    # No tools - use streaming directly
                    yield from self._stream_response(messages)
                    return

                # Use non-streaming for tool detection
                # Use base_model for tool calls since custom models may not support tools properly
                try:
                    response = ollama.chat(
                        model=self.agent.base_model,
                        messages=messages,
                        tools=tools,
                        stream=False,
                    )
                except Exception as tool_error:
                    # Check if model doesn't support tools
                    error_msg = str(tool_error).lower()
                    if "does not support tools" in error_msg:
                        # Fall back to streaming without tools
                        tools = []
                        yield from self._stream_response(messages)
                        return
                    raise

                message = response.get("message", {})
                tool_calls = message.get("tool_calls", [])

                if not tool_calls:
                    # No tool calls - yield the final response
                    response_content = message.get("content", "")
                    if response_content:
                        # Stream the response character by character
                        for char in response_content:
                            yield char
                        # Save to history (only final assistant response)
                        self.history.messages.append(
                            Message(
                                role="assistant",
                                content=response_content,
                                timestamp=datetime.now(),
                            )
                        )
                    return

                # Execute tool calls
                # Add assistant message with tool calls to messages (not to history)
                messages.append(message)

                for call in tool_calls:
                    func = call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", {})

                    # Check if this is an MCP tool - if so, run async in event loop
                    if self._mcp_manager and name in self._mcp_manager.tool_registry:
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            self._execute_tool_async(name, args)
                        )
                    else:
                        result = self._execute_tool(name, args)

                    # Add tool result to messages (not to history)
                    # Use tool_name as per Ollama's tool calling format
                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": result if result else "No results returned",
                    })

        except Exception as e:
            # Check for connection errors
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str or "connect" in error_str:
                raise OllamaConnectionError()
            raise

    async def send_message_async(self, content: str) -> list[str]:
        """Send a message asynchronously and return response chunks.

        Async version of send_message() for use with MCP tools.
        Implements agent loop for tool calling with async MCP tool execution.

        Args:
            content: The message content to send.

        Returns:
            List of response chunks.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
            RuntimeError: If no session is active.
        """
        if self.agent is None or self.history is None:
            raise RuntimeError("No active session. Call start_async() first.")

        # Append user message to history
        user_message = Message(
            role="user",
            content=content,
            timestamp=datetime.now(),
        )
        self.history.messages.append(user_message)

        # Build messages list for Ollama with enhanced system prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._get_system_prompt()}
        ]
        messages.extend(
            {"role": msg.role, "content": msg.content}
            for msg in self.history.messages
        )

        tools = self._get_tools()
        response_chunks: list[str] = []

        # Agent loop - continue until no more tool calls
        try:
            while True:
                if not tools:
                    # No tools - use streaming directly
                    for chunk in self._stream_response(messages):
                        response_chunks.append(chunk)
                    return response_chunks

                # Use non-streaming for tool detection
                # Use base_model for tool calls since custom models may not support tools properly
                try:
                    response = ollama.chat(
                        model=self.agent.base_model,
                        messages=messages,
                        tools=tools,
                        stream=False,
                    )
                except Exception as tool_error:
                    # Check if model doesn't support tools
                    error_msg = str(tool_error).lower()
                    if "does not support tools" in error_msg:
                        # Fall back to streaming without tools
                        tools = []
                        for chunk in self._stream_response(messages):
                            response_chunks.append(chunk)
                        return response_chunks
                    raise

                message = response.get("message", {})
                tool_calls = message.get("tool_calls", [])

                if not tool_calls:
                    # No tool calls - collect the final response
                    response_content = message.get("content", "")
                    if response_content:
                        # Collect response character by character
                        for char in response_content:
                            response_chunks.append(char)
                        # Save to history (only final assistant response)
                        self.history.messages.append(
                            Message(
                                role="assistant",
                                content=response_content,
                                timestamp=datetime.now(),
                            )
                        )
                    return response_chunks

                # Execute tool calls
                # Add assistant message with tool calls to messages (not to history)
                messages.append(message)

                for call in tool_calls:
                    func = call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", {})

                    # Use async tool execution
                    result = await self._execute_tool_async(name, args)

                    # Add tool result to messages (not to history)
                    # Use tool_name as per Ollama's tool calling format
                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": result if result else "No results returned",
                    })

        except Exception as e:
            # Check for connection errors
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str or "connect" in error_str:
                raise OllamaConnectionError()
            raise

    def _stream_response(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        """Stream response without tools.

        Args:
            messages: Messages to send to Ollama.

        Yields:
            Response chunks.
        """
        stream = ollama.chat(
            model=self.agent.name,
            messages=messages,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            chunk_content = chunk.get("message", {}).get("content", "")
            full_response += chunk_content
            yield chunk_content

        self.history.messages.append(
            Message(
                role="assistant",
                content=full_response,
                timestamp=datetime.now(),
            )
        )

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

    @property
    def has_mcp_tools(self) -> bool:
        """Check if MCP tools are available in this session.

        Returns:
            True if MCP manager is connected with tools, False otherwise.
        """
        return self._mcp_manager is not None and len(self._mcp_manager.tool_registry) > 0

    def get_display_name(self) -> str:
        """Get the display name of the current agent.

        Returns:
            The agent's display name, or empty string if no session is active.
        """
        if self.agent is None:
            return ""
        return self.agent.display_name
