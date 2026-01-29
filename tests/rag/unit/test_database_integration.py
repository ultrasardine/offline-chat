"""
Unit tests for database integration.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from offline_chat.rag.database_integration import DatabaseIntegration
from offline_chat.rag.document_processor import DocumentProcessor


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create a test database with sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER
        )
    """)

    # Insert sample data
    cursor.executemany(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        [
            ("Alice", "alice@example.com", 30),
            ("Bob", "bob@example.com", 25),
            ("Charlie", None, 35),
        ]
    )

    # Create an empty table
    cursor.execute("""
        CREATE TABLE empty_table (
            id INTEGER PRIMARY KEY,
            data TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink()


def test_init_with_valid_path(temp_db):
    """Test initialization with a valid database path."""
    db_integration = DatabaseIntegration(temp_db)
    assert db_integration.db_path == Path(temp_db)
    assert db_integration.document_processor is not None


def test_init_with_custom_processor(temp_db):
    """Test initialization with a custom document processor."""
    processor = DocumentProcessor(chunk_size=256, chunk_overlap=25)
    db_integration = DatabaseIntegration(temp_db, processor)
    assert db_integration.document_processor is processor


def test_init_with_empty_path():
    """Test initialization with empty path raises ValueError."""
    with pytest.raises(ValueError, match="Database path cannot be empty"):
        DatabaseIntegration("")


def test_init_with_nonexistent_file():
    """Test initialization with non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Database file not found"):
        DatabaseIntegration("/nonexistent/path/to/db.sqlite")


def test_validate_table_exists_true(temp_db):
    """Test table validation returns True for existing table."""
    db_integration = DatabaseIntegration(temp_db)
    assert db_integration.validate_table_exists("users") is True


def test_validate_table_exists_false(temp_db):
    """Test table validation returns False for non-existent table."""
    db_integration = DatabaseIntegration(temp_db)
    assert db_integration.validate_table_exists("nonexistent_table") is False


def test_validate_table_exists_empty_name(temp_db):
    """Test table validation with empty name raises ValueError."""
    db_integration = DatabaseIntegration(temp_db)
    with pytest.raises(ValueError, match="Table name cannot be empty"):
        db_integration.validate_table_exists("")


def test_fetch_table_rows(temp_db):
    """Test fetching rows from a table."""
    db_integration = DatabaseIntegration(temp_db)
    rows = db_integration.fetch_table_rows("users")

    assert len(rows) == 3
    assert all(isinstance(row, dict) for row in rows)

    # Check first row
    assert rows[0]["name"] == "Alice"
    assert rows[0]["email"] == "alice@example.com"
    assert rows[0]["age"] == 30

    # Check row with NULL value
    assert rows[2]["name"] == "Charlie"
    assert rows[2]["email"] is None


def test_fetch_table_rows_with_limit(temp_db):
    """Test fetching rows with a limit."""
    db_integration = DatabaseIntegration(temp_db)
    rows = db_integration.fetch_table_rows("users", limit=2)

    assert len(rows) == 2


def test_fetch_table_rows_empty_table(temp_db):
    """Test fetching rows from an empty table."""
    db_integration = DatabaseIntegration(temp_db)
    rows = db_integration.fetch_table_rows("empty_table")

    assert rows == []


def test_fetch_table_rows_nonexistent_table(temp_db):
    """Test fetching rows from non-existent table raises ValueError."""
    db_integration = DatabaseIntegration(temp_db)
    with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
        db_integration.fetch_table_rows("nonexistent")


def test_fetch_table_rows_empty_name(temp_db):
    """Test fetching rows with empty table name raises ValueError."""
    db_integration = DatabaseIntegration(temp_db)
    with pytest.raises(ValueError, match="Table name cannot be empty"):
        db_integration.fetch_table_rows("")


def test_get_table_as_chunks(temp_db):
    """Test converting table rows to DocumentChunks."""
    db_integration = DatabaseIntegration(temp_db)
    chunks = db_integration.get_table_as_chunks("users")

    assert len(chunks) == 3

    # Check first chunk
    assert chunks[0].source_type == "database"
    assert chunks[0].source_identifier == "users"
    assert chunks[0].chunk_index == 0
    assert "Table: users" in chunks[0].text
    assert "name: Alice" in chunks[0].text
    assert "email: alice@example.com" in chunks[0].text

    # Check metadata - row data is flattened with row_ prefix
    assert chunks[0].metadata["table_name"] == "users"
    assert chunks[0].metadata["row_name"] == "Alice"
    assert chunks[0].metadata["row_email"] == "alice@example.com"


def test_get_table_as_chunks_with_limit(temp_db):
    """Test converting limited table rows to DocumentChunks."""
    db_integration = DatabaseIntegration(temp_db)
    chunks = db_integration.get_table_as_chunks("users", limit=1)

    assert len(chunks) == 1


def test_get_table_as_chunks_empty_table(temp_db):
    """Test converting empty table returns empty list."""
    db_integration = DatabaseIntegration(temp_db)
    chunks = db_integration.get_table_as_chunks("empty_table")

    assert chunks == []


def test_list_tables(temp_db):
    """Test listing all tables in the database."""
    db_integration = DatabaseIntegration(temp_db)
    tables = db_integration.list_tables()

    assert "users" in tables
    assert "empty_table" in tables
    assert len(tables) == 2


def test_get_table_info(temp_db):
    """Test getting table information."""
    db_integration = DatabaseIntegration(temp_db)
    info = db_integration.get_table_info("users")

    assert info["columns"] == ["id", "name", "email", "age"]
    assert info["row_count"] == 3


def test_get_table_info_empty_table(temp_db):
    """Test getting info for empty table."""
    db_integration = DatabaseIntegration(temp_db)
    info = db_integration.get_table_info("empty_table")

    assert info["columns"] == ["id", "data"]
    assert info["row_count"] == 0


def test_get_table_info_nonexistent_table(temp_db):
    """Test getting info for non-existent table raises ValueError."""
    db_integration = DatabaseIntegration(temp_db)
    with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
        db_integration.get_table_info("nonexistent")


def test_get_table_info_empty_name(temp_db):
    """Test getting info with empty table name raises ValueError."""
    db_integration = DatabaseIntegration(temp_db)
    with pytest.raises(ValueError, match="Table name cannot be empty"):
        db_integration.get_table_info("")
