"""Property-based tests for database configuration migration.

This module contains property-based tests using Hypothesis to verify universal
properties of the migration functionality that converts inline database configs
to centralized connection management.

Properties tested:
- Property 20: Migration Connection Creation
- Property 21: Migration Config Update
- Property 22: Migration Detection
- Property 23: Migration Error Handling

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.migration import detect_inline_configs, migrate_agent
from offline_chat.database.result import is_err, is_ok, unwrap, unwrap_err

# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid agent names (kebab-case)
valid_agent_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30
).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s and s[0] not in '0123456789')

# Database types
database_types = st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])

# Valid connection names (kebab-case)
valid_connection_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30
).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s and s[0] not in '0123456789')


# Strategy for generating inline database configs
@st.composite
def inline_database_config(draw, db_type=None):
    """Generate a valid inline database configuration."""
    if db_type is None:
        db_type = draw(database_types)

    config = {"type": db_type}

    # Use text that won't be stripped to empty
    non_empty_text = st.text(
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs', 'Zs', 'Zl', 'Zp')),
        min_size=1,
        max_size=50
    ).filter(lambda s: s.strip() != '')

    if db_type == "sqlite":
        config["file_path"] = f"/tmp/test_{draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=5, max_size=10))}.db"
    else:
        config["host"] = draw(non_empty_text)
        config["port"] = draw(st.integers(min_value=1, max_value=65535))
        config["username"] = draw(non_empty_text)
        config["password"] = draw(non_empty_text)

        if db_type == "oracle":
            config["service_name"] = draw(non_empty_text)
        else:  # postgresql or mysql
            config["database"] = draw(non_empty_text)

    return config


# ============================================================================
# Helper Functions
# ============================================================================

def setup_test_environment():
    """Set up test environment with temporary directories and managers."""
    tmp_dir = Path(tempfile.mkdtemp())

    agents_dir = tmp_dir / "agents"
    connections_file = tmp_dir / "connections.json"

    agents_dir.mkdir(parents=True, exist_ok=True)

    db_manager = DatabaseConnectionManager(store_path=connections_file)

    return {
        "tmp_dir": tmp_dir,
        "agents_dir": agents_dir,
        "connections_file": connections_file,
        "db_manager": db_manager,
    }


def create_agent_with_inline_config(agents_dir: Path, agent_name: str, database_config: dict) -> Path:
    """Create an agent config file with inline database_config."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
        "database_config": database_config
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return config_path


def create_agent_with_connection_references(agents_dir: Path, agent_name: str, connection_refs: list[str]) -> Path:
    """Create an agent config file with legacy connection_references."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
        "connection_references": connection_refs
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return config_path



def create_agent_without_inline_config(agents_dir: Path, agent_name: str) -> Path:
    """Create an agent config file without inline database_config."""
    agent_dir = agents_dir / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    config_path = agent_dir / "config.json"
    config_data = {
        "name": agent_name,
        "display_name": f"Test Agent {agent_name}",
        "base_model": "llama3:latest",
        "system_prompt": "You are a test agent.",
        "temperature": 0.7,
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return config_path


# ============================================================================
# Property 20: Migration Connection Creation
# ============================================================================

@given(
    agent_name=valid_agent_names,
    db_config=inline_database_config(),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_20_migration_connection_creation(agent_name, db_config):
    """Property 20: Migration Connection Creation

    **Validates: Requirements 9.2, 9.3**

    For any agent with inline database_config, running migration should create
    a new connection in the store with a name following the pattern
    "{agent_name}-{database_type}".
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create agent with inline config
    config_path = create_agent_with_inline_config(agents_dir, agent_name, db_config)

    # Load the config
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Run migration
    result = migrate_agent(agent_name, config_data, config_path, db_manager)

    # Migration should succeed
    assert is_ok(result), f"Migration should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Get the expected connection name
    db_type = db_config["type"]
    expected_connection_name = f"{agent_name}-{db_type}"

    # Verify connection was created in the store
    conn_result = db_manager.get_connection(expected_connection_name)
    assert is_ok(conn_result), \
        f"Connection '{expected_connection_name}' should exist in store"

    # Verify connection has correct database type
    connection = unwrap(conn_result)
    assert connection.database_type == db_type, \
        f"Connection database_type should be {db_type}, got {connection.database_type}"


# ============================================================================
# Property 21: Migration Config Update
# ============================================================================

@given(
    agent_name=valid_agent_names,
    db_config=inline_database_config(),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_21_migration_config_update(agent_name, db_config):
    """Property 21: Migration Config Update

    **Validates: Requirements 9.4, 9.5**

    For any agent with inline database_config, after successful migration,
    the agent config should have the new connection name in connection_assignments
    and the database_config field should be removed.
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create agent with inline config
    config_path = create_agent_with_inline_config(agents_dir, agent_name, db_config)

    # Load the config
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Verify database_config exists before migration
    assert "database_config" in config_data, "Config should have database_config before migration"

    # Run migration
    result = migrate_agent(agent_name, config_data, config_path, db_manager)
    assert is_ok(result), f"Migration should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the updated config from file
    with open(config_path, "r", encoding="utf-8") as f:
        updated_config = json.load(f)

    # Verify database_config field is removed
    assert "database_config" not in updated_config, \
        "database_config field should be removed after migration"

    # Verify connection_assignments field exists
    assert "connection_assignments" in updated_config, \
        "connection_assignments field should exist after migration"

    # Verify connection_assignments has the correct connection
    db_type = db_config["type"]
    expected_connection_name = f"{agent_name}-{db_type}"

    assignments = updated_config["connection_assignments"]
    assert len(assignments) > 0, "Should have at least one connection assignment"

    # Find the assignment for our connection
    found = False
    for assignment in assignments:
        if assignment["connection_name"] == expected_connection_name:
            found = True
            # Verify access level is READ_WRITE for backward compatibility
            assert assignment["access_level"] == "read-write", \
                f"Access level should be 'read-write', got {assignment['access_level']}"
            break

    assert found, f"Connection '{expected_connection_name}' should be in connection_assignments"



@given(
    agent_name=valid_agent_names,
    connection_refs=st.lists(valid_connection_names, min_size=1, max_size=3, unique=True),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_21_migration_config_update_legacy_references(agent_name, connection_refs):
    """Property 21: Migration Config Update (Legacy References)

    **Validates: Requirements 9.4, 9.5**

    For any agent with legacy connection_references, after successful migration,
    the agent config should have connection_assignments and the connection_references
    field should be removed.
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create the referenced connections first
    for conn_name in connection_refs:
        conn = DatabaseConnection(
            name=conn_name,
            database_type="sqlite",
            file_path=f"/tmp/{conn_name}.db"
        )
        result = db_manager.create_connection(conn)
        assert is_ok(result), f"Failed to create connection {conn_name}"

    # Create agent with legacy connection_references
    config_path = create_agent_with_connection_references(agents_dir, agent_name, connection_refs)

    # Load the config
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    # Verify connection_references exists before migration
    assert "connection_references" in config_data, \
        "Config should have connection_references before migration"

    # Run migration
    result = migrate_agent(agent_name, config_data, config_path, db_manager)
    assert is_ok(result), f"Migration should succeed: {unwrap_err(result) if is_err(result) else ''}"

    # Load the updated config from file
    with open(config_path, "r", encoding="utf-8") as f:
        updated_config = json.load(f)

    # Verify connection_references field is removed
    assert "connection_references" not in updated_config, \
        "connection_references field should be removed after migration"

    # Verify connection_assignments field exists
    assert "connection_assignments" in updated_config, \
        "connection_assignments field should exist after migration"

    # Verify all connection references are converted to assignments
    assignments = updated_config["connection_assignments"]
    assert len(assignments) == len(connection_refs), \
        f"Should have {len(connection_refs)} assignments, got {len(assignments)}"

    # Verify all connection names are present with READ_WRITE access
    assignment_names = {a["connection_name"] for a in assignments}
    assert assignment_names == set(connection_refs), \
        f"Assignment names {assignment_names} should match references {set(connection_refs)}"

    for assignment in assignments:
        assert assignment["access_level"] == "read-write", \
            f"Access level should be 'read-write', got {assignment['access_level']}"


# ============================================================================
# Property 22: Migration Detection
# ============================================================================

@given(
    agents_with_inline=st.lists(
        st.tuples(valid_agent_names, inline_database_config()),
        min_size=0,
        max_size=5,
        unique_by=lambda x: x[0]  # Unique by agent name
    ),
    agents_without_inline=st.lists(
        valid_agent_names,
        min_size=0,
        max_size=5,
        unique=True
    ),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_22_migration_detection(agents_with_inline, agents_without_inline):
    """Property 22: Migration Detection

    **Validates: Requirements 9.1**

    For any set of agents, the system should correctly identify which agents
    have inline database_config fields that need migration.
    """
    # Ensure no overlap between agent names
    inline_names = {name for name, _ in agents_with_inline}
    assume(not any(name in inline_names for name in agents_without_inline))

    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]

    # Create agents with inline configs
    for agent_name, db_config in agents_with_inline:
        create_agent_with_inline_config(agents_dir, agent_name, db_config)

    # Create agents without inline configs
    for agent_name in agents_without_inline:
        create_agent_without_inline_config(agents_dir, agent_name)

    # Run detection
    detected = detect_inline_configs(agents_dir)

    # Verify correct number of agents detected
    assert len(detected) == len(agents_with_inline), \
        f"Should detect {len(agents_with_inline)} agents, detected {len(detected)}"

    # Verify all agents with inline configs are detected
    detected_names = {name for name, _ in detected}
    expected_names = {name for name, _ in agents_with_inline}
    assert detected_names == expected_names, \
        f"Detected names {detected_names} should match expected {expected_names}"

    # Verify agents without inline configs are not detected
    for agent_name in agents_without_inline:
        assert agent_name not in detected_names, \
            f"Agent {agent_name} without inline config should not be detected"



@given(
    agents_with_legacy_refs=st.lists(
        st.tuples(
            valid_agent_names,
            st.lists(valid_connection_names, min_size=1, max_size=3, unique=True)
        ),
        min_size=0,
        max_size=3,
        unique_by=lambda x: x[0]  # Unique by agent name
    ),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_22_migration_detection_legacy_references(agents_with_legacy_refs):
    """Property 22: Migration Detection (Legacy References)

    **Validates: Requirements 9.1**

    For any set of agents with legacy connection_references, the system should
    correctly identify them as needing migration.
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create all referenced connections
    all_connection_names = set()
    for _, conn_refs in agents_with_legacy_refs:
        all_connection_names.update(conn_refs)

    for conn_name in all_connection_names:
        conn = DatabaseConnection(
            name=conn_name,
            database_type="sqlite",
            file_path=f"/tmp/{conn_name}.db"
        )
        result = db_manager.create_connection(conn)
        assert is_ok(result), f"Failed to create connection {conn_name}"

    # Create agents with legacy connection_references
    for agent_name, conn_refs in agents_with_legacy_refs:
        create_agent_with_connection_references(agents_dir, agent_name, conn_refs)

    # Run detection
    detected = detect_inline_configs(agents_dir)

    # Verify correct number of agents detected
    assert len(detected) == len(agents_with_legacy_refs), \
        f"Should detect {len(agents_with_legacy_refs)} agents, detected {len(detected)}"

    # Verify all agents with legacy references are detected
    detected_names = {name for name, _ in detected}
    expected_names = {name for name, _ in agents_with_legacy_refs}
    assert detected_names == expected_names, \
        f"Detected names {detected_names} should match expected {expected_names}"


# ============================================================================
# Property 23: Migration Error Handling
# ============================================================================

@given(
    agent_name=valid_agent_names,
    db_config=inline_database_config(),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_23_migration_error_handling_invalid_config(agent_name, db_config):
    """Property 23: Migration Error Handling

    **Validates: Requirements 9.6**

    For any agent migration that encounters an error, the original agent
    configuration should remain unchanged (no partial migration).

    This test simulates an error by making the config file read-only.
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create agent with inline config
    config_path = create_agent_with_inline_config(agents_dir, agent_name, db_config)

    # Load the original config
    with open(config_path, "r", encoding="utf-8") as f:
        original_config = json.load(f)

    # Make the config file read-only to simulate an error during save
    import os
    os.chmod(config_path, 0o444)

    try:
        # Run migration - should fail due to read-only file
        result = migrate_agent(agent_name, original_config.copy(), config_path, db_manager)

        # Migration should fail
        assert is_err(result), "Migration should fail when config file is read-only"

        # Restore write permissions to read the file
        os.chmod(config_path, 0o644)

        # Load the config from file
        with open(config_path, "r", encoding="utf-8") as f:
            current_config = json.load(f)

        # Verify the config is unchanged (still has database_config)
        assert "database_config" in current_config, \
            "Original config should be preserved when migration fails"
        assert current_config["database_config"] == db_config, \
            "database_config should be unchanged when migration fails"

        # Verify connection_assignments was not added
        assert "connection_assignments" not in current_config, \
            "connection_assignments should not be added when migration fails"

    finally:
        # Ensure we restore write permissions for cleanup
        try:
            os.chmod(config_path, 0o644)
        except Exception:
            pass


@given(
    agent_name=valid_agent_names,
    nonexistent_refs=st.lists(valid_connection_names, min_size=1, max_size=3, unique=True),
)
@settings(deadline=2000, max_examples=50)
@pytest.mark.property_test
def test_property_23_migration_error_handling_missing_connection(agent_name, nonexistent_refs):
    """Property 23: Migration Error Handling (Missing Connection)

    **Validates: Requirements 9.6**

    For any agent with connection_references that don't exist in the store,
    migration should fail and preserve the original configuration.
    """
    # Set up test environment
    env = setup_test_environment()
    agents_dir = env["agents_dir"]
    db_manager = env["db_manager"]

    # Create agent with legacy connection_references (but don't create the connections)
    config_path = create_agent_with_connection_references(agents_dir, agent_name, nonexistent_refs)

    # Load the original config
    with open(config_path, "r", encoding="utf-8") as f:
        original_config = json.load(f)

    # Run migration - should fail because connections don't exist
    result = migrate_agent(agent_name, original_config.copy(), config_path, db_manager)

    # Migration should fail
    assert is_err(result), "Migration should fail when referenced connections don't exist"
    error_msg = unwrap_err(result)
    assert "not found" in error_msg.lower(), \
        f"Error message should mention 'not found': {error_msg}"

    # Load the config from file
    with open(config_path, "r", encoding="utf-8") as f:
        current_config = json.load(f)

    # Verify the config is unchanged (still has connection_references)
    assert "connection_references" in current_config, \
        "Original config should be preserved when migration fails"
    assert current_config["connection_references"] == nonexistent_refs, \
        "connection_references should be unchanged when migration fails"

    # Verify connection_assignments was not added
    assert "connection_assignments" not in current_config, \
        "connection_assignments should not be added when migration fails"
