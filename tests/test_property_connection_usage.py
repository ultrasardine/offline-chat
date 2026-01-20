"""Property-based tests for connection usage tracking.

This module contains property-based tests using Hypothesis to verify universal
properties of connection usage tracking functionality.

Properties tested:
- Property 10: Connection Usage Tracking
- Property 33: Access Level Display

**Validates: Requirements 3.4, 12.10**
"""

import json
import tempfile
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path

from offline_chat.agent import Agent
from offline_chat.database import AccessLevel, AgentConnectionAssignment
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_ok, is_err, unwrap, unwrap_err
from offline_chat.manager import AgentManager


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid connection names (kebab-case)
valid_connection_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30
).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s and s[0] not in '0123456789')

# Valid agent names (kebab-case)
valid_agent_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30
).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s and s[0] not in '0123456789')

# Access levels
access_levels = st.sampled_from([
    AccessLevel.READ_ONLY,
    AccessLevel.READ_WRITE,
    AccessLevel.TABLE_SPECIFIC_READ,
    AccessLevel.TABLE_SPECIFIC_READ_WRITE,
])

# Table names
table_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="_"
    ),
    min_size=1,
    max_size=20
).filter(lambda s: s[0] not in ('_', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))

# Lists of table names
table_lists = st.lists(table_names, min_size=1, max_size=10, unique=True)


# ============================================================================
# Helper Functions
# ============================================================================

def setup_test_environment():
    """Set up test environment with temporary directories and managers."""
    # Create a temporary directory
    tmp_dir = Path(tempfile.mkdtemp())
    
    agents_dir = tmp_dir / "agents"
    history_dir = tmp_dir / "history"
    connections_file = tmp_dir / "connections.json"
    
    agents_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    
    db_manager = DatabaseConnectionManager(
        store_path=connections_file,
        agents_dir=agents_dir
    )
    agent_manager = AgentManager(
        agents_dir=agents_dir,
        history_dir=history_dir,
        db_manager=db_manager,
    )
    
    return {
        "tmp_dir": tmp_dir,
        "agents_dir": agents_dir,
        "history_dir": history_dir,
        "connections_file": connections_file,
        "db_manager": db_manager,
        "agent_manager": agent_manager,
    }


def create_test_connection(db_manager, name: str, temp_path: Path) -> bool:
    """Create a test SQLite connection."""
    conn = DatabaseConnection(
        name=name,
        database_type="sqlite",
        file_path=str(temp_path / f"{name}.db")
    )
    result = db_manager.create_connection(conn)
    return is_ok(result)


def create_test_agent(agent_manager, name: str) -> bool:
    """Create a test agent without Ollama registration."""
    agent = Agent(
        name=name,
        display_name=f"Test Agent {name}",
        base_model="llama3:latest",
        system_prompt="You are a test agent.",
    )
    
    # Save agent config manually (skip Ollama registration for tests)
    agent_dir = agent_manager._get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_manager._get_config_path(agent.name)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(agent.to_dict(), f, indent=2)
    
    return True


# ============================================================================
# Property 10: Connection Usage Tracking
# ============================================================================

@given(
    connection_name=valid_connection_names,
    agent_names=st.lists(valid_agent_names, min_size=1, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_10_connection_usage_tracking(
    connection_name, agent_names, access_level
):
    """Property 10: Connection Usage Tracking
    
    **Validates: Requirements 3.4**
    
    For any connection, the system should correctly identify all agents that
    reference it in their connection_assignments array.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]
    
    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["tmp_dir"])
    
    # Create all agents and assign the connection to them
    for agent_name in agent_names:
        assert create_test_agent(agent_manager, agent_name)
        
        # Prepare allowed_tables if needed
        allowed_tables = ["test_table"] if access_level in (
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ) else None
        
        # Assign the connection
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=connection_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Failed to assign connection to {agent_name}"
    
    # Get agents using the connection
    agents_using = db_manager.get_agents_using_connection(connection_name)
    
    # Verify all agents are identified
    assert len(agents_using) == len(agent_names), \
        f"Should identify {len(agent_names)} agents, got {len(agents_using)}"
    
    # Verify the correct agents are identified
    assert set(agents_using) == set(agent_names), \
        f"Identified agents {set(agents_using)} should match expected {set(agent_names)}"


@given(
    connection_name=valid_connection_names,
    using_agents=st.lists(valid_agent_names, min_size=1, max_size=3, unique=True),
    non_using_agents=st.lists(valid_agent_names, min_size=1, max_size=3, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_10_connection_usage_tracking_partial(
    connection_name, using_agents, non_using_agents, access_level
):
    """Property 10: Connection Usage Tracking (Partial Usage)
    
    **Validates: Requirements 3.4**
    
    For any connection, the system should correctly identify only the agents
    that reference it, excluding agents that don't use it.
    """
    # Ensure agent names don't overlap
    assume(not any(name in using_agents for name in non_using_agents))
    
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]
    
    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["tmp_dir"])
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Create agents that use the connection
    for agent_name in using_agents:
        assert create_test_agent(agent_manager, agent_name)
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=connection_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Failed to assign connection to {agent_name}"
    
    # Create agents that don't use the connection
    for agent_name in non_using_agents:
        assert create_test_agent(agent_manager, agent_name)
        # Don't assign the connection to these agents
    
    # Get agents using the connection
    agents_using = db_manager.get_agents_using_connection(connection_name)
    
    # Verify only the using agents are identified
    assert len(agents_using) == len(using_agents), \
        f"Should identify {len(using_agents)} agents, got {len(agents_using)}"
    
    assert set(agents_using) == set(using_agents), \
        f"Identified agents should only include agents that use the connection"
    
    # Verify non-using agents are not included
    for agent_name in non_using_agents:
        assert agent_name not in agents_using, \
            f"Agent {agent_name} should not be identified as using the connection"


@given(
    connection_name=valid_connection_names,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_10_connection_usage_tracking_no_usage(connection_name):
    """Property 10: Connection Usage Tracking (No Usage)
    
    **Validates: Requirements 3.4**
    
    For any connection that is not used by any agents, the system should
    return an empty list.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["tmp_dir"])
    
    # Get agents using the connection (should be none)
    agents_using = db_manager.get_agents_using_connection(connection_name)
    
    # Verify no agents are identified
    assert len(agents_using) == 0, \
        f"Should identify 0 agents for unused connection, got {len(agents_using)}"


@given(
    connection_name=valid_connection_names,
    agent_name=valid_agent_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_10_connection_usage_tracking_after_removal(
    connection_name, agent_name, access_level
):
    """Property 10: Connection Usage Tracking (After Removal)
    
    **Validates: Requirements 3.4**
    
    For any connection, after removing it from an agent, the system should
    no longer identify that agent as using the connection.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]
    
    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["tmp_dir"])
    
    # Create the agent
    assert create_test_agent(agent_manager, agent_name)
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Assign the connection
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )
    assert is_ok(result), f"Failed to assign connection"
    
    # Verify agent is using the connection
    agents_using = db_manager.get_agents_using_connection(connection_name)
    assert agent_name in agents_using, "Agent should be using the connection"
    
    # Remove the connection from the agent
    result = agent_manager.remove_connection(
        agent_name=agent_name,
        connection_name=connection_name,
    )
    assert is_ok(result), f"Failed to remove connection"
    
    # Verify agent is no longer using the connection
    agents_using_after = db_manager.get_agents_using_connection(connection_name)
    assert agent_name not in agents_using_after, \
        "Agent should no longer be using the connection after removal"


# ============================================================================
# Property 33: Access Level Display
# ============================================================================

@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    access_level=access_levels,
    tables=table_lists,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_33_access_level_display(
    agent_name, connection_name, access_level, tables
):
    """Property 33: Access Level Display
    
    **Validates: Requirements 12.10**
    
    For any agent with connection assignments, displaying the agent configuration
    should show the access level for each connection.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]
    
    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["tmp_dir"])
    
    # Create the agent
    assert create_test_agent(agent_manager, agent_name)
    
    # Prepare allowed_tables based on access level
    allowed_tables = tables if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Assign the connection with access level
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )
    assert is_ok(result), f"Assignment failed"
    
    # Load the agent configuration from file
    config_path = agent_manager._get_config_path(agent_name)
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    # Verify connection_assignments exists
    assert "connection_assignments" in config_data, \
        "Config should have connection_assignments field"
    
    assignments = config_data["connection_assignments"]
    assert len(assignments) == 1, "Should have exactly one assignment"
    
    assignment = assignments[0]
    
    # Verify access level is displayed in the configuration
    assert "access_level" in assignment, \
        "Assignment should have access_level field"
    
    assert assignment["access_level"] == access_level.value, \
        f"Access level should be {access_level.value}, got {assignment['access_level']}"
    
    # Verify connection name is displayed
    assert "connection_name" in assignment, \
        "Assignment should have connection_name field"
    
    assert assignment["connection_name"] == connection_name, \
        f"Connection name should be {connection_name}, got {assignment['connection_name']}"
    
    # Verify allowed_tables is displayed for table-specific access
    if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE):
        assert "allowed_tables" in assignment, \
            "Assignment should have allowed_tables field for table-specific access"
        assert assignment["allowed_tables"] == tables, \
            f"Allowed tables should be {tables}, got {assignment['allowed_tables']}"


@given(
    agent_name=valid_agent_names,
    connections_and_levels=st.lists(
        st.tuples(valid_connection_names, access_levels),
        min_size=2,
        max_size=5,
        unique_by=lambda x: x[0]  # Unique connection names
    ),
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_33_access_level_display_multiple_connections(
    agent_name, connections_and_levels
):
    """Property 33: Access Level Display (Multiple Connections)
    
    **Validates: Requirements 12.10**
    
    For any agent with multiple connection assignments, displaying the agent
    configuration should show the access level for each connection.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]
    
    # Create the agent
    assert create_test_agent(agent_manager, agent_name)
    
    # Create connections and assign them with different access levels
    for conn_name, access_level in connections_and_levels:
        # Create the connection
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
        
        # Prepare allowed_tables if needed
        allowed_tables = ["test_table"] if access_level in (
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ) else None
        
        # Assign the connection
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Failed to assign connection {conn_name}"
    
    # Load the agent configuration from file
    config_path = agent_manager._get_config_path(agent_name)
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    # Verify connection_assignments exists
    assert "connection_assignments" in config_data, \
        "Config should have connection_assignments field"
    
    assignments = config_data["connection_assignments"]
    assert len(assignments) == len(connections_and_levels), \
        f"Should have {len(connections_and_levels)} assignments, got {len(assignments)}"
    
    # Create a mapping of connection name to access level from assignments
    assignment_map = {
        a["connection_name"]: a["access_level"]
        for a in assignments
    }
    
    # Verify each connection has the correct access level displayed
    for conn_name, access_level in connections_and_levels:
        assert conn_name in assignment_map, \
            f"Connection {conn_name} should be in assignments"
        
        assert assignment_map[conn_name] == access_level.value, \
            f"Connection {conn_name} should have access level {access_level.value}, " \
            f"got {assignment_map[conn_name]}"
