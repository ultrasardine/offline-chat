"""Tests for MCPServerConfig data model.

This module contains property-based tests and unit tests for the MCPServerConfig dataclass.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import MCPConfigError, MCPServerConfig


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


class TestMCPServerConfigRoundTrip:
    """Property 1: MCP Server Configuration Round Trip.

    Feature: mcp-integration, Property 1: MCP Server Configuration Round Trip
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

    For any valid MCPServerConfig object with name, command, args, optional env vars,
    and disabled flag, serializing to dictionary and deserializing back SHALL produce
    an equivalent configuration object with all fields preserved.
    """

    @settings(max_examples=100)
    @given(config=valid_mcp_config_strategy())
    def test_serialization_round_trip(self, config: MCPServerConfig):
        """Serializing and deserializing an MCPServerConfig should preserve all fields."""
        # Serialize to dict
        data = config.to_dict()

        # Deserialize back to MCPServerConfig
        restored = MCPServerConfig.from_dict(data)

        # Verify all fields are preserved
        assert restored.name == config.name
        assert restored.command == config.command
        assert restored.args == config.args
        assert restored.env == config.env
        assert restored.disabled == config.disabled

    @settings(max_examples=100)
    @given(config=valid_mcp_config_strategy())
    def test_to_dict_contains_all_fields(self, config: MCPServerConfig):
        """to_dict should include all required fields."""
        data = config.to_dict()

        required_fields = ["name", "command", "args", "env", "disabled"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @settings(max_examples=100)
    @given(config=valid_mcp_config_strategy())
    def test_to_dict_creates_copies(self, config: MCPServerConfig):
        """to_dict should create copies of mutable fields."""
        data = config.to_dict()

        # Modifying the returned dict should not affect the original
        data["args"].append("new-arg")
        data["env"]["NEW_VAR"] = "value"

        assert "new-arg" not in config.args
        assert "NEW_VAR" not in config.env

    def test_specific_round_trip_example(self):
        """Unit test for a specific round-trip example."""
        original = MCPServerConfig(
            name="fetch",
            command="uvx",
            args=["mcp-server-fetch"],
            env={"FASTMCP_LOG_LEVEL": "ERROR"},
            disabled=False,
        )

        data = original.to_dict()
        restored = MCPServerConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.command == original.command
        assert restored.args == original.args
        assert restored.env == original.env
        assert restored.disabled == original.disabled

    def test_round_trip_with_empty_args_and_env(self):
        """Unit test for round-trip with empty args and env."""
        original = MCPServerConfig(
            name="simple-server",
            command="python",
            args=[],
            env={},
            disabled=True,
        )

        data = original.to_dict()
        restored = MCPServerConfig.from_dict(data)

        assert restored.args == []
        assert restored.env == {}
        assert restored.disabled is True

    def test_from_dict_with_missing_optional_fields(self):
        """from_dict should handle missing optional fields with defaults."""
        data = {
            "name": "minimal-server",
            "command": "uvx",
        }

        config = MCPServerConfig.from_dict(data)

        assert config.name == "minimal-server"
        assert config.command == "uvx"
        assert config.args == []
        assert config.env == {}
        assert config.disabled is False


class TestMCPServerConfigValidation:
    """Property 7: MCP Config Validation.

    Feature: mcp-integration, Property 7: MCP Config Validation
    **Validates: Requirements 5.4**

    For any MCPServerConfig, the name field SHALL be non-empty, the command field
    SHALL be non-empty, and the args field SHALL be a list (possibly empty).
    """

    @settings(max_examples=100)
    @given(config=valid_mcp_config_strategy())
    def test_valid_config_passes_validation(self, config: MCPServerConfig):
        """Valid MCPServerConfig objects should pass validation without error."""
        # Should not raise any exception
        config.validate()

    @settings(max_examples=100)
    @given(
        command=valid_command_strategy(),
        args=valid_args_strategy(),
        env=valid_env_strategy(),
        disabled=st.booleans(),
    )
    def test_empty_name_fails_validation(
        self, command: str, args: list[str], env: dict[str, str], disabled: bool
    ):
        """MCPServerConfig with empty name should fail validation."""
        config = MCPServerConfig(
            name="",
            command=command,
            args=args,
            env=env,
            disabled=disabled,
        )
        with pytest.raises(MCPConfigError, match="name must be a non-empty string"):
            config.validate()

    @settings(max_examples=100)
    @given(
        name=valid_server_name_strategy(),
        args=valid_args_strategy(),
        env=valid_env_strategy(),
        disabled=st.booleans(),
    )
    def test_empty_command_fails_validation(
        self, name: str, args: list[str], env: dict[str, str], disabled: bool
    ):
        """MCPServerConfig with empty command should fail validation."""
        config = MCPServerConfig(
            name=name,
            command="",
            args=args,
            env=env,
            disabled=disabled,
        )
        with pytest.raises(MCPConfigError, match="command must be a non-empty string"):
            config.validate()

    def test_validation_with_valid_minimal_config(self):
        """Unit test: minimal valid config should pass validation."""
        config = MCPServerConfig(
            name="test-server",
            command="uvx",
        )
        # Should not raise
        config.validate()

    def test_validation_with_valid_full_config(self):
        """Unit test: full valid config should pass validation."""
        config = MCPServerConfig(
            name="fetch-server",
            command="uvx",
            args=["mcp-server-fetch"],
            env={"LOG_LEVEL": "DEBUG"},
            disabled=False,
        )
        # Should not raise
        config.validate()

    def test_validation_with_empty_args_list(self):
        """Unit test: empty args list should be valid."""
        config = MCPServerConfig(
            name="test-server",
            command="python",
            args=[],
        )
        # Should not raise
        config.validate()

    def test_validation_with_whitespace_only_name(self):
        """Unit test: whitespace-only name should fail validation."""
        config = MCPServerConfig(
            name="   ",
            command="uvx",
        )
        with pytest.raises(MCPConfigError, match="name must be a non-empty string"):
            config.validate()

    def test_validation_with_whitespace_only_command(self):
        """Unit test: whitespace-only command should fail validation."""
        config = MCPServerConfig(
            name="test-server",
            command="   ",
        )
        with pytest.raises(MCPConfigError, match="command must be a non-empty string"):
            config.validate()
