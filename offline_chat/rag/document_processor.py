"""
Document processor for chunking and preparing documents for RAG.

This module handles text chunking with configurable size and overlap,
metadata preservation, and database row to text conversion.
"""

from typing import Any

from offline_chat.rag.models import DocumentChunk


class DocumentProcessor:
    """
    Processes documents into chunks for embedding and storage.

    Handles text chunking with configurable size and overlap, preserves metadata,
    and converts database rows to text representations.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """
        Initialize document processor with chunking parameters.

        Args:
            chunk_size: Maximum size of each chunk in characters (default: 512)
            chunk_overlap: Number of characters to overlap between chunks (default: 50)

        Raises:
            ValueError: If chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_text_document(
        self,
        content: str,
        source_url: str
    ) -> list[DocumentChunk]:
        """
        Process a text document into chunks with metadata.

        Args:
            content: Raw text content to chunk
            source_url: URL or identifier of the source

        Returns:
            List of DocumentChunk objects with text and metadata
        """
        if not content:
            return []

        chunks = self._chunk_text(content)

        return [
            DocumentChunk(
                text=chunk_text,
                source_type="web",
                source_identifier=source_url,
                chunk_index=idx,
                metadata={
                    "source_url": source_url,
                    "chunk_index": idx,
                    "total_chunks": len(chunks)
                }
            )
            for idx, chunk_text in enumerate(chunks)
        ]

    def process_database_rows(
        self,
        table_name: str,
        rows: list[dict[str, Any]]
    ) -> list[DocumentChunk]:
        """
        Convert database rows into text chunks with metadata.

        Each row is converted to a text representation that includes all column
        names and their corresponding values in a readable format.

        Args:
            table_name: Name of the database table
            rows: List of row dictionaries with column names as keys

        Returns:
            List of DocumentChunk objects representing each row
        """
        if not rows:
            return []

        chunks = []
        for idx, row in enumerate(rows):
            text = self._row_to_text(table_name, row)

            # Flatten row data into metadata (ChromaDB doesn't support nested dicts)
            # Prefix row column names with "row_" to avoid conflicts
            metadata = {
                "table_name": table_name,
                "row_index": idx,
            }

            # Add each row column as a separate metadata field
            for key, value in row.items():
                # Convert value to string if it's not a simple type
                if value is None:
                    metadata[f"row_{key}"] = "NULL"
                elif isinstance(value, (str, int, float, bool)):
                    metadata[f"row_{key}"] = value
                else:
                    metadata[f"row_{key}"] = str(value)

            chunks.append(
                DocumentChunk(
                    text=text,
                    source_type="database",
                    source_identifier=table_name,
                    chunk_index=idx,
                    metadata=metadata
                )
            )

        return chunks

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)

            # Move start position forward by (chunk_size - overlap)
            start += self.chunk_size - self.chunk_overlap

            # Stop if we've reached the end
            if end >= len(text):
                break

        return chunks

    def _row_to_text(self, table_name: str, row: dict[str, Any]) -> str:
        """
        Convert a database row to a text representation.

        Includes table name, column names, and values in a readable format.

        Args:
            table_name: Name of the table
            row: Dictionary of column names to values

        Returns:
            Text representation of the row
        """
        lines = [f"Table: {table_name}"]

        for column_name, value in row.items():
            # Format the value appropriately
            if value is None:
                formatted_value = "NULL"
            elif isinstance(value, str):
                formatted_value = value
            else:
                formatted_value = str(value)

            lines.append(f"{column_name}: {formatted_value}")

        return "\n".join(lines)
