"""Property-based tests for CLI display formatting.

This module tests the CLI display functions to ensure database status
and credentials are displayed correctly with proper masking.
"""

from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from offline_chat.agent import Agent
from offline_chat.cli import CLI
from offline_chat.manager import AgentManager
from offline_chat.mcp_config import MCPServerConfig


# Custom strategies for generating test data
@st.composite
def database_config_strategy(draw):
    """Generate a database MCP server configuration."""
    db_type = draw(st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]))
    name = draw(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
        )
    )

    config = MCPServerConfig(
        name=name,
        command="sql" if db_type == "oracle" else "uvx",
        args=["-mcp"] if db_type == "oracle" else ["mcp-server"],
        database_type=db_type,
    )

    if db_type == "oracle":
        config.oracle_connection_name = draw(st.text(min_size=1, max_size=20))
    elif db_type == "sqlite":
        config.database_path = draw(st.text(min_size=1, max_size=50))
    else:  # postgresql or mysql
        config.database_host = draw(st.text(min_size=1, max_size=30))
        config.database_port = draw(st.integers(min_value=1024, max_value=65535))
        config.database_name = draw(st.text(min_size=1, max_size=20))
        config.database_user = draw(st.text(min_size=1, max_size=20))
        config.database_password = draw(st.text(min_size=8, max_size=30))

    return config


@st.composite
def agent_with_databases_strategy(draw):
    """Generate an agent with database configurations."""
    name = draw(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"
            ),
        )
    )

    # Generate 1-3 database configurations
    num_databases = draw(st.integers(min_value=1, max_value=3))
    databases = [draw(database_config_strategy()) for _ in range(num_databases)]

    agent = Agent(
        name=name,
        display_name=draw(st.text(min_size=1, max_size=50)),
        base_model="llama3:latest",
        system_prompt=draw(st.text(min_size=10, max_size=100)),
        temperature=draw(st.floats(min_value=0.0, max_value=1.0)),
        language="English",
        web_search_enabled=draw(st.booleans()),
        mcp_servers=databases,
        created_at=datetime.now(),
    )

    return agent


# Property 26: Database status display
@given(agent=agent_with_databases_strategy())
@pytest.mark.property_test
def test_list_agents_shows_database_status(agent):
    """
    Feature: database-access, Property 26: Database status display

    **Validates: Requirements 7.1**

    For any agent, the CLI display should show database access status
    that accurately reflects whether the agent has database configurations.

    This test verifies that when an agent has database configurations,
    the list display shows the database types and names correctly.
    """
    # Create a mock manager with the agent
    manager = AgentManager()

    # Mock the list_agents method to return our test agent
    with patch.object(manager, "list_agents", return_value=[agent]):
        cli = CLI(manager=manager)

        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            cli.list_agents_flow()
            output = fake_out.getvalue()

        # Verify database status is shown
        database_servers = [
            s for s in agent.mcp_servers if hasattr(s, "database_type") and s.database_type
        ]

        if database_servers:
            # Should show "Databases:" in output
            assert "Databases:" in output or "Database:" in output

            # Should show each database type and name
            for db in database_servers:
                if not db.disabled:
                    assert db.database_type in output
                    assert db.name in output


# Property 27: Password masking in CLI display
@given(
    db_type=st.sampled_from(["oracle", "postgresql", "mysql"]),
    password=st.text(
        min_size=8,
        max_size=30,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="!@#$%^&*"
        ),
    ),
)
@pytest.mark.property_test
def test_agent_details_masks_passwords(db_type, password):
    """
    Feature: database-access, Property 27: Password masking in CLI display

    **Validates: Requirements 7.2**

    For any agent with database configurations, the CLI detail view should
    display connection information with passwords masked.

    This test verifies that passwords are never displayed in plain text,
    regardless of the password content or database type.
    """
    # Create an agent with a database that has a password
    config = MCPServerConfig(
        name="test_db",
        command="sql" if db_type == "oracle" else "uvx",
        args=["-mcp"],
        database_type=db_type,
        database_user="testuser",
        database_password=password,
    )

    if db_type == "oracle":
        config.oracle_tns_name = "TEST_TNS"
    else:
        config.database_host = "localhost"
        config.database_port = 5432
        config.database_name = "testdb"

    agent = Agent(
        name="test-agent",
        display_name="Test Agent",
        base_model="llama3:latest",
        system_prompt="Test agent",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[config],
        created_at=datetime.now(),
    )

    # Create CLI and mock agent selection
    manager = AgentManager()
    cli = CLI(manager=manager)

    # Mock _select_agent to return our test agent
    with patch.object(cli, "_select_agent", return_value=agent):
        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            with patch("builtins.input", return_value="0"):  # Cancel after viewing
                cli.view_agent_details_flow()
            output = fake_out.getvalue()

    # Verify password is masked
    assert password not in output, f"Password '{password}' should not appear in output"
    assert "****" in output, "Masked password (****) should appear in output"


# Property 28: Multiple database display
@given(num_databases=st.integers(min_value=1, max_value=5))
@pytest.mark.property_test
def test_list_agents_shows_all_databases(num_databases):
    """
    Feature: database-access, Property 28: Multiple database display

    **Validates: Requirements 7.3**

    For any agent with N database configurations where N > 0, the CLI
    should list all N databases in the display.

    This test verifies that when an agent has multiple databases,
    all of them are shown in the listing.
    """
    # Create database configurations
    databases = []
    db_types = ["oracle", "postgresql", "mysql", "sqlite"]

    for i in range(num_databases):
        db_type = db_types[i % len(db_types)]
        config = MCPServerConfig(
            name=f"db_{i}",
            command="sql" if db_type == "oracle" else "uvx",
            args=["-mcp"],
            database_type=db_type,
        )

        if db_type == "oracle":
            config.oracle_connection_name = f"CONN_{i}"
        elif db_type == "sqlite":
            config.database_path = f"/tmp/db_{i}.db"
        else:
            config.database_host = "localhost"
            config.database_port = 5432 + i
            config.database_name = f"db_{i}"
            config.database_user = f"user_{i}"

        databases.append(config)

    # Create agent with all databases
    agent = Agent(
        name="multi-db-agent",
        display_name="Multi DB Agent",
        base_model="llama3:latest",
        system_prompt="Agent with multiple databases",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=databases,
        created_at=datetime.now(),
    )

    # Create CLI and test listing
    manager = AgentManager()
    with patch.object(manager, "list_agents", return_value=[agent]):
        cli = CLI(manager=manager)

        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            cli.list_agents_flow()
            output = fake_out.getvalue()

        # Verify all databases are shown
        for db in databases:
            if not db.disabled:
                # Each database name should appear in output
                assert db.name in output, f"Database '{db.name}' should appear in output"
                # Each database type should appear in output
                assert db.database_type in output, f"Type '{db.database_type}' should appear"


@given(agent=agent_with_databases_strategy())
@pytest.mark.property_test
def test_agent_details_shows_all_databases(agent):
    """
    Feature: database-access, Property 28: Multiple database display

    **Validates: Requirements 7.3**

    For any agent with multiple databases, the detail view should
    show complete information for each database.
    """
    # Create CLI and mock agent selection
    manager = AgentManager()
    cli = CLI(manager=manager)

    # Mock _select_agent to return our test agent
    with patch.object(cli, "_select_agent", return_value=agent):
        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            with patch("builtins.input", return_value="0"):  # Cancel after viewing
                cli.view_agent_details_flow()
            output = fake_out.getvalue()

    # Verify all databases are shown in detail view
    database_servers = [
        s for s in agent.mcp_servers if hasattr(s, "database_type") and s.database_type
    ]

    for db in database_servers:
        if not db.disabled:
            # Each database name should appear
            assert db.name in output, f"Database '{db.name}' should appear in detail view"
            # Each database type should appear
            assert db.database_type in output, f"Type '{db.database_type}' should appear"

            # Type-specific fields should appear
            if db.database_type == "oracle" and db.oracle_connection_name:
                assert db.oracle_connection_name in output
            elif db.database_type == "sqlite" and db.database_path:
                assert db.database_path in output
            elif db.database_type in ["postgresql", "mysql"]:
                if db.database_host:
                    assert db.database_host in output
                if db.database_name:
                    assert db.database_name in output


# Unit tests for edge cases


def test_list_agents_shows_no_database_access_for_agent_without_databases():
    """
    Test that agents without databases show "No database access".

    **Validates: Requirements 7.4**
    """
    # Create an agent without any database configurations
    agent = Agent(
        name="no-db-agent",
        display_name="No DB Agent",
        base_model="llama3:latest",
        system_prompt="Agent without database access",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[],  # No MCP servers at all
        created_at=datetime.now(),
    )

    # Create CLI and test listing
    manager = AgentManager()
    with patch.object(manager, "list_agents", return_value=[agent]):
        cli = CLI(manager=manager)

        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            cli.list_agents_flow()
            output = fake_out.getvalue()

        # Verify "No database access" is shown
        assert "No database access" in output


def test_list_agents_shows_no_database_access_for_agent_with_only_non_db_mcp():
    """
    Test that agents with only non-database MCP servers show "No database access".

    **Validates: Requirements 7.4**
    """
    # Create a non-database MCP server
    mcp_server = MCPServerConfig(
        name="filesystem",
        command="uvx",
        args=["mcp-server-filesystem", "/tmp"],
        # No database_type field
    )

    # Create an agent with non-database MCP server
    agent = Agent(
        name="mcp-agent",
        display_name="MCP Agent",
        base_model="llama3:latest",
        system_prompt="Agent with MCP but no database",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[mcp_server],
        created_at=datetime.now(),
    )

    # Create CLI and test listing
    manager = AgentManager()
    with patch.object(manager, "list_agents", return_value=[agent]):
        cli = CLI(manager=manager)

        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            cli.list_agents_flow()
            output = fake_out.getvalue()

        # Verify "No database access" is shown
        assert "No database access" in output
        # Verify the non-database MCP server is shown separately
        assert "MCP:" in output
        assert "filesystem" in output


def test_agent_details_shows_no_database_access_message():
    """
    Test that agent detail view shows "No database access" for agents without databases.

    **Validates: Requirements 7.4**
    """
    # Create an agent without database configurations
    agent = Agent(
        name="no-db-agent",
        display_name="No DB Agent",
        base_model="llama3:latest",
        system_prompt="Agent without database access",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[],
        created_at=datetime.now(),
    )

    # Create CLI and mock agent selection
    manager = AgentManager()
    cli = CLI(manager=manager)

    # Mock _select_agent to return our test agent
    with patch.object(cli, "_select_agent", return_value=agent):
        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            with patch("builtins.input", return_value="0"):  # Cancel after viewing
                cli.view_agent_details_flow()
            output = fake_out.getvalue()

    # Verify "No database access" is shown
    assert "Database Access: No database access" in output


def test_list_agents_handles_disabled_databases():
    """
    Test that disabled databases are not shown in the listing.

    **Validates: Requirements 7.1**
    """
    # Create a disabled database configuration
    disabled_db = MCPServerConfig(
        name="disabled_db",
        command="sql",
        args=["-mcp"],
        database_type="oracle",
        oracle_connection_name="DISABLED_CONN",
        disabled=True,  # Disabled
    )

    # Create an enabled database configuration
    enabled_db = MCPServerConfig(
        name="enabled_db",
        command="sql",
        args=["-mcp"],
        database_type="postgresql",
        database_host="localhost",
        database_port=5432,
        database_name="testdb",
        disabled=False,
    )

    # Create agent with both databases
    agent = Agent(
        name="mixed-db-agent",
        display_name="Mixed DB Agent",
        base_model="llama3:latest",
        system_prompt="Agent with enabled and disabled databases",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[disabled_db, enabled_db],
        created_at=datetime.now(),
    )

    # Create CLI and test listing
    manager = AgentManager()
    with patch.object(manager, "list_agents", return_value=[agent]):
        cli = CLI(manager=manager)

        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            cli.list_agents_flow()
            output = fake_out.getvalue()

        # Verify only enabled database is shown
        assert "enabled_db" in output
        assert "postgresql" in output
        # Disabled database should not appear
        assert "disabled_db" not in output


def test_agent_details_shows_disabled_status():
    """
    Test that agent detail view shows disabled status for databases.

    **Validates: Requirements 7.2**
    """
    # Create a disabled database configuration
    disabled_db = MCPServerConfig(
        name="disabled_db",
        command="sql",
        args=["-mcp"],
        database_type="oracle",
        oracle_connection_name="DISABLED_CONN",
        disabled=True,
    )

    agent = Agent(
        name="test-agent",
        display_name="Test Agent",
        base_model="llama3:latest",
        system_prompt="Test agent",
        temperature=0.7,
        language="English",
        web_search_enabled=False,
        mcp_servers=[disabled_db],
        created_at=datetime.now(),
    )

    # Create CLI and mock agent selection
    manager = AgentManager()
    cli = CLI(manager=manager)

    # Mock _select_agent to return our test agent
    with patch.object(cli, "_select_agent", return_value=agent):
        # Capture output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            with patch("builtins.input", return_value="0"):  # Cancel after viewing
                cli.view_agent_details_flow()
            output = fake_out.getvalue()

    # Verify disabled status is shown
    assert "disabled_db" in output
    assert "disabled" in output.lower()
