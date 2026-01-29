"""Unit tests for AgentConnectionAssignment dataclass.

This module tests the AgentConnectionAssignment dataclass, including:
- Dataclass initialization
- JSON serialization (to_dict)
- JSON deserialization (from_dict)
- Edge cases and error handling
"""

import pytest

from offline_chat.database import AccessLevel, AgentConnectionAssignment


class TestAgentConnectionAssignmentInitialization:
    """Tests for AgentConnectionAssignment initialization."""

    def test_create_with_read_only_access(self):
        """Test creating an assignment with read-only access."""
        assignment = AgentConnectionAssignment(
            connection_name="prod-db",
            access_level=AccessLevel.READ_ONLY
        )

        assert assignment.connection_name == "prod-db"
        assert assignment.access_level == AccessLevel.READ_ONLY
        assert assignment.allowed_tables is None

    def test_create_with_read_write_access(self):
        """Test creating an assignment with read-write access."""
        assignment = AgentConnectionAssignment(
            connection_name="dev-db",
            access_level=AccessLevel.READ_WRITE
        )

        assert assignment.connection_name == "dev-db"
        assert assignment.access_level == AccessLevel.READ_WRITE
        assert assignment.allowed_tables is None

    def test_create_with_table_specific_read_access(self):
        """Test creating an assignment with table-specific read access."""
        assignment = AgentConnectionAssignment(
            connection_name="analytics-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users", "orders"]
        )

        assert assignment.connection_name == "analytics-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert assignment.allowed_tables == ["users", "orders"]

    def test_create_with_table_specific_read_write_access(self):
        """Test creating an assignment with table-specific read-write access."""
        assignment = AgentConnectionAssignment(
            connection_name="app-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["products", "inventory", "suppliers"]
        )

        assert assignment.connection_name == "app-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE
        assert assignment.allowed_tables == ["products", "inventory", "suppliers"]

    def test_create_with_empty_allowed_tables(self):
        """Test creating an assignment with an empty allowed_tables list."""
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=[]
        )

        assert assignment.connection_name == "test-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert assignment.allowed_tables == []

    def test_create_with_single_allowed_table(self):
        """Test creating an assignment with a single allowed table."""
        assignment = AgentConnectionAssignment(
            connection_name="single-table-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["users"]
        )

        assert assignment.connection_name == "single-table-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE
        assert assignment.allowed_tables == ["users"]


class TestAgentConnectionAssignmentSerialization:
    """Tests for AgentConnectionAssignment to_dict method."""

    def test_to_dict_read_only(self):
        """Test serializing an assignment with read-only access."""
        assignment = AgentConnectionAssignment(
            connection_name="prod-db",
            access_level=AccessLevel.READ_ONLY
        )

        result = assignment.to_dict()

        assert result == {
            "connection_name": "prod-db",
            "access_level": "read-only",
            "allowed_tables": None
        }

    def test_to_dict_read_write(self):
        """Test serializing an assignment with read-write access."""
        assignment = AgentConnectionAssignment(
            connection_name="dev-db",
            access_level=AccessLevel.READ_WRITE
        )

        result = assignment.to_dict()

        assert result == {
            "connection_name": "dev-db",
            "access_level": "read-write",
            "allowed_tables": None
        }

    def test_to_dict_table_specific_read(self):
        """Test serializing an assignment with table-specific read access."""
        assignment = AgentConnectionAssignment(
            connection_name="analytics-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users", "orders"]
        )

        result = assignment.to_dict()

        assert result == {
            "connection_name": "analytics-db",
            "access_level": "table-specific-read",
            "allowed_tables": ["users", "orders"]
        }

    def test_to_dict_table_specific_read_write(self):
        """Test serializing an assignment with table-specific read-write access."""
        assignment = AgentConnectionAssignment(
            connection_name="app-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["products", "inventory"]
        )

        result = assignment.to_dict()

        assert result == {
            "connection_name": "app-db",
            "access_level": "table-specific-read-write",
            "allowed_tables": ["products", "inventory"]
        }

    def test_to_dict_empty_allowed_tables(self):
        """Test serializing an assignment with empty allowed_tables list."""
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=[]
        )

        result = assignment.to_dict()

        assert result == {
            "connection_name": "test-db",
            "access_level": "table-specific-read",
            "allowed_tables": []
        }

    def test_to_dict_preserves_access_level_enum_value(self):
        """Test that to_dict converts AccessLevel enum to its string value."""
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.READ_ONLY
        )

        result = assignment.to_dict()

        # Verify it's a string, not an enum
        assert isinstance(result["access_level"], str)
        assert result["access_level"] == "read-only"


class TestAgentConnectionAssignmentDeserialization:
    """Tests for AgentConnectionAssignment from_dict method."""

    def test_from_dict_read_only(self):
        """Test deserializing an assignment with read-only access."""
        data = {
            "connection_name": "prod-db",
            "access_level": "read-only",
            "allowed_tables": None
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "prod-db"
        assert assignment.access_level == AccessLevel.READ_ONLY
        assert assignment.allowed_tables is None

    def test_from_dict_read_write(self):
        """Test deserializing an assignment with read-write access."""
        data = {
            "connection_name": "dev-db",
            "access_level": "read-write",
            "allowed_tables": None
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "dev-db"
        assert assignment.access_level == AccessLevel.READ_WRITE
        assert assignment.allowed_tables is None

    def test_from_dict_table_specific_read(self):
        """Test deserializing an assignment with table-specific read access."""
        data = {
            "connection_name": "analytics-db",
            "access_level": "table-specific-read",
            "allowed_tables": ["users", "orders"]
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "analytics-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert assignment.allowed_tables == ["users", "orders"]

    def test_from_dict_table_specific_read_write(self):
        """Test deserializing an assignment with table-specific read-write access."""
        data = {
            "connection_name": "app-db",
            "access_level": "table-specific-read-write",
            "allowed_tables": ["products", "inventory", "suppliers"]
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "app-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE
        assert assignment.allowed_tables == ["products", "inventory", "suppliers"]

    def test_from_dict_without_allowed_tables_key(self):
        """Test deserializing when allowed_tables key is missing (should default to None)."""
        data = {
            "connection_name": "test-db",
            "access_level": "read-only"
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "test-db"
        assert assignment.access_level == AccessLevel.READ_ONLY
        assert assignment.allowed_tables is None

    def test_from_dict_empty_allowed_tables(self):
        """Test deserializing with an empty allowed_tables list."""
        data = {
            "connection_name": "test-db",
            "access_level": "table-specific-read",
            "allowed_tables": []
        }

        assignment = AgentConnectionAssignment.from_dict(data)

        assert assignment.connection_name == "test-db"
        assert assignment.access_level == AccessLevel.TABLE_SPECIFIC_READ
        assert assignment.allowed_tables == []

    def test_from_dict_missing_connection_name(self):
        """Test that from_dict raises KeyError when connection_name is missing."""
        data = {
            "access_level": "read-only",
            "allowed_tables": None
        }

        with pytest.raises(KeyError):
            AgentConnectionAssignment.from_dict(data)

    def test_from_dict_missing_access_level(self):
        """Test that from_dict raises KeyError when access_level is missing."""
        data = {
            "connection_name": "test-db",
            "allowed_tables": None
        }

        with pytest.raises(KeyError):
            AgentConnectionAssignment.from_dict(data)

    def test_from_dict_invalid_access_level(self):
        """Test that from_dict raises ValueError for invalid access_level."""
        data = {
            "connection_name": "test-db",
            "access_level": "invalid-level",
            "allowed_tables": None
        }

        with pytest.raises(ValueError):
            AgentConnectionAssignment.from_dict(data)


class TestAgentConnectionAssignmentRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_round_trip_read_only(self):
        """Test that an assignment survives a round-trip through to_dict/from_dict."""
        original = AgentConnectionAssignment(
            connection_name="prod-db",
            access_level=AccessLevel.READ_ONLY
        )

        data = original.to_dict()
        restored = AgentConnectionAssignment.from_dict(data)

        assert restored.connection_name == original.connection_name
        assert restored.access_level == original.access_level
        assert restored.allowed_tables == original.allowed_tables

    def test_round_trip_table_specific_read_write(self):
        """Test round-trip with table-specific read-write access."""
        original = AgentConnectionAssignment(
            connection_name="app-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables=["users", "orders", "products"]
        )

        data = original.to_dict()
        restored = AgentConnectionAssignment.from_dict(data)

        assert restored.connection_name == original.connection_name
        assert restored.access_level == original.access_level
        assert restored.allowed_tables == original.allowed_tables

    def test_round_trip_empty_allowed_tables(self):
        """Test round-trip with empty allowed_tables list."""
        original = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=[]
        )

        data = original.to_dict()
        restored = AgentConnectionAssignment.from_dict(data)

        assert restored.connection_name == original.connection_name
        assert restored.access_level == original.access_level
        assert restored.allowed_tables == original.allowed_tables

    def test_round_trip_preserves_table_order(self):
        """Test that round-trip preserves the order of allowed_tables."""
        original = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["zebra", "apple", "banana"]
        )

        data = original.to_dict()
        restored = AgentConnectionAssignment.from_dict(data)

        assert restored.allowed_tables == ["zebra", "apple", "banana"]


class TestAgentConnectionAssignmentEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_connection_name_with_special_characters(self):
        """Test assignment with connection name containing hyphens and numbers."""
        assignment = AgentConnectionAssignment(
            connection_name="prod-db-123",
            access_level=AccessLevel.READ_ONLY
        )

        assert assignment.connection_name == "prod-db-123"

    def test_allowed_tables_with_special_names(self):
        """Test assignment with table names containing special characters."""
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["user_data", "order_items", "product_123"]
        )

        assert assignment.allowed_tables == ["user_data", "order_items", "product_123"]

    def test_allowed_tables_with_duplicate_names(self):
        """Test that duplicate table names are preserved (validation is elsewhere)."""
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users", "users", "orders"]
        )

        # The dataclass doesn't validate duplicates - that's the validator's job
        assert assignment.allowed_tables == ["users", "users", "orders"]

    def test_many_allowed_tables(self):
        """Test assignment with many allowed tables."""
        tables = [f"table_{i}" for i in range(100)]
        assignment = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=tables
        )

        assert len(assignment.allowed_tables) == 100
        assert assignment.allowed_tables[0] == "table_0"
        assert assignment.allowed_tables[99] == "table_99"

    def test_equality_same_values(self):
        """Test that two assignments with same values are equal."""
        assignment1 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.READ_ONLY
        )
        assignment2 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.READ_ONLY
        )

        assert assignment1 == assignment2

    def test_equality_different_connection_name(self):
        """Test that assignments with different connection names are not equal."""
        assignment1 = AgentConnectionAssignment(
            connection_name="db1",
            access_level=AccessLevel.READ_ONLY
        )
        assignment2 = AgentConnectionAssignment(
            connection_name="db2",
            access_level=AccessLevel.READ_ONLY
        )

        assert assignment1 != assignment2

    def test_equality_different_access_level(self):
        """Test that assignments with different access levels are not equal."""
        assignment1 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.READ_ONLY
        )
        assignment2 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.READ_WRITE
        )

        assert assignment1 != assignment2

    def test_equality_different_allowed_tables(self):
        """Test that assignments with different allowed_tables are not equal."""
        assignment1 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["users"]
        )
        assignment2 = AgentConnectionAssignment(
            connection_name="test-db",
            access_level=AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables=["orders"]
        )

        assert assignment1 != assignment2
