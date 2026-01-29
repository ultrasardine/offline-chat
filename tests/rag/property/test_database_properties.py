"""
Property-based tests for database integration.
"""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from offline_chat.rag.database_integration import DatabaseIntegration


@contextmanager
def temp_db_with_tables():
    """Context manager to create a temporary SQLite database with known tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create several test tables
        cursor.execute("CREATE TABLE table_a (id INTEGER PRIMARY KEY, data TEXT)")
        cursor.execute("CREATE TABLE table_b (id INTEGER PRIMARY KEY, value INTEGER)")
        cursor.execute("CREATE TABLE table_c (id INTEGER PRIMARY KEY, name TEXT)")

        conn.commit()
        conn.close()

        yield db_path
    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


# Strategy for generating invalid table names
invalid_table_names = st.one_of(
    st.text(min_size=1, max_size=50).filter(
        lambda x: x not in ["table_a", "table_b", "table_c"] and not x.startswith("sqlite_")
    ),
    st.from_regex(r"[a-z_][a-z0-9_]*", fullmatch=True).filter(
        lambda x: x not in ["table_a", "table_b", "table_c"] and not x.startswith("sqlite_")
    )
)


@given(table_name=invalid_table_names)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None  # Disable deadline due to database I/O variability
)
@pytest.mark.property_test
def test_property_database_table_validation(table_name):
    """
    Feature: rag-capabilities, Property 7: Database Table Validation

    **Validates: Requirements 3.1**

    For any table name that does not exist in the SQLite database,
    attempting to add it as a knowledge source should be rejected by validation.

    This property ensures that the system validates table existence before
    attempting to use database tables as knowledge sources.
    """
    with temp_db_with_tables() as db_path:
        db_integration = DatabaseIntegration(db_path)

        # The table should not exist (since we're generating names not in our test tables)
        exists = db_integration.validate_table_exists(table_name)

        if not exists:
            # If the table doesn't exist, fetching rows should raise ValueError
            with pytest.raises(ValueError, match="does not exist"):
                db_integration.fetch_table_rows(table_name)


@given(
    table_name=st.sampled_from(["table_a", "table_b", "table_c"]),
    limit=st.one_of(st.none(), st.integers(min_value=0, max_value=100))
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None  # Disable deadline due to database I/O variability
)
@pytest.mark.property_test
def test_property_valid_table_fetching(table_name, limit):
    """
    Feature: rag-capabilities, Property 7 (positive case): Valid Table Fetching

    **Validates: Requirements 3.1**

    For any table name that exists in the SQLite database,
    validation should succeed and rows should be fetchable.
    """
    with temp_db_with_tables() as db_path:
        db_integration = DatabaseIntegration(db_path)

        # Table should exist
        assert db_integration.validate_table_exists(table_name) is True

        # Fetching rows should not raise an error
        rows = db_integration.fetch_table_rows(table_name, limit=limit)

        # Should return a list (possibly empty)
        assert isinstance(rows, list)

        # If limit is specified, should respect it
        if limit is not None:
            assert len(rows) <= limit


@given(
    rows=st.lists(
        st.fixed_dictionaries({
            "id": st.integers(min_value=1, max_value=1000),
            "name": st.text(min_size=1, max_size=50),
            "value": st.one_of(
                st.integers(min_value=-9223372036854775808, max_value=9223372036854775807),
                st.none()
            )
        }),
        min_size=1,
        max_size=20,
        unique_by=lambda x: x["id"]  # Ensure unique IDs
    )
)
@pytest.mark.property_test
def test_property_database_row_text_completeness(rows):
    """
    Feature: rag-capabilities, Property 8: Database Row Text Representation Completeness

    **Validates: Requirements 3.2, 3.3**

    For any database row, the text representation should contain all column
    names and their corresponding values.

    This ensures that when database rows are converted to text for embedding,
    no information is lost and all columns are represented.
    """
    # Create a temporary database and insert the rows
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table matching the row structure
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)

        # Insert the generated rows
        for row in rows:
            cursor.execute(
                "INSERT INTO test_table (id, name, value) VALUES (?, ?, ?)",
                (row["id"], row["name"], row["value"])
            )

        conn.commit()
        conn.close()

        # Now test the property
        db_integration = DatabaseIntegration(db_path)
        chunks = db_integration.get_table_as_chunks("test_table")

        # Should have one chunk per row
        assert len(chunks) == len(rows)

        # Create a mapping of row IDs to rows for easier lookup
        rows_by_id = {row["id"]: row for row in rows}

        # Each chunk should contain all column names and values
        for chunk in chunks:
            text = chunk.text

            # Should contain table name
            assert "Table: test_table" in text

            # Should contain all column names
            assert "id:" in text
            assert "name:" in text
            assert "value:" in text

            # Get the row ID from metadata to find the corresponding row
            row_id = chunk.metadata["row_id"]
            row = rows_by_id[row_id]

            # Check that the values from the row are in the text
            assert f"id: {row['id']}" in text
            assert f"name: {row['name']}" in text

            if row["value"] is None:
                assert "value: NULL" in text
            else:
                assert f"value: {row['value']}" in text

            # Verify row data is flattened into metadata with row_ prefix
            assert chunk.metadata["table_name"] == "test_table"
            for column_name, value in row.items():
                metadata_key = f"row_{column_name}"
                assert metadata_key in chunk.metadata
                if value is None:
                    assert chunk.metadata[metadata_key] == "NULL"
                else:
                    assert chunk.metadata[metadata_key] == value

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


@given(table_name=st.text(min_size=1, max_size=50))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_property_table_info_consistency(table_name):
    """
    Feature: rag-capabilities: Table Info Consistency

    **Validates: Requirements 3.1**

    For any table name, if the table exists, get_table_info should return
    valid information. If it doesn't exist, it should raise ValueError.
    """
    with temp_db_with_tables() as db_path:
        db_integration = DatabaseIntegration(db_path)

        exists = db_integration.validate_table_exists(table_name)

        if exists:
            # Should be able to get table info
            info = db_integration.get_table_info(table_name)
            assert "columns" in info
            assert "row_count" in info
            assert isinstance(info["columns"], list)
            assert isinstance(info["row_count"], int)
            assert info["row_count"] >= 0
        else:
            # Should raise ValueError
            with pytest.raises(ValueError, match="does not exist"):
                db_integration.get_table_info(table_name)
