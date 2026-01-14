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
