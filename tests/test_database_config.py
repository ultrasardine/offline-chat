"""Tests for database configuration serialization.

This module contains property-based tests for database MCP server configuration
serialization and deserialization, ensuring all database settings including
credentials are preserved through round-trip operations.
"""

import pytest
from datetime import datetime
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import Agent, MCPServerConfig


# Strategy for generating valid database types
def database_type_strategy():
    """Generate valid database types."""
    return st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"])


# Strategy for generating Oracle database configurations
def oracle_mcp_config_strategy():
    """Generate Oracle database MCP server configurations."""
    return st.builds(
        MCPServerConfig,
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        command=st.just("sql"),
        args=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        env=st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=3,
        ),
        disabled=st.booleans(),
        database_type=st.just("oracle"),
        oracle_connection_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        oracle_tns_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        database_host=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_port=st.one_of(st.none(), st.integers(min_value=1, max_value=65535)),
        database_name=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_user=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        database_password=st.one_of(st.none(), st.text(min_size=0, max_size=100)),
    )


# Strategy for generating SQLite database configurations
def sqlite_mcp_config_strategy():
    """Generate SQLite database MCP server configurations."""
    return st.builds(
        MCPServerConfig,
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        command=st.just("uvx"),
        args=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        env=st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=3,
        ),
        disabled=st.booleans(),
        database_type=st.just("sqlite"),
        database_path=st.text(min_size=1, max_size=200),
    )


# Strategy for generating PostgreSQL database configurations
def postgresql_mcp_config_strategy():
    """Generate PostgreSQL database MCP server configurations."""
    return st.builds(
        MCPServerConfig,
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        command=st.just("uvx"),
        args=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        env=st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=3,
        ),
        disabled=st.booleans(),
        database_type=st.just("postgresql"),
        database_host=st.text(min_size=1, max_size=100),
        database_port=st.integers(min_value=1, max_value=65535),
        database_name=st.text(min_size=1, max_size=100),
        database_user=st.text(min_size=1, max_size=100),
        database_password=st.text(min_size=0, max_size=100),
    )


# Strategy for generating MySQL database configurations
def mysql_mcp_config_strategy():
    """Generate MySQL database MCP server configurations."""
    return st.builds(
        MCPServerConfig,
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        command=st.just("uvx"),
        args=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        env=st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=3,
        ),
        disabled=st.booleans(),
        database_type=st.just("mysql"),
        database_host=st.text(min_size=1, max_size=100),
        database_port=st.integers(min_value=1, max_value=65535),
        database_name=st.text(min_size=1, max_size=100),
        database_user=st.text(min_size=1, max_size=100),
        database_password=st.text(min_size=0, max_size=100),
    )


# Strategy for generating any database MCP configuration
def database_mcp_config_strategy():
    """Generate any type of database MCP server configuration."""
    return st.one_of(
        oracle_mcp_config_strategy(),
        sqlite_mcp_config_strategy(),
        postgresql_mcp_config_strategy(),
        mysql_mcp_config_strategy(),
    )


# Strategy for generating agents with database MCP servers
def agent_with_database_strategy():
    """Generate agents with database MCP server configurations."""
    return st.builds(
        Agent,
        name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
            min_size=1,
            max_size=50,
        ).filter(lambda s: s and s[0] != "-" and s[-1] != "-" and "--" not in s),
        display_name=st.text(min_size=1, max_size=100),
        base_model=st.sampled_from(["llama3:latest", "mistral:latest", "phi3:latest"]),
        system_prompt=st.text(min_size=10, max_size=500),
        temperature=st.floats(min_value=0.0, max_value=1.0),
        language=st.sampled_from(["English", "German", "Spanish", "French"]),
        web_search_enabled=st.booleans(),
        mcp_servers=st.lists(database_mcp_config_strategy(), min_size=1, max_size=3),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestDatabaseConfigurationSerializationRoundTrip:
    """Property 6: Configuration serialization round-trip.

    Feature: database-access, Property 6: Configuration serialization round-trip
    **Validates: Requirements 1.8**

    For any agent with database MCP server configurations, saving and then loading
    the agent configuration should preserve all database settings including credentials.
    """

    @settings(max_examples=100)
    @given(agent=agent_with_database_strategy())
    def test_agent_with_database_config_round_trip(self, agent: Agent):
        """Agent with database configs should preserve all settings through serialization."""
        # Serialize to dict
        data = agent.to_dict()

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify all base agent fields are preserved
        assert restored.name == agent.name
        assert restored.display_name == agent.display_name
        assert restored.base_model == agent.base_model
        assert restored.system_prompt == agent.system_prompt
        assert restored.temperature == agent.temperature
        assert restored.language == agent.language
        assert restored.web_search_enabled == agent.web_search_enabled
        assert restored.created_at == agent.created_at

        # Verify MCP servers count is preserved
        assert len(restored.mcp_servers) == len(agent.mcp_servers)

        # Verify each database MCP server configuration is preserved
        for original_mcp, restored_mcp in zip(agent.mcp_servers, restored.mcp_servers):
            # Basic MCP fields
            assert restored_mcp.name == original_mcp.name
            assert restored_mcp.command == original_mcp.command
            assert restored_mcp.args == original_mcp.args
            assert restored_mcp.env == original_mcp.env
            assert restored_mcp.disabled == original_mcp.disabled

            # Database-specific fields
            assert restored_mcp.database_type == original_mcp.database_type
            assert restored_mcp.oracle_connection_name == original_mcp.oracle_connection_name
            assert restored_mcp.oracle_tns_name == original_mcp.oracle_tns_name
            assert restored_mcp.database_path == original_mcp.database_path
            assert restored_mcp.database_host == original_mcp.database_host
            assert restored_mcp.database_port == original_mcp.database_port
            assert restored_mcp.database_name == original_mcp.database_name
            assert restored_mcp.database_user == original_mcp.database_user
            
            # CRITICAL: Verify credentials (passwords) are preserved
            assert restored_mcp.database_password == original_mcp.database_password

    @settings(max_examples=100)
    @given(agent=agent_with_database_strategy())
    def test_database_credentials_preserved_in_serialization(self, agent: Agent):
        """Database credentials including passwords must be preserved in serialization."""
        # Serialize to dict
        data = agent.to_dict()

        # Verify mcp_servers are in the serialized data
        assert "mcp_servers" in data
        assert len(data["mcp_servers"]) == len(agent.mcp_servers)

        # Verify each database config includes credentials
        for original_mcp, serialized_mcp in zip(agent.mcp_servers, data["mcp_servers"]):
            if original_mcp.database_user is not None:
                assert "database_user" in serialized_mcp
                assert serialized_mcp["database_user"] == original_mcp.database_user

            if original_mcp.database_password is not None:
                assert "database_password" in serialized_mcp
                assert serialized_mcp["database_password"] == original_mcp.database_password

    def test_specific_oracle_database_round_trip(self):
        """Unit test: Oracle database config with credentials should round-trip correctly."""
        mcp_config = MCPServerConfig(
            name="prod-oracle",
            command="sql",
            args=["-mcp", "-connection", "PROD_DB"],
            env={},
            disabled=False,
            database_type="oracle",
            oracle_connection_name="PROD_DB",
            database_host="db.example.com",
            database_port=1521,
            database_name="ORCL",
            database_user="admin",
            database_password="SecurePass123!",
        )

        agent = Agent(
            name="data-analyst",
            display_name="Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst with database access.",
            temperature=0.7,
            language="English",
            web_search_enabled=False,
            mcp_servers=[mcp_config],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify database config is preserved
        assert len(restored.mcp_servers) == 1
        restored_db = restored.mcp_servers[0]
        
        assert restored_db.name == "prod-oracle"
        assert restored_db.database_type == "oracle"
        assert restored_db.oracle_connection_name == "PROD_DB"
        assert restored_db.database_host == "db.example.com"
        assert restored_db.database_port == 1521
        assert restored_db.database_name == "ORCL"
        assert restored_db.database_user == "admin"
        assert restored_db.database_password == "SecurePass123!"

    def test_specific_postgresql_database_round_trip(self):
        """Unit test: PostgreSQL database config with credentials should round-trip correctly."""
        mcp_config = MCPServerConfig(
            name="analytics-postgres",
            command="uvx",
            args=["postgres-mcp-server"],
            env={"PGPASSWORD": "pg_secret"},
            disabled=False,
            database_type="postgresql",
            database_host="postgres.example.com",
            database_port=5432,
            database_name="analytics",
            database_user="analyst",
            database_password="pg_secret",
        )

        agent = Agent(
            name="analytics-agent",
            display_name="Analytics Agent",
            base_model="llama3:latest",
            system_prompt="You analyze data from PostgreSQL.",
            temperature=0.5,
            mcp_servers=[mcp_config],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify database config is preserved
        assert len(restored.mcp_servers) == 1
        restored_db = restored.mcp_servers[0]
        
        assert restored_db.name == "analytics-postgres"
        assert restored_db.database_type == "postgresql"
        assert restored_db.database_host == "postgres.example.com"
        assert restored_db.database_port == 5432
        assert restored_db.database_name == "analytics"
        assert restored_db.database_user == "analyst"
        assert restored_db.database_password == "pg_secret"

    def test_specific_sqlite_database_round_trip(self):
        """Unit test: SQLite database config should round-trip correctly."""
        mcp_config = MCPServerConfig(
            name="local-sqlite",
            command="uvx",
            args=["sqlite-mcp-server", "--db-path", "/data/local.db"],
            env={},
            disabled=False,
            database_type="sqlite",
            database_path="/data/local.db",
        )

        agent = Agent(
            name="local-agent",
            display_name="Local Agent",
            base_model="llama3:latest",
            system_prompt="You work with local SQLite databases.",
            temperature=0.7,
            mcp_servers=[mcp_config],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify database config is preserved
        assert len(restored.mcp_servers) == 1
        restored_db = restored.mcp_servers[0]
        
        assert restored_db.name == "local-sqlite"
        assert restored_db.database_type == "sqlite"
        assert restored_db.database_path == "/data/local.db"

    def test_multiple_database_configs_round_trip(self):
        """Unit test: Agent with multiple database configs should preserve all."""
        oracle_config = MCPServerConfig(
            name="oracle-prod",
            command="sql",
            args=["-mcp", "admin/pass@localhost:1521/ORCL"],
            database_type="oracle",
            database_host="localhost",
            database_port=1521,
            database_name="ORCL",
            database_user="admin",
            database_password="pass",
        )

        postgres_config = MCPServerConfig(
            name="postgres-dev",
            command="uvx",
            args=["postgres-mcp-server"],
            database_type="postgresql",
            database_host="localhost",
            database_port=5432,
            database_name="devdb",
            database_user="dev",
            database_password="devpass",
        )

        sqlite_config = MCPServerConfig(
            name="sqlite-local",
            command="uvx",
            args=["sqlite-mcp-server"],
            database_type="sqlite",
            database_path="/tmp/test.db",
        )

        agent = Agent(
            name="multi-db-agent",
            display_name="Multi-Database Agent",
            base_model="llama3:latest",
            system_prompt="You work with multiple databases.",
            temperature=0.7,
            mcp_servers=[oracle_config, postgres_config, sqlite_config],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify all three database configs are preserved
        assert len(restored.mcp_servers) == 3

        # Check Oracle config
        oracle_restored = restored.mcp_servers[0]
        assert oracle_restored.database_type == "oracle"
        assert oracle_restored.database_user == "admin"
        assert oracle_restored.database_password == "pass"

        # Check PostgreSQL config
        postgres_restored = restored.mcp_servers[1]
        assert postgres_restored.database_type == "postgresql"
        assert postgres_restored.database_user == "dev"
        assert postgres_restored.database_password == "devpass"

        # Check SQLite config
        sqlite_restored = restored.mcp_servers[2]
        assert sqlite_restored.database_type == "sqlite"
        assert sqlite_restored.database_path == "/tmp/test.db"

    def test_empty_password_preserved(self):
        """Unit test: Empty passwords should be preserved (not converted to None)."""
        mcp_config = MCPServerConfig(
            name="no-pass-db",
            command="uvx",
            args=["postgres-mcp-server"],
            database_type="postgresql",
            database_host="localhost",
            database_port=5432,
            database_name="testdb",
            database_user="testuser",
            database_password="",  # Empty password
        )

        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test agent.",
            mcp_servers=[mcp_config],
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )

        # Serialize and deserialize
        data = agent.to_dict()
        restored = Agent.from_dict(data)

        # Verify empty password is preserved
        restored_db = restored.mcp_servers[0]
        assert restored_db.database_password == ""
        assert restored_db.database_password is not None
