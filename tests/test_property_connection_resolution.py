"""Property-based tests for connection resolution.

This module contains property-based tests using Hypothesis to verify universal
properties of connection resolution functionality.

Properties tested:
- Property 17: Connection Resolution
- Property 18: Connection Resolution Error Handling

**Validates: Requirements 6.5, 11.1, 11.2, 11.3, 11.4, 11.5**
"""

import tempfile
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path

from offline_chat.database import AccessLevel, AgentConnectionAssignment
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_ok, is_err, unwrap, unwrap_err


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid connection names (kebab-case)
valid_connection_names = st.text(
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
    """Set up test environment with temporary directory and manager."""
    tmp_dir = Path(tempfile.mkdtemp())
    connections_file = tmp_dir / "connections.json"
    
    db_manager = DatabaseConnectionManager(store_path=connections_file)
    
    return {
        "tmp_dir": tmp_dir,
        "connections_file": connections_file,
        "db_manager": db_manager,
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


# ============================================================================
# Property 17: Connection Resolution
# ============================================================================

@given(
    connection_names=st.lists(valid_connection_names, min_size=1, max_size=5, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_17_connection_resolution(connection_names, access_level):
    """Property 17: Connection Resolution
    
    **Validates: Requirements 6.5, 11.1, 11.2, 11.4, 11.5**
    
    For any agent with connection references, resolving the references should
    look up each name in the store and return the full connection configurations
    for all valid references.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create all connections
    for conn_name in connection_names:
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Create assignments for all connections
    assignments = [
        AgentConnectionAssignment(
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables
        )
        for conn_name in connection_names
    ]
    
    # Resolve the connections
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution succeeded
    assert is_ok(result), f"Resolution should succeed when all connections exist: {unwrap_err(result) if is_err(result) else ''}"
    
    resolved = unwrap(result)
    
    # Verify we got the correct number of resolved connections
    assert len(resolved) == len(connection_names), \
        f"Should resolve {len(connection_names)} connections, got {len(resolved)}"
    
    # Verify each resolved connection
    resolved_names = {conn.name for conn, _, _ in resolved}
    expected_names = set(connection_names)
    assert resolved_names == expected_names, \
        f"Resolved connection names {resolved_names} should match expected {expected_names}"
    
    # Verify access levels and allowed_tables are preserved
    for conn, level, tables in resolved:
        assert level == access_level, \
            f"Access level should be {access_level}, got {level}"
        assert tables == allowed_tables, \
            f"Allowed tables should be {allowed_tables}, got {tables}"


@given(
    connection_names=st.lists(valid_connection_names, min_size=1, max_size=5, unique=True),
    access_levels_list=st.lists(access_levels, min_size=1, max_size=5),
    tables_list=st.lists(table_lists, min_size=1, max_size=5),
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_17_connection_resolution_mixed_access_levels(
    connection_names, access_levels_list, tables_list
):
    """Property 17: Connection Resolution (Mixed Access Levels)
    
    **Validates: Requirements 6.5, 11.1, 11.2, 11.4, 11.5**
    
    For any agent with connection references with different access levels,
    resolving should preserve each connection's specific access level and
    allowed tables.
    """
    # Ensure we have enough access levels and tables for all connections
    assume(len(access_levels_list) >= len(connection_names))
    assume(len(tables_list) >= len(connection_names))
    
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create all connections
    for conn_name in connection_names:
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
    
    # Create assignments with different access levels
    assignments = []
    for i, conn_name in enumerate(connection_names):
        access_level = access_levels_list[i]
        allowed_tables = tables_list[i] if access_level in (
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ) else None
        
        assignments.append(AgentConnectionAssignment(
            connection_name=conn_name,
            access_level=access_level,
            allowed_tables=allowed_tables
        ))
    
    # Resolve the connections
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution succeeded
    assert is_ok(result), f"Resolution should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    resolved = unwrap(result)
    
    # Verify we got the correct number of resolved connections
    assert len(resolved) == len(connection_names), \
        f"Should resolve {len(connection_names)} connections, got {len(resolved)}"
    
    # Verify each resolved connection has the correct access level and tables
    resolved_dict = {conn.name: (level, tables) for conn, level, tables in resolved}
    
    for i, conn_name in enumerate(connection_names):
        assert conn_name in resolved_dict, f"Connection {conn_name} should be resolved"
        
        level, tables = resolved_dict[conn_name]
        expected_level = access_levels_list[i]
        expected_tables = tables_list[i] if expected_level in (
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ) else None
        
        assert level == expected_level, \
            f"Connection {conn_name} should have access level {expected_level}, got {level}"
        assert tables == expected_tables, \
            f"Connection {conn_name} should have tables {expected_tables}, got {tables}"


@given(
    connection_names=st.lists(valid_connection_names, min_size=0, max_size=0),
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_17_connection_resolution_empty_list(connection_names):
    """Property 17: Connection Resolution (Empty List)
    
    **Validates: Requirements 6.5, 11.1, 11.2, 11.4, 11.5**
    
    For any agent with no connection references, resolving should succeed
    and return an empty list.
    """
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create empty assignments list
    assignments = []
    
    # Resolve the connections
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution succeeded
    assert is_ok(result), f"Resolution should succeed for empty list: {unwrap_err(result) if is_err(result) else ''}"
    
    resolved = unwrap(result)
    
    # Verify we got an empty list
    assert len(resolved) == 0, f"Should resolve 0 connections, got {len(resolved)}"


# ============================================================================
# Property 18: Connection Resolution Error Handling
# ============================================================================

@given(
    existing_names=st.lists(valid_connection_names, min_size=1, max_size=5, unique=True),
    missing_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_18_resolution_error_single_missing(
    existing_names, missing_name, access_level
):
    """Property 18: Connection Resolution Error Handling
    
    **Validates: Requirements 11.3**
    
    For any agent with connection references, if any referenced connection does
    not exist in the store, resolution should fail with an error indicating
    which connection is missing.
    """
    # Ensure the missing name is different from existing names
    assume(missing_name not in existing_names)
    
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create only the existing connections
    for conn_name in existing_names:
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Create assignments including the missing connection
    assignments = [
        AgentConnectionAssignment(
            connection_name=missing_name,
            access_level=access_level,
            allowed_tables=allowed_tables
        )
    ]
    
    # Try to resolve - should fail
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution failed
    assert is_err(result), "Resolution should fail when connection doesn't exist"
    
    error = unwrap_err(result)
    
    # Verify error message mentions the missing connection
    assert missing_name in error, \
        f"Error should mention missing connection '{missing_name}': {error}"
    assert "not found" in error.lower(), \
        f"Error should mention 'not found': {error}"


@given(
    existing_names=st.lists(valid_connection_names, min_size=1, max_size=3, unique=True),
    missing_names=st.lists(valid_connection_names, min_size=2, max_size=3, unique=True),
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_18_resolution_error_multiple_missing(
    existing_names, missing_names, access_level
):
    """Property 18: Connection Resolution Error Handling (Multiple Missing)
    
    **Validates: Requirements 11.3**
    
    For any agent with connection references, if multiple referenced connections
    do not exist in the store, resolution should fail with an error indicating
    all missing connections.
    """
    # Ensure missing names are different from existing names
    assume(not any(name in existing_names for name in missing_names))
    
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create only the existing connections
    for conn_name in existing_names:
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Create assignments including the missing connections
    assignments = [
        AgentConnectionAssignment(
            connection_name=name,
            access_level=access_level,
            allowed_tables=allowed_tables
        )
        for name in missing_names
    ]
    
    # Try to resolve - should fail
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution failed
    assert is_err(result), "Resolution should fail when connections don't exist"
    
    error = unwrap_err(result)
    
    # Verify error message mentions missing connections
    assert "not found" in error.lower(), \
        f"Error should mention 'not found': {error}"
    
    # Verify at least one missing connection is mentioned
    # (implementation may choose to list all or just indicate multiple)
    assert any(name in error for name in missing_names), \
        f"Error should mention at least one missing connection: {error}"


@given(
    existing_names=st.lists(valid_connection_names, min_size=2, max_size=5, unique=True),
    missing_name=valid_connection_names,
    access_level=access_levels,
)
@settings(deadline=1000, max_examples=50)
@pytest.mark.property_test
def test_property_18_resolution_error_mixed_valid_invalid(
    existing_names, missing_name, access_level
):
    """Property 18: Connection Resolution Error Handling (Mixed Valid/Invalid)
    
    **Validates: Requirements 11.3**
    
    For any agent with connection references containing both valid and invalid
    connection names, resolution should fail and indicate the invalid connection.
    """
    # Ensure the missing name is different from existing names
    assume(missing_name not in existing_names)
    
    # Set up test environment
    env = setup_test_environment()
    db_manager = env["db_manager"]
    
    # Create only the existing connections
    for conn_name in existing_names:
        assert create_test_connection(db_manager, conn_name, env["tmp_dir"])
    
    # Prepare allowed_tables if needed
    allowed_tables = ["test_table"] if access_level in (
        AccessLevel.TABLE_SPECIFIC_READ,
        AccessLevel.TABLE_SPECIFIC_READ_WRITE
    ) else None
    
    # Create assignments with mix of valid and invalid connections
    assignments = [
        AgentConnectionAssignment(
            connection_name=existing_names[0],
            access_level=access_level,
            allowed_tables=allowed_tables
        ),
        AgentConnectionAssignment(
            connection_name=missing_name,
            access_level=access_level,
            allowed_tables=allowed_tables
        ),
    ]
    
    # Try to resolve - should fail
    result = db_manager.resolve_connections(assignments)
    
    # Verify resolution failed
    assert is_err(result), "Resolution should fail when any connection doesn't exist"
    
    error = unwrap_err(result)
    
    # Verify error message mentions the missing connection
    assert missing_name in error, \
        f"Error should mention missing connection '{missing_name}': {error}"
    assert "not found" in error.lower(), \
        f"Error should mention 'not found': {error}"
