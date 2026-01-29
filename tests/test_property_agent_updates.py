"""Property-based tests for agent updates.

This module contains property-based tests using Hypothesis to verify universal
properties of agent update functionality.

Properties tested:
- Property 19: Agent Update Persistence
- Property 25: Connection Addition to Agent
- Property 26: Connection Removal from Agent

**Validates: Requirements 7.4, 7.5, 7.6**
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

# System prompts
system_prompts = st.text(min_size=10, max_size=200)

# Temperature values
temperatures = st.floats(min_value=0.0, max_value=1.0)

# Languages (use simple alphabetic strings)
languages = st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu")), min_size=3, max_size=20)

# Web search enabled
web_search_flags = st.booleans()

# Guidelines (use simpler text generation)
guidelines = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=" .,"),
        min_size=5,
        max_size=50,
    ),
    min_size=0,
    max_size=5,
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


def create_test_agent(agent_manager, name: str, **kwargs) -> bool:
    """Create a test agent without Ollama registration."""
    agent = Agent(
        name=name,
        display_name=kwargs.get("display_name", f"Test Agent {name}"),
        base_model=kwargs.get("base_model", "llama3:latest"),
        system_prompt=kwargs.get("system_prompt", "You are a test agent."),
        temperature=kwargs.get("temperature", 0.7),
        language=kwargs.get("language", None),
        web_search_enabled=kwargs.get("web_search_enabled", False),
        guidelines=kwargs.get("guidelines", []),
    )

    # Save agent config manually (skip Ollama registration for tests)
    agent_dir = agent_manager._get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)

    config_path = agent_manager._get_config_path(agent.name)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(agent.to_dict(), f, indent=2)

    return True


# ============================================================================
# Property 19: Agent Update Persistence
# ============================================================================


@given(
    agent_name=valid_agent_names,
    initial_prompt=system_prompts,
    initial_temp=temperatures,
    initial_language=languages,
    initial_web_search=web_search_flags,
    initial_guidelines=guidelines,
    updated_prompt=system_prompts,
    updated_temp=temperatures,
    updated_language=languages,
    updated_web_search=web_search_flags,
    updated_guidelines=guidelines,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_19_agent_update_persistence(
    agent_name,
    initial_prompt,
    initial_temp,
    initial_language,
    initial_web_search,
    initial_guidelines,
    updated_prompt,
    updated_temp,
    updated_language,
    updated_web_search,
    updated_guidelines,
):
    """Property 19: Agent Update Persistence

    **Validates: Requirements 7.4, 7.5, 7.6**

    For any agent and any valid updates (system_prompt, temperature, language,
    web_search, connection_references, mcp_servers), after successful update,
    loading the agent config should reflect all the changes.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]

    # Create the agent with initial values
    assert create_test_agent(
        agent_manager,
        agent_name,
        system_prompt=initial_prompt,
        temperature=initial_temp,
        language=initial_language,
        web_search_enabled=initial_web_search,
        guidelines=initial_guidelines,
    )

    # Prepare updates
    updates = {
        "system_prompt": updated_prompt,
        "temperature": updated_temp,
        "language": updated_language,
        "web_search_enabled": updated_web_search,
        "guidelines": updated_guidelines,
    }

    # Update the agent
    result = agent_manager.update_agent(agent_name=agent_name, updates=updates)

    # Verify update succeeded
    assert is_ok(result), f"Update should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after update"

    # Verify all updates persisted
    assert reloaded_agent.system_prompt == updated_prompt, (
        f"System prompt should be updated to '{updated_prompt}', got '{reloaded_agent.system_prompt}'"
    )
    assert reloaded_agent.temperature == updated_temp, (
        f"Temperature should be updated to {updated_temp}, got {reloaded_agent.temperature}"
    )
    assert reloaded_agent.language == updated_language, (
        f"Language should be updated to '{updated_language}', got '{reloaded_agent.language}'"
    )
    assert reloaded_agent.web_search_enabled == updated_web_search, (
        f"Web search should be updated to {updated_web_search}, got {reloaded_agent.web_search_enabled}"
    )
    assert reloaded_agent.guidelines == updated_guidelines, (
        f"Guidelines should be updated to {updated_guidelines}, got {reloaded_agent.guidelines}"
    )


@given(
    agent_name=valid_agent_names,
    system_prompt=system_prompts,
    temperature=temperatures,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_19_agent_update_persistence_single_field(agent_name, system_prompt, temperature):
    """Property 19: Agent Update Persistence (Single Field)

    **Validates: Requirements 7.4, 7.5, 7.6**

    For any agent and any single field update, after successful update,
    loading the agent config should reflect the change while preserving
    other fields.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]

    # Create the agent with initial values
    initial_prompt = "Initial prompt"
    initial_temp = 0.5
    initial_language = "English"

    assert create_test_agent(
        agent_manager,
        agent_name,
        system_prompt=initial_prompt,
        temperature=initial_temp,
        language=initial_language,
    )

    # Update only system_prompt
    result = agent_manager.update_agent(agent_name=agent_name, updates={"system_prompt": system_prompt})

    assert is_ok(result), f"Update should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load and verify
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent.system_prompt == system_prompt, "System prompt should be updated"
    assert reloaded_agent.temperature == initial_temp, "Temperature should be preserved"
    assert reloaded_agent.language == initial_language, "Language should be preserved"

    # Update only temperature
    result = agent_manager.update_agent(agent_name=agent_name, updates={"temperature": temperature})

    assert is_ok(result), f"Update should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load and verify
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent.system_prompt == system_prompt, "System prompt should be preserved"
    assert reloaded_agent.temperature == temperature, "Temperature should be updated"
    assert reloaded_agent.language == initial_language, "Language should be preserved"


# ============================================================================
# Property 25: Connection Addition to Agent
# ============================================================================


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_25_connection_addition(agent_name, connection_name, access_level):
    """Property 25: Connection Addition to Agent

    **Validates: Requirements 7.4**

    For any agent and any valid connection name, adding the connection should
    result in the connection name appearing in the agent's connection_assignments
    array.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    agent_manager = env["agent_manager"]

    # Create the connection
    assert create_test_connection(db_manager, connection_name, env["connections_file"].parent)

    # Create the agent
    assert create_test_agent(agent_manager, agent_name)

    # Verify agent starts with no connections
    agent = agent_manager.get_agent(agent_name)
    initial_count = len(agent.connection_assignments)

    # Prepare allowed_tables if needed
    allowed_tables = (
        ["test_table"]
        if access_level in (AccessLevel.TABLE_SPECIFIC_READ, AccessLevel.TABLE_SPECIFIC_READ_WRITE)
        else None
    )

    # Add the connection
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )

    # Verify addition succeeded
    assert is_ok(result), f"Connection addition should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after connection addition"

    # Verify the connection was added
    assert len(reloaded_agent.connection_assignments) == initial_count + 1, (
        f"Should have {initial_count + 1} connections after addition, got {len(reloaded_agent.connection_assignments)}"
    )

    # Verify the connection name appears in the assignments
    connection_names = {a.connection_name for a in reloaded_agent.connection_assignments}
    assert connection_name in connection_names, (
        f"Connection '{connection_name}' should be in assignments: {connection_names}"
    )

    # Verify the access level is correct
    added_assignment = next(a for a in reloaded_agent.connection_assignments if a.connection_name == connection_name)
    assert added_assignment.access_level == access_level, (
        f"Access level should be {access_level}, got {added_assignment.access_level}"
    )


@given(
    agent_name=valid_agent_names,
    connection_names=st.lists(valid_connection_names, min_size=2, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_25_connection_addition_multiple(agent_name, connection_names, access_level):
    """Property 25: Connection Addition to Agent (Multiple Connections)

    **Validates: Requirements 7.4**

    For any agent and multiple valid connection names, adding each connection
    should result in all connection names appearing in the agent's
    connection_assignments array.
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

    # Add each connection
    for conn_name in connection_names:
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Connection addition should succeed for {conn_name}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after connection additions"

    # Verify all connections were added
    assert len(reloaded_agent.connection_assignments) == len(connection_names), (
        f"Should have {len(connection_names)} connections, got {len(reloaded_agent.connection_assignments)}"
    )

    # Verify all connection names appear in the assignments
    stored_names = {a.connection_name for a in reloaded_agent.connection_assignments}
    expected_names = set(connection_names)
    assert stored_names == expected_names, (
        f"Stored connection names {stored_names} should match expected {expected_names}"
    )


# ============================================================================
# Property 26: Connection Removal from Agent
# ============================================================================


@given(
    agent_name=valid_agent_names,
    connection_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_26_connection_removal(agent_name, connection_name, access_level):
    """Property 26: Connection Removal from Agent

    **Validates: Requirements 7.5**

    For any agent and any connection name currently in its connection_assignments,
    removing the connection should result in the connection name no longer
    appearing in the array.
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

    # Add the connection first
    result = agent_manager.assign_connection(
        agent_name=agent_name,
        connection_name=connection_name,
        access_level=access_level,
        allowed_tables=allowed_tables,
    )
    assert is_ok(result), f"Connection addition should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Verify the connection was added
    agent = agent_manager.get_agent(agent_name)
    assert len(agent.connection_assignments) == 1, "Should have 1 connection after addition"
    assert agent.connection_assignments[0].connection_name == connection_name

    # Remove the connection
    result = agent_manager.remove_connection(
        agent_name=agent_name,
        connection_name=connection_name,
    )

    # Verify removal succeeded
    assert is_ok(result), f"Connection removal should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after connection removal"

    # Verify the connection was removed
    assert len(reloaded_agent.connection_assignments) == 0, (
        f"Should have 0 connections after removal, got {len(reloaded_agent.connection_assignments)}"
    )

    # Verify the connection name does not appear in the assignments
    connection_names = {a.connection_name for a in reloaded_agent.connection_assignments}
    assert connection_name not in connection_names, (
        f"Connection '{connection_name}' should not be in assignments: {connection_names}"
    )


@given(
    agent_name=valid_agent_names,
    connection_names=st.lists(valid_connection_names, min_size=2, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_26_connection_removal_from_multiple(agent_name, connection_names, access_level):
    """Property 26: Connection Removal from Agent (Multiple Connections)

    **Validates: Requirements 7.5**

    For any agent with multiple connections, removing one connection should
    result in only that connection being removed while others remain.
    """
    # Ensure we have at least 2 connections
    assume(len(connection_names) >= 2)

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

    # Add all connections
    for conn_name in connection_names:
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Connection addition should succeed for {conn_name}"

    # Verify all connections were added
    agent = agent_manager.get_agent(agent_name)
    assert len(agent.connection_assignments) == len(connection_names)

    # Remove the first connection
    connection_to_remove = connection_names[0]
    result = agent_manager.remove_connection(
        agent_name=agent_name,
        connection_name=connection_to_remove,
    )

    # Verify removal succeeded
    assert is_ok(result), f"Connection removal should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after connection removal"

    # Verify the connection count decreased by 1
    assert len(reloaded_agent.connection_assignments) == len(connection_names) - 1, (
        f"Should have {len(connection_names) - 1} connections after removal, got {len(reloaded_agent.connection_assignments)}"
    )

    # Verify the removed connection is not in the assignments
    stored_names = {a.connection_name for a in reloaded_agent.connection_assignments}
    assert connection_to_remove not in stored_names, (
        f"Removed connection '{connection_to_remove}' should not be in assignments: {stored_names}"
    )

    # Verify the other connections are still present
    expected_remaining = set(connection_names[1:])
    assert stored_names == expected_remaining, (
        f"Remaining connections {stored_names} should match expected {expected_remaining}"
    )


@given(
    agent_name=valid_agent_names,
    connection_names=st.lists(valid_connection_names, min_size=1, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_26_connection_removal_all(agent_name, connection_names, access_level):
    """Property 26: Connection Removal from Agent (Remove All)

    **Validates: Requirements 7.5**

    For any agent with connections, removing all connections should result
    in an empty connection_assignments array.
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

    # Add all connections
    for conn_name in connection_names:
        result = agent_manager.assign_connection(
            agent_name=agent_name,
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables,
        )
        assert is_ok(result), f"Connection addition should succeed for {conn_name}"

    # Verify all connections were added
    agent = agent_manager.get_agent(agent_name)
    assert len(agent.connection_assignments) == len(connection_names)

    # Remove all connections
    for conn_name in connection_names:
        result = agent_manager.remove_connection(
            agent_name=agent_name,
            connection_name=conn_name,
        )
        assert is_ok(result), f"Connection removal should succeed for {conn_name}"

    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after removing all connections"

    # Verify all connections were removed
    assert len(reloaded_agent.connection_assignments) == 0, (
        f"Should have 0 connections after removing all, got {len(reloaded_agent.connection_assignments)}"
    )

    # Verify the assignments array is empty
    assert reloaded_agent.connection_assignments == [], "Connection assignments should be an empty list"
