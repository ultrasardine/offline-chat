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


# Strategy for generating database types
def database_type_strategy():
    """Generate valid database types."""
    return st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"])


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
        database_type=st.one_of(st.none(), database_type_strategy()),
        oracle_connection_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        oracle_tns_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        database_path=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
        database_host=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_port=st.one_of(st.none(), st.integers(min_value=1, max_value=65535)),
        database_name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_user=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_password=st.one_of(st.none(), st.text(min_size=0, max_size=100)),
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

        # Verify database-specific fields are preserved
        assert restored.database_type == config.database_type
        assert restored.oracle_connection_name == config.oracle_connection_name
        assert restored.oracle_tns_name == config.oracle_tns_name
        assert restored.database_path == config.database_path
        assert restored.database_host == config.database_host
        assert restored.database_port == config.database_port
        assert restored.database_name == config.database_name
        assert restored.database_user == config.database_user
        assert restored.database_password == config.database_password

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
        # Database fields should default to None
        assert config.database_type is None
        assert config.oracle_connection_name is None
        assert config.oracle_tns_name is None
        assert config.database_path is None
        assert config.database_host is None
        assert config.database_port is None
        assert config.database_name is None
        assert config.database_user is None
        assert config.database_password is None

    def test_round_trip_with_oracle_database_config(self):
        """Unit test for round-trip with Oracle database configuration."""
        original = MCPServerConfig(
            name="oracle-db",
            command="sql",
            args=["-mcp", "-connection", "PROD_DB"],
            env={},
            disabled=False,
            database_type="oracle",
            oracle_connection_name="PROD_DB",
            database_host="localhost",
            database_port=1521,
            database_name="ORCL",
            database_user="admin",
            database_password="secret123",
        )

        data = original.to_dict()
        restored = MCPServerConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.command == original.command
        assert restored.database_type == "oracle"
        assert restored.oracle_connection_name == "PROD_DB"
        assert restored.database_host == "localhost"
        assert restored.database_port == 1521
        assert restored.database_name == "ORCL"
        assert restored.database_user == "admin"
        assert restored.database_password == "secret123"

    def test_round_trip_with_sqlite_database_config(self):
        """Unit test for round-trip with SQLite database configuration."""
        original = MCPServerConfig(
            name="sqlite-db",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
            env={},
            disabled=False,
            database_type="sqlite",
            database_path="/tmp/test.db",
        )

        data = original.to_dict()
        restored = MCPServerConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.database_type == "sqlite"
        assert restored.database_path == "/tmp/test.db"

    def test_round_trip_with_postgresql_database_config(self):
        """Unit test for round-trip with PostgreSQL database configuration."""
        original = MCPServerConfig(
            name="postgres-db",
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-postgres",
                "postgresql://analyst:pgpass@db.example.com:5432/analytics",
            ],
            env={},
            disabled=False,
            database_type="postgresql",
            database_host="db.example.com",
            database_port=5432,
            database_name="analytics",
            database_user="analyst",
            database_password="pgpass",
        )

        data = original.to_dict()
        restored = MCPServerConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.database_type == "postgresql"
        assert restored.database_host == "db.example.com"
        assert restored.database_port == 5432
        assert restored.database_name == "analytics"
        assert restored.database_user == "analyst"
        assert restored.database_password == "pgpass"

    def test_to_dict_excludes_none_database_fields(self):
        """to_dict should not include database fields when they are None."""
        config = MCPServerConfig(
            name="regular-server",
            command="uvx",
            args=["some-server"],
        )

        data = config.to_dict()

        # Database fields should not be in the dict when None
        assert "database_type" not in data
        assert "oracle_connection_name" not in data
        assert "oracle_tns_name" not in data
        assert "database_path" not in data
        assert "database_host" not in data
        assert "database_port" not in data
        assert "database_name" not in data
        assert "database_user" not in data
        assert "database_password" not in data


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
    def test_empty_name_fails_validation(self, command: str, args: list[str], env: dict[str, str], disabled: bool):
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
    def test_empty_command_fails_validation(self, name: str, args: list[str], env: dict[str, str], disabled: bool):
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
