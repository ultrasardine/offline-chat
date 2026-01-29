"""Unit tests for DatabaseConnection dataclass."""

import json
from datetime import datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from offline_chat.database.connection import DatabaseConnection


class TestDatabaseConnectionBasics:
    """Test basic DatabaseConnection functionality."""

    def test_create_oracle_connection(self):
        """Test creating an Oracle connection with all required fields."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username="test_user",
            password="test_pass",
        )

        assert conn.name == "test-oracle"
        assert conn.database_type == "oracle"
        assert conn.host == "localhost"
        assert conn.port == 1521
        assert conn.service_name == "TESTDB"
        assert conn.username == "test_user"
        assert conn.password == "test_pass"
        assert isinstance(conn.created_at, datetime)
        assert isinstance(conn.updated_at, datetime)

    def test_create_postgresql_connection(self):
        """Test creating a PostgreSQL connection."""
        conn = DatabaseConnection(
            name="test-postgres",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="test_pass",
        )

        assert conn.name == "test-postgres"
        assert conn.database_type == "postgresql"
        assert conn.database == "testdb"

    def test_create_mysql_connection(self):
        """Test creating a MySQL connection."""
        conn = DatabaseConnection(
            name="test-mysql",
            database_type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            username="test_user",
            password="test_pass",
        )

        assert conn.name == "test-mysql"
        assert conn.database_type == "mysql"
        assert conn.port == 3306

    def test_create_sqlite_connection(self):
        """Test creating a SQLite connection."""
        conn = DatabaseConnection(name="test-sqlite", database_type="sqlite", file_path="/path/to/database.db")

        assert conn.name == "test-sqlite"
        assert conn.database_type == "sqlite"
        assert conn.file_path == "/path/to/database.db"
        assert conn.host is None
        assert conn.port is None

    def test_additional_params(self):
        """Test connection with additional parameters."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="test_pass",
            additional_params={"ssl": True, "timeout": 30},
        )

        assert conn.additional_params == {"ssl": True, "timeout": 30}


class TestDatabaseConnectionSerialization:
    """Test JSON serialization and deserialization."""

    def test_to_dict_oracle(self):
        """Test converting Oracle connection to dictionary."""
        conn = DatabaseConnection(
            name="test-oracle",
            database_type="oracle",
            host="localhost",
            port=1521,
            service_name="TESTDB",
            username="test_user",
            password="test_pass",
        )

        data = conn.to_dict()

        assert data["name"] == "test-oracle"
        assert data["database_type"] == "oracle"
        assert data["host"] == "localhost"
        assert data["port"] == 1521
        assert data["service_name"] == "TESTDB"
        assert data["username"] == "test_user"
        assert data["password"] == "test_pass"
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_to_dict_sqlite(self):
        """Test converting SQLite connection to dictionary."""
        conn = DatabaseConnection(name="test-sqlite", database_type="sqlite", file_path="/path/to/db.db")

        data = conn.to_dict()

        assert data["name"] == "test-sqlite"
        assert data["database_type"] == "sqlite"
        assert data["file_path"] == "/path/to/db.db"
        assert data["host"] is None
        assert data["port"] is None

    def test_from_dict_oracle(self):
        """Test creating Oracle connection from dictionary."""
        data = {
            "name": "test-oracle",
            "database_type": "oracle",
            "host": "localhost",
            "port": 1521,
            "service_name": "TESTDB",
            "username": "test_user",
            "password": "test_pass",
            "created_at": "2025-01-13T10:00:00",
            "updated_at": "2025-01-13T10:00:00",
        }

        conn = DatabaseConnection.from_dict(data)

        assert conn.name == "test-oracle"
        assert conn.database_type == "oracle"
        assert conn.host == "localhost"
        assert conn.port == 1521
        assert conn.service_name == "TESTDB"
        assert conn.username == "test_user"
        assert conn.password == "test_pass"
        assert isinstance(conn.created_at, datetime)
        assert isinstance(conn.updated_at, datetime)

    def test_from_dict_sqlite(self):
        """Test creating SQLite connection from dictionary."""
        data = {
            "name": "test-sqlite",
            "database_type": "sqlite",
            "file_path": "/path/to/db.db",
            "created_at": "2025-01-13T10:00:00",
            "updated_at": "2025-01-13T10:00:00",
        }

        conn = DatabaseConnection.from_dict(data)

        assert conn.name == "test-sqlite"
        assert conn.database_type == "sqlite"
        assert conn.file_path == "/path/to/db.db"

    def test_from_dict_with_additional_params(self):
        """Test creating connection from dict with additional params."""
        data = {
            "name": "test-conn",
            "database_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "test_user",
            "password": "test_pass",
            "additional_params": {"ssl": True, "timeout": 30},
            "created_at": "2025-01-13T10:00:00",
            "updated_at": "2025-01-13T10:00:00",
        }

        conn = DatabaseConnection.from_dict(data)

        assert conn.additional_params == {"ssl": True, "timeout": 30}

    def test_from_dict_without_timestamps(self):
        """Test creating connection from dict without timestamp fields."""
        data = {"name": "test-conn", "database_type": "sqlite", "file_path": "/path/to/db.db"}

        conn = DatabaseConnection.from_dict(data)

        assert isinstance(conn.created_at, datetime)
        assert isinstance(conn.updated_at, datetime)

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="test_pass",
            additional_params={"ssl": True},
        )

        data = original.to_dict()
        restored = DatabaseConnection.from_dict(data)

        assert restored.name == original.name
        assert restored.database_type == original.database_type
        assert restored.host == original.host
        assert restored.port == original.port
        assert restored.database == original.database
        assert restored.username == original.username
        assert restored.password == original.password
        assert restored.additional_params == original.additional_params


class TestDatabaseConnectionMasking:
    """Test sensitive field masking functionality."""

    def test_mask_password(self):
        """Test that password is masked in masked output."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="secret_password",
        )

        masked = conn.mask_sensitive_fields()

        assert masked["password"] == "********"
        assert masked["username"] == "test_user"  # Username not masked
        assert masked["host"] == "localhost"

    def test_mask_no_password(self):
        """Test masking when password is None."""
        conn = DatabaseConnection(name="test-sqlite", database_type="sqlite", file_path="/path/to/db.db")

        masked = conn.mask_sensitive_fields()

        assert masked["password"] is None
        assert masked["file_path"] == "/path/to/db.db"

    def test_mask_additional_params_password(self):
        """Test masking sensitive keys in additional_params."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="test_pass",
            additional_params={"ssl": True, "api_key": "secret_key", "timeout": 30, "auth_token": "secret_token"},
        )

        masked = conn.mask_sensitive_fields()

        assert masked["password"] == "********"
        assert masked["additional_params"]["ssl"] is True
        assert masked["additional_params"]["api_key"] == "********"
        assert masked["additional_params"]["auth_token"] == "********"
        assert masked["additional_params"]["timeout"] == 30

    def test_mask_preserves_original(self):
        """Test that masking doesn't modify the original connection."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="secret_password",
        )

        masked = conn.mask_sensitive_fields()

        # Original should be unchanged
        assert conn.password == "secret_password"
        # Masked should have asterisks
        assert masked["password"] == "********"

    def test_mask_all_sensitive_keywords(self):
        """Test that all sensitive keywords are masked."""
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="test_user",
            password="test_pass",
            additional_params={
                "db_password": "secret1",
                "access_token": "secret2",
                "secret_key": "secret3",
                "api_credential": "secret4",
                "normal_param": "visible",
            },
        )

        masked = conn.mask_sensitive_fields()

        assert masked["additional_params"]["db_password"] == "********"
        assert masked["additional_params"]["access_token"] == "********"
        assert masked["additional_params"]["secret_key"] == "********"
        assert masked["additional_params"]["api_credential"] == "********"
        assert masked["additional_params"]["normal_param"] == "visible"


class TestDatabaseConnectionEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_additional_params(self):
        """Test connection with empty additional_params."""
        conn = DatabaseConnection(
            name="test-conn", database_type="sqlite", file_path="/path/to/db.db", additional_params={}
        )

        assert conn.additional_params == {}
        masked = conn.mask_sensitive_fields()
        assert masked["additional_params"] == {}

    def test_none_additional_params_in_dict(self):
        """Test from_dict when additional_params is missing."""
        data = {"name": "test-conn", "database_type": "sqlite", "file_path": "/path/to/db.db"}

        conn = DatabaseConnection.from_dict(data)

        assert conn.additional_params == {}

    def test_all_optional_fields_none(self):
        """Test connection with minimal required fields."""
        conn = DatabaseConnection(name="test-conn", database_type="sqlite")

        assert conn.host is None
        assert conn.port is None
        assert conn.database is None
        assert conn.service_name is None
        assert conn.username is None
        assert conn.password is None
        assert conn.file_path is None


# ============================================================================
# Property-Based Tests
# ============================================================================


# Custom Hypothesis strategies for generating valid connection data
def valid_connection_name():
    """Generate valid kebab-case connection names."""
    return st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"), min_size=1, max_size=50
    ).filter(lambda s: s[0] != "-" and s[-1] != "-" and "--" not in s)


def oracle_connection_strategy():
    """Generate valid Oracle connection configurations."""
    return st.builds(
        DatabaseConnection,
        name=valid_connection_name(),
        database_type=st.just("oracle"),
        host=st.text(min_size=1, max_size=100),
        port=st.integers(min_value=1, max_value=65535),
        service_name=st.text(min_size=1, max_size=50),
        username=st.text(min_size=1, max_size=50),
        password=st.text(min_size=1, max_size=100),
        database=st.none(),
        file_path=st.none(),
        additional_params=st.dictionaries(
            st.text(min_size=1, max_size=20), st.one_of(st.text(), st.integers(), st.booleans())
        ),
    )


def postgresql_connection_strategy():
    """Generate valid PostgreSQL connection configurations."""
    return st.builds(
        DatabaseConnection,
        name=valid_connection_name(),
        database_type=st.just("postgresql"),
        host=st.text(min_size=1, max_size=100),
        port=st.integers(min_value=1, max_value=65535),
        database=st.text(min_size=1, max_size=50),
        username=st.text(min_size=1, max_size=50),
        password=st.text(min_size=1, max_size=100),
        service_name=st.none(),
        file_path=st.none(),
        additional_params=st.dictionaries(
            st.text(min_size=1, max_size=20), st.one_of(st.text(), st.integers(), st.booleans())
        ),
    )


def mysql_connection_strategy():
    """Generate valid MySQL connection configurations."""
    return st.builds(
        DatabaseConnection,
        name=valid_connection_name(),
        database_type=st.just("mysql"),
        host=st.text(min_size=1, max_size=100),
        port=st.integers(min_value=1, max_value=65535),
        database=st.text(min_size=1, max_size=50),
        username=st.text(min_size=1, max_size=50),
        password=st.text(min_size=1, max_size=100),
        service_name=st.none(),
        file_path=st.none(),
        additional_params=st.dictionaries(
            st.text(min_size=1, max_size=20), st.one_of(st.text(), st.integers(), st.booleans())
        ),
    )


def sqlite_connection_strategy():
    """Generate valid SQLite connection configurations."""
    return st.builds(
        DatabaseConnection,
        name=valid_connection_name(),
        database_type=st.just("sqlite"),
        file_path=st.text(min_size=1, max_size=200),
        host=st.none(),
        port=st.none(),
        database=st.none(),
        service_name=st.none(),
        username=st.none(),
        password=st.none(),
        additional_params=st.dictionaries(
            st.text(min_size=1, max_size=20), st.one_of(st.text(), st.integers(), st.booleans())
        ),
    )


def any_connection_strategy():
    """Generate any valid database connection."""
    return st.one_of(
        oracle_connection_strategy(),
        postgresql_connection_strategy(),
        mysql_connection_strategy(),
        sqlite_connection_strategy(),
    )


class TestConnectionStoreStructureProperty:
    """Property-based tests for connection store structure.

    Feature: database-connection-management
    Property 6: Connection Store Structure

    **Validates: Requirements 1.3**
    """

    @given(connections=st.lists(any_connection_strategy(), min_size=0, max_size=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_connection_store_structure(self, connections):
        """
        Property 6: Connection Store Structure

        For any connection store after saving connections, the JSON file should
        contain a "connections" array where each element has the required fields
        (name, database_type, and type-specific parameters).

        **Validates: Requirements 1.3**
        """
        # Simulate a connection store structure
        store_data = {"version": "1.0", "connections": [conn.to_dict() for conn in connections]}

        # Verify the store can be serialized to JSON
        json_str = json.dumps(store_data)
        assert json_str is not None

        # Verify the store can be deserialized from JSON
        loaded_store = json.loads(json_str)

        # Verify top-level structure
        assert "connections" in loaded_store
        assert isinstance(loaded_store["connections"], list)
        assert len(loaded_store["connections"]) == len(connections)

        # Verify each connection has required fields
        for i, conn_data in enumerate(loaded_store["connections"]):
            original_conn = connections[i]

            # All connections must have name and database_type
            assert "name" in conn_data
            assert "database_type" in conn_data
            assert conn_data["name"] == original_conn.name
            assert conn_data["database_type"] == original_conn.database_type

            # Verify type-specific required fields
            if conn_data["database_type"] == "oracle":
                assert "host" in conn_data
                assert "port" in conn_data
                assert "service_name" in conn_data
                assert "username" in conn_data
                assert "password" in conn_data
                assert conn_data["host"] == original_conn.host
                assert conn_data["port"] == original_conn.port
                assert conn_data["service_name"] == original_conn.service_name

            elif conn_data["database_type"] in ["postgresql", "mysql"]:
                assert "host" in conn_data
                assert "port" in conn_data
                assert "database" in conn_data
                assert "username" in conn_data
                assert "password" in conn_data
                assert conn_data["host"] == original_conn.host
                assert conn_data["port"] == original_conn.port
                assert conn_data["database"] == original_conn.database

            elif conn_data["database_type"] == "sqlite":
                assert "file_path" in conn_data
                assert conn_data["file_path"] == original_conn.file_path

            # Verify timestamps are present and in ISO format
            assert "created_at" in conn_data
            assert "updated_at" in conn_data
            assert isinstance(conn_data["created_at"], str)
            assert isinstance(conn_data["updated_at"], str)
            # Verify they can be parsed as ISO format
            datetime.fromisoformat(conn_data["created_at"])
            datetime.fromisoformat(conn_data["updated_at"])

    @given(connections=st.lists(any_connection_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_connection_serialization_roundtrip(self, connections):
        """
        Property 6: Connection Store Structure (Roundtrip)

        For any set of connections, serializing to JSON and deserializing back
        should preserve all connection data.

        **Validates: Requirements 1.3**
        """
        # Serialize connections to store format
        store_data = {"version": "1.0", "connections": [conn.to_dict() for conn in connections]}

        # Convert to JSON and back
        json_str = json.dumps(store_data)
        loaded_store = json.loads(json_str)

        # Deserialize connections
        restored_connections = [DatabaseConnection.from_dict(conn_data) for conn_data in loaded_store["connections"]]

        # Verify all connections were restored correctly
        assert len(restored_connections) == len(connections)

        for original, restored in zip(connections, restored_connections):
            assert restored.name == original.name
            assert restored.database_type == original.database_type
            assert restored.host == original.host
            assert restored.port == original.port
            assert restored.database == original.database
            assert restored.service_name == original.service_name
            assert restored.username == original.username
            assert restored.password == original.password
            assert restored.file_path == original.file_path
            assert restored.additional_params == original.additional_params
            # Timestamps should be preserved (within microsecond precision)
            assert abs((restored.created_at - original.created_at).total_seconds()) < 0.001
            assert abs((restored.updated_at - original.updated_at).total_seconds()) < 0.001

    @given(connection=any_connection_strategy())
    @settings(max_examples=100)
    def test_individual_connection_required_fields(self, connection):
        """
        Property 6: Connection Store Structure (Individual)

        For any individual connection, its dictionary representation must
        contain all required fields for its database type.

        **Validates: Requirements 1.3**
        """
        conn_dict = connection.to_dict()

        # Universal required fields
        assert "name" in conn_dict
        assert "database_type" in conn_dict
        assert "created_at" in conn_dict
        assert "updated_at" in conn_dict
        assert "additional_params" in conn_dict

        # Type-specific required fields
        db_type = conn_dict["database_type"]

        if db_type == "oracle":
            required_fields = ["host", "port", "service_name", "username", "password"]
            for field in required_fields:
                assert field in conn_dict
                assert conn_dict[field] is not None

        elif db_type in ["postgresql", "mysql"]:
            required_fields = ["host", "port", "database", "username", "password"]
            for field in required_fields:
                assert field in conn_dict
                assert conn_dict[field] is not None

        elif db_type == "sqlite":
            assert "file_path" in conn_dict
            assert conn_dict["file_path"] is not None
