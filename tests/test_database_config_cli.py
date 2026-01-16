"""Property-based tests for database configuration CLI functions.

This module tests the CLI validation functions using property-based testing
to ensure they handle all valid inputs correctly.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from offline_chat.database_config_cli import (
    list_sqlcl_connections,
    validate_sqlite_path,
)


# Property 24: Oracle connection detection
@given(
    connections=st.lists(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
        ),
        min_size=0,
        max_size=10,
        unique=True,
    )
)
@pytest.mark.property_test
def test_list_sqlcl_connections_detects_existing_connections(connections):
    """
    Feature: database-access, Property 24: Oracle connection detection

    **Validates: Requirements 6.3**

    For any system with SQLcl installed, the CLI should detect and list
    existing SQLcl connections when configuring Oracle database access.

    This test verifies that when a connections.json file exists with
    connection names, the list_sqlcl_connections function correctly
    extracts and returns all connection names.
    """
    # Create a temporary SQLcl config directory
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlcl_dir = Path(tmpdir) / ".sqlcl"
        sqlcl_dir.mkdir()
        connections_file = sqlcl_dir / "connections.json"

        # Create connections.json with the generated connection names
        connections_data = {name: {"url": f"jdbc:oracle:thin:@{name}"} for name in connections}

        with open(connections_file, "w") as f:
            json.dump(connections_data, f)

        # Mock Path.home() to return our temp directory
        with patch("offline_chat.database_config_cli.Path.home", return_value=Path(tmpdir)):
            result = list_sqlcl_connections()

        # Verify all connections are detected
        assert set(result) == set(connections)
        assert len(result) == len(connections)


@pytest.mark.property_test
def test_list_sqlcl_connections_returns_empty_when_no_file():
    """
    Feature: database-access, Property 24: Oracle connection detection

    **Validates: Requirements 6.3**

    When no SQLcl connections.json file exists, the function should
    return an empty list rather than raising an error.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock Path.home() to return a directory without .sqlcl
        with patch("offline_chat.database_config_cli.Path.home", return_value=Path(tmpdir)):
            result = list_sqlcl_connections()

        assert result == []


@pytest.mark.property_test
def test_list_sqlcl_connections_handles_list_format():
    """
    Feature: database-access, Property 24: Oracle connection detection

    **Validates: Requirements 6.3**

    SQLcl connections.json may be formatted as a list of connection objects.
    The function should handle this format correctly.
    """
    connections = [
        {"name": "PROD_DB", "url": "jdbc:oracle:thin:@prod"},
        {"name": "TEST_DB", "url": "jdbc:oracle:thin:@test"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        sqlcl_dir = Path(tmpdir) / ".sqlcl"
        sqlcl_dir.mkdir()
        connections_file = sqlcl_dir / "connections.json"

        with open(connections_file, "w") as f:
            json.dump(connections, f)

        with patch("offline_chat.database_config_cli.Path.home", return_value=Path(tmpdir)):
            result = list_sqlcl_connections()

        assert set(result) == {"PROD_DB", "TEST_DB"}


# Property 25: SQLite file path validation
@given(
    filename=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-."),
    )
)
@pytest.mark.property_test
def test_validate_sqlite_path_accepts_existing_files(filename):
    """
    Feature: database-access, Property 25: SQLite file path validation

    **Validates: Requirements 6.5**

    For any file path, the SQLite configuration validator should accept it
    if the file exists and reject it with an error message if it doesn't.

    This test verifies that validate_sqlite_path returns True for any
    existing file path.
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        temp_path = f.name

    try:
        # Verify the file exists
        assert os.path.isfile(temp_path)

        # Test validation
        result = validate_sqlite_path(temp_path)

        # Should accept existing file
        assert result is True
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@given(
    path=st.text(
        min_size=1,
        max_size=200,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/_-."
        ),
    )
)
@pytest.mark.property_test
def test_validate_sqlite_path_rejects_nonexistent_files(path):
    """
    Feature: database-access, Property 25: SQLite file path validation

    **Validates: Requirements 6.5**

    For any file path that doesn't exist, the SQLite configuration validator
    should reject it by returning False.
    """
    # Ensure the path doesn't exist by using a very unlikely path
    nonexistent_path = f"/tmp/nonexistent_db_test_{path}_xyz123.db"

    # Make sure it really doesn't exist
    if os.path.exists(nonexistent_path):
        os.unlink(nonexistent_path)

    # Test validation
    result = validate_sqlite_path(nonexistent_path)

    # Should reject non-existent file
    assert result is False


@pytest.mark.property_test
def test_validate_sqlite_path_rejects_directories():
    """
    Feature: database-access, Property 25: SQLite file path validation

    **Validates: Requirements 6.5**

    The validator should reject directory paths, only accepting file paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with a directory path
        result = validate_sqlite_path(tmpdir)

        # Should reject directory
        assert result is False


@pytest.mark.property_test
def test_validate_sqlite_path_handles_relative_paths():
    """
    Feature: database-access, Property 25: SQLite file path validation

    **Validates: Requirements 6.5**

    The validator should correctly handle relative file paths.
    """
    # Create a temporary file in current directory
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False, dir=".") as f:
        temp_path = f.name
        relative_path = os.path.basename(temp_path)

    try:
        # Test with relative path
        result = validate_sqlite_path(relative_path)

        # Should accept existing file via relative path
        assert result is True
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# Unit tests for edge cases
def test_list_sqlcl_connections_handles_invalid_json():
    """Test that invalid JSON in connections.json is handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlcl_dir = Path(tmpdir) / ".sqlcl"
        sqlcl_dir.mkdir()
        connections_file = sqlcl_dir / "connections.json"

        # Write invalid JSON
        with open(connections_file, "w") as f:
            f.write("{ invalid json }")

        with patch("offline_chat.database_config_cli.Path.home", return_value=Path(tmpdir)):
            result = list_sqlcl_connections()

        # Should return empty list on error
        assert result == []


def test_validate_sqlite_path_with_empty_string():
    """Test that empty string path is rejected."""
    result = validate_sqlite_path("")
    assert result is False


def test_validate_sqlite_path_with_special_characters():
    """Test that paths with special characters are handled correctly."""
    # Create a file with special characters in name
    with tempfile.NamedTemporaryFile(mode="w", suffix=" test (1).db", delete=False) as f:
        temp_path = f.name

    try:
        result = validate_sqlite_path(temp_path)
        assert result is True
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
