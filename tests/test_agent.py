"""Tests for Agent data model.

This module contains property-based tests and unit tests for the Agent dataclass.
"""

import re
from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import Agent
from offline_chat.mcp_config import MCPServerConfig


# Strategy for generating valid kebab-case names
def valid_kebab_case_strategy():
    """Generate valid kebab-case strings."""
    # Generate segments of lowercase letters and numbers
    segment = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=1,
        max_size=10,
    )
    # Generate 1-5 segments joined by hyphens
    return st.lists(segment, min_size=1, max_size=5).map(lambda parts: "-".join(parts))


# Strategy for generating invalid names (various invalid patterns)
def invalid_name_strategy():
    """Generate strings that should fail kebab-case validation."""
    return st.one_of(
        # Empty string
        st.just(""),
        # Contains uppercase
        st.text(min_size=1).filter(lambda s: any(c.isupper() for c in s)),
        # Contains spaces
        st.text(min_size=1).filter(lambda s: " " in s),
        # Starts with hyphen
        st.text(min_size=1).map(lambda s: "-" + s.lower().replace(" ", "")),
        # Ends with hyphen
        st.text(min_size=1).map(lambda s: s.lower().replace(" ", "") + "-"),
        # Contains consecutive hyphens
        st.text(min_size=1).map(lambda s: s.lower().replace(" ", "") + "--" + "a"),
        # Contains special characters
        st.text(min_size=1).filter(lambda s: any(c in s for c in "!@#$%^&*()+=[]{}|;:',.<>?/~`")),
    )


class TestAgentNameValidation:
    """Property 1: Agent Name Validation.

    Feature: offline-chat, Property 1: Agent Name Validation
    Validates: Requirements 1.2

    For any string input as an agent name, the validation function SHALL accept
    only strings matching the pattern ^[a-z0-9]+(-[a-z0-9]+)*$ (lowercase letters,
    numbers, and hyphens, not starting or ending with hyphen).
    """

    @settings(max_examples=100)
    @given(name=valid_kebab_case_strategy())
    def test_valid_names_are_accepted(self, name: str):
        """Valid kebab-case names should pass validation."""
        agent = Agent(
            name=name,
            display_name="Test",
            base_model="llama3:latest",
            system_prompt="Test prompt",
        )
        assert agent.validate_name() is True

    @settings(max_examples=100)
    @given(name=invalid_name_strategy())
    def test_invalid_names_are_rejected(self, name: str):
        """Invalid names should fail validation."""
        # Skip if the generated string accidentally matches valid pattern
        pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        if re.match(pattern, name):
            return  # Skip this case as it's actually valid

        agent = Agent(
            name=name,
            display_name="Test",
            base_model="llama3:latest",
            system_prompt="Test prompt",
        )
        assert agent.validate_name() is False

    def test_specific_valid_examples(self):
        """Unit tests for specific valid name examples."""
        valid_names = [
            "agent",
            "my-agent",
            "agent1",
            "my-agent-123",
            "a",
            "a1b2c3",
            "test-agent-v2",
        ]
        for name in valid_names:
            agent = Agent(
                name=name,
                display_name="Test",
                base_model="llama3:latest",
                system_prompt="Test",
            )
            assert agent.validate_name() is True, f"Expected '{name}' to be valid"

    def test_specific_invalid_examples(self):
        """Unit tests for specific invalid name examples."""
        invalid_names = [
            "",
            "-agent",
            "agent-",
            "my--agent",
            "My-Agent",
            "my agent",
            "my_agent",
            "agent!",
            "123-",
            "-123",
        ]
        for name in invalid_names:
            agent = Agent(
                name=name,
                display_name="Test",
                base_model="llama3:latest",
                system_prompt="Test",
            )
            assert agent.validate_name() is False, f"Expected '{name}' to be invalid"


# Strategy for generating valid Agent objects
def valid_agent_strategy():
    """Generate valid Agent objects for property testing."""
    return st.builds(
        Agent,
        name=valid_kebab_case_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama", "llama2"]),
        system_prompt=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        web_search_enabled=st.booleans(),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestAgentSerializationRoundTrip:
    """Property 3: Agent Serialization Round-Trip.

    Feature: offline-chat, Property 3: Agent Serialization Round-Trip
    Validates: Requirements 1.4, 2.1

    For any valid Agent object, serializing it to JSON (to_dict) and then
    deserializing (from_dict) SHALL produce an equivalent Agent object with
    all fields preserved.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_serialization_round_trip(self, agent: Agent):
        """Serializing and deserializing an Agent should preserve all fields."""
        # Serialize to dict
        data = agent.to_dict()

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify all fields are preserved
        assert restored.name == agent.name
        assert restored.display_name == agent.display_name
        assert restored.base_model == agent.base_model
        assert restored.system_prompt == agent.system_prompt
        assert restored.temperature == agent.temperature
        assert restored.web_search_enabled == agent.web_search_enabled
        assert restored.created_at == agent.created_at

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_to_dict_contains_all_fields(self, agent: Agent):
        """to_dict should include all required fields."""
        data = agent.to_dict()

        required_fields = [
            "name",
            "display_name",
            "base_model",
            "system_prompt",
            "temperature",
            "web_search_enabled",
            "created_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_specific_round_trip_example(self):
        """Unit test for a specific round-trip example."""
        original = Agent(
            name="german-tutor",
            display_name="German Language Tutor",
            base_model="llama3:latest",
            system_prompt="You are a friendly German language tutor.",
            temperature=0.7,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        restored = Agent.from_dict(data)

        assert restored.name == original.name
        assert restored.display_name == original.display_name
        assert restored.base_model == original.base_model
        assert restored.system_prompt == original.system_prompt
        assert restored.temperature == original.temperature
        assert restored.created_at == original.created_at


class TestAgentSerializationRoundTripExtended:
    """Property 3: Agent Serialization Round-Trip (Extended).

    Feature: web-search, Property 3: Agent Serialization Round-Trip (Extended)
    **Validates: Requirements 4.5**

    For any valid Agent object with web_search_enabled set to either True or False,
    serializing it to dictionary (to_dict) and then deserializing (from_dict) SHALL
    produce an equivalent Agent object with all fields preserved, including
    web_search_enabled.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_web_search_enabled_round_trip(self, agent: Agent):
        """web_search_enabled field should be preserved through serialization."""
        # Serialize to dict
        data = agent.to_dict()

        # Verify web_search_enabled is in serialized data
        assert "web_search_enabled" in data
        assert data["web_search_enabled"] == agent.web_search_enabled

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify web_search_enabled is preserved
        assert restored.web_search_enabled == agent.web_search_enabled

    @settings(max_examples=100)
    @given(
        agent=valid_agent_strategy(),
        web_search_value=st.booleans(),
    )
    def test_web_search_enabled_explicit_values(self, agent: Agent, web_search_value: bool):
        """Explicitly test both True and False values for web_search_enabled."""
        # Create agent with explicit web_search_enabled value
        agent_with_search = Agent(
            name=agent.name,
            display_name=agent.display_name,
            base_model=agent.base_model,
            system_prompt=agent.system_prompt,
            temperature=agent.temperature,
            language=agent.language,
            web_search_enabled=web_search_value,
            created_at=agent.created_at,
        )

        # Serialize and deserialize
        data = agent_with_search.to_dict()
        restored = Agent.from_dict(data)

        # Verify the value is preserved
        assert restored.web_search_enabled == web_search_value

    def test_web_search_enabled_defaults_to_false(self):
        """web_search_enabled should default to False when not in data."""
        data = {
            "name": "test-agent",
            "display_name": "Test Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a test agent.",
            "temperature": 0.7,
            "language": "English",
            "created_at": datetime.now().isoformat(),
            # web_search_enabled intentionally omitted
        }

        agent = Agent.from_dict(data)
        assert agent.web_search_enabled is False

    def test_web_search_enabled_true_preserved(self):
        """Unit test: web_search_enabled=True should be preserved."""
        original = Agent(
            name="research-assistant",
            display_name="Research Assistant",
            base_model="llama3:latest",
            system_prompt="You are a research assistant with web access.",
            temperature=0.7,
            web_search_enabled=True,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        assert data["web_search_enabled"] is True

        restored = Agent.from_dict(data)
        assert restored.web_search_enabled is True

    def test_web_search_enabled_false_preserved(self):
        """Unit test: web_search_enabled=False should be preserved."""
        original = Agent(
            name="offline-assistant",
            display_name="Offline Assistant",
            base_model="llama3:latest",
            system_prompt="You are an offline assistant.",
            temperature=0.7,
            web_search_enabled=False,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        assert data["web_search_enabled"] is False

        restored = Agent.from_dict(data)
        assert restored.web_search_enabled is False


class TestModelfileGeneration:
    """Property 4: Modelfile Generation Correctness.

    Feature: offline-chat, Property 4: Modelfile Generation Correctness
    Validates: Requirements 1.4

    For any valid Agent configuration, the generated Modelfile SHALL contain:
    - A FROM directive with the base_model value
    - A SYSTEM directive with the system_prompt value
    - A PARAMETER temperature directive with the temperature value
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_from_directive(self, agent: Agent):
        """Modelfile should contain FROM directive with base_model."""
        modelfile = agent.to_modelfile()
        assert f"FROM {agent.base_model}" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_system_directive(self, agent: Agent):
        """Modelfile should contain SYSTEM directive with system_prompt."""
        modelfile = agent.to_modelfile()
        # The system prompt is escaped in the modelfile
        assert 'SYSTEM "' in modelfile
        # Verify the modelfile starts with SYSTEM directive after FROM
        assert "SYSTEM" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_temperature_parameter(self, agent: Agent):
        """Modelfile should contain PARAMETER temperature directive."""
        modelfile = agent.to_modelfile()
        assert f"PARAMETER temperature {agent.temperature}" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_structure_is_valid(self, agent: Agent):
        """Modelfile should have valid structure with all directives."""
        modelfile = agent.to_modelfile()
        lines = [line.strip() for line in modelfile.strip().split("\n") if line.strip()]

        # Should have at least 3 non-empty lines: FROM, SYSTEM, PARAMETER
        assert len(lines) >= 3

        # First line should be FROM
        assert lines[0].startswith("FROM ")

        # Should contain SYSTEM directive
        system_lines = [line for line in lines if line.startswith("SYSTEM ")]
        assert len(system_lines) == 1

        # Should contain PARAMETER temperature
        param_lines = [line for line in lines if line.startswith("PARAMETER temperature")]
        assert len(param_lines) == 1

    def test_specific_modelfile_example(self):
        """Unit test for a specific Modelfile generation example."""
        agent = Agent(
            name="german-tutor",
            display_name="German Language Tutor",
            base_model="llama3:latest",
            system_prompt="You are a friendly German language tutor.",
            temperature=0.7,
        )

        modelfile = agent.to_modelfile()

        assert "FROM llama3:latest" in modelfile
        assert 'SYSTEM "You are a friendly German language tutor."' in modelfile
        assert "PARAMETER temperature 0.7" in modelfile

    def test_modelfile_escapes_quotes_in_system_prompt(self):
        """Modelfile should properly escape quotes in system prompt."""
        agent = Agent(
            name="test-agent",
            display_name="Test",
            base_model="llama3:latest",
            system_prompt='Say "hello" to the user.',
            temperature=0.5,
        )

        modelfile = agent.to_modelfile()

        # Quotes should be escaped
        assert '\\"hello\\"' in modelfile
        # The modelfile should still be valid (SYSTEM directive present)
        assert "SYSTEM" in modelfile

    def test_modelfile_escapes_newlines_in_system_prompt(self):
        """Modelfile should properly escape newlines in system prompt."""
        agent = Agent(
            name="test-agent",
            display_name="Test",
            base_model="llama3:latest",
            system_prompt="Line 1\nLine 2\nLine 3",
            temperature=0.5,
        )

        modelfile = agent.to_modelfile()

        # Newlines should be escaped as \n
        assert '\\n' in modelfile
        assert 'Line 1\\nLine 2\\nLine 3' in modelfile
        # Should NOT contain actual newlines in the SYSTEM directive value
        lines = modelfile.split('\n')
        system_line = [line for line in lines if line.startswith('SYSTEM')][0]
        # The SYSTEM line itself should be a single line
        assert system_line.startswith('SYSTEM "')
        assert system_line.endswith('"')

    def test_modelfile_escapes_complex_system_prompt(self):
        """Modelfile should escape complex prompts with multiple special characters."""
        agent = Agent(
            name="test-agent",
            display_name="Test",
            base_model="llama3:latest",
            system_prompt='WRONG:\nUser: "What?"\nYou: "Let me check..." ❌\n\nRIGHT:\nYou: "Answer" ✓',
            temperature=0.5,
        )

        modelfile = agent.to_modelfile()

        # Should escape newlines and quotes
        assert '\\n' in modelfile
        assert '\\"' in modelfile
        # Should preserve unicode characters
        assert '❌' in modelfile
        assert '✓' in modelfile
        # Should be a valid single-line SYSTEM directive
        lines = modelfile.split('\n')
        system_line = [line for line in lines if line.startswith('SYSTEM')][0]
        assert system_line.startswith('SYSTEM "')
        assert system_line.endswith('"')


# Strategy for generating valid MCP server names
def valid_server_name_strategy():
    """Generate valid server names (non-empty strings)."""
    return st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip())


# Strategy for generating valid commands
def valid_command_strategy():
    """Generate valid command strings (non-empty)."""
    return st.sampled_from(["uvx", "npx", "python", "node", "/usr/bin/env"])


# Strategy for generating valid args lists
def valid_args_strategy():
    """Generate valid argument lists."""
    return st.lists(
        st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        min_size=0,
        max_size=10,
    )


# Strategy for generating valid env dicts
def valid_env_strategy():
    """Generate valid environment variable dictionaries."""
    return st.dictionaries(
        keys=st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789",
            min_size=1,
            max_size=30,
        ).filter(lambda s: s and s[0].isalpha()),
        values=st.text(min_size=0, max_size=100),
        min_size=0,
        max_size=5,
    )


# Strategy for generating valid MCPServerConfig objects
def valid_mcp_config_strategy():
    """Generate valid MCPServerConfig objects for property testing."""
    return st.builds(
        MCPServerConfig,
        name=valid_server_name_strategy(),
        command=valid_command_strategy(),
        args=valid_args_strategy(),
        env=valid_env_strategy(),
        disabled=st.booleans(),
    )


# Strategy for generating valid Agent objects with MCP servers
def valid_agent_with_mcp_strategy():
    """Generate valid Agent objects with MCP server configurations."""
    return st.builds(
        Agent,
        name=valid_kebab_case_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama", "llama2"]),
        system_prompt=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        language=st.sampled_from(["English", "German", "Spanish", "French"]),
        web_search_enabled=st.booleans(),
        mcp_servers=st.lists(valid_mcp_config_strategy(), min_size=0, max_size=5),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestAgentMCPServersRoundTrip:
    """Property 2: Agent Configuration Round Trip with MCP Servers.

    Feature: mcp-integration, Property 2: Agent Configuration Round Trip with MCP Servers
    **Validates: Requirements 1.4**

    For any valid Agent object containing zero or more MCP server configurations,
    serializing to dictionary and deserializing back SHALL produce an equivalent
    Agent with equivalent MCP configurations.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_with_mcp_strategy())
    def test_agent_mcp_round_trip(self, agent: Agent):
        """Serializing and deserializing an Agent with MCP configs should preserve all fields."""
        # Serialize to dict
        data = agent.to_dict()

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify all base fields are preserved
        assert restored.name == agent.name
        assert restored.display_name == agent.display_name
        assert restored.base_model == agent.base_model
        assert restored.system_prompt == agent.system_prompt
        assert restored.temperature == agent.temperature
        assert restored.language == agent.language
        assert restored.web_search_enabled == agent.web_search_enabled
        assert restored.created_at == agent.created_at

        # Verify MCP servers are preserved
        assert len(restored.mcp_servers) == len(agent.mcp_servers)
        for original_mcp, restored_mcp in zip(agent.mcp_servers, restored.mcp_servers):
            assert restored_mcp.name == original_mcp.name
            assert restored_mcp.command == original_mcp.command
            assert restored_mcp.args == original_mcp.args
            assert restored_mcp.env == original_mcp.env
            assert restored_mcp.disabled == original_mcp.disabled

    @settings(max_examples=100)
    @given(agent=valid_agent_with_mcp_strategy())
    def test_to_dict_contains_mcp_servers_field(self, agent: Agent):
        """to_dict should include mcp_servers field."""
        data = agent.to_dict()
        assert "mcp_servers" in data
        assert isinstance(data["mcp_servers"], list)
        assert len(data["mcp_servers"]) == len(agent.mcp_servers)

    def test_specific_agent_with_mcp_round_trip(self):
        """Unit test for a specific Agent with MCP servers round-trip."""
        mcp_configs = [
            MCPServerConfig(
                name="fetch",
                command="uvx",
                args=["mcp-server-fetch"],
                env={"FASTMCP_LOG_LEVEL": "ERROR"},
                disabled=False,
            ),
            MCPServerConfig(
                name="filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                env={},
                disabled=False,
            ),
        ]

        original = Agent(
            name="research-assistant",
            display_name="Research Assistant",
            base_model="llama3:latest",
            system_prompt="You are a helpful research assistant.",
            temperature=0.7,
            language="English",
            web_search_enabled=False,
            mcp_servers=mcp_configs,
            created_at=datetime(2025, 1, 14, 10, 0, 0),
        )

        data = original.to_dict()
        restored = Agent.from_dict(data)

        assert restored.name == original.name
        assert len(restored.mcp_servers) == 2
        assert restored.mcp_servers[0].name == "fetch"
        assert restored.mcp_servers[0].command == "uvx"
        assert restored.mcp_servers[1].name == "filesystem"
        expected_args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        assert restored.mcp_servers[1].args == expected_args

    def test_agent_with_empty_mcp_servers_round_trip(self):
        """Unit test for Agent with empty MCP servers list."""
        original = Agent(
            name="simple-agent",
            display_name="Simple Agent",
            base_model="llama3:latest",
            system_prompt="You are a simple agent.",
            temperature=0.5,
            mcp_servers=[],
            created_at=datetime(2025, 1, 14, 10, 0, 0),
        )

        data = original.to_dict()
        restored = Agent.from_dict(data)

        assert restored.mcp_servers == []


class TestAgentBackwardCompatibility:
    """Property 6: Backward Compatibility - Empty MCP Config.

    Feature: mcp-integration, Property 6: Backward Compatibility - Empty MCP Config
    **Validates: Requirements 6.1**

    For any agent configuration dictionary that does not contain an `mcp_servers` field,
    deserializing SHALL result in an agent with an empty MCP servers list (not None, not error).
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_missing_mcp_servers_defaults_to_empty_list(self, agent: Agent):
        """Agent config without mcp_servers should deserialize with empty list."""
        # Serialize to dict and remove mcp_servers field
        data = agent.to_dict()
        del data["mcp_servers"]

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify mcp_servers defaults to empty list
        assert restored.mcp_servers == []
        assert isinstance(restored.mcp_servers, list)

    def test_legacy_agent_config_without_mcp_servers(self):
        """Unit test: legacy agent config without mcp_servers field."""
        legacy_data = {
            "name": "legacy-agent",
            "display_name": "Legacy Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a legacy agent.",
            "temperature": 0.7,
            "language": "English",
            "web_search_enabled": False,
            "created_at": datetime.now().isoformat(),
            # mcp_servers intentionally omitted
        }

        agent = Agent.from_dict(legacy_data)

        assert agent.name == "legacy-agent"
        assert agent.mcp_servers == []
        assert isinstance(agent.mcp_servers, list)

    def test_agent_with_explicit_empty_mcp_servers(self):
        """Unit test: agent config with explicit empty mcp_servers list."""
        data = {
            "name": "new-agent",
            "display_name": "New Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a new agent.",
            "temperature": 0.7,
            "language": "English",
            "web_search_enabled": True,
            "mcp_servers": [],
            "created_at": datetime.now().isoformat(),
        }

        agent = Agent.from_dict(data)

        assert agent.mcp_servers == []
        assert agent.web_search_enabled is True


class TestAgentConnectionAssignments:
    """Tests for agent connection assignments and guidelines.

    Feature: database-connection-management
    **Validates: Requirements 6.3, 12.9, 13.1, 13.8**
    """

    def test_agent_with_connection_assignments(self):
        """Unit test: agent with connection assignments."""
        from offline_chat.database.access_level import AccessLevel
        from offline_chat.database.connection_assignment import AgentConnectionAssignment

        assignments = [
            AgentConnectionAssignment(
                connection_name="prod-db",
                access_level=AccessLevel.READ_ONLY,
                allowed_tables=None
            ),
            AgentConnectionAssignment(
                connection_name="dev-db",
                access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
                allowed_tables=["users", "orders"]
            )
        ]

        agent = Agent(
            name="data-agent",
            display_name="Data Agent",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            connection_assignments=assignments,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        assert len(agent.connection_assignments) == 2
        assert agent.connection_assignments[0].connection_name == "prod-db"
        assert agent.connection_assignments[0].access_level == AccessLevel.READ_ONLY
        assert agent.connection_assignments[1].connection_name == "dev-db"
        assert agent.connection_assignments[1].allowed_tables == ["users", "orders"]

    def test_agent_connection_assignments_serialization(self):
        """Unit test: connection assignments round-trip serialization."""
        from offline_chat.database.access_level import AccessLevel
        from offline_chat.database.connection_assignment import AgentConnectionAssignment

        assignments = [
            AgentConnectionAssignment(
                connection_name="test-db",
                access_level=AccessLevel.READ_WRITE,
                allowed_tables=None
            )
        ]

        original = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            connection_assignments=assignments,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        assert "connection_assignments" in data
        assert len(data["connection_assignments"]) == 1
        assert data["connection_assignments"][0]["connection_name"] == "test-db"
        assert data["connection_assignments"][0]["access_level"] == "read-write"

        restored = Agent.from_dict(data)
        assert len(restored.connection_assignments) == 1
        assert restored.connection_assignments[0].connection_name == "test-db"
        assert restored.connection_assignments[0].access_level == AccessLevel.READ_WRITE

    def test_agent_with_guidelines(self):
        """Unit test: agent with guidelines."""
        guidelines = [
            "Always explain your reasoning",
            "Be concise and clear",
            "Verify facts before responding"
        ]

        agent = Agent(
            name="careful-agent",
            display_name="Careful Agent",
            base_model="llama3:latest",
            system_prompt="You are a careful assistant.",
            guidelines=guidelines,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        assert len(agent.guidelines) == 3
        assert agent.guidelines[0] == "Always explain your reasoning"
        assert agent.guidelines[2] == "Verify facts before responding"

    def test_agent_guidelines_serialization(self):
        """Unit test: guidelines round-trip serialization."""
        guidelines = ["Guideline 1", "Guideline 2"]

        original = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            guidelines=guidelines,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        assert "guidelines" in data
        assert data["guidelines"] == guidelines

        restored = Agent.from_dict(data)
        assert restored.guidelines == guidelines

    def test_get_full_system_prompt_with_guidelines(self):
        """Unit test: get_full_system_prompt includes guidelines."""
        guidelines = [
            "Be helpful",
            "Be accurate",
            "Be concise"
        ]

        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            guidelines=guidelines,
        )

        full_prompt = agent.get_full_system_prompt()

        assert "You are a helpful assistant." in full_prompt
        assert "Guidelines:" in full_prompt
        assert "- Be helpful" in full_prompt
        assert "- Be accurate" in full_prompt
        assert "- Be concise" in full_prompt

    def test_get_full_system_prompt_without_guidelines(self):
        """Unit test: get_full_system_prompt without guidelines returns base prompt."""
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            guidelines=[],
        )

        full_prompt = agent.get_full_system_prompt()

        assert full_prompt == "You are a helpful assistant."
        assert "Guidelines:" not in full_prompt

    def test_backward_compatibility_connection_references_migration(self):
        """Unit test: old connection_references migrated to connection_assignments."""
        from offline_chat.database.access_level import AccessLevel

        legacy_data = {
            "name": "legacy-agent",
            "display_name": "Legacy Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a legacy agent.",
            "temperature": 0.7,
            "language": "English",
            "web_search_enabled": False,
            "connection_references": ["db1", "db2"],
            "created_at": datetime.now().isoformat(),
        }

        agent = Agent.from_dict(legacy_data)

        # Should have migrated to connection_assignments with READ_WRITE access
        assert len(agent.connection_assignments) == 2
        assert agent.connection_assignments[0].connection_name == "db1"
        assert agent.connection_assignments[0].access_level == AccessLevel.READ_WRITE
        assert agent.connection_assignments[1].connection_name == "db2"
        assert agent.connection_assignments[1].access_level == AccessLevel.READ_WRITE

    def test_backward_compatibility_empty_connection_assignments(self):
        """Unit test: missing connection_assignments defaults to empty list."""
        data = {
            "name": "simple-agent",
            "display_name": "Simple Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a simple agent.",
            "temperature": 0.7,
            "language": "English",
            "created_at": datetime.now().isoformat(),
            # connection_assignments intentionally omitted
        }

        agent = Agent.from_dict(data)

        assert agent.connection_assignments == []
        assert isinstance(agent.connection_assignments, list)

    def test_backward_compatibility_empty_guidelines(self):
        """Unit test: missing guidelines defaults to empty list."""
        data = {
            "name": "simple-agent",
            "display_name": "Simple Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a simple agent.",
            "temperature": 0.7,
            "language": "English",
            "created_at": datetime.now().isoformat(),
            # guidelines intentionally omitted
        }

        agent = Agent.from_dict(data)

        assert agent.guidelines == []
        assert isinstance(agent.guidelines, list)

    def test_legacy_fields_preserved_in_serialization(self):
        """Unit test: legacy fields preserved for backward compatibility."""
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            connection_references=["old-db"],
            database_config={"type": "oracle", "host": "localhost"},
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = agent.to_dict()

        assert "connection_references" in data
        assert data["connection_references"] == ["old-db"]
        assert "database_config" in data
        assert data["database_config"]["type"] == "oracle"

    def test_new_and_legacy_fields_coexist(self):
        """Unit test: new connection_assignments and legacy fields can coexist."""
        from offline_chat.database.access_level import AccessLevel
        from offline_chat.database.connection_assignment import AgentConnectionAssignment

        assignments = [
            AgentConnectionAssignment(
                connection_name="new-db",
                access_level=AccessLevel.READ_ONLY,
                allowed_tables=None
            )
        ]

        agent = Agent(
            name="hybrid-agent",
            display_name="Hybrid Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            connection_assignments=assignments,
            connection_references=["old-db"],  # Legacy field
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = agent.to_dict()

        # Both should be present
        assert len(data["connection_assignments"]) == 1
        assert data["connection_references"] == ["old-db"]

        restored = Agent.from_dict(data)
        assert len(restored.connection_assignments) == 1
        assert restored.connection_assignments[0].connection_name == "new-db"


# Strategy for generating valid guideline lists
def valid_guidelines_strategy():
    """Generate valid guideline lists (non-empty strings without newlines)."""
    return st.lists(
        st.text(
            alphabet=st.characters(blacklist_characters="\n\r\t"),
            min_size=1,
            max_size=200
        ).map(lambda s: s.strip()).filter(lambda s: s),
        min_size=0,
        max_size=10,
    )


# Strategy for generating valid Agent objects with guidelines
def valid_agent_with_guidelines_strategy():
    """Generate valid Agent objects with guidelines for property testing."""
    return st.builds(
        Agent,
        name=valid_kebab_case_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama", "llama2"]),
        system_prompt=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        language=st.sampled_from(["English", "German", "Spanish", "French"]),
        web_search_enabled=st.booleans(),
        guidelines=valid_guidelines_strategy(),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestAgentGuidelinesProperties:
    """Property tests for agent guidelines functionality.

    Feature: database-connection-management
    **Validates: Requirements 13.1, 13.4, 13.8, 13.9, 13.10**
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_with_guidelines_strategy())
    def test_property_34_guidelines_storage(self, agent: Agent):
        """Property 34: Guidelines Storage.

        **Validates: Requirements 13.1, 13.4**

        For any agent and list of guidelines, after adding guidelines, the agent
        config should contain exactly those guidelines in the same order.
        """
        # Serialize to dict
        data = agent.to_dict()

        # Verify guidelines field exists and contains the guidelines
        assert "guidelines" in data
        assert isinstance(data["guidelines"], list)
        assert data["guidelines"] == agent.guidelines

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify guidelines are preserved in the same order
        assert len(restored.guidelines) == len(agent.guidelines)
        assert restored.guidelines == agent.guidelines

        # Verify order is preserved
        for i, (original, restored_guideline) in enumerate(zip(agent.guidelines, restored.guidelines)):
            assert restored_guideline == original, f"Guideline at index {i} differs"

    @settings(max_examples=100)
    @given(
        agent=valid_agent_with_guidelines_strategy().filter(lambda a: len(a.guidelines) > 0)
    )
    def test_property_38_guidelines_in_system_prompt(self, agent: Agent):
        """Property 38: Guidelines in System Prompt.

        **Validates: Requirements 13.8, 13.10**

        For any agent with guidelines, the full system prompt should include the
        base system prompt followed by the guidelines formatted as bullet points.
        """
        full_prompt = agent.get_full_system_prompt()

        # Verify base system prompt is included
        assert agent.system_prompt in full_prompt

        # Verify "Guidelines:" header is present
        assert "Guidelines:" in full_prompt

        # Verify each guideline appears as a bullet point
        for guideline in agent.guidelines:
            assert f"- {guideline}" in full_prompt

        # Verify structure: base prompt comes before guidelines
        base_prompt_index = full_prompt.index(agent.system_prompt)
        guidelines_index = full_prompt.index("Guidelines:")
        assert base_prompt_index < guidelines_index

        # Verify guidelines section contains all guidelines in order
        # Split the prompt to get the guidelines section
        guidelines_section = full_prompt.split("Guidelines:")[1]
        guidelines_lines = [line.strip() for line in guidelines_section.split("\n") if line.strip().startswith("- ")]

        # Verify we have the correct number of guideline lines
        assert len(guidelines_lines) == len(agent.guidelines)

        # Verify each guideline appears in the correct position
        for i, guideline in enumerate(agent.guidelines):
            expected_line = f"- {guideline}"
            assert guidelines_lines[i] == expected_line, f"Guideline at index {i} differs"

    @settings(max_examples=100)
    @given(
        agent=valid_agent_with_guidelines_strategy().filter(lambda a: len(a.guidelines) == 0)
    )
    def test_property_39_empty_guidelines_handling(self, agent: Agent):
        """Property 39: Empty Guidelines Handling.

        **Validates: Requirements 13.9**

        For any agent with no guidelines, the full system prompt should be
        identical to the base system prompt.
        """
        full_prompt = agent.get_full_system_prompt()

        # Verify full prompt equals base system prompt exactly
        assert full_prompt == agent.system_prompt

        # Verify no guidelines section is present
        assert "Guidelines:" not in full_prompt
        assert "- " not in full_prompt or agent.system_prompt.count("- ") == full_prompt.count("- ")

        # Verify no extra whitespace or formatting was added
        assert len(full_prompt) == len(agent.system_prompt)

    @settings(max_examples=100)
    @given(
        base_agent=valid_agent_strategy(),
        guidelines=valid_guidelines_strategy().filter(lambda g: len(g) > 0)
    )
    def test_property_34_guidelines_order_preservation(self, base_agent: Agent, guidelines: list[str]):
        """Property 34: Guidelines Storage - Order Preservation.

        **Validates: Requirements 13.1, 13.4**

        Verify that guidelines maintain their exact order through serialization
        and deserialization cycles.
        """
        # Create agent with specific guidelines
        agent = Agent(
            name=base_agent.name,
            display_name=base_agent.display_name,
            base_model=base_agent.base_model,
            system_prompt=base_agent.system_prompt,
            temperature=base_agent.temperature,
            guidelines=guidelines,
            created_at=base_agent.created_at,
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify exact order preservation
        assert restored.guidelines == guidelines
        for i, (expected, actual) in enumerate(zip(guidelines, restored.guidelines)):
            assert actual == expected, f"Guideline at position {i} differs"

    @settings(max_examples=100)
    @given(
        agent=valid_agent_with_guidelines_strategy(),
        additional_guidelines=st.lists(
            st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
            min_size=1,
            max_size=5
        )
    )
    def test_property_34_guidelines_accumulation(self, agent: Agent, additional_guidelines: list[str]):
        """Property 34: Guidelines Storage - Accumulation.

        **Validates: Requirements 13.1, 13.4**

        Verify that adding guidelines to an existing list maintains all guidelines
        in the correct order.
        """
        original_count = len(agent.guidelines)
        original_guidelines = agent.guidelines.copy()

        # Add new guidelines
        agent.guidelines.extend(additional_guidelines)

        # Verify all guidelines are present
        assert len(agent.guidelines) == original_count + len(additional_guidelines)

        # Verify original guidelines are still at the beginning
        for i, original in enumerate(original_guidelines):
            assert agent.guidelines[i] == original

        # Verify new guidelines are at the end
        for i, new_guideline in enumerate(additional_guidelines):
            assert agent.guidelines[original_count + i] == new_guideline

        # Verify serialization preserves the accumulated list
        data = agent.to_dict()
        restored = Agent.from_dict(data)
        assert restored.guidelines == agent.guidelines
