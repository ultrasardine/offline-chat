"""Unit tests for AccessLevel enum."""

import pytest
from offline_chat.database import AccessLevel


class TestAccessLevel:
    """Test suite for AccessLevel enum."""

    def test_access_level_values(self):
        """Test that all access level values are defined correctly."""
        assert AccessLevel.READ_ONLY.value == "read-only"
        assert AccessLevel.READ_WRITE.value == "read-write"
        assert AccessLevel.TABLE_SPECIFIC_READ.value == "table-specific-read"
        assert AccessLevel.TABLE_SPECIFIC_READ_WRITE.value == "table-specific-read-write"

    def test_access_level_from_string(self):
        """Test that access levels can be created from string values."""
        assert AccessLevel("read-only") == AccessLevel.READ_ONLY
        assert AccessLevel("read-write") == AccessLevel.READ_WRITE
        assert AccessLevel("table-specific-read") == AccessLevel.TABLE_SPECIFIC_READ
        assert AccessLevel("table-specific-read-write") == AccessLevel.TABLE_SPECIFIC_READ_WRITE

    def test_access_level_invalid_value(self):
        """Test that invalid access level values raise ValueError."""
        with pytest.raises(ValueError):
            AccessLevel("invalid-level")

    def test_access_level_count(self):
        """Test that exactly 4 access levels are defined."""
        assert len(list(AccessLevel)) == 4

    def test_access_level_names(self):
        """Test that all access level names are correct."""
        levels = {level.name for level in AccessLevel}
        expected = {"READ_ONLY", "READ_WRITE", "TABLE_SPECIFIC_READ", "TABLE_SPECIFIC_READ_WRITE"}
        assert levels == expected

    def test_access_level_is_string_enum(self):
        """Test that AccessLevel values are strings."""
        for level in AccessLevel:
            assert isinstance(level.value, str)

    def test_access_level_equality(self):
        """Test that access levels can be compared for equality."""
        level1 = AccessLevel.READ_ONLY
        level2 = AccessLevel("read-only")
        assert level1 == level2
        assert level1 != AccessLevel.READ_WRITE
