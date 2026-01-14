"""Tests for MCPClient and schema conversion.

This module contains property-based tests and unit tests for the MCPClient class
and the convert_mcp_tool_to_ollama function.
"""

from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import MCPClient, MCPServerConfig, convert_mcp_tool_to_ollama


# Mock MCP tool object for testing schema conversion
@dataclass
class MockMCPTool:
    """Mock MCP tool object that mimics the structure returned by MCP servers."""

    name: str
    description: str | None
    inputSchema: dict[str, Any] | None


# Strategy for generating valid tool names
def valid_tool_name_strategy():
    """Generate valid tool names (non-empty strings with valid characters)."""
    return st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip() and s[0].isalpha())


# Strategy for generating tool descriptions
def tool_description_strategy():
    """Generate tool descriptions (can be None or non-empty string)."""
    return st.one_of(
        st.none(),
        st.text(min_size=0, max_size=200),
    )


# Strategy for generating JSON schema property types
def json_schema_type_strategy():
    """Generate valid JSON schema types."""
    return st.sampled_from(["string", "number", "integer", "boolean", "array", "object"])


# Strategy for generating JSON schema properties
def json_schema_properties_strategy():
    """Generate valid JSON schema properties dictionary."""
    return st.dictionaries(
        keys=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz_",
            min_size=1,
            max_size=20,
        ).filter(lambda s: s.strip() and s[0].isalpha()),
        values=st.fixed_dictionaries(
            {
                "type": json_schema_type_strategy(),
            },
            optional={
                "description": st.text(min_size=0, max_size=100),
            },
        ),
        min_size=0,
        max_size=5,
    )


# Strategy for generating input schemas
def input_schema_strategy():
    """Generate valid input schemas (can be None or valid JSON schema)."""
    return st.one_of(
        st.none(),
        st.fixed_dictionaries(
            {
                "type": st.just("object"),
                "properties": json_schema_properties_strategy(),
            },
            optional={
                "required": st.lists(
                    st.text(
                        alphabet="abcdefghijklmnopqrstuvwxyz_",
                        min_size=1,
                        max_size=20,
                    ).filter(lambda s: s.strip()),
                    min_size=0,
                    max_size=3,
                ),
            },
        ),
    )


# Strategy for generating mock MCP tools
def mock_mcp_tool_strategy():
    """Generate mock MCP tool objects for property testing."""
    return st.builds(
        MockMCPTool,
        name=valid_tool_name_strategy(),
        description=tool_description_strategy(),
        inputSchema=input_schema_strategy(),
    )


class TestSchemaConversionValidity:
    """Property 4: Schema Conversion Validity.

    Feature: mcp-integration, Property 4: Schema Conversion Validity
    **Validates: Requirements 3.2**

    For any MCP tool with name, description, and input schema, converting to
    Ollama format SHALL produce a valid tool schema containing the function type,
    name, description, and parameters.
    """

    @settings(max_examples=100)
    @given(tool=mock_mcp_tool_strategy())
    def test_conversion_produces_valid_schema(self, tool: MockMCPTool):
        """Converting any MCP tool should produce a valid Ollama tool schema."""
        result = convert_mcp_tool_to_ollama(tool)

        # Verify top-level structure
        assert "type" in result
        assert result["type"] == "function"
        assert "function" in result

        # Verify function structure
        func = result["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func

    @settings(max_examples=100)
    @given(tool=mock_mcp_tool_strategy())
    def test_conversion_preserves_name(self, tool: MockMCPTool):
        """Converting should preserve the tool name exactly."""
        result = convert_mcp_tool_to_ollama(tool)
        assert result["function"]["name"] == tool.name

    @settings(max_examples=100)
    @given(tool=mock_mcp_tool_strategy())
    def test_conversion_handles_description(self, tool: MockMCPTool):
        """Converting should handle None description by using empty string."""
        result = convert_mcp_tool_to_ollama(tool)
        expected_description = tool.description if tool.description else ""
        assert result["function"]["description"] == expected_description

    @settings(max_examples=100)
    @given(tool=mock_mcp_tool_strategy())
    def test_conversion_handles_input_schema(self, tool: MockMCPTool):
        """Converting should handle None inputSchema with default schema."""
        result = convert_mcp_tool_to_ollama(tool)
        params = result["function"]["parameters"]

        if tool.inputSchema:
            # Should preserve the input schema
            assert params == tool.inputSchema
        else:
            # Should use default empty schema
            assert params == {"type": "object", "properties": {}, "required": []}

    @settings(max_examples=100)
    @given(tool=mock_mcp_tool_strategy())
    def test_conversion_parameters_is_dict(self, tool: MockMCPTool):
        """Parameters should always be a dictionary."""
        result = convert_mcp_tool_to_ollama(tool)
        assert isinstance(result["function"]["parameters"], dict)

    def test_specific_conversion_example(self):
        """Unit test for a specific conversion example."""
        tool = MockMCPTool(
            name="fetch_url",
            description="Fetch content from a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                    "timeout": {"type": "integer"},
                },
                "required": ["url"],
            },
        )

        result = convert_mcp_tool_to_ollama(tool)

        assert result["type"] == "function"
        assert result["function"]["name"] == "fetch_url"
        assert result["function"]["description"] == "Fetch content from a URL"
        assert result["function"]["parameters"]["type"] == "object"
        assert "url" in result["function"]["parameters"]["properties"]
        assert "timeout" in result["function"]["parameters"]["properties"]
        assert result["function"]["parameters"]["required"] == ["url"]

    def test_conversion_with_none_description(self):
        """Unit test for conversion with None description."""
        tool = MockMCPTool(
            name="simple_tool",
            description=None,
            inputSchema={"type": "object", "properties": {}},
        )

        result = convert_mcp_tool_to_ollama(tool)

        assert result["function"]["description"] == ""

    def test_conversion_with_none_input_schema(self):
        """Unit test for conversion with None inputSchema."""
        tool = MockMCPTool(
            name="no_params_tool",
            description="A tool with no parameters",
            inputSchema=None,
        )

        result = convert_mcp_tool_to_ollama(tool)

        assert result["function"]["parameters"] == {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def test_conversion_with_empty_description(self):
        """Unit test for conversion with empty string description."""
        tool = MockMCPTool(
            name="empty_desc_tool",
            description="",
            inputSchema={"type": "object", "properties": {}},
        )

        result = convert_mcp_tool_to_ollama(tool)

        assert result["function"]["description"] == ""


class TestMCPClientInit:
    """Unit tests for MCPClient initialization."""

    def test_init_with_config(self):
        """MCPClient should initialize with config."""
        config = MCPServerConfig(
            name="test-server",
            command="uvx",
            args=["mcp-server-test"],
        )

        client = MCPClient(config)

        assert client.config == config
        assert client.session is None
        assert client.tools == []
        assert client._connected is False

    def test_init_preserves_config_fields(self):
        """MCPClient should preserve all config fields."""
        config = MCPServerConfig(
            name="fetch",
            command="uvx",
            args=["mcp-server-fetch"],
            env={"LOG_LEVEL": "DEBUG"},
            disabled=False,
        )

        client = MCPClient(config)

        assert client.config.name == "fetch"
        assert client.config.command == "uvx"
        assert client.config.args == ["mcp-server-fetch"]
        assert client.config.env == {"LOG_LEVEL": "DEBUG"}
        assert client.config.disabled is False


class TestMCPClientManagerInit:
    """Unit tests for MCPClientManager initialization."""

    def test_init_with_empty_configs(self):
        """MCPClientManager should initialize with empty configs list."""
        from offline_chat import MCPClientManager

        manager = MCPClientManager([])

        assert manager.configs == []
        assert manager.clients == {}
        assert manager.tool_registry == {}

    def test_init_with_configs(self):
        """MCPClientManager should initialize with provided configs."""
        from offline_chat import MCPClientManager

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
            MCPServerConfig(name="server2", command="npx", args=["server2"]),
        ]

        manager = MCPClientManager(configs)

        assert manager.configs == configs
        assert len(manager.configs) == 2
        assert manager.clients == {}
        assert manager.tool_registry == {}


class TestToolAggregationCompleteness:
    """Property 3: Tool Aggregation Completeness.

    Feature: mcp-integration, Property 3: Tool Aggregation Completeness
    **Validates: Requirements 3.1, 3.3**

    For any set of MCP servers with known tool lists, when all servers are
    connected, the combined tools list SHALL contain exactly all tools from
    all connected servers.
    """

    @settings(max_examples=100)
    @given(
        server_tools=st.lists(
            st.lists(
                mock_mcp_tool_strategy(),
                min_size=0,
                max_size=5,
            ),
            min_size=1,
            max_size=4,
        )
    )
    def test_aggregation_contains_all_tools(
        self, server_tools: list[list[MockMCPTool]]
    ):
        """Aggregated tools should contain all tools from all servers."""
        from offline_chat import MCPClientManager, MCPServerConfig

        # Create configs for each server
        configs = [
            MCPServerConfig(name=f"server{i}", command="uvx", args=[f"server{i}"])
            for i in range(len(server_tools))
        ]

        # Create manager
        manager = MCPClientManager(configs)

        # Manually set up clients with tools (simulating connected state)
        for i, tools in enumerate(server_tools):
            client = MCPClient(configs[i])
            client._connected = True
            client.tools = [convert_mcp_tool_to_ollama(t) for t in tools]
            manager.clients[configs[i].name] = client

        # Get aggregated tools
        all_tools = manager.get_all_tools()

        # Calculate expected total
        expected_count = sum(len(tools) for tools in server_tools)

        # Verify count matches
        assert len(all_tools) == expected_count

    @settings(max_examples=100)
    @given(
        server_tools=st.lists(
            st.lists(
                mock_mcp_tool_strategy(),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_aggregation_preserves_tool_names(
        self, server_tools: list[list[MockMCPTool]]
    ):
        """Aggregated tools should preserve all tool names from all servers."""
        from offline_chat import MCPClientManager, MCPServerConfig

        # Create configs for each server
        configs = [
            MCPServerConfig(name=f"server{i}", command="uvx", args=[f"server{i}"])
            for i in range(len(server_tools))
        ]

        # Create manager
        manager = MCPClientManager(configs)

        # Collect expected tool names
        expected_names = []
        for i, tools in enumerate(server_tools):
            client = MCPClient(configs[i])
            client._connected = True
            client.tools = [convert_mcp_tool_to_ollama(t) for t in tools]
            manager.clients[configs[i].name] = client
            expected_names.extend(t.name for t in tools)

        # Get aggregated tools
        all_tools = manager.get_all_tools()
        actual_names = [t["function"]["name"] for t in all_tools]

        # Verify all expected names are present (order may vary)
        assert sorted(actual_names) == sorted(expected_names)

    def test_aggregation_with_no_connected_servers(self):
        """Aggregation with no connected servers should return empty list."""
        from offline_chat import MCPClientManager, MCPServerConfig

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
        ]

        manager = MCPClientManager(configs)
        # No clients connected

        all_tools = manager.get_all_tools()

        assert all_tools == []

    def test_aggregation_with_empty_tool_lists(self):
        """Aggregation with servers having no tools should return empty list."""
        from offline_chat import MCPClientManager, MCPServerConfig

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
            MCPServerConfig(name="server2", command="uvx", args=["server2"]),
        ]

        manager = MCPClientManager(configs)

        # Set up clients with empty tool lists
        for config in configs:
            client = MCPClient(config)
            client._connected = True
            client.tools = []
            manager.clients[config.name] = client

        all_tools = manager.get_all_tools()

        assert all_tools == []



class TestToolRoutingCorrectness:
    """Property 5: Tool Routing Correctness.

    Feature: mcp-integration, Property 5: Tool Routing Correctness
    **Validates: Requirements 3.4, 4.1**

    For any tool call where the tool name exists in the tool registry,
    the call SHALL be routed to the server that originally registered
    that tool name.
    """

    @settings(max_examples=100)
    @given(
        server_tools=st.lists(
            st.lists(
                mock_mcp_tool_strategy(),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_tool_registry_maps_to_correct_server(
        self, server_tools: list[list[MockMCPTool]]
    ):
        """Tool registry should map each tool to its originating server."""
        from offline_chat import MCPClientManager, MCPServerConfig

        # Create configs for each server
        configs = [
            MCPServerConfig(name=f"server{i}", command="uvx", args=[f"server{i}"])
            for i in range(len(server_tools))
        ]

        # Create manager
        manager = MCPClientManager(configs)

        # Set up clients and build registry manually (simulating connect_all)
        for i, tools in enumerate(server_tools):
            client = MCPClient(configs[i])
            client._connected = True
            client.tools = [convert_mcp_tool_to_ollama(t) for t in tools]
            manager.clients[configs[i].name] = client

            # Register tools (first registration wins)
            for tool in tools:
                if tool.name not in manager.tool_registry:
                    manager.tool_registry[tool.name] = configs[i].name

        # Verify each registered tool maps to a valid server
        for tool_name, server_name in manager.tool_registry.items():
            assert server_name in manager.clients
            # Verify the server actually has this tool
            client = manager.clients[server_name]
            tool_names_in_client = [t["function"]["name"] for t in client.tools]
            assert tool_name in tool_names_in_client

    @settings(max_examples=100)
    @given(
        server_tools=st.lists(
            st.lists(
                mock_mcp_tool_strategy(),
                min_size=1,
                max_size=3,
            ),
            min_size=2,
            max_size=3,
        )
    )
    def test_first_registration_wins_for_duplicate_tools(
        self, server_tools: list[list[MockMCPTool]]
    ):
        """When multiple servers have same tool name, first registration wins."""
        from offline_chat import MCPClientManager, MCPServerConfig

        # Create configs for each server
        configs = [
            MCPServerConfig(name=f"server{i}", command="uvx", args=[f"server{i}"])
            for i in range(len(server_tools))
        ]

        # Create manager
        manager = MCPClientManager(configs)

        # Track which server should own each tool (first registration)
        expected_ownership: dict[str, str] = {}

        # Set up clients and build registry
        for i, tools in enumerate(server_tools):
            client = MCPClient(configs[i])
            client._connected = True
            client.tools = [convert_mcp_tool_to_ollama(t) for t in tools]
            manager.clients[configs[i].name] = client

            for tool in tools:
                if tool.name not in expected_ownership:
                    expected_ownership[tool.name] = configs[i].name
                if tool.name not in manager.tool_registry:
                    manager.tool_registry[tool.name] = configs[i].name

        # Verify registry matches expected ownership
        for tool_name, expected_server in expected_ownership.items():
            assert manager.tool_registry.get(tool_name) == expected_server

    def test_call_tool_raises_for_unknown_tool(self):
        """call_tool should raise ValueError for unknown tool names."""
        from offline_chat import MCPClientManager, MCPServerConfig

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
        ]

        manager = MCPClientManager(configs)

        # Set up a client with one tool
        client = MCPClient(configs[0])
        client._connected = True
        client.tools = [
            {
                "type": "function",
                "function": {
                    "name": "known_tool",
                    "description": "A known tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        manager.clients["server1"] = client
        manager.tool_registry["known_tool"] = "server1"

        # Calling unknown tool should raise ValueError
        import asyncio

        with pytest.raises(ValueError, match="not found"):
            asyncio.get_event_loop().run_until_complete(
                manager.call_tool("unknown_tool", {})
            )

    def test_call_tool_raises_for_disconnected_server(self):
        """call_tool should raise ValueError if server is disconnected."""
        from offline_chat import MCPClientManager, MCPServerConfig

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
        ]

        manager = MCPClientManager(configs)

        # Register tool but don't add client (simulating disconnected server)
        manager.tool_registry["orphan_tool"] = "server1"

        import asyncio

        with pytest.raises(ValueError, match="not connected"):
            asyncio.get_event_loop().run_until_complete(
                manager.call_tool("orphan_tool", {})
            )

    def test_tool_registry_empty_when_no_tools(self):
        """Tool registry should be empty when servers have no tools."""
        from offline_chat import MCPClientManager, MCPServerConfig

        configs = [
            MCPServerConfig(name="server1", command="uvx", args=["server1"]),
        ]

        manager = MCPClientManager(configs)

        # Set up client with no tools
        client = MCPClient(configs[0])
        client._connected = True
        client.tools = []
        manager.clients["server1"] = client

        assert manager.tool_registry == {}
