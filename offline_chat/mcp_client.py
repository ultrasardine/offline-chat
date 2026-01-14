"""MCP Client for connecting to and communicating with MCP servers.

This module provides the MCPClient class for managing connections to MCP servers
via stdio transport, discovering tools, and executing tool calls.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from offline_chat.mcp_config import MCPServerConfig

logger = logging.getLogger(__name__)


def convert_mcp_tool_to_ollama(mcp_tool: Any) -> dict[str, Any]:
    """Convert MCP tool schema to Ollama-compatible format.

    Args:
        mcp_tool: Tool object from MCP server with name, description, and inputSchema.

    Returns:
        Ollama-compatible tool schema dictionary.
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": mcp_tool.inputSchema
            if mcp_tool.inputSchema
            else {"type": "object", "properties": {}, "required": []},
        },
    }


class MCPClient:
    """Client for connecting to and communicating with an MCP server.

    Uses stdio transport to communicate with the server process.
    Implements async context manager protocol for resource management.

    Attributes:
        config: The server configuration.
        session: The MCP ClientSession (set after connect).
        tools: List of available tools from this server in Ollama format.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """Initialize with server configuration.

        Args:
            config: The MCP server configuration.
        """
        self.config = config
        self.session: ClientSession | None = None
        self.tools: list[dict[str, Any]] = []
        self._exit_stack: AsyncExitStack | None = None
        self._connected: bool = False

    async def __aenter__(self) -> "MCPClient":
        """Connect to the MCP server when entering async context.

        Returns:
            Self after successful connection.
        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Disconnect from the MCP server when exiting async context."""
        await self.disconnect()

    async def connect(self) -> bool:
        """Establish connection to the MCP server.

        Launches the server process and initializes the MCP session.
        After successful connection, retrieves the list of available tools.

        Returns:
            True if connection successful, False otherwise.
        """
        if self._connected:
            return True

        if self.config.disabled:
            logger.info(f"MCP server '{self.config.name}' is disabled, skipping connection")
            return False

        try:
            # Create server parameters for stdio connection
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env if self.config.env else None,
            )

            # Create exit stack for managing async contexts
            self._exit_stack = AsyncExitStack()

            # Enter the stdio client context
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            # Create and enter the client session context
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the session
            await self.session.initialize()

            # Retrieve available tools
            await self._fetch_tools()

            self._connected = True
            logger.info(
                f"Connected to MCP server '{self.config.name}' with {len(self.tools)} tools"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.config.name}': {e}")
            # Clean up on failure
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            self.session = None
            return False

    async def disconnect(self) -> None:
        """Close the connection to the MCP server.

        Cleans up all resources including the session and server process.
        """
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during disconnect from '{self.config.name}': {e}")
            finally:
                self._exit_stack = None
                self.session = None
                self._connected = False
                self.tools = []
                logger.info(f"Disconnected from MCP server '{self.config.name}'")

    async def _fetch_tools(self) -> None:
        """Fetch and convert tools from the MCP server.

        Retrieves the list of tools from the server and converts them
        to Ollama-compatible format.
        """
        if not self.session:
            return

        try:
            response = await self.session.list_tools()
            self.tools = [convert_mcp_tool_to_ollama(tool) for tool in response.tools]
        except Exception as e:
            logger.error(f"Failed to fetch tools from '{self.config.name}': {e}")
            self.tools = []

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the server.

        Returns:
            List of tool schemas in Ollama-compatible format.
        """
        if not self._connected:
            return []
        return self.tools.copy()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool on the server.

        Args:
            name: The tool name.
            arguments: Tool arguments as a dictionary.

        Returns:
            Tool execution result as string.

        Raises:
            RuntimeError: If not connected or tool execution fails.
        """
        if not self.session or not self._connected:
            raise RuntimeError(f"Not connected to MCP server '{self.config.name}'")

        try:
            result = await self.session.call_tool(name, arguments)

            # Extract text content from the result
            if result.content:
                # MCP returns content as a list of content items
                text_parts = []
                for content_item in result.content:
                    if hasattr(content_item, "text"):
                        text_parts.append(content_item.text)
                    elif hasattr(content_item, "data"):
                        # Handle binary/blob content
                        text_parts.append(f"[Binary data: {len(content_item.data)} bytes]")
                    else:
                        text_parts.append(str(content_item))
                return "\n".join(text_parts) if text_parts else ""
            return ""

        except Exception as e:
            error_msg = f"Tool '{name}' execution failed on server '{self.config.name}': {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"


class MCPClientManager:
    """Manages connections to multiple MCP servers.

    Handles connecting to all configured servers, aggregating tools,
    and routing tool calls to the appropriate server.

    Attributes:
        configs: List of MCP server configurations.
        clients: Dictionary mapping server names to connected clients.
        tool_registry: Dictionary mapping tool names to server names.
    """

    def __init__(self, configs: list[MCPServerConfig]) -> None:
        """Initialize with server configurations.

        Args:
            configs: List of MCP server configurations.
        """
        self.configs = configs
        self.clients: dict[str, MCPClient] = {}
        self.tool_registry: dict[str, str] = {}

    async def __aenter__(self) -> "MCPClientManager":
        """Connect to all configured MCP servers when entering async context.

        Returns:
            Self after attempting connections.
        """
        await self.connect_all()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Disconnect from all MCP servers when exiting async context."""
        await self.disconnect_all()

    async def connect_all(self) -> None:
        """Connect to all enabled MCP servers.

        Logs errors for servers that fail to connect but continues
        with remaining servers. After successful connections, builds
        the tool registry mapping tool names to server names.
        """
        for config in self.configs:
            if config.disabled:
                logger.info(f"MCP server '{config.name}' is disabled, skipping")
                continue

            client = MCPClient(config)
            try:
                success = await client.connect()
                if success:
                    self.clients[config.name] = client
                    # Register tools from this server
                    for tool in client.tools:
                        tool_name = tool["function"]["name"]
                        if tool_name in self.tool_registry:
                            logger.warning(
                                f"Tool '{tool_name}' from server '{config.name}' "
                                f"conflicts with existing tool from server "
                                f"'{self.tool_registry[tool_name]}'. Using first registered."
                            )
                        else:
                            self.tool_registry[tool_name] = config.name
                    logger.info(
                        f"Connected to MCP server '{config.name}' "
                        f"with {len(client.tools)} tools"
                    )
                else:
                    logger.warning(f"Failed to connect to MCP server '{config.name}'")
            except Exception as e:
                logger.error(f"Error connecting to MCP server '{config.name}': {e}")

    async def disconnect_all(self) -> None:
        """Disconnect from all connected MCP servers.

        Cleans up all client connections and clears the tool registry.
        """
        for server_name, client in list(self.clients.items()):
            try:
                await client.disconnect()
                logger.info(f"Disconnected from MCP server '{server_name}'")
            except Exception as e:
                logger.warning(f"Error disconnecting from '{server_name}': {e}")

        self.clients.clear()
        self.tool_registry.clear()

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get combined tools from all connected servers.

        Returns:
            List of all tool schemas in Ollama-compatible format.
            Tools are aggregated from all connected servers.
        """
        all_tools: list[dict[str, Any]] = []
        for client in self.clients.values():
            all_tools.extend(client.tools)
        return all_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Route and execute a tool call.

        Routes the tool call to the server that registered the tool
        and returns the execution result.

        Args:
            name: The tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result as string.

        Raises:
            ValueError: If tool not found in any connected server.
        """
        if name not in self.tool_registry:
            raise ValueError(f"Tool '{name}' not found in any connected MCP server")

        server_name = self.tool_registry[name]
        if server_name not in self.clients:
            raise ValueError(
                f"Server '{server_name}' for tool '{name}' is not connected"
            )

        client = self.clients[server_name]
        return await client.call_tool(name, arguments)
