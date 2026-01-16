"""Property-based tests for database tool discovery and registration.

This module tests the tool discovery and registration behavior when
database MCP servers are configured, including tool namespacing for
multiple databases.
"""

from dataclasses import dataclass
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import MCPClient, MCPClientManager, MCPServerConfig


# Mock MCP tool object for testing
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


# Strategy for generating database tool names (common database operations)
def database_tool_name_strategy():
    """Generate realistic database tool names."""
    return st.sampled_from(
        [
            "run-sql",
            "list-connections",
            "query_database",
            "list_tables",
            "describe_table",
            "get_schema",
            "execute_query",
        ]
    )


# Strategy for generating tool descriptions
def tool_description_strategy():
    """Generate tool descriptions (can be None or non-empty string)."""
    return st.one_of(
        st.none(),
        st.text(min_size=1, max_size=200),
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


# Strategy for generating mock database tools
def mock_database_tool_strategy():
    """Generate mock database tool objects for property testing."""
    return st.builds(
        MockMCPTool,
        name=database_tool_name_strategy(),
        description=tool_description_strategy(),
        inputSchema=input_schema_strategy(),
    )


# Strategy for generating database server configs
def database_server_config_strategy():
    """Generate database server configurations."""
    db_types = st.sampled_from(["sqlite", "postgresql", "mysql", "oracle"])
    server_names = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=20,
    ).filter(lambda s: s.strip() and s[0].isalpha())

    return st.builds(
        MCPServerConfig,
        name=server_names,
        command=st.just("uvx"),
        args=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=3),
        env=st.just({}),
        disabled=st.just(False),
        database_type=db_types,
    )


class TestToolRegistrationOnSessionStart:
    """Property 35: Tool registration on session start.

    Feature: database-access, Property 35: Tool registration on session start
    **Validates: Requirements 10.1**

    For any agent with database access, starting a chat session should result
    in database tools being registered with the tool calling system.
    """

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,  # Ensure unique tool names
        )
    )
    def test_database_tools_registered_after_connection(self, db_tools: list[MockMCPTool]):
        """Database tools should be registered after server connection."""
        from offline_chat import convert_mcp_tool_to_ollama

        # Create a database server config
        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        # Create manager
        manager = MCPClientManager([config])

        # Simulate connected client with database tools
        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Register tools
        manager._register_tools_with_namespacing()

        # Verify all unique tools are registered
        assert len(manager.tool_registry) == len(db_tools)

        # Verify each tool is in the registry
        for tool in db_tools:
            assert tool.name in manager.tool_registry

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,  # Ensure unique tool names
        )
    )
    def test_tool_registry_maps_to_database_server(self, db_tools: list[MockMCPTool]):
        """Tool registry should map database tools to their database server."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="prod_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        manager._register_tools_with_namespacing()

        # Verify all tools map to the correct server
        for tool in db_tools:
            assert manager.tool_registry[tool.name] == "prod_db"


class TestDatabaseToolsInToolList:
    """Property 36: Database tools in tool list.

    Feature: database-access, Property 36: Database tools in tool list
    **Validates: Requirements 10.2**

    For any agent session with database access, requesting available tools
    should return a list that includes all database tools.
    """

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,
        )
    )
    def test_get_all_tools_includes_database_tools(self, db_tools: list[MockMCPTool]):
        """get_all_tools should include all database tools."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="analytics_db",
            command="uvx",
            args=["postgres-mcp-server"],
            database_type="postgresql",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify count matches
        assert len(all_tools) == len(db_tools)

        # Verify all tool names are present
        tool_names = [t["function"]["name"] for t in all_tools]
        expected_names = [t.name for t in db_tools]
        assert sorted(tool_names) == sorted(expected_names)

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
        regular_tools=st.lists(
            st.builds(
                MockMCPTool,
                name=valid_tool_name_strategy(),
                description=tool_description_strategy(),
                inputSchema=input_schema_strategy(),
            ),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
    )
    def test_get_all_tools_includes_both_database_and_regular_tools(
        self, db_tools: list[MockMCPTool], regular_tools: list[MockMCPTool]
    ):
        """get_all_tools should include both database and regular MCP tools."""
        from offline_chat import convert_mcp_tool_to_ollama

        db_config = MCPServerConfig(
            name="data_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        regular_config = MCPServerConfig(
            name="fetch",
            command="uvx",
            args=["mcp-server-fetch"],
        )

        manager = MCPClientManager([db_config, regular_config])

        # Set up database client
        db_client = MCPClient(db_config)
        db_client._connected = True
        db_client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[db_config.name] = db_client

        # Set up regular client
        regular_client = MCPClient(regular_config)
        regular_client._connected = True
        regular_client.tools = [convert_mcp_tool_to_ollama(t) for t in regular_tools]
        manager.clients[regular_config.name] = regular_client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify total count
        expected_count = len(db_tools) + len(regular_tools)
        assert len(all_tools) == expected_count


class TestToolDescriptionsPresent:
    """Property 37: Tool descriptions present.

    Feature: database-access, Property 37: Tool descriptions present
    **Validates: Requirements 10.3**

    For any registered database tool, the tool definition should include
    a non-empty description field.
    """

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,
        )
    )
    def test_database_tools_have_descriptions(self, db_tools: list[MockMCPTool]):
        """All database tools should have description fields."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify all tools have description field
        for tool in all_tools:
            assert "description" in tool["function"]
            # Description should be a string (may be empty if original was None)
            assert isinstance(tool["function"]["description"], str)

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            st.builds(
                MockMCPTool,
                name=database_tool_name_strategy(),
                description=st.text(min_size=1, max_size=200),  # Non-None descriptions
                inputSchema=input_schema_strategy(),
            ),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,
        )
    )
    def test_database_tools_preserve_non_empty_descriptions(self, db_tools: list[MockMCPTool]):
        """Database tools with non-None descriptions should preserve them."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify descriptions are preserved
        for i, tool in enumerate(all_tools):
            expected_desc = db_tools[i].description
            assert tool["function"]["description"] == expected_desc


class TestToolNamespacingForMultipleDatabases:
    """Property 38: Tool namespacing for multiple databases.

    Feature: database-access, Property 38: Tool namespacing for multiple databases
    **Validates: Requirements 10.4**

    For any agent with N databases configured where N > 1, the registered
    tools should be namespaced by database name to prevent conflicts.
    """

    @settings(max_examples=100)
    @given(
        num_databases=st.integers(min_value=2, max_value=4),
        tools_per_db=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
    )
    def test_multiple_databases_have_namespaced_tools(
        self, num_databases: int, tools_per_db: list[MockMCPTool]
    ):
        """Tools from multiple databases should be namespaced with database name."""
        from offline_chat import convert_mcp_tool_to_ollama

        # Create multiple database configs
        configs = [
            MCPServerConfig(
                name=f"db{i}",
                command="uvx",
                args=["sqlite-mcp-server"],
                database_type="sqlite",
            )
            for i in range(num_databases)
        ]

        manager = MCPClientManager(configs)

        # Set up clients with the same tools
        for config in configs:
            client = MCPClient(config)
            client._connected = True
            client.tools = [convert_mcp_tool_to_ollama(t) for t in tools_per_db]
            manager.clients[config.name] = client

        # Register tools with namespacing
        manager._register_tools_with_namespacing()

        # Verify tools are namespaced
        for config in configs:
            for tool in tools_per_db:
                # Tool should be registered with database name prefix
                namespaced_name = f"{config.name}_{tool.name}"
                assert namespaced_name in manager.tool_registry
                assert manager.tool_registry[namespaced_name] == config.name

    @settings(max_examples=100)
    @given(
        tools_per_db=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
    )
    def test_single_database_uses_original_tool_names(self, tools_per_db: list[MockMCPTool]):
        """Tools from a single database should use original names without namespacing."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="only_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in tools_per_db]
        manager.clients[config.name] = client

        # Register tools
        manager._register_tools_with_namespacing()

        # Verify tools use original names (no namespacing)
        for tool in tools_per_db:
            assert tool.name in manager.tool_registry
            assert manager.tool_registry[tool.name] == "only_db"

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
        regular_tools=st.lists(
            st.builds(
                MockMCPTool,
                name=valid_tool_name_strategy(),
                description=tool_description_strategy(),
                inputSchema=input_schema_strategy(),
            ),
            min_size=1,
            max_size=3,
            unique_by=lambda t: t.name,
        ),
    )
    def test_regular_mcp_servers_not_namespaced(
        self, db_tools: list[MockMCPTool], regular_tools: list[MockMCPTool]
    ):
        """Regular MCP servers should not have their tools namespaced."""
        from offline_chat import convert_mcp_tool_to_ollama

        db_config = MCPServerConfig(
            name="data_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        regular_config = MCPServerConfig(
            name="fetch",
            command="uvx",
            args=["mcp-server-fetch"],
            # No database_type
        )

        manager = MCPClientManager([db_config, regular_config])

        # Set up database client
        db_client = MCPClient(db_config)
        db_client._connected = True
        db_client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[db_config.name] = db_client

        # Set up regular client
        regular_client = MCPClient(regular_config)
        regular_client._connected = True
        regular_client.tools = [convert_mcp_tool_to_ollama(t) for t in regular_tools]
        manager.clients[regular_config.name] = regular_client

        # Register tools
        manager._register_tools_with_namespacing()

        # Verify regular tools use original names
        for tool in regular_tools:
            assert tool.name in manager.tool_registry
            assert manager.tool_registry[tool.name] == "fetch"

        # Database tools should also use original names (only one database)
        for tool in db_tools:
            assert tool.name in manager.tool_registry


class TestParameterSchemasPresent:
    """Property 39: Parameter schemas present.

    Feature: database-access, Property 39: Parameter schemas present
    **Validates: Requirements 10.5**

    For any registered database tool, the tool definition should include
    a parameter schema that describes all required and optional parameters.
    """

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            mock_database_tool_strategy(),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,
        )
    )
    def test_database_tools_have_parameter_schemas(self, db_tools: list[MockMCPTool]):
        """All database tools should have parameter schema fields."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify all tools have parameters field
        for tool in all_tools:
            assert "parameters" in tool["function"]
            params = tool["function"]["parameters"]
            assert isinstance(params, dict)
            # Should have at least a type field
            assert "type" in params

    @settings(max_examples=100)
    @given(
        db_tools=st.lists(
            st.builds(
                MockMCPTool,
                name=database_tool_name_strategy(),
                description=tool_description_strategy(),
                inputSchema=st.fixed_dictionaries(
                    {
                        "type": st.just("object"),
                        "properties": json_schema_properties_strategy(),
                        "required": st.lists(
                            st.text(
                                alphabet="abcdefghijklmnopqrstuvwxyz_",
                                min_size=1,
                                max_size=20,
                            ).filter(lambda s: s.strip()),
                            min_size=0,
                            max_size=3,
                        ),
                    }
                ),
            ),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t.name,
        )
    )
    def test_database_tools_preserve_parameter_schemas(self, db_tools: list[MockMCPTool]):
        """Database tools should preserve their parameter schemas."""
        from offline_chat import convert_mcp_tool_to_ollama

        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(t) for t in db_tools]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify parameter schemas are preserved
        for i, tool in enumerate(all_tools):
            expected_schema = db_tools[i].inputSchema
            actual_schema = tool["function"]["parameters"]
            assert actual_schema == expected_schema

    def test_database_tool_with_no_schema_gets_default(self):
        """Database tools with None inputSchema should get default empty schema."""
        from offline_chat import convert_mcp_tool_to_ollama

        tool = MockMCPTool(
            name="simple_query",
            description="Execute a simple query",
            inputSchema=None,
        )

        config = MCPServerConfig(
            name="test_db",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
        )

        manager = MCPClientManager([config])

        client = MCPClient(config)
        client._connected = True
        client.tools = [convert_mcp_tool_to_ollama(tool)]
        manager.clients[config.name] = client

        # Get all tools
        all_tools = manager.get_all_tools()

        # Verify default schema is used
        assert len(all_tools) == 1
        params = all_tools[0]["function"]["parameters"]
        assert params == {"type": "object", "properties": {}, "required": []}
