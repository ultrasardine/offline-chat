"""Property-based tests for agent connection assignment with access control.

This module contains property-based tests using Hypothesis to verify universal
properties of agent connection assignment functionality.

Properties tested:
- Property 14: Agent Connection Assignment Validation
- Property 15: Agent Connection Storage
- Property 16: Connection Assignment Cardinality
- Property 32: Access Level Storage

**Validates: Requirements 6.1, 6.2, 6.3, 12.9**
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from offline_chat.agent import Agent
from offline_chat.database import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_err, is_ok, unwrap_err
from offline_chat.manager import AgentManager

# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid connection names (kebab-case)
valid_connection_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=30).filter(
    lambda s: s[0] != "-" and s[-1] != "-" and "--" not in s and s[0] not in "0123456789"
)

# Valid agent names (kebab-case)
valid_agent_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=30).filter(
    lambda s: s[0] != "-" and s[-1] != "-" and "--" not in s and s[0] not in "0123456789"
)

# Access levels
access_levels = st.sampled_from(
    [
        AccessLevel.READ_ONLY,
        AccessLevel.READ_WRITE,
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE,
    ]
)

# Table names
table_names = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"), min_size=1, max_size=20
).filter(lambda s: s[0] not in ("_", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))

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

    db_manager = DatabaseConnectionManager(store_path=connections_file)
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
    conn = DatabaseConnection(name=name, database_type="sqlite", file_path=str(temp_path / f"{name}.db"))
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
# Property 14: Agent Connection Assignment Validation
# ============================================================================


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_14_assignment_validation_existing_connection(agent_name, connection_name, access_level):
    """Property 14: Agent Connection Assignment Validation

    **Validates: Requirements 6.2**

    For any agent and any list of connection names, assigning connections should
    succeed only if all connection names exist in the store; if any name doesn't
    exist, the assignment should fail.

    This test verifies that assignment succeeds when the connection exists.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Prepare allowed_tables if needed
    allowed_tables = (
        ["test_table"]
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    # Assign the connection - should succeed
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )

    # Verify assignment succeeded
    assert is_ok(result), (
        f"Assignment should succeed when connection exists: {unwrap_err(result) if is_err(result) else ''}"
    )


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    nonexistent_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_14_assignment_validation_nonexistent_connection(
    agent_name, connection_name, nonexistent_name, access_level
):
    """Property 14: Agent Connection Assignment Validation

    **Validates: Requirements 6.2**

    For any agent and any list of connection names, assigning connections should
    succeed only if all connection names exist in the store; if any name doesn't
    exist, the assignment should fail.

    This test verifies that assignment fails when the connection doesn't exist.
    """
    # Ensure the nonexistent name is different from the connection name
    assume(nonexistent_name != connection_name)

    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create only one connection
    assert create_test_connection(db_manager, connection_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Prepare allowed_tables if needed
    allowed_tables = (
        ["test_table"]
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    # Try to assign the nonexistent connection - should fail
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=nonexistent_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )

    # Verify assignment failed
    assert is_err(result), "Assignment should fail when connection doesn't exist"
    error = unwrap_err(result)
    assert "not found" in error.lower(), f"Error should mention 'not found': {error}"


# ============================================================================
# Property 15: Agent Connection Storage
# ============================================================================


@given(
    agent_name=valid_agent_names,
    connection_names=st.lists(valid_connection_names, min_size=1, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_15_connection_storage(agent_name, connection_names, access_level):
    """Property 15: Agent Connection Storage

    **Validates: Requirements 6.3**

    For any agent and any list of valid connection names, after successful
    assignment, the agent's config file should contain a connection_assignments
    array with exactly those connection names.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create all connections
    for conn_name in connection_names:
        assert create_test_connection(db_manager, conn_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Prepare allowed_tables if needed
    allowed_tables = (
        ["test_table"]
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    # Assign all connections
    for conn_name in connection_names:
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Failed to assign connection {conn_name}: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent config from file
    config_path = agent_manager._get_config_path(agent_name)
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Verify connection_assignments exists and has correct length
    assert "connection_assignments" in config_data, "Config should have connection_assignments field"
    assignments = config_data["connection_assignments"]
    assert len(assignments) == len(connection_names), (
        f"Should have {len(connection_names)} assignments, got {len(assignments)}"
    )

    # Verify all connection names are present
    stored_names = {a["connection_name"] for a in assignments}
    expected_names = set(connection_names)
    assert stored_names == expected_names, (
        f"Stored connection names {stored_names} should match expected {expected_names}"
    )

    # Verify access levels are stored correctly
    for assignment in assignments:
        assert assignment["access_level"] == access_level.value, (
            f"Access level should be {access_level.value}, got {assignment['access_level']}"
        )


# ============================================================================
# Property 16: Connection Assignment Cardinality
# ============================================================================


@given(
    agent_name=valid_agent_names,
    num_connections=st.integers(min_value=0, max_value=10),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_16_assignment_cardinality(agent_name, num_connections, access_level):
    """Property 16: Connection Assignment Cardinality

    **Validates: Requirements 6.1**

    For any agent, the system should allow assignment of zero or more connections
    (0 to N), including empty lists and lists with multiple connections.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Generate unique connection names
    connection_names = [f"conn-{i}" for i in range(num_connections)]

    # Create all connections
    for conn_name in connection_names:
        assert create_test_connection(db_manager, conn_name, env["connections_file"].parent)

    # Prepare allowed_tables if needed
    allowed_tables = (
        ["test_table"]
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    # Assign all connections
    for conn_name in connection_names:
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Failed to assign connection {conn_name}"

    # Load the agent and verify cardinality
    agent = agent_manager.get_agent(agent_name)
    assert agent is not None, "Agent should exist"
    assert len(agent.connection_assignments) == num_connections, (
        f"Agent should have {num_connections} assignments, got {len(agent.connection_assignments)}"
    )

    # Verify all connection names are present
    if num_connections > 0:
        stored_names = {a.connection_name for a in agent.connection_assignments}
        expected_names = set(connection_names)
        assert stored_names == expected_names, "Stored connection names should match expected"


@given(
    agent_name=valid_agent_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_16_assignment_cardinality_zero(agent_name, access_level):
    """Property 16: Connection Assignment Cardinality (Zero Case)

    **Validates: Requirements 6.1**

    Specifically tests that agents can have zero connections assigned.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Load the agent and verify it has zero connections
    agent = agent_manager.get_agent(agent_name)
    assert agent is not None, "Agent should exist"
    assert len(agent.connection_assignments) == 0, "Newly created agent should have zero connection assignments"


# ============================================================================
# Property 32: Access Level Storage
# ============================================================================


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    access_level=access_levels,
    tables=table_lists,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_32_access_level_storage(agent_name, connection_name, access_level, tables):
    """Property 32: Access Level Storage

    **Validates: Requirements 12.9**

    For any agent and connection assignment, the access level should be stored
    in the agent config and retrievable when loading the config.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Prepare allowed_tables based on access level
    allowed_tables = (
        tables if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE) else None
    )

    # Assign the connection with access level
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )
    assert is_ok(result), f"Assignment failed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent from storage
    agent = agent_manager.get_agent(agent_name)
    assert agent is not None, "Agent should exist"

    # Verify the assignment exists
    assert len(agent.connection_assignments) == 1, "Should have exactly one assignment"
    assignment = agent.connection_assignments[0]

    # Verify access level is stored correctly
    assert assignment.access_level == access_level, (
        f"Access level should be {access_level}, got {assignment.access_level}"
    )

    # Verify connection name is stored correctly
    assert assignment.connection_name == connection_name, (
        f"Connection name should be {connection_name}, got {assignment.connection_name}"
    )

    # Verify allowed_tables is stored correctly
    if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE):
        assert assignment.allowed_tables == tables, (
            f"Allowed tables should be {tables}, got {assignment.allowed_tables}"
        )
    else:
        assert assignment.allowed_tables is None, (
            f"Allowed tables should be None for {access_level}, got {assignment.allowed_tables}"
        )


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    initial_access=access_levels,
    updated_access=access_levels,
    initial_tables=table_lists,
    updated_tables=table_lists,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_32_access_level_storage_update(
    agent_name, connection_name, initial_access, updated_access, initial_tables, updated_tables
):
    """Property 32: Access Level Storage (Update Case)

    **Validates: Requirements 12.9**

    For any agent and connection assignment, updating the access level should
    persist the new access level in storage.
    """
    # Ensure the access levels are different
    assume(initial_access != updated_access or initial_tables != updated_tables)

    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Assign with initial access level
    initial_allowed = (
        initial_tables
        if initial_access in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    result1 = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=initial_access,
        allowed_tables=initial_allowed,
    )
    assert is_ok(result1), f"Initial assignment failed: {unwrap_err(result1) if is_err(result1) else ''}"

    # Update with new access level
    updated_allowed = (
        updated_tables
        if updated_access in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    result2 = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=updated_access,
        allowed_tables=updated_allowed,
    )
    assert is_ok(result2), f"Update assignment failed: {unwrap_err(result2) if is_err(result2) else ''}"

    # Load the agent from storage
    agent = agent_manager.get_agent(agent_name)
    assert agent is not None, "Agent should exist"

    # Verify only one assignment exists (update, not duplicate)
    assert len(agent.connection_assignments) == 1, "Should have exactly one assignment after update"

    assignment = agent.connection_assignments[0]

    # Verify the updated access level is stored
    assert assignment.access_level == updated_access, (
        f"Access level should be updated to {updated_access}, got {assignment.access_level}"
    )

    # Verify the updated allowed_tables is stored
    if updated_access in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE):
        assert assignment.allowed_tables == updated_tables, (
            f"Allowed tables should be updated to {updated_tables}, got {assignment.allowed_tables}"
        )
    else:
        assert assignment.allowed_tables is None, (
            f"Allowed tables should be None for {updated_access}, got {assignment.allowed_tables}"
        )
