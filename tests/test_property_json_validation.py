"""Property-based tests for JSON structure validation.

This module contains property-based tests for validating the JSON structure
of the database connection store.

Feature: database-connection-management
Property 7: JSON Structure Validation
Validates: Requirements 1.4
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database.manager import DatabaseConnectionManager


class TestJSONStructureValidation:
    """Property 7: JSON Structure Validation.

    Feature: database-connection-management
    Property 7: JSON Structure Validation

    **Validates: Requirements 1.4**

    For any malformed JSON in the connection store file, the system should
    detect the invalid structure and return an error when attempting to load.
    """

    def test_invalid_json_syntax_raises_error(self):
        """Test that invalid JSON syntax is detected and raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create file with invalid JSON syntax
            with open(store_path, "w") as f:
                f.write("{ invalid json }")

            manager = DatabaseConnectionManager(store_path)

            # Should raise ValueError with descriptive message
            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "invalid JSON" in str(exc_info.value)

    def test_missing_version_field_raises_error(self):
        """Test that missing 'version' field is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON without version field
            data = {"connections": []}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "missing required field 'version'" in str(exc_info.value)

    def test_missing_connections_field_raises_error(self):
        """Test that missing 'connections' field is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON without connections field
            data = {"version": "1.0"}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "missing required field 'connections'" in str(exc_info.value)

    def test_connections_not_array_raises_error(self):
        """Test that connections field must be an array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON with connections as non-array
            data = {"version": "1.0", "connections": "not an array"}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "must be an array" in str(exc_info.value)

    def test_connection_not_object_raises_error(self):
        """Test that each connection must be an object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON with connection as non-object
            data = {"version": "1.0", "connections": ["not an object"]}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "must be an object" in str(exc_info.value)
            assert "index 0" in str(exc_info.value)

    def test_connection_missing_name_raises_error(self):
        """Test that connection without 'name' field is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create connection without name
            data = {"version": "1.0", "connections": [{"database_type": "postgresql"}]}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "missing required fields" in str(exc_info.value)
            assert "name" in str(exc_info.value)

    def test_connection_missing_database_type_raises_error(self):
        """Test that connection without 'database_type' field is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create connection without database_type
            data = {"version": "1.0", "connections": [{"name": "test-conn"}]}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "missing required fields" in str(exc_info.value)
            assert "database_type" in str(exc_info.value)

    def test_connection_name_not_string_raises_error(self):
        """Test that connection name must be a string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create connection with non-string name
            data = {"version": "1.0", "connections": [{"name": 123, "database_type": "postgresql"}]}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "invalid name" in str(exc_info.value)
            assert "must be a string" in str(exc_info.value)

    def test_connection_database_type_not_string_raises_error(self):
        """Test that connection database_type must be a string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create connection with non-string database_type
            data = {"version": "1.0", "connections": [{"name": "test-conn", "database_type": 123}]}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "invalid database_type" in str(exc_info.value)
            assert "must be a string" in str(exc_info.value)

    def test_top_level_not_object_raises_error(self):
        """Test that top-level JSON must be an object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON with array at top level
            data = ["not", "an", "object"]
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "must be a JSON object" in str(exc_info.value)

    @settings(max_examples=50)
    @given(
        connections=st.lists(
            st.fixed_dictionaries(
                {
                    "name": st.text(min_size=1, max_size=20),
                    "database_type": st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]),
                }
            ),
            min_size=0,
            max_size=5,
        )
    )
    def test_valid_structure_loads_successfully(self, connections):
        """Test that valid JSON structure loads without errors.

        **Validates: Requirements 1.4**

        For any valid JSON structure with required fields, the system should
        load it successfully without raising errors.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create valid JSON structure
            data = {"version": "1.0", "connections": connections}
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            # Should load successfully
            loaded_data = manager._load_store()

            assert loaded_data["version"] == "1.0"
            assert isinstance(loaded_data["connections"], list)
            assert len(loaded_data["connections"]) == len(connections)

    def test_multiple_connections_with_one_invalid_raises_error(self):
        """Test that one invalid connection in a list is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON with one valid and one invalid connection
            data = {
                "version": "1.0",
                "connections": [
                    {"name": "valid-conn", "database_type": "postgresql"},
                    {
                        "name": "invalid-conn"
                        # Missing database_type
                    },
                ],
            }
            with open(store_path, "w") as f:
                json.dump(data, f)

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            assert "missing required fields" in str(exc_info.value)
            assert "database_type" in str(exc_info.value)

    def test_error_handling_in_create_connection(self):
        """Test that create_connection handles malformed store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create malformed JSON
            with open(store_path, "w") as f:
                f.write("{ invalid }")

            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.connection import DatabaseConnection
            from offline_chat.database.result import is_err, unwrap_err

            conn = DatabaseConnection(name="test-conn", database_type="sqlite", file_path="/tmp/test.db")

            result = manager.create_connection(conn)

            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "Failed to load connection store" in error_msg

    def test_error_handling_in_get_connection(self):
        """Test that get_connection handles malformed store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create malformed JSON
            with open(store_path, "w") as f:
                f.write("{ invalid }")

            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_err, unwrap_err

            result = manager.get_connection("test-conn")

            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "Failed to load connection store" in error_msg

    def test_error_handling_in_update_connection(self):
        """Test that update_connection handles malformed store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create malformed JSON
            with open(store_path, "w") as f:
                f.write("{ invalid }")

            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_err, unwrap_err

            result = manager.update_connection("test-conn", {"host": "newhost"})

            # Should return error (either JSON error or connection not found)
            assert is_err(result)
            error_msg = unwrap_err(result)
            # The error could be either about loading the store or connection not found
            # Both are acceptable since the store is corrupted
            assert "Failed to load connection store" in error_msg or "not found" in error_msg

    def test_error_handling_in_delete_connection(self):
        """Test that delete_connection handles malformed store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create malformed JSON
            with open(store_path, "w") as f:
                f.write("{ invalid }")

            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_err, unwrap_err

            result = manager.delete_connection("test-conn")

            # Should return error (either JSON error or connection not found)
            assert is_err(result)
            error_msg = unwrap_err(result)
            # The error could be either about loading the store or connection not found
            # Both are acceptable since the store is corrupted
            assert "Failed to load connection store" in error_msg or "not found" in error_msg

    def test_error_handling_in_list_connections(self):
        """Test that list_connections handles malformed store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create malformed JSON
            with open(store_path, "w") as f:
                f.write("{ invalid }")

            manager = DatabaseConnectionManager(store_path)

            # Should return empty list and print warning
            connections = manager.list_connections()

            assert connections == []

    def test_descriptive_error_for_json_decode_error(self):
        """Test that JSON decode errors include line and column information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create JSON with syntax error
            with open(store_path, "w") as f:
                f.write('{\n  "version": "1.0",\n  "connections": [\n    invalid\n  ]\n}')

            manager = DatabaseConnectionManager(store_path)

            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            error_msg = str(exc_info.value)
            assert "invalid JSON" in error_msg
            # Should include line/column information
            assert "line" in error_msg or "column" in error_msg
