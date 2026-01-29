"""
Database integration for RAG capabilities.

This module provides functionality to validate SQLite tables, fetch rows,
and convert them to text representations for embedding and retrieval.
"""

import sqlite3
from pathlib import Path
from typing import Any

from offline_chat.rag.document_processor import DocumentProcessor
from offline_chat.rag.models import DocumentChunk


class DatabaseIntegration:
    """
    Handles database table validation and row fetching for RAG.

    Provides methods to check table existence, fetch rows, and convert
    them to text representations using DocumentProcessor.
    """

    def __init__(self, db_path: str | Path, document_processor: DocumentProcessor | None = None):
        """
        Initialize database integration with a SQLite database path.

        Args:
            db_path: Path to the SQLite database file
            document_processor: Optional DocumentProcessor instance for row conversion.
                               If not provided, a default one will be created.

        Raises:
            ValueError: If db_path is empty or None
            FileNotFoundError: If the database file does not exist
        """
        if not db_path:
            raise ValueError("Database path cannot be empty")

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        self.document_processor = document_processor or DocumentProcessor()

    def validate_table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the SQLite database.

        Args:
            table_name: Name of the table to validate

        Returns:
            True if the table exists, False otherwise

        Raises:
            ValueError: If table_name is empty or None
        """
        if not table_name:
            raise ValueError("Table name cannot be empty")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                result = cursor.fetchone()
                return result is not None
        except sqlite3.Error:
            return False

    def fetch_table_rows(
        self,
        table_name: str,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch rows from a table as dictionaries.

        Args:
            table_name: Name of the table to fetch from
            limit: Optional maximum number of rows to fetch

        Returns:
            List of dictionaries where keys are column names and values are row values

        Raises:
            ValueError: If table_name is empty or table does not exist
            sqlite3.Error: If there's an error executing the query
        """
        if not table_name:
            raise ValueError("Table name cannot be empty")

        if not self.validate_table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist in database")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable column name access
                cursor = conn.cursor()

                query = f"SELECT * FROM {table_name}"
                if limit is not None:
                    query += f" LIMIT {limit}"

                cursor.execute(query)
                rows = cursor.fetchall()

                # Convert sqlite3.Row objects to dictionaries
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Error fetching rows from table '{table_name}': {e}") from e

    def get_table_as_chunks(
        self,
        table_name: str,
        limit: int | None = None
    ) -> list[DocumentChunk]:
        """
        Fetch table rows and convert them to DocumentChunk objects.

        This is a convenience method that combines fetch_table_rows and
        DocumentProcessor.process_database_rows.

        Args:
            table_name: Name of the table to process
            limit: Optional maximum number of rows to fetch

        Returns:
            List of DocumentChunk objects representing the table rows

        Raises:
            ValueError: If table_name is empty or table does not exist
            sqlite3.Error: If there's an error fetching rows
        """
        rows = self.fetch_table_rows(table_name, limit)
        return self.document_processor.process_database_rows(table_name, rows)

    def list_tables(self) -> list[str]:
        """
        List all tables in the database.

        Returns:
            List of table names in the database

        Raises:
            sqlite3.Error: If there's an error querying the database
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Error listing tables: {e}") from e

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """
        Get information about a table's structure.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary containing table information:
                - columns: List of column names
                - row_count: Number of rows in the table

        Raises:
            ValueError: If table_name is empty or table does not exist
            sqlite3.Error: If there's an error querying the database
        """
        if not table_name:
            raise ValueError("Table name cannot be empty")

        if not self.validate_table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist in database")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]

                return {
                    "columns": columns,
                    "row_count": row_count
                }
        except sqlite3.Error as e:
            raise sqlite3.Error(f"Error getting table info for '{table_name}': {e}") from e
