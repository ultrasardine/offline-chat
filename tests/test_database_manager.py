"""Unit tests for DatabaseConnectionManager."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager


class TestDatabaseConnectionManagerInitialization:
    """Test DatabaseConnectionManager initialization and store setup."""

    def test_init_creates_store_if_missing(self):
        """Test that initialization creates store file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "test_connections.json"

            # Store should not exist yet
            assert not store_path.exists()

            # Initialize manager
            manager = DatabaseConnectionManager(store_path)

            # Store should now exist
            assert store_path.exists()
            assert manager.store_path == store_path

    def test_init_creates_parent_directory(self):
        """Test that initialization creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "subdir" / "nested" / "connections.json"

            # Parent directories should not exist
            assert not store_path.parent.exists()

            # Initialize manager
            DatabaseConnectionManager(store_path)

            # Parent directories and store should exist
            assert store_path.parent.exists()
            assert store_path.exists()

    def test_init_with_existing_store(self):
        """Test initialization with an existing store file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create existing store with data
            existing_data = {
                "version": "1.0",
                "connections": [
                    {
                        "name": "existing-conn",
                        "database_type": "sqlite",
                        "file_path": "/path/to/db.db",
                        "created_at": "2025-01-13T10:00:00",
                        "updated_at": "2025-01-13T10:00:00"
                    }
                ]
            }
            with open(store_path, 'w') as f:
                json.dump(existing_data, f)

            # Initialize manager
            DatabaseConnectionManager(store_path)

            # Store should still exist with original data
            assert store_path.exists()
            with open(store_path, 'r') as f:
                data = json.load(f)
            assert len(data["connections"]) == 1
            assert data["connections"][0]["name"] == "existing-conn"

    def test_init_default_path(self):
        """Test initialization with default path."""
        manager = DatabaseConnectionManager()

        expected_path = Path.home() / ".offline-chat" / "database_connections.json"
        assert manager.store_path == expected_path

    def test_store_has_correct_initial_structure(self):
        """Test that newly created store has correct JSON structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            DatabaseConnectionManager(store_path)

            # Load and verify structure
            with open(store_path, 'r') as f:
                data = json.load(f)

            assert "version" in data
            assert data["version"] == "1.0"
            assert "connections" in data
            assert isinstance(data["connections"], list)
            assert len(data["connections"]) == 0

    def test_secure_permissions_set(self):
        """Test that store file has secure permissions (600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            DatabaseConnectionManager(store_path)

            # Check file permissions (Unix-like systems only)
            if os.name != 'nt':  # Skip on Windows
                stat_info = os.stat(store_path)
                permissions = stat_info.st_mode & 0o777
                assert permissions == 0o600, f"Expected 0o600, got {oct(permissions)}"

    def test_verify_permissions_warns_on_permissive_permissions(self, capsys):
        """Test that _verify_permissions warns when permissions are too permissive."""
        if os.name == 'nt':  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create manager (this sets permissions to 600)
            manager = DatabaseConnectionManager(store_path)

            # Manually set permissive permissions (644 - group and others can read)
            os.chmod(store_path, 0o644)

            # Verify permissions should warn
            manager._verify_permissions()

            # Check that warning was printed
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "insecure permissions" in captured.out
            assert "0o644" in captured.out

    def test_verify_permissions_no_warning_on_secure_permissions(self, capsys):
        """Test that _verify_permissions doesn't warn when permissions are secure."""
        if os.name == 'nt':  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create manager (this sets permissions to 600)
            manager = DatabaseConnectionManager(store_path)

            # Verify permissions should not warn
            manager._verify_permissions()

            # Check that no warning was printed
            captured = capsys.readouterr()
            assert "WARNING" not in captured.out

    def test_verify_permissions_on_load(self, capsys):
        """Test that permissions are verified when loading the store."""
        if os.name == 'nt':  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create manager
            manager = DatabaseConnectionManager(store_path)

            # Set permissive permissions
            os.chmod(store_path, 0o666)

            # Load store should trigger permission verification
            manager._load_store()

            # Check that warning was printed
            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "insecure permissions" in captured.out

    def test_verify_permissions_handles_missing_file(self):
        """Test that _verify_permissions handles missing file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "nonexistent.json"

            # Create manager instance without initializing store
            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Should not raise an error
            manager._verify_permissions()  # Should silently return


class TestDatabaseConnectionManagerLoadSave:
    """Test loading and saving store data."""

    def test_load_store(self):
        """Test loading data from store file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create store with test data
            test_data = {
                "version": "1.0",
                "connections": [
                    {
                        "name": "test-conn",
                        "database_type": "sqlite",
                        "file_path": "/path/to/db.db",
                        "created_at": "2025-01-13T10:00:00",
                        "updated_at": "2025-01-13T10:00:00"
                    }
                ]
            }
            with open(store_path, 'w') as f:
                json.dump(test_data, f)

            manager = DatabaseConnectionManager(store_path)
            loaded_data = manager._load_store()

            assert loaded_data["version"] == "1.0"
            assert len(loaded_data["connections"]) == 1
            assert loaded_data["connections"][0]["name"] == "test-conn"

    def test_save_store(self):
        """Test saving data to store file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)

            # Save new data
            new_data = {
                "version": "1.0",
                "connections": [
                    {
                        "name": "new-conn",
                        "database_type": "postgresql",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "user",
                        "password": "pass",
                        "created_at": "2025-01-13T10:00:00",
                        "updated_at": "2025-01-13T10:00:00"
                    }
                ]
            }
            manager._save_store(new_data)

            # Verify data was saved
            with open(store_path, 'r') as f:
                saved_data = json.load(f)

            assert saved_data["version"] == "1.0"
            assert len(saved_data["connections"]) == 1
            assert saved_data["connections"][0]["name"] == "new-conn"

    def test_save_store_preserves_permissions(self):
        """Test that saving store preserves secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)

            # Save data
            data = {"version": "1.0", "connections": []}
            manager._save_store(data)

            # Check permissions (Unix-like systems only)
            if os.name != 'nt':
                stat_info = os.stat(store_path)
                permissions = stat_info.st_mode & 0o777
                assert permissions == 0o600

    def test_load_store_invalid_json(self):
        """Test loading store with invalid JSON raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create invalid JSON file
            with open(store_path, 'w') as f:
                f.write("{ invalid json }")

            manager = DatabaseConnectionManager(store_path)

            # Should raise ValueError (wrapping JSONDecodeError) with descriptive message
            with pytest.raises(ValueError) as exc_info:
                manager._load_store()

            # Verify error message contains useful information
            assert "invalid JSON" in str(exc_info.value)

    def test_load_store_missing_file(self):
        """Test loading non-existent store raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Don't create the file, just initialize path
            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Delete the file if it exists
            if store_path.exists():
                store_path.unlink()

            with pytest.raises(FileNotFoundError):
                manager._load_store()


class TestDatabaseConnectionManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_multiple_managers_same_store(self):
        """Test that multiple managers can access the same store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create first manager and add data
            manager1 = DatabaseConnectionManager(store_path)
            data = {
                "version": "1.0",
                "connections": [
                    {
                        "name": "shared-conn",
                        "database_type": "sqlite",
                        "file_path": "/path/to/db.db",
                        "created_at": "2025-01-13T10:00:00",
                        "updated_at": "2025-01-13T10:00:00"
                    }
                ]
            }
            manager1._save_store(data)

            # Create second manager and verify it can read the data
            manager2 = DatabaseConnectionManager(store_path)
            loaded_data = manager2._load_store()

            assert len(loaded_data["connections"]) == 1
            assert loaded_data["connections"][0]["name"] == "shared-conn"

    def test_empty_store_is_valid(self):
        """Test that an empty connection list is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)
            data = manager._load_store()

            assert data["version"] == "1.0"
            assert data["connections"] == []

    def test_store_with_unicode_characters(self):
        """Test that store handles Unicode characters correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)

            # Save data with Unicode characters
            data = {
                "version": "1.0",
                "connections": [
                    {
                        "name": "unicode-conn",
                        "database_type": "postgresql",
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "用户",  # Chinese characters
                        "password": "пароль",  # Cyrillic characters
                        "created_at": "2025-01-13T10:00:00",
                        "updated_at": "2025-01-13T10:00:00"
                    }
                ]
            }
            manager._save_store(data)

            # Load and verify
            loaded_data = manager._load_store()
            assert loaded_data["connections"][0]["username"] == "用户"
            assert loaded_data["connections"][0]["password"] == "пароль"



class TestStoreInitializationProperty:
    """Property-based tests for store initialization.

    Feature: database-connection-management
    Property 6: Connection Store Structure

    **Validates: Requirements 1.2, 1.3**
    """

    @given(
        store_dir=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'),
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] not in '-_' and s[-1] not in '-_')
    )
    @settings(max_examples=100)
    def test_store_initialization_creates_valid_structure(self, store_dir):
        """
        Property 6: Connection Store Structure

        For any newly created store, it should be properly initialized with
        correct JSON structure containing version and empty connections array.

        **Validates: Requirements 1.2, 1.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / store_dir / "connections.json"

            # Initialize manager - this should create the store
            DatabaseConnectionManager(store_path)

            # Verify store file was created
            assert store_path.exists(), "Store file should be created"

            # Load and verify structure
            with open(store_path, 'r') as f:
                data = json.load(f)

            # Verify required top-level fields
            assert "version" in data, "Store must have 'version' field"
            assert "connections" in data, "Store must have 'connections' field"

            # Verify field types and values
            assert isinstance(data["version"], str), "Version must be a string"
            assert data["version"] == "1.0", "Version should be '1.0'"
            assert isinstance(data["connections"], list), "Connections must be a list"
            assert len(data["connections"]) == 0, "New store should have empty connections list"

    @given(
        nested_depth=st.integers(min_value=1, max_value=5),
        dir_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='_-'),
                min_size=1,
                max_size=20
            ).filter(lambda s: s[0] not in '-_' and s[-1] not in '-_'),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_store_initialization_creates_nested_directories(self, nested_depth, dir_names):
        """
        Property 6: Connection Store Structure

        For any store path with nested directories, initialization should
        create all parent directories and the store with correct structure.

        **Validates: Requirements 1.2, 1.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested path
            nested_path = Path(tmpdir)
            for i in range(min(nested_depth, len(dir_names))):
                nested_path = nested_path / dir_names[i]
            store_path = nested_path / "connections.json"

            # Parent directories should not exist yet
            assert not store_path.parent.exists(), "Parent directories should not exist initially"

            # Initialize manager
            DatabaseConnectionManager(store_path)

            # Verify all parent directories were created
            assert store_path.parent.exists(), "Parent directories should be created"
            assert store_path.exists(), "Store file should be created"

            # Verify store structure
            with open(store_path, 'r') as f:
                data = json.load(f)

            assert "version" in data
            assert "connections" in data
            assert isinstance(data["connections"], list)
            assert len(data["connections"]) == 0

    @given(
        store_filename=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='_-.'),
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] not in '-_.' and s[-1] not in '-_.' and '..' not in s)
    )
    @settings(max_examples=100)
    def test_store_initialization_with_various_filenames(self, store_filename):
        """
        Property 6: Connection Store Structure

        For any valid filename, store initialization should create a properly
        structured JSON file.

        **Validates: Requirements 1.2, 1.3**
        """
        # Ensure filename has .json extension
        if not store_filename.endswith('.json'):
            store_filename += '.json'

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / store_filename

            # Initialize manager
            DatabaseConnectionManager(store_path)

            # Verify store exists and has correct structure
            assert store_path.exists()

            with open(store_path, 'r') as f:
                data = json.load(f)

            assert data["version"] == "1.0"
            assert data["connections"] == []

    @given(
        num_initializations=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_store_initialization_is_idempotent(self, num_initializations):
        """
        Property 6: Connection Store Structure

        For any number of repeated initializations on the same path,
        the store should remain valid and unchanged after the first creation.

        **Validates: Requirements 1.2, 1.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Initialize multiple times
            for i in range(num_initializations):
                DatabaseConnectionManager(store_path)

                # Verify store structure after each initialization
                with open(store_path, 'r') as f:
                    data = json.load(f)

                assert "version" in data
                assert "connections" in data
                assert isinstance(data["connections"], list)

                # If this is not the first initialization, verify the store wasn't reset
                if i > 0:
                    # Store should still be valid (we're not testing that it preserves
                    # data here, just that re-initialization doesn't corrupt it)
                    assert data["version"] == "1.0"

    @given(
        store_path_components=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='_-'),
                min_size=1,
                max_size=30
            ).filter(lambda s: s[0] not in '-_' and s[-1] not in '-_'),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=100, deadline=500)
    def test_store_initialization_json_is_valid(self, store_path_components):
        """
        Property 6: Connection Store Structure

        For any store path, the initialized store should contain valid JSON
        that can be parsed without errors.

        **Validates: Requirements 1.2, 1.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Build path from components
            store_path = Path(tmpdir)
            for component in store_path_components:
                store_path = store_path / component
            store_path = store_path / "connections.json"

            # Initialize manager
            DatabaseConnectionManager(store_path)

            # Verify JSON is valid by parsing it
            with open(store_path, 'r') as f:
                data = json.load(f)  # Should not raise JSONDecodeError

            # Verify it's a dictionary (not array or primitive)
            assert isinstance(data, dict), "Store root should be a dictionary"

            # Verify required structure
            assert "version" in data
            assert "connections" in data
            assert isinstance(data["connections"], list)




class TestCreateConnection:
    """Test create_connection() method."""

    def test_create_connection_success(self):
        """Test creating a valid connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a valid connection
            conn = DatabaseConnection(
                name="test-oracle",
                database_type="oracle",
                host="localhost",
                port=1521,
                service_name="TESTDB",
                username="testuser",
                password="testpass"
            )

            result = manager.create_connection(conn)

            # Verify success
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result), f"Expected Ok, got Err: {result}"
            created_conn = unwrap(result)
            assert created_conn.name == "test-oracle"
            assert created_conn.database_type == "oracle"

            # Verify connection was saved to store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            assert store_data["connections"][0]["name"] == "test-oracle"

    def test_create_connection_duplicate_name(self):
        """Test that creating a connection with duplicate name fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create first connection
            conn1 = DatabaseConnection(
                name="duplicate-name",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            result1 = manager.create_connection(conn1)

            from offline_chat.database.result import is_ok
            assert is_ok(result1)

            # Try to create second connection with same name
            conn2 = DatabaseConnection(
                name="duplicate-name",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass"
            )
            result2 = manager.create_connection(conn2)

            # Verify failure
            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result2)
            error_msg = unwrap_err(result2)
            assert "already exists" in error_msg
            assert "duplicate-name" in error_msg

            # Verify only one connection in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1

    def test_create_connection_invalid_name_uppercase(self):
        """Test that connection names with uppercase letters are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="InvalidName",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg

    def test_create_connection_invalid_name_spaces(self):
        """Test that connection names with spaces are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="invalid name",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg

    def test_create_connection_invalid_name_starts_with_hyphen(self):
        """Test that connection names starting with hyphen are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="-invalid",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg

    def test_create_connection_invalid_name_ends_with_hyphen(self):
        """Test that connection names ending with hyphen are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="invalid-",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg

    def test_create_connection_invalid_name_empty(self):
        """Test that empty connection names are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg

    def test_create_connection_invalid_database_type(self):
        """Test that invalid database types are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="test-conn",
                database_type="mongodb",  # Not supported
                host="localhost",
                port=27017
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "Invalid database type" in error_msg
            assert "mongodb" in error_msg
            assert "oracle" in error_msg
            assert "postgresql" in error_msg
            assert "mysql" in error_msg
            assert "sqlite" in error_msg

    def test_create_connection_all_supported_types(self):
        """Test creating connections for all supported database types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_ok

            # Oracle
            oracle_conn = DatabaseConnection(
                name="test-oracle",
                database_type="oracle",
                host="localhost",
                port=1521,
                service_name="TESTDB",
                username="user",
                password="pass"
            )
            assert is_ok(manager.create_connection(oracle_conn))

            # PostgreSQL
            postgres_conn = DatabaseConnection(
                name="test-postgres",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass"
            )
            assert is_ok(manager.create_connection(postgres_conn))

            # MySQL
            mysql_conn = DatabaseConnection(
                name="test-mysql",
                database_type="mysql",
                host="localhost",
                port=3306,
                database="testdb",
                username="user",
                password="pass"
            )
            assert is_ok(manager.create_connection(mysql_conn))

            # SQLite
            sqlite_conn = DatabaseConnection(
                name="test-sqlite",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            assert is_ok(manager.create_connection(sqlite_conn))

            # Verify all connections were saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 4

    def test_create_connection_valid_kebab_case_names(self):
        """Test that various valid kebab-case names are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_ok

            valid_names = [
                "simple",
                "with-hyphen",
                "multiple-hyphens-here",
                "with123numbers",
                "numbers-123-mixed",
                "a",
                "a1",
                "1a",
                "123"
            ]

            for name in valid_names:
                conn = DatabaseConnection(
                    name=name,
                    database_type="sqlite",
                    file_path=f"/path/to/{name}.db"
                )
                result = manager.create_connection(conn)
                assert is_ok(result), f"Expected '{name}' to be valid, but got error: {result}"

            # Verify all connections were saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == len(valid_names)

    def test_create_connection_preserves_all_fields(self):
        """Test that all connection fields are preserved when saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="full-conn",
                database_type="postgresql",
                host="db.example.com",
                port=5432,
                database="proddb",
                username="admin",
                password="secret123",
                additional_params={"ssl": True, "timeout": 30}
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok
            assert is_ok(result)

            # Load and verify all fields
            store_data = manager._load_store()
            saved_conn = store_data["connections"][0]

            assert saved_conn["name"] == "full-conn"
            assert saved_conn["database_type"] == "postgresql"
            assert saved_conn["host"] == "db.example.com"
            assert saved_conn["port"] == 5432
            assert saved_conn["database"] == "proddb"
            assert saved_conn["username"] == "admin"
            assert saved_conn["password"] == "secret123"
            assert saved_conn["additional_params"]["ssl"] is True
            assert saved_conn["additional_params"]["timeout"] == 30
            assert "created_at" in saved_conn
            assert "updated_at" in saved_conn


class TestKebabCaseValidation:
    """Test _is_valid_kebab_case() helper method."""

    def test_valid_kebab_case_names(self):
        """Test that valid kebab-case names are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            valid_names = [
                "simple",
                "with-hyphen",
                "multiple-hyphens-here",
                "with123numbers",
                "numbers-123-mixed",
                "a",
                "a1",
                "1a",
                "123",
                "kebab-case-name",
                "my-connection-1"
            ]

            for name in valid_names:
                assert manager._is_valid_kebab_case(name), f"'{name}' should be valid"

    def test_invalid_kebab_case_names(self):
        """Test that invalid names are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            invalid_names = [
                "",  # Empty
                "-starts-with-hyphen",
                "ends-with-hyphen-",
                "Has-Uppercase",
                "has spaces",
                "has_underscore",
                "has.dot",
                "has@special",
                "has!exclamation",
                "ALLCAPS",
                "camelCase",
                "PascalCase",
                "snake_case"
            ]

            for name in invalid_names:
                assert not manager._is_valid_kebab_case(name), f"'{name}' should be invalid"



# ============================================================================
# Property-Based Tests for Connection Creation
# ============================================================================

class TestConnectionCreationProperties:
    """Property-based tests for connection creation.

    Feature: database-connection-management
    Properties: 1, 2, 3, 5

    **Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.6, 2.7**
    """

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_connection_name_uniqueness(self, name, db_type):
        """
        Property 1: Connection Name Uniqueness

        For any connection store and any connection name, attempting to create
        a second connection with the same name should fail with an error
        indicating the name already exists.

        **Validates: Requirements 2.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create first connection
            if db_type == 'sqlite':
                conn1 = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/path/to/db.db"
                )
            elif db_type == 'oracle':
                conn1 = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
            else:  # postgresql or mysql
                conn1 = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )

            result1 = manager.create_connection(conn1)

            from offline_chat.database.result import is_err, is_ok, unwrap_err

            # First creation should succeed
            assert is_ok(result1), f"First connection creation should succeed: {result1}"

            # Try to create second connection with same name but different type
            different_db_type = 'sqlite' if db_type != 'sqlite' else 'postgresql'
            if different_db_type == 'sqlite':
                conn2 = DatabaseConnection(
                    name=name,
                    database_type=different_db_type,
                    file_path="/different/path.db"
                )
            else:
                conn2 = DatabaseConnection(
                    name=name,
                    database_type=different_db_type,
                    host="different-host",
                    port=5432,
                    database="differentdb",
                    username="different_user",
                    password="different_pass"
                )

            result2 = manager.create_connection(conn2)

            # Second creation should fail
            assert is_err(result2), "Second connection with same name should fail"
            error_msg = unwrap_err(result2)
            assert "already exists" in error_msg.lower(), f"Error should mention 'already exists': {error_msg}"
            assert name in error_msg, f"Error should mention connection name '{name}': {error_msg}"

            # Verify only one connection in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Store should contain only one connection"
            assert store_data["connections"][0]["name"] == name

    @given(
        name=st.one_of(
            # Names with uppercase letters
            st.text(min_size=1, max_size=50).filter(lambda s: any(c.isupper() for c in s)),
            # Names with spaces
            st.text(min_size=1, max_size=50).filter(lambda s: ' ' in s),
            # Names with underscores
            st.text(min_size=1, max_size=50).filter(lambda s: '_' in s),
            # Names with special characters
            st.text(
                alphabet=st.characters(blacklist_categories=('Ll', 'Nd'), blacklist_characters='-'),
                min_size=1,
                max_size=50
            ),
            # Names starting with hyphen
            st.text(
                alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
                min_size=2,
                max_size=50
            ).map(lambda s: '-' + s),
            # Names ending with hyphen
            st.text(
                alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
                min_size=2,
                max_size=50
            ).map(lambda s: s + '-'),
            # Empty names
            st.just('')
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_connection_name_format_validation_invalid(self, name):
        """
        Property 2: Connection Name Format Validation (Invalid Names)

        For any connection name that is not in kebab-case format, the system
        should reject it with an error indicating invalid format.

        **Validates: Requirements 2.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name=name,
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err

            # Should fail with kebab-case error
            assert is_err(result), f"Invalid name '{name}' should be rejected"
            error_msg = unwrap_err(result)
            assert "kebab-case" in error_msg.lower(), f"Error should mention 'kebab-case': {error_msg}"

            # Verify connection was not saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 0, "Invalid connection should not be saved"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_connection_name_format_validation_valid(self, name):
        """
        Property 2: Connection Name Format Validation (Valid Names)

        For any connection name in valid kebab-case format, the system should
        accept it (assuming other validations pass).

        **Validates: Requirements 2.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name=name,
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok

            # Should succeed (name format is valid)
            assert is_ok(result), f"Valid kebab-case name '{name}' should be accepted: {result}"

            # Verify connection was saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            assert store_data["connections"][0]["name"] == name

    @given(
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_database_type_validation_valid(self, db_type):
        """
        Property 3: Database Type Validation (Valid Types)

        For any connection with a supported database_type, the system should
        accept it (assuming other validations pass).

        **Validates: Requirements 2.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection with valid database type
            if db_type == 'sqlite':
                conn = DatabaseConnection(
                    name="test-conn",
                    database_type=db_type,
                    file_path="/path/to/db.db"
                )
            elif db_type == 'oracle':
                conn = DatabaseConnection(
                    name="test-conn",
                    database_type=db_type,
                    host="localhost",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name="test-conn",
                    database_type=db_type,
                    host="localhost",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok

            # Should succeed (database type is valid)
            assert is_ok(result), f"Valid database type '{db_type}' should be accepted: {result}"

            # Verify connection was saved with correct type
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            assert store_data["connections"][0]["database_type"] == db_type

    @given(
        db_type=st.text(min_size=1, max_size=50).filter(
            lambda s: s not in ['oracle', 'postgresql', 'mysql', 'sqlite']
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_database_type_validation_invalid(self, db_type):
        """
        Property 3: Database Type Validation (Invalid Types)

        For any connection with an unsupported database_type, the system should
        reject it with an error listing supported types.

        **Validates: Requirements 2.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name="test-conn",
                database_type=db_type,
                host="localhost",
                port=5432
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, unwrap_err

            # Should fail with invalid database type error
            assert is_err(result), f"Invalid database type '{db_type}' should be rejected"
            error_msg = unwrap_err(result)
            assert "invalid database type" in error_msg.lower(), f"Error should mention 'invalid database type': {error_msg}"
            assert db_type in error_msg, f"Error should mention the invalid type '{db_type}': {error_msg}"

            # Error should list supported types
            assert "oracle" in error_msg.lower()
            assert "postgresql" in error_msg.lower()
            assert "mysql" in error_msg.lower()
            assert "sqlite" in error_msg.lower()

            # Verify connection was not saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 0, "Invalid connection should not be saved"

    @given(
        connection=st.one_of(
            # Valid Oracle connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('oracle'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                service_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                database=st.none(),
                file_path=st.none()
            ),
            # Valid PostgreSQL connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('postgresql'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                service_name=st.none(),
                file_path=st.none()
            ),
            # Valid MySQL connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('mysql'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                service_name=st.none(),
                file_path=st.none()
            ),
            # Valid SQLite connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('sqlite'),
                file_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
                host=st.none(),
                port=st.none(),
                database=st.none(),
                service_name=st.none(),
                username=st.none(),
                password=st.none()
            )
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_connection_persistence_on_success(self, connection):
        """
        Property 5: Connection Persistence Based on Validation (Success Case)

        For any valid connection, if validation succeeds, the connection should
        be saved to the store and retrievable.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            result = manager.create_connection(connection)

            from offline_chat.database.result import is_ok

            # Should succeed (all validations pass)
            assert is_ok(result), f"Valid connection should be created successfully: {result}"

            # Verify connection was saved to store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Connection should be saved to store"

            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == connection.name
            assert saved_conn["database_type"] == connection.database_type

            # Verify type-specific fields were saved
            if connection.database_type == 'oracle':
                assert saved_conn["host"] == connection.host
                assert saved_conn["port"] == connection.port
                assert saved_conn["service_name"] == connection.service_name
                assert saved_conn["username"] == connection.username
                assert saved_conn["password"] == connection.password
            elif connection.database_type in ['postgresql', 'mysql']:
                assert saved_conn["host"] == connection.host
                assert saved_conn["port"] == connection.port
                assert saved_conn["database"] == connection.database
                assert saved_conn["username"] == connection.username
                assert saved_conn["password"] == connection.password
            elif connection.database_type == 'sqlite':
                assert saved_conn["file_path"] == connection.file_path

            # Verify connection is retrievable by deserializing
            restored_conn = DatabaseConnection.from_dict(saved_conn)
            assert restored_conn.name == connection.name
            assert restored_conn.database_type == connection.database_type

    @given(
        name=st.one_of(
            # Invalid format names
            st.text(min_size=1, max_size=50).filter(lambda s: any(c.isupper() for c in s)),
            st.text(min_size=1, max_size=50).filter(lambda s: ' ' in s),
            st.just(''),
            st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=2,
                max_size=50
            ).map(lambda s: '-' + s),
            st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=2,
                max_size=50
            ).map(lambda s: s + '-')
        ),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_connection_persistence_on_failure_invalid_name(self, name, db_type):
        """
        Property 5: Connection Persistence Based on Validation (Failure Case - Invalid Name)

        For any connection with invalid name format, if validation fails, the
        connection should not appear in the store.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection with invalid name
            if db_type == 'sqlite':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/path/to/db.db"
                )
            elif db_type == 'oracle':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err

            # Should fail (invalid name format)
            assert is_err(result), f"Connection with invalid name '{name}' should fail"

            # Verify connection was NOT saved to store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 0, "Failed connection should not be saved to store"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.text(min_size=1, max_size=50).filter(
            lambda s: s not in ['oracle', 'postgresql', 'mysql', 'sqlite']
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_connection_persistence_on_failure_invalid_type(self, name, db_type):
        """
        Property 5: Connection Persistence Based on Validation (Failure Case - Invalid Type)

        For any connection with invalid database type, if validation fails, the
        connection should not appear in the store.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            conn = DatabaseConnection(
                name=name,
                database_type=db_type,
                host="localhost",
                port=5432
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err

            # Should fail (invalid database type)
            assert is_err(result), f"Connection with invalid type '{db_type}' should fail"

            # Verify connection was NOT saved to store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 0, "Failed connection should not be saved to store"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_update_persistence_on_success(self, name, db_type):
        """
        Property 5: Connection Persistence Based on Validation (Update Success Case)

        For any connection update, if validation succeeds, the updated connection
        should be persisted to the store and retrievable with the new values.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if db_type == 'sqlite':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/original/path.db"
                )
                updates = {"file_path": "/updated/path.db"}
                expected_field = "file_path"
                expected_value = "/updated/path.db"
            elif db_type == 'oracle':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=1521,
                    service_name="ORIGDB",
                    username="origuser",
                    password="origpass"
                )
                updates = {
                    "host": "updated-host",
                    "port": 1522,
                    "service_name": "UPDATEDDB"
                }
                expected_field = "host"
                expected_value = "updated-host"
            elif db_type == 'postgresql':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=5432,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                updates = {
                    "host": "updated-host",
                    "port": 5433,
                    "database": "updateddb"
                }
                expected_field = "host"
                expected_value = "updated-host"
            else:  # mysql
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=3306,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                updates = {
                    "host": "updated-host",
                    "port": 3307,
                    "database": "updateddb"
                }
                expected_field = "host"
                expected_value = "updated-host"

            # Create the original connection
            create_result = manager.create_connection(original_conn)

            from offline_chat.database.result import is_ok, unwrap

            assert is_ok(create_result), f"Original connection creation should succeed: {create_result}"

            # Update the connection with valid parameters
            update_result = manager.update_connection(name, updates)

            # Update should succeed (all validations pass)
            assert is_ok(update_result), f"Valid update should succeed: {update_result}"

            # Verify updated connection was persisted to store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Should still have exactly one connection"

            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name, "Connection name should be unchanged"
            assert saved_conn["database_type"] == db_type, "Database type should be unchanged"

            # Verify the updated field was persisted
            assert saved_conn[expected_field] == expected_value, \
                f"Updated field '{expected_field}' should be persisted with value '{expected_value}'"

            # Verify connection is retrievable with updated values
            get_result = manager.get_connection(name)
            assert is_ok(get_result), "Updated connection should be retrievable"

            retrieved_conn = unwrap(get_result)
            assert getattr(retrieved_conn, expected_field) == expected_value, \
                f"Retrieved connection should have updated {expected_field}"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_update_persistence_on_failure(self, name, db_type):
        """
        Property 5: Connection Persistence Based on Validation (Update Failure Case)

        For any connection update, if validation fails, the original connection
        should be preserved unchanged in the store.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection with valid parameters
            if db_type == 'oracle':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=1521,
                    service_name="ORIGDB",
                    username="origuser",
                    password="origpass"
                )
                # Update with invalid port (out of range)
                invalid_updates = {"port": 99999}
                original_value = 1521
                check_field = "port"
            elif db_type == 'postgresql':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=5432,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                # Update with invalid port (out of range)
                invalid_updates = {"port": -1}
                original_value = 5432
                check_field = "port"
            else:  # mysql
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=3306,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                # Update with invalid port (out of range)
                invalid_updates = {"port": 0}
                original_value = 3306
                check_field = "port"

            # Create the original connection
            create_result = manager.create_connection(original_conn)

            from offline_chat.database.result import is_err, is_ok, unwrap

            assert is_ok(create_result), f"Original connection creation should succeed: {create_result}"

            # Attempt to update with invalid parameters
            update_result = manager.update_connection(name, invalid_updates)

            # Update should fail (validation fails)
            assert is_err(update_result), f"Invalid update should fail: {update_result}"

            # Verify original connection is preserved in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Should still have exactly one connection"

            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name, "Connection name should be unchanged"
            assert saved_conn[check_field] == original_value, \
                f"Original field '{check_field}' should be preserved with value '{original_value}'"

            # Verify connection is retrievable with original values
            get_result = manager.get_connection(name)
            assert is_ok(get_result), "Original connection should still be retrievable"

            retrieved_conn = unwrap(get_result)
            assert getattr(retrieved_conn, check_field) == original_value, \
                f"Retrieved connection should have original {check_field} value"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_update_persistence_missing_required_field(self, name, db_type):
        """
        Property 5: Connection Persistence Based on Validation (Update Missing Field)

        For any connection update that removes a required field, validation should
        fail and the original connection should be preserved.

        **Validates: Requirements 2.5, 2.6, 2.7, 8.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection with all required fields
            if db_type == 'sqlite':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/original/path.db"
                )
                # Try to update with empty file_path (required field)
                invalid_updates = {"file_path": ""}
                original_value = "/original/path.db"
                check_field = "file_path"
            elif db_type == 'oracle':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=1521,
                    service_name="ORIGDB",
                    username="origuser",
                    password="origpass"
                )
                # Try to update with empty service_name (required field)
                invalid_updates = {"service_name": ""}
                original_value = "ORIGDB"
                check_field = "service_name"
            elif db_type == 'postgresql':
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=5432,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                # Try to update with empty database (required field)
                invalid_updates = {"database": ""}
                original_value = "origdb"
                check_field = "database"
            else:  # mysql
                original_conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="original-host",
                    port=3306,
                    database="origdb",
                    username="origuser",
                    password="origpass"
                )
                # Try to update with empty username (required field)
                invalid_updates = {"username": ""}
                original_value = "origuser"
                check_field = "username"

            # Create the original connection
            create_result = manager.create_connection(original_conn)

            from offline_chat.database.result import is_err, is_ok, unwrap

            assert is_ok(create_result), f"Original connection creation should succeed: {create_result}"

            # Attempt to update with missing required field
            update_result = manager.update_connection(name, invalid_updates)

            # Update should fail (validation fails due to missing required field)
            assert is_err(update_result), f"Update with missing required field should fail: {update_result}"

            # Verify original connection is preserved in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Should still have exactly one connection"

            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name, "Connection name should be unchanged"
            assert saved_conn[check_field] == original_value, \
                f"Original field '{check_field}' should be preserved with value '{original_value}'"

            # Verify connection is retrievable with original values
            get_result = manager.get_connection(name)
            assert is_ok(get_result), "Original connection should still be retrievable"

            retrieved_conn = unwrap(get_result)
            assert getattr(retrieved_conn, check_field) == original_value, \
                f"Retrieved connection should have original {check_field} value"



class TestListConnections:
    """Test list_connections() method."""

    def test_list_connections_empty_store(self):
        """Test listing connections from an empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            connections = manager.list_connections()

            assert isinstance(connections, list)
            assert len(connections) == 0

    def test_list_connections_single_connection(self):
        """Test listing connections with one connection in store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-sqlite",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            manager.create_connection(conn)

            # List connections
            connections = manager.list_connections()

            assert len(connections) == 1
            assert connections[0].name == "test-sqlite"
            assert connections[0].database_type == "sqlite"
            assert connections[0].file_path == "/path/to/db.db"

    def test_list_connections_multiple_connections(self):
        """Test listing connections with multiple connections in store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create multiple connections
            conn1 = DatabaseConnection(
                name="oracle-prod",
                database_type="oracle",
                host="db.example.com",
                port=1521,
                service_name="PRODDB",
                username="user1",
                password="pass1"
            )
            conn2 = DatabaseConnection(
                name="postgres-dev",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="devdb",
                username="user2",
                password="pass2"
            )
            conn3 = DatabaseConnection(
                name="mysql-test",
                database_type="mysql",
                host="localhost",
                port=3306,
                database="testdb",
                username="user3",
                password="pass3"
            )

            manager.create_connection(conn1)
            manager.create_connection(conn2)
            manager.create_connection(conn3)

            # List connections
            connections = manager.list_connections()

            assert len(connections) == 3

            # Verify all connections are present
            names = {conn.name for conn in connections}
            assert names == {"oracle-prod", "postgres-dev", "mysql-test"}

            # Verify connection details
            oracle_conn = next(c for c in connections if c.name == "oracle-prod")
            assert oracle_conn.database_type == "oracle"
            assert oracle_conn.host == "db.example.com"
            assert oracle_conn.port == 1521

            postgres_conn = next(c for c in connections if c.name == "postgres-dev")
            assert postgres_conn.database_type == "postgresql"
            assert postgres_conn.database == "devdb"

            mysql_conn = next(c for c in connections if c.name == "mysql-test")
            assert mysql_conn.database_type == "mysql"
            assert mysql_conn.port == 3306

    def test_list_connections_returns_database_connection_objects(self):
        """Test that list_connections returns DatabaseConnection objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            manager.create_connection(conn)

            # List connections
            connections = manager.list_connections()

            assert len(connections) == 1
            assert isinstance(connections[0], DatabaseConnection)

    def test_list_connections_with_corrupted_store(self):
        """Test that list_connections handles corrupted store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create corrupted JSON file
            with open(store_path, 'w') as f:
                f.write("{ invalid json }")

            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Should return empty list instead of raising exception
            connections = manager.list_connections()

            assert isinstance(connections, list)
            assert len(connections) == 0

    def test_list_connections_with_missing_store(self):
        """Test that list_connections handles missing store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "nonexistent" / "connections.json"

            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Should return empty list instead of raising exception
            connections = manager.list_connections()

            assert isinstance(connections, list)
            assert len(connections) == 0

    def test_list_connections_skips_invalid_entries(self):
        """Test that list_connections skips invalid connection entries.

        This test creates a connection with invalid field types that will
        cause from_dict() to fail during iteration.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a valid connection
            conn = DatabaseConnection(
                name="valid-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            manager.create_connection(conn)

            # Manually add a connection with invalid field types
            # This will pass JSON validation but fail during from_dict()
            store_data = manager._load_store()
            store_data["connections"].append({
                "name": "invalid-conn",
                "database_type": "sqlite",
                "created_at": "not-a-valid-datetime",  # Invalid datetime format
            })
            manager._save_store(store_data)

            # List connections - should skip invalid entry during iteration
            connections = manager.list_connections()

            assert len(connections) == 1
            assert connections[0].name == "valid-conn"


class TestGetConnection:
    """Test get_connection() method."""

    def test_get_connection_success(self):
        """Test getting an existing connection by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-oracle",
                database_type="oracle",
                host="localhost",
                port=1521,
                service_name="TESTDB",
                username="testuser",
                password="testpass"
            )
            manager.create_connection(conn)

            # Get the connection
            result = manager.get_connection("test-oracle")

            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            retrieved_conn = unwrap(result)
            assert retrieved_conn.name == "test-oracle"
            assert retrieved_conn.database_type == "oracle"
            assert retrieved_conn.host == "localhost"
            assert retrieved_conn.port == 1521
            assert retrieved_conn.service_name == "TESTDB"
            assert retrieved_conn.username == "testuser"
            assert retrieved_conn.password == "testpass"

    def test_get_connection_not_found(self):
        """Test getting a non-existent connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Try to get a connection that doesn't exist
            result = manager.get_connection("nonexistent-conn")

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)

            error_msg = unwrap_err(result)
            assert "not found" in error_msg
            assert "nonexistent-conn" in error_msg

    def test_get_connection_from_multiple(self):
        """Test getting a specific connection when multiple exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create multiple connections
            conn1 = DatabaseConnection(
                name="conn-1",
                database_type="sqlite",
                file_path="/path/to/db1.db"
            )
            conn2 = DatabaseConnection(
                name="conn-2",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="db2",
                username="user2",
                password="pass2"
            )
            conn3 = DatabaseConnection(
                name="conn-3",
                database_type="mysql",
                host="localhost",
                port=3306,
                database="db3",
                username="user3",
                password="pass3"
            )

            manager.create_connection(conn1)
            manager.create_connection(conn2)
            manager.create_connection(conn3)

            # Get the middle connection
            result = manager.get_connection("conn-2")

            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            retrieved_conn = unwrap(result)
            assert retrieved_conn.name == "conn-2"
            assert retrieved_conn.database_type == "postgresql"
            assert retrieved_conn.database == "db2"

    def test_get_connection_returns_database_connection_object(self):
        """Test that get_connection returns a DatabaseConnection object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            manager.create_connection(conn)

            # Get the connection
            result = manager.get_connection("test-conn")

            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            retrieved_conn = unwrap(result)
            assert isinstance(retrieved_conn, DatabaseConnection)

    def test_get_connection_with_corrupted_store(self):
        """Test that get_connection handles corrupted store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Create corrupted JSON file
            with open(store_path, 'w') as f:
                f.write("{ invalid json }")

            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Should return error instead of raising exception
            result = manager.get_connection("any-conn")

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)

            error_msg = unwrap_err(result)
            assert "Failed to load connection store" in error_msg

    def test_get_connection_with_missing_store(self):
        """Test that get_connection handles missing store gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "nonexistent" / "connections.json"

            manager = DatabaseConnectionManager.__new__(DatabaseConnectionManager)
            manager.store_path = store_path

            # Should return error instead of raising exception
            result = manager.get_connection("any-conn")

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)

            error_msg = unwrap_err(result)
            assert "Failed to load connection store" in error_msg

    def test_get_connection_with_invalid_data(self):
        """Test that get_connection handles invalid connection data.

        This test creates a connection with invalid field types that will
        cause from_dict() to fail during retrieval.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Manually add a connection with invalid field types
            # This will pass JSON validation but fail during from_dict()
            store_data = manager._load_store()
            store_data["connections"].append({
                "name": "invalid-conn",
                "database_type": "sqlite",
                "created_at": "not-a-valid-datetime",  # Invalid datetime format
            })
            manager._save_store(store_data)

            # Try to get the invalid connection
            result = manager.get_connection("invalid-conn")

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)

            error_msg = unwrap_err(result)
            assert "Invalid connection data" in error_msg
            assert "invalid-conn" in error_msg

    def test_get_connection_case_sensitive(self):
        """Test that connection name lookup is case-sensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection with lowercase name
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            manager.create_connection(conn)

            # Try to get with different case (should fail since names must be kebab-case)
            result = manager.get_connection("Test-Conn")

            from offline_chat.database.result import is_err
            assert is_err(result)

    def test_get_connection_empty_store(self):
        """Test getting a connection from an empty store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Try to get a connection from empty store
            result = manager.get_connection("any-conn")

            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)

            error_msg = unwrap_err(result)
            assert "not found" in error_msg



class TestListConnectionsProperty:
    """Property-based tests for list_connections() method.

    Feature: database-connection-management
    Property 8: List Returns All Connections

    **Validates: Requirements 3.1**
    """

    @given(
        num_connections=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_list_returns_all_connections_no_duplicates(self, num_connections):
        """
        Property 8: List Returns All Connections

        For any set of connections in the store, listing connections should
        return all of them with no connections missing or duplicated.

        **Validates: Requirements 3.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a set of unique connection names
            created_names = set()

            # Create various types of connections
            for i in range(num_connections):
                # Vary the database type
                db_type_index = i % 4

                if db_type_index == 0:
                    # SQLite connection
                    conn = DatabaseConnection(
                        name=f"conn-sqlite-{i}",
                        database_type="sqlite",
                        file_path=f"/path/to/db{i}.db"
                    )
                elif db_type_index == 1:
                    # PostgreSQL connection
                    conn = DatabaseConnection(
                        name=f"conn-postgres-{i}",
                        database_type="postgresql",
                        host=f"host{i}.example.com",
                        port=5432 + i,
                        database=f"db{i}",
                        username=f"user{i}",
                        password=f"pass{i}"
                    )
                elif db_type_index == 2:
                    # MySQL connection
                    conn = DatabaseConnection(
                        name=f"conn-mysql-{i}",
                        database_type="mysql",
                        host=f"host{i}.example.com",
                        port=3306 + i,
                        database=f"db{i}",
                        username=f"user{i}",
                        password=f"pass{i}"
                    )
                else:
                    # Oracle connection
                    conn = DatabaseConnection(
                        name=f"conn-oracle-{i}",
                        database_type="oracle",
                        host=f"host{i}.example.com",
                        port=1521 + i,
                        service_name=f"SERVICE{i}",
                        username=f"user{i}",
                        password=f"pass{i}"
                    )

                result = manager.create_connection(conn)
                from offline_chat.database.result import is_ok
                assert is_ok(result), f"Failed to create connection {conn.name}"
                created_names.add(conn.name)

            # List all connections
            listed_connections = manager.list_connections()

            # Extract names from listed connections
            listed_names = [conn.name for conn in listed_connections]

            # Property 1: All created connections should be in the list
            assert len(listed_names) == num_connections, \
                f"Expected {num_connections} connections, got {len(listed_names)}"

            # Property 2: No duplicates in the list
            assert len(listed_names) == len(set(listed_names)), \
                f"Duplicate connections found in list: {listed_names}"

            # Property 3: All created names should be present
            assert set(listed_names) == created_names, \
                f"Listed names {set(listed_names)} != created names {created_names}"

            # Property 4: All returned objects should be DatabaseConnection instances
            for conn in listed_connections:
                assert isinstance(conn, DatabaseConnection), \
                    f"Expected DatabaseConnection, got {type(conn)}"

    @given(
        connection_configs=st.lists(
            st.tuples(
                # name
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=('Ll', 'Nd'),
                        whitelist_characters='-'
                    ),
                    min_size=1,
                    max_size=30
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                # database_type
                st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
            ),
            min_size=0,
            max_size=15,
            unique_by=lambda x: x[0]  # Ensure unique names
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_list_returns_all_connections_various_types(self, connection_configs):
        """
        Property 8: List Returns All Connections

        For any set of connections with various database types, listing
        connections should return all of them correctly.

        **Validates: Requirements 3.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            created_connections = []

            # Create connections based on generated configs
            for name, db_type in connection_configs:
                if db_type == 'sqlite':
                    conn = DatabaseConnection(
                        name=name,
                        database_type=db_type,
                        file_path=f"/path/to/{name}.db"
                    )
                elif db_type == 'oracle':
                    conn = DatabaseConnection(
                        name=name,
                        database_type=db_type,
                        host="localhost",
                        port=1521,
                        service_name="TESTDB",
                        username="user",
                        password="pass"
                    )
                elif db_type == 'postgresql':
                    conn = DatabaseConnection(
                        name=name,
                        database_type=db_type,
                        host="localhost",
                        port=5432,
                        database="testdb",
                        username="user",
                        password="pass"
                    )
                else:  # mysql
                    conn = DatabaseConnection(
                        name=name,
                        database_type=db_type,
                        host="localhost",
                        port=3306,
                        database="testdb",
                        username="user",
                        password="pass"
                    )

                result = manager.create_connection(conn)
                from offline_chat.database.result import is_ok
                if is_ok(result):
                    created_connections.append(conn)

            # List all connections
            listed_connections = manager.list_connections()

            # Verify count matches
            assert len(listed_connections) == len(created_connections), \
                f"Expected {len(created_connections)} connections, got {len(listed_connections)}"

            # Verify all names are present
            created_names = {conn.name for conn in created_connections}
            listed_names = {conn.name for conn in listed_connections}
            assert listed_names == created_names, \
                f"Listed names {listed_names} != created names {created_names}"

            # Verify no duplicates
            listed_name_list = [conn.name for conn in listed_connections]
            assert len(listed_name_list) == len(set(listed_name_list)), \
                "Duplicate connections found in list"

            # Verify database types are preserved
            for created_conn in created_connections:
                matching_listed = [c for c in listed_connections if c.name == created_conn.name]
                assert len(matching_listed) == 1, \
                    f"Expected exactly one match for {created_conn.name}"
                assert matching_listed[0].database_type == created_conn.database_type, \
                    f"Database type mismatch for {created_conn.name}"

    @given(
        num_sqlite=st.integers(min_value=0, max_value=10),
        num_postgres=st.integers(min_value=0, max_value=10),
        num_mysql=st.integers(min_value=0, max_value=10),
        num_oracle=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_list_returns_all_connections_mixed_types(
        self, num_sqlite, num_postgres, num_mysql, num_oracle
    ):
        """
        Property 8: List Returns All Connections

        For any combination of different database types, listing connections
        should return all of them with correct counts per type.

        **Validates: Requirements 3.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            total_expected = num_sqlite + num_postgres + num_mysql + num_oracle
            created_by_type = {
                'sqlite': [],
                'postgresql': [],
                'mysql': [],
                'oracle': []
            }

            # Create SQLite connections
            for i in range(num_sqlite):
                conn = DatabaseConnection(
                    name=f"sqlite-{i}",
                    database_type="sqlite",
                    file_path=f"/path/to/db{i}.db"
                )
                manager.create_connection(conn)
                created_by_type['sqlite'].append(conn.name)

            # Create PostgreSQL connections
            for i in range(num_postgres):
                conn = DatabaseConnection(
                    name=f"postgres-{i}",
                    database_type="postgresql",
                    host="localhost",
                    port=5432,
                    database=f"db{i}",
                    username="user",
                    password="pass"
                )
                manager.create_connection(conn)
                created_by_type['postgresql'].append(conn.name)

            # Create MySQL connections
            for i in range(num_mysql):
                conn = DatabaseConnection(
                    name=f"mysql-{i}",
                    database_type="mysql",
                    host="localhost",
                    port=3306,
                    database=f"db{i}",
                    username="user",
                    password="pass"
                )
                manager.create_connection(conn)
                created_by_type['mysql'].append(conn.name)

            # Create Oracle connections
            for i in range(num_oracle):
                conn = DatabaseConnection(
                    name=f"oracle-{i}",
                    database_type="oracle",
                    host="localhost",
                    port=1521,
                    service_name=f"SERVICE{i}",
                    username="user",
                    password="pass"
                )
                manager.create_connection(conn)
                created_by_type['oracle'].append(conn.name)

            # List all connections
            listed_connections = manager.list_connections()

            # Verify total count
            assert len(listed_connections) == total_expected, \
                f"Expected {total_expected} connections, got {len(listed_connections)}"

            # Verify count by type
            listed_by_type = {
                'sqlite': [],
                'postgresql': [],
                'mysql': [],
                'oracle': []
            }
            for conn in listed_connections:
                listed_by_type[conn.database_type].append(conn.name)

            for db_type in ['sqlite', 'postgresql', 'mysql', 'oracle']:
                assert len(listed_by_type[db_type]) == len(created_by_type[db_type]), \
                    f"Type {db_type}: expected {len(created_by_type[db_type])}, " \
                    f"got {len(listed_by_type[db_type])}"

                assert set(listed_by_type[db_type]) == set(created_by_type[db_type]), \
                    f"Type {db_type}: names mismatch"

            # Verify no duplicates across all connections
            all_listed_names = [conn.name for conn in listed_connections]
            assert len(all_listed_names) == len(set(all_listed_names)), \
                "Duplicate connections found in list"

    @given(
        num_connections=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_list_preserves_connection_attributes(self, num_connections):
        """
        Property 8: List Returns All Connections

        For any set of connections, listing should preserve all connection
        attributes (not just names).

        **Validates: Requirements 3.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            created_connections = []

            # Create connections with various attributes
            for i in range(num_connections):
                conn = DatabaseConnection(
                    name=f"test-conn-{i}",
                    database_type="postgresql",
                    host=f"host{i}.example.com",
                    port=5432 + i,
                    database=f"database{i}",
                    username=f"user{i}",
                    password=f"password{i}"
                )
                result = manager.create_connection(conn)
                from offline_chat.database.result import is_ok
                assert is_ok(result)
                created_connections.append(conn)

            # List all connections
            listed_connections = manager.list_connections()

            # Verify all attributes are preserved
            for created_conn in created_connections:
                matching = [c for c in listed_connections if c.name == created_conn.name]
                assert len(matching) == 1, f"Expected one match for {created_conn.name}"

                listed_conn = matching[0]
                assert listed_conn.database_type == created_conn.database_type
                assert listed_conn.host == created_conn.host
                assert listed_conn.port == created_conn.port
                assert listed_conn.database == created_conn.database
                assert listed_conn.username == created_conn.username
                assert listed_conn.password == created_conn.password

    def test_list_empty_store_returns_empty_list(self):
        """
        Property 8: List Returns All Connections

        For an empty store, listing connections should return an empty list
        (not None or error).

        **Validates: Requirements 3.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # List connections from empty store
            connections = manager.list_connections()

            # Should return empty list, not None
            assert connections is not None
            assert isinstance(connections, list)
            assert len(connections) == 0



class TestUpdateConnection:
    """Test update_connection() method."""

    def test_update_connection_success(self):
        """Test successfully updating a connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create initial connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok
            assert is_ok(result)

            # Update the connection
            updates = {
                "host": "newhost.example.com",
                "port": 5433,
                "password": "newpass"
            }
            result = manager.update_connection("test-conn", updates)

            # Verify success
            from offline_chat.database.result import unwrap
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.name == "test-conn"
            assert updated_conn.host == "newhost.example.com"
            assert updated_conn.port == 5433
            assert updated_conn.password == "newpass"
            # Unchanged fields should remain
            assert updated_conn.database_type == "postgresql"
            assert updated_conn.database == "testdb"
            assert updated_conn.username == "user"

            # Verify changes were persisted
            retrieved = manager.get_connection("test-conn")
            assert is_ok(retrieved)
            retrieved_conn = unwrap(retrieved)
            assert retrieved_conn.host == "newhost.example.com"
            assert retrieved_conn.port == 5433

    def test_update_connection_not_found(self):
        """Test updating a non-existent connection fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Try to update non-existent connection
            updates = {"host": "newhost.example.com"}
            result = manager.update_connection("nonexistent", updates)

            # Verify failure
            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "not found" in error_msg.lower()
            assert "nonexistent" in error_msg

    def test_update_connection_name_change_rejected(self):
        """Test that attempting to change connection name is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="original-name",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok
            assert is_ok(result)

            # Try to change name
            updates = {"name": "new-name"}
            result = manager.update_connection("original-name", updates)

            # Verify rejection
            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "cannot change" in error_msg.lower()
            assert "name" in error_msg.lower()

            # Verify original connection unchanged
            original = manager.get_connection("original-name")
            assert is_ok(original)

    def test_update_connection_preserves_original_on_failure(self):
        """Test that failed update preserves original connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Try to update with invalid database type
            updates = {"database_type": "invalid-type"}
            result = manager.update_connection("test-conn", updates)

            # Verify failure
            from offline_chat.database.result import is_err
            assert is_err(result)

            # Verify original connection is preserved
            original = manager.get_connection("test-conn")
            assert is_ok(original)
            original_conn = unwrap(original)
            assert original_conn.database_type == "postgresql"
            assert original_conn.host == "localhost"
            assert original_conn.port == 5432

    def test_update_connection_multiple_fields(self):
        """Test updating multiple fields at once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="multi-update",
                database_type="mysql",
                host="localhost",
                port=3306,
                database="olddb",
                username="olduser",
                password="oldpass"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Update multiple fields
            updates = {
                "host": "newhost.example.com",
                "port": 3307,
                "database": "newdb",
                "username": "newuser",
                "password": "newpass"
            }
            result = manager.update_connection("multi-update", updates)

            # Verify all updates applied
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.host == "newhost.example.com"
            assert updated_conn.port == 3307
            assert updated_conn.database == "newdb"
            assert updated_conn.username == "newuser"
            assert updated_conn.password == "newpass"
            # Unchanged field
            assert updated_conn.database_type == "mysql"

    def test_update_connection_empty_updates(self):
        """Test updating with empty updates dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Update with empty dict
            result = manager.update_connection("test-conn", {})

            # Should succeed (no changes)
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.name == "test-conn"
            assert updated_conn.database_type == "sqlite"
            assert updated_conn.file_path == "/path/to/db.db"

    def test_update_connection_invalid_database_type(self):
        """Test that updating to invalid database type fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok
            assert is_ok(result)

            # Try to update to invalid database type
            updates = {"database_type": "mongodb"}
            result = manager.update_connection("test-conn", updates)

            # Verify failure
            from offline_chat.database.result import is_err, unwrap_err
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "invalid database type" in error_msg.lower()
            assert "mongodb" in error_msg

    def test_update_connection_updates_timestamp(self):
        """Test that update_connection updates the updated_at timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Get original timestamp
            original = manager.get_connection("test-conn")
            original_conn = unwrap(original)
            original_timestamp = original_conn.updated_at

            # Wait a moment to ensure timestamp difference
            import time
            time.sleep(0.01)

            # Update connection
            updates = {"file_path": "/new/path/to/db.db"}
            result = manager.update_connection("test-conn", updates)

            # Verify timestamp was updated
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.updated_at != original_timestamp
            # The updated timestamp should be more recent
            # Both are datetime objects, so we can compare directly
            assert updated_conn.updated_at > original_timestamp

    def test_update_connection_with_additional_params(self):
        """Test updating additional_params field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass",
                additional_params={"ssl": True}
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Update additional_params
            updates = {
                "additional_params": {
                    "ssl": True,
                    "timeout": 30,
                    "pool_size": 10
                }
            }
            result = manager.update_connection("test-conn", updates)

            # Verify update
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.additional_params["ssl"] is True
            assert updated_conn.additional_params["timeout"] == 30
            assert updated_conn.additional_params["pool_size"] == 10

    def test_update_connection_oracle_to_postgresql_fields(self):
        """Test updating connection type-specific fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create Oracle connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="oracle",
                host="localhost",
                port=1521,
                service_name="TESTDB",
                username="user",
                password="pass"
            )
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok, unwrap
            assert is_ok(result)

            # Update to PostgreSQL-style (change database_type and add database field)
            updates = {
                "database_type": "postgresql",
                "port": 5432,
                "database": "testdb",
                "service_name": None  # Clear Oracle-specific field
            }
            result = manager.update_connection("test-conn", updates)

            # Verify update
            assert is_ok(result)
            updated_conn = unwrap(result)
            assert updated_conn.database_type == "postgresql"
            assert updated_conn.port == 5432
            assert updated_conn.database == "testdb"
            assert updated_conn.service_name is None



# ============================================================================
# Property-Based Tests for Connection Updates
# ============================================================================

class TestConnectionUpdateProperties:
    """Property-based tests for connection updates.

    Feature: database-connection-management
    Properties: 11, 12

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
    """

    @given(
        original_name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        new_name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_update_name_immutability(self, original_name, new_name, db_type):
        """
        Property 11: Update Name Immutability

        For any existing connection, attempting to update its name field should
        be rejected, while updates to other fields should be allowed.

        **Validates: Requirements 4.1**
        """
        # Skip if names are the same (not testing name change in that case)
        if original_name == new_name:
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if db_type == 'sqlite':
                conn = DatabaseConnection(
                    name=original_name,
                    database_type=db_type,
                    file_path="/path/to/db.db"
                )
            elif db_type == 'oracle':
                conn = DatabaseConnection(
                    name=original_name,
                    database_type=db_type,
                    host="localhost",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=original_name,
                    database_type=db_type,
                    host="localhost",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, is_ok, unwrap_err

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Attempt to update the name
            updates = {"name": new_name}
            result = manager.update_connection(original_name, updates)

            # Update should fail
            assert is_err(result), f"Name change should be rejected for '{original_name}' -> '{new_name}'"
            error_msg = unwrap_err(result)
            assert "cannot change" in error_msg.lower() or "name" in error_msg.lower(), \
                f"Error should mention name change restriction: {error_msg}"

            # Verify original connection still exists with original name
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1, "Should still have exactly one connection"
            assert store_data["connections"][0]["name"] == original_name, \
                "Connection name should remain unchanged"

            # Verify new name was NOT created
            result = manager.get_connection(new_name)
            assert is_err(result), f"New name '{new_name}' should not exist"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite']),
        update_field=st.sampled_from(['host', 'port', 'database', 'username', 'password', 'file_path'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_update_other_fields_allowed(self, name, db_type, update_field):
        """
        Property 11: Update Name Immutability (Other Fields Allowed)

        For any existing connection, updates to fields other than name should
        be allowed.

        **Validates: Requirements 4.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if db_type == 'sqlite':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/path/to/db.db"
                )
                # Only file_path is relevant for sqlite
                if update_field not in ['file_path']:
                    return  # Skip irrelevant fields
                updates = {"file_path": "/new/path/to/db.db"}
            elif db_type == 'oracle':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
                # Skip fields not relevant to oracle
                if update_field in ['database', 'file_path']:
                    return
                # Create appropriate update
                if update_field == 'host':
                    updates = {"host": "newhost.example.com"}
                elif update_field == 'port':
                    updates = {"port": 1522}
                elif update_field == 'username':
                    updates = {"username": "newuser"}
                elif update_field == 'password':
                    updates = {"password": "newpass"}
                else:
                    return
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="localhost",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )
                # Skip fields not relevant to postgresql/mysql
                if update_field == 'file_path':
                    return
                # Create appropriate update
                if update_field == 'host':
                    updates = {"host": "newhost.example.com"}
                elif update_field == 'port':
                    updates = {"port": 5433 if db_type == 'postgresql' else 3307}
                elif update_field == 'database':
                    updates = {"database": "newdb"}
                elif update_field == 'username':
                    updates = {"username": "newuser"}
                elif update_field == 'password':
                    updates = {"password": "newpass"}
                else:
                    return

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok, unwrap

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Update the field (not name)
            result = manager.update_connection(name, updates)

            # Update should succeed
            assert is_ok(result), f"Update of '{update_field}' should succeed: {result}"

            # Verify the update was applied
            updated_conn = unwrap(result)
            assert updated_conn.name == name, "Name should remain unchanged"

            # Verify the specific field was updated
            for field, value in updates.items():
                assert getattr(updated_conn, field) == value, \
                    f"Field '{field}' should be updated to '{value}'"

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        original_db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite']),
        new_host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        new_port=st.integers(min_value=1, max_value=65535)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_update_persistence_on_success(
        self, name, original_db_type, new_host, new_port
    ):
        """
        Property 12: Update Persistence Based on Validation (Success Case)

        For any connection update, if validation succeeds, the updated values
        should be persisted to the store.

        **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
        """
        # Skip sqlite since it doesn't have host/port
        if original_db_type == 'sqlite':
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if original_db_type == 'oracle':
                conn = DatabaseConnection(
                    name=name,
                    database_type=original_db_type,
                    host="original-host",
                    port=1521,
                    service_name="TESTDB",
                    username="user",
                    password="pass"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=name,
                    database_type=original_db_type,
                    host="original-host",
                    port=5432 if original_db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="user",
                    password="pass"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok, unwrap

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Update with valid values
            updates = {
                "host": new_host,
                "port": new_port
            }
            result = manager.update_connection(name, updates)

            # Update should succeed (validation passes)
            assert is_ok(result), f"Valid update should succeed: {result}"

            # Verify updated values are persisted in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name
            assert saved_conn["host"] == new_host, \
                f"Host should be updated to '{new_host}' in store"
            assert saved_conn["port"] == new_port, \
                f"Port should be updated to {new_port} in store"

            # Verify connection is retrievable with updated values
            result = manager.get_connection(name)
            assert is_ok(result)
            retrieved_conn = unwrap(result)
            assert retrieved_conn.host == new_host
            assert retrieved_conn.port == new_port

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        original_db_type=st.sampled_from(['oracle', 'postgresql', 'mysql']),
        invalid_db_type=st.text(min_size=1, max_size=50).filter(
            lambda s: s not in ['oracle', 'postgresql', 'mysql', 'sqlite']
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_update_persistence_on_failure(
        self, name, original_db_type, invalid_db_type
    ):
        """
        Property 12: Update Persistence Based on Validation (Failure Case)

        For any connection update, if validation fails, the original connection
        should remain unchanged in the store.

        **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if original_db_type == 'oracle':
                conn = DatabaseConnection(
                    name=name,
                    database_type=original_db_type,
                    host="original-host",
                    port=1521,
                    service_name="TESTDB",
                    username="original-user",
                    password="original-pass"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=name,
                    database_type=original_db_type,
                    host="original-host",
                    port=5432 if original_db_type == 'postgresql' else 3306,
                    database="testdb",
                    username="original-user",
                    password="original-pass"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_err, is_ok, unwrap

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Store original values
            original_host = conn.host
            original_port = conn.port
            original_username = conn.username
            original_password = conn.password

            # Attempt update with invalid database type (should fail validation)
            updates = {
                "database_type": invalid_db_type,
                "host": "new-host",
                "username": "new-user"
            }
            result = manager.update_connection(name, updates)

            # Update should fail (validation fails)
            assert is_err(result), f"Invalid update should fail for db_type '{invalid_db_type}'"

            # Verify original connection is preserved in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name
            assert saved_conn["database_type"] == original_db_type, \
                "Database type should remain unchanged"
            assert saved_conn["host"] == original_host, \
                "Host should remain unchanged after failed update"
            assert saved_conn["port"] == original_port, \
                "Port should remain unchanged after failed update"
            assert saved_conn["username"] == original_username, \
                "Username should remain unchanged after failed update"
            assert saved_conn["password"] == original_password, \
                "Password should remain unchanged after failed update"

            # Verify connection is retrievable with original values
            result = manager.get_connection(name)
            assert is_ok(result)
            retrieved_conn = unwrap(result)
            assert retrieved_conn.database_type == original_db_type
            assert retrieved_conn.host == original_host
            assert retrieved_conn.port == original_port
            assert retrieved_conn.username == original_username
            assert retrieved_conn.password == original_password

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['sqlite']),
        original_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        new_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip())
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_update_persistence_sqlite(
        self, name, db_type, original_path, new_path
    ):
        """
        Property 12: Update Persistence Based on Validation (SQLite)

        For any SQLite connection update, if validation succeeds, the updated
        file_path should be persisted to the store.

        **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original SQLite connection
            conn = DatabaseConnection(
                name=name,
                database_type=db_type,
                file_path=original_path
            )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok, unwrap

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Update file_path
            updates = {"file_path": new_path}
            result = manager.update_connection(name, updates)

            # Update should succeed
            assert is_ok(result), f"Valid update should succeed: {result}"

            # Verify updated file_path is persisted in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            saved_conn = store_data["connections"][0]
            assert saved_conn["name"] == name
            assert saved_conn["file_path"] == new_path, \
                f"File path should be updated to '{new_path}' in store"

            # Verify connection is retrievable with updated value
            result = manager.get_connection(name)
            assert is_ok(result)
            retrieved_conn = unwrap(result)
            assert retrieved_conn.file_path == new_path

    @given(
        name=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
            min_size=1,
            max_size=50
        ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
        db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite']),
        num_updates=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_multiple_updates_persistence(
        self, name, db_type, num_updates
    ):
        """
        Property 12: Update Persistence Based on Validation (Multiple Updates)

        For any connection, multiple successful updates should all be persisted,
        with each update building on the previous state.

        **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create original connection
            if db_type == 'sqlite':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    file_path="/path/0.db"
                )
            elif db_type == 'oracle':
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="host-0",
                    port=1521,
                    service_name="DB0",
                    username="user-0",
                    password="pass-0"
                )
            else:  # postgresql or mysql
                conn = DatabaseConnection(
                    name=name,
                    database_type=db_type,
                    host="host-0",
                    port=5432 if db_type == 'postgresql' else 3306,
                    database="db-0",
                    username="user-0",
                    password="pass-0"
                )

            result = manager.create_connection(conn)

            from offline_chat.database.result import is_ok, unwrap

            # Creation should succeed
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Perform multiple updates
            for i in range(1, num_updates + 1):
                if db_type == 'sqlite':
                    updates = {"file_path": f"/path/{i}.db"}
                    expected_value = f"/path/{i}.db"
                    field_to_check = "file_path"
                elif db_type == 'oracle':
                    updates = {"service_name": f"DB{i}"}
                    expected_value = f"DB{i}"
                    field_to_check = "service_name"
                else:  # postgresql or mysql
                    updates = {"database": f"db-{i}"}
                    expected_value = f"db-{i}"
                    field_to_check = "database"

                result = manager.update_connection(name, updates)

                # Each update should succeed
                assert is_ok(result), f"Update {i} should succeed: {result}"

                # Verify the update was persisted
                store_data = manager._load_store()
                assert len(store_data["connections"]) == 1
                saved_conn = store_data["connections"][0]
                assert saved_conn[field_to_check] == expected_value, \
                    f"After update {i}, {field_to_check} should be '{expected_value}'"

            # Final verification: retrieve connection and check final state
            result = manager.get_connection(name)
            assert is_ok(result)
            final_conn = unwrap(result)

            if db_type == 'sqlite':
                assert final_conn.file_path == f"/path/{num_updates}.db"
            elif db_type == 'oracle':
                assert final_conn.service_name == f"DB{num_updates}"
            else:
                assert final_conn.database == f"db-{num_updates}"



# ============================================================================
# DELETE CONNECTION TESTS
# ============================================================================


class TestDeleteConnection:
    """Test delete_connection() method."""

    def test_delete_connection_success(self):
        """Test deleting a connection that is not in use."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            from offline_chat.database.result import is_ok

            result = manager.create_connection(conn)
            assert is_ok(result)

            # Verify connection exists
            connections = manager.list_connections()
            assert len(connections) == 1

            # Delete the connection
            result = manager.delete_connection("test-conn")
            assert is_ok(result)

            # Verify connection was removed
            connections = manager.list_connections()
            assert len(connections) == 0

            # Verify connection is not in store
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 0

    def test_delete_connection_not_found(self):
        """Test deleting a connection that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_err, unwrap_err

            # Try to delete non-existent connection
            result = manager.delete_connection("nonexistent")

            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "not found" in error_msg.lower()
            assert "nonexistent" in error_msg

    def test_delete_connection_in_use(self):
        """Test that deleting a connection in use by agents fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="in-use-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            from offline_chat.database.result import is_err, is_ok, unwrap_err

            result = manager.create_connection(conn)
            assert is_ok(result)

            # Mock get_agents_using_connection to return agents
            original_method = manager.get_agents_using_connection
            manager.get_agents_using_connection = lambda name: ["agent1", "agent2"]

            try:
                # Try to delete connection that's in use
                result = manager.delete_connection("in-use-conn")

                assert is_err(result)
                error_msg = unwrap_err(result)
                assert "cannot delete" in error_msg.lower()
                assert "in-use-conn" in error_msg
                assert "agent1" in error_msg
                assert "agent2" in error_msg

                # Verify connection still exists
                connections = manager.list_connections()
                assert len(connections) == 1
                assert connections[0].name == "in-use-conn"
            finally:
                # Restore original method
                manager.get_agents_using_connection = original_method

    def test_delete_connection_preserves_other_connections(self):
        """Test that deleting one connection doesn't affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            from offline_chat.database.result import is_ok

            # Create multiple connections
            conn1 = DatabaseConnection(
                name="conn-1",
                database_type="sqlite",
                file_path="/path/to/db1.db"
            )
            conn2 = DatabaseConnection(
                name="conn-2",
                database_type="sqlite",
                file_path="/path/to/db2.db"
            )
            conn3 = DatabaseConnection(
                name="conn-3",
                database_type="sqlite",
                file_path="/path/to/db3.db"
            )

            assert is_ok(manager.create_connection(conn1))
            assert is_ok(manager.create_connection(conn2))
            assert is_ok(manager.create_connection(conn3))

            # Verify all connections exist
            connections = manager.list_connections()
            assert len(connections) == 3

            # Delete middle connection
            result = manager.delete_connection("conn-2")
            assert is_ok(result)

            # Verify only conn-2 was deleted
            connections = manager.list_connections()
            assert len(connections) == 2

            names = {conn.name for conn in connections}
            assert "conn-1" in names
            assert "conn-2" not in names
            assert "conn-3" in names

    def test_delete_connection_multiple_times(self):
        """Test that deleting the same connection twice fails the second time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            from offline_chat.database.result import is_err, is_ok, unwrap_err

            result = manager.create_connection(conn)
            assert is_ok(result)

            # First deletion should succeed
            result = manager.delete_connection("test-conn")
            assert is_ok(result)

            # Second deletion should fail
            result = manager.delete_connection("test-conn")
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "not found" in error_msg.lower()


class TestGetAgentsUsingConnection:
    """Test get_agents_using_connection() method."""

    def test_get_agents_using_connection_placeholder(self):
        """Test that get_agents_using_connection returns empty list (placeholder)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create a connection
            conn = DatabaseConnection(
                name="test-conn",
                database_type="sqlite",
                file_path="/path/to/db.db"
            )

            from offline_chat.database.result import is_ok

            result = manager.create_connection(conn)
            assert is_ok(result)

            # Get agents using connection (should return empty list for now)
            agents = manager.get_agents_using_connection("test-conn")

            assert isinstance(agents, list)
            assert len(agents) == 0

    def test_get_agents_using_connection_nonexistent(self):
        """Test get_agents_using_connection with non-existent connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Get agents for non-existent connection
            agents = manager.get_agents_using_connection("nonexistent")

            assert isinstance(agents, list)
            assert len(agents) == 0



# ============================================================================
# Property-Based Tests for Deletion Referential Integrity
# ============================================================================

class TestDeletionReferentialIntegrityProperty:
    """Property-based tests for deletion referential integrity.

    Feature: database-connection-management
    Property: 13

    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    @given(
        connection=st.one_of(
            # Valid Oracle connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('oracle'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                service_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                database=st.none(),
                file_path=st.none()
            ),
            # Valid PostgreSQL connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('postgresql'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                service_name=st.none(),
                file_path=st.none()
            ),
            # Valid MySQL connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('mysql'),
                host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                port=st.integers(min_value=1, max_value=65535),
                database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
                password=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
                service_name=st.none(),
                file_path=st.none()
            ),
            # Valid SQLite connection
            st.builds(
                DatabaseConnection,
                name=st.text(
                    alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                    min_size=1,
                    max_size=50
                ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
                database_type=st.just('sqlite'),
                file_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
                host=st.none(),
                port=st.none(),
                database=st.none(),
                service_name=st.none(),
                username=st.none(),
                password=st.none()
            )
        ),
        agent_names=st.lists(
            st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=1,
                max_size=30
            ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
            min_size=0,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_deletion_referential_integrity(self, connection, agent_names):
        """
        Property 13: Deletion Referential Integrity

        For any connection, if it is referenced by one or more agents, deletion
        should fail with an error listing the agents; if it is not referenced by
        any agents, deletion should succeed and remove it from the store.

        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        from unittest.mock import patch

        from offline_chat.database.result import is_err, is_ok, unwrap_err

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create the connection
            result = manager.create_connection(connection)
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Verify connection was saved
            store_data = manager._load_store()
            assert len(store_data["connections"]) == 1
            assert store_data["connections"][0]["name"] == connection.name

            # Mock get_agents_using_connection to return the agent_names list
            with patch.object(manager, 'get_agents_using_connection', return_value=agent_names):
                # Attempt to delete the connection
                delete_result = manager.delete_connection(connection.name)

                if len(agent_names) > 0:
                    # Case 1: Connection is referenced by one or more agents
                    # Deletion should fail
                    assert is_err(delete_result), \
                        f"Deletion should fail when connection is used by {len(agent_names)} agent(s)"

                    error_msg = unwrap_err(delete_result)

                    # Error message should indicate the connection cannot be deleted
                    assert "cannot delete" in error_msg.lower(), \
                        f"Error should mention 'cannot delete': {error_msg}"

                    # Error message should mention the connection name
                    assert connection.name in error_msg, \
                        f"Error should mention connection name '{connection.name}': {error_msg}"

                    # Error message should list the agents using the connection
                    assert "used by" in error_msg.lower() or "using" in error_msg.lower(), \
                        f"Error should mention agents using the connection: {error_msg}"

                    # All agent names should appear in the error message
                    for agent_name in agent_names:
                        assert agent_name in error_msg, \
                            f"Error should list agent '{agent_name}': {error_msg}"

                    # Verify connection was NOT deleted from store
                    store_data_after = manager._load_store()
                    assert len(store_data_after["connections"]) == 1, \
                        "Connection should still exist in store after failed deletion"
                    assert store_data_after["connections"][0]["name"] == connection.name, \
                        "Original connection should remain unchanged"

                else:
                    # Case 2: Connection is not referenced by any agents
                    # Deletion should succeed
                    assert is_ok(delete_result), \
                        f"Deletion should succeed when connection is not used by any agents: {delete_result}"

                    # Verify connection was removed from store
                    store_data_after = manager._load_store()
                    assert len(store_data_after["connections"]) == 0, \
                        "Connection should be removed from store after successful deletion"

                    # Verify the connection no longer exists
                    get_result = manager.get_connection(connection.name)
                    assert is_err(get_result), \
                        "Getting deleted connection should fail"

                    get_error = unwrap_err(get_result)
                    assert "not found" in get_error.lower(), \
                        f"Error should indicate connection not found: {get_error}"

    @given(
        connection=st.builds(
            DatabaseConnection,
            name=st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=1,
                max_size=50
            ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
            database_type=st.just('sqlite'),
            file_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            host=st.none(),
            port=st.none(),
            database=st.none(),
            service_name=st.none(),
            username=st.none(),
            password=st.none()
        ),
        num_agents=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_deletion_fails_with_multiple_agents(self, connection, num_agents):
        """
        Property 13: Deletion Referential Integrity (Multiple Agents)

        For any connection referenced by multiple agents, deletion should fail
        and the error message should list all agents using the connection.

        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        from unittest.mock import patch

        from offline_chat.database.result import is_err, is_ok, unwrap_err

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create the connection
            result = manager.create_connection(connection)
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Generate agent names
            agent_names = [f"agent-{i}" for i in range(num_agents)]

            # Mock get_agents_using_connection to return the agent names
            with patch.object(manager, 'get_agents_using_connection', return_value=agent_names):
                # Attempt to delete the connection
                delete_result = manager.delete_connection(connection.name)

                # Deletion should fail
                assert is_err(delete_result), \
                    f"Deletion should fail when connection is used by {num_agents} agents"

                error_msg = unwrap_err(delete_result)

                # Error message should list all agents
                for agent_name in agent_names:
                    assert agent_name in error_msg, \
                        f"Error should list agent '{agent_name}': {error_msg}"

                # Verify connection still exists
                store_data = manager._load_store()
                assert len(store_data["connections"]) == 1
                assert store_data["connections"][0]["name"] == connection.name

    @given(
        connection=st.builds(
            DatabaseConnection,
            name=st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=1,
                max_size=50
            ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
            database_type=st.just('sqlite'),
            file_path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            host=st.none(),
            port=st.none(),
            database=st.none(),
            service_name=st.none(),
            username=st.none(),
            password=st.none()
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_deletion_succeeds_with_no_agents(self, connection):
        """
        Property 13: Deletion Referential Integrity (No Agents)

        For any connection not referenced by any agents, deletion should succeed
        and remove the connection from the store.

        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        from unittest.mock import patch

        from offline_chat.database.result import is_err, is_ok

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create the connection
            result = manager.create_connection(connection)
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Verify connection exists
            store_data_before = manager._load_store()
            assert len(store_data_before["connections"]) == 1

            # Mock get_agents_using_connection to return empty list
            with patch.object(manager, 'get_agents_using_connection', return_value=[]):
                # Attempt to delete the connection
                delete_result = manager.delete_connection(connection.name)

                # Deletion should succeed
                assert is_ok(delete_result), \
                    f"Deletion should succeed when connection is not used: {delete_result}"

                # Verify connection was removed
                store_data_after = manager._load_store()
                assert len(store_data_after["connections"]) == 0, \
                    "Connection should be removed from store"

                # Verify connection no longer exists
                get_result = manager.get_connection(connection.name)
                assert is_err(get_result), \
                    "Getting deleted connection should fail"

    @given(
        connection=st.builds(
            DatabaseConnection,
            name=st.text(
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789-',
                min_size=1,
                max_size=50
            ).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s),
            database_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite']),
            host=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
            port=st.one_of(st.none(), st.integers(min_value=1, max_value=65535)),
            database=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            service_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            username=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
            password=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
            file_path=st.one_of(st.none(), st.text(min_size=1, max_size=200))
        ).filter(lambda c:
            # Ensure valid connection based on database type
            (c.database_type == 'sqlite' and c.file_path is not None and c.file_path.strip()) or
            (c.database_type == 'oracle' and c.host is not None and c.host.strip() and c.port is not None and
             c.service_name is not None and c.service_name.strip() and c.username is not None and c.username.strip() and c.password is not None and c.password.strip()) or
            (c.database_type in ['postgresql', 'mysql'] and c.host is not None and c.host.strip() and c.port is not None and
             c.database is not None and c.database.strip() and c.username is not None and c.username.strip() and c.password is not None and c.password.strip())
        ),
        has_agents=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_deletion_behavior_based_on_usage(self, connection, has_agents):
        """
        Property 13: Deletion Referential Integrity (Usage-Based Behavior)

        For any connection, deletion behavior should depend solely on whether
        the connection is referenced by agents: fail if referenced, succeed if not.

        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        from unittest.mock import patch

        from offline_chat.database.result import is_err, is_ok, unwrap_err

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"
            manager = DatabaseConnectionManager(store_path)

            # Create the connection
            result = manager.create_connection(connection)
            assert is_ok(result), f"Connection creation should succeed: {result}"

            # Determine agent list based on has_agents flag
            agent_names = ["test-agent-1", "test-agent-2"] if has_agents else []

            # Mock get_agents_using_connection
            with patch.object(manager, 'get_agents_using_connection', return_value=agent_names):
                # Attempt to delete the connection
                delete_result = manager.delete_connection(connection.name)

                if has_agents:
                    # Should fail when agents are using the connection
                    assert is_err(delete_result), \
                        "Deletion should fail when connection is in use"

                    error_msg = unwrap_err(delete_result)
                    assert connection.name in error_msg

                    # Verify connection still exists
                    store_data = manager._load_store()
                    assert len(store_data["connections"]) == 1

                else:
                    # Should succeed when no agents are using the connection
                    assert is_ok(delete_result), \
                        f"Deletion should succeed when connection is not in use: {delete_result}"

                    # Verify connection was removed
                    store_data = manager._load_store()
                    assert len(store_data["connections"]) == 0
