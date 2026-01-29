"""
Unit tests for DocumentProcessor.
"""

import pytest

from offline_chat.rag.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Unit tests for the DocumentProcessor class."""

    def test_initialization_with_defaults(self):
        """Test processor initialization with default parameters."""
        processor = DocumentProcessor()
        assert processor.chunk_size == 512
        assert processor.chunk_overlap == 50

    def test_initialization_with_custom_params(self):
        """Test processor initialization with custom parameters."""
        processor = DocumentProcessor(chunk_size=256, chunk_overlap=25)
        assert processor.chunk_size == 256
        assert processor.chunk_overlap == 25

    def test_initialization_invalid_chunk_size(self):
        """Test that invalid chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            DocumentProcessor(chunk_size=0)

        with pytest.raises(ValueError, match="chunk_size must be positive"):
            DocumentProcessor(chunk_size=-10)

    def test_initialization_invalid_chunk_overlap(self):
        """Test that invalid chunk_overlap raises ValueError."""
        with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
            DocumentProcessor(chunk_overlap=-1)

    def test_initialization_overlap_exceeds_size(self):
        """Test that chunk_overlap >= chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            DocumentProcessor(chunk_size=100, chunk_overlap=100)

        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            DocumentProcessor(chunk_size=100, chunk_overlap=150)

    def test_process_text_document_empty_content(self):
        """Test processing empty text document returns empty list."""
        processor = DocumentProcessor()
        chunks = processor.process_text_document("", "http://example.com")
        assert chunks == []

    def test_process_text_document_single_chunk(self):
        """Test processing text that fits in a single chunk."""
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=10)
        content = "This is a short text."
        chunks = processor.process_text_document(content, "http://example.com")

        assert len(chunks) == 1
        assert chunks[0].text == content
        assert chunks[0].source_type == "web"
        assert chunks[0].source_identifier == "http://example.com"
        assert chunks[0].chunk_index == 0
        assert chunks[0].metadata["source_url"] == "http://example.com"
        assert chunks[0].metadata["total_chunks"] == 1

    def test_process_text_document_multiple_chunks(self):
        """Test processing text that requires multiple chunks."""
        processor = DocumentProcessor(chunk_size=20, chunk_overlap=5)
        content = "This is a longer text that will be split into multiple chunks for testing."
        chunks = processor.process_text_document(content, "http://example.com")

        # Should have multiple chunks
        assert len(chunks) > 1

        # Each chunk should have correct metadata
        for idx, chunk in enumerate(chunks):
            assert chunk.source_type == "web"
            assert chunk.source_identifier == "http://example.com"
            assert chunk.chunk_index == idx
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert len(chunk.text) <= 20

    def test_chunk_overlap_behavior(self):
        """Test that chunk overlap works correctly."""
        processor = DocumentProcessor(chunk_size=10, chunk_overlap=3)
        content = "0123456789ABCDEFGHIJ"  # 20 characters
        chunks = processor.process_text_document(content, "http://test.com")

        # First chunk: 0-9 (10 chars)
        assert chunks[0].text == "0123456789"

        # Second chunk should start at position 7 (10 - 3 overlap)
        # and go to position 16 (7 + 10 - 1)
        assert chunks[1].text == "789ABCDEFG"

        # Verify overlap exists
        assert "789" in chunks[0].text
        assert "789" in chunks[1].text

    def test_process_text_document_single_word(self):
        """Test processing a single-word document."""
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=10)
        content = "Hello"
        chunks = processor.process_text_document(content, "http://example.com")

        assert len(chunks) == 1
        assert chunks[0].text == "Hello"

    def test_process_database_rows_empty_list(self):
        """Test processing empty row list returns empty list."""
        processor = DocumentProcessor()
        chunks = processor.process_database_rows("users", [])
        assert chunks == []

    def test_process_database_rows_single_row(self):
        """Test processing a single database row."""
        processor = DocumentProcessor()
        rows = [{"id": 1, "name": "Alice", "age": 30}]
        chunks = processor.process_database_rows("users", rows)

        assert len(chunks) == 1
        chunk = chunks[0]

        # Verify text contains table name and all columns
        assert "users" in chunk.text
        assert "id" in chunk.text
        assert "1" in chunk.text
        assert "name" in chunk.text
        assert "Alice" in chunk.text
        assert "age" in chunk.text
        assert "30" in chunk.text

        # Verify metadata
        assert chunk.source_type == "database"
        assert chunk.source_identifier == "users"
        assert chunk.chunk_index == 0
        assert chunk.metadata["table_name"] == "users"
        # Verify row data is flattened into metadata with row_ prefix
        assert chunk.metadata["row_id"] == 1
        assert chunk.metadata["row_name"] == "Alice"
        assert chunk.metadata["row_age"] == 30

    def test_process_database_rows_multiple_rows(self):
        """Test processing multiple database rows."""
        processor = DocumentProcessor()
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        chunks = processor.process_database_rows("users", rows)

        assert len(chunks) == 3

        for idx, chunk in enumerate(chunks):
            assert chunk.source_type == "database"
            assert chunk.source_identifier == "users"
            assert chunk.chunk_index == idx
            # Verify row data is flattened into metadata
            assert chunk.metadata["row_id"] == rows[idx]["id"]
            assert chunk.metadata["row_name"] == rows[idx]["name"]

    def test_process_database_rows_with_null_values(self):
        """Test processing rows with NULL values."""
        processor = DocumentProcessor()
        rows = [{"id": 1, "name": "Alice", "email": None}]
        chunks = processor.process_database_rows("users", rows)

        assert len(chunks) == 1
        chunk = chunks[0]

        # NULL values should be represented as "NULL" in text
        assert "NULL" in chunk.text
        assert "email" in chunk.text

    def test_process_database_rows_with_various_types(self):
        """Test processing rows with various data types."""
        processor = DocumentProcessor()
        rows = [{
            "id": 42,
            "name": "Test",
            "price": 19.99,
            "active": True,
            "description": None
        }]
        chunks = processor.process_database_rows("products", rows)

        assert len(chunks) == 1
        chunk = chunks[0]

        # All values should be in the text
        assert "42" in chunk.text
        assert "Test" in chunk.text
        assert "19.99" in chunk.text
        assert "True" in chunk.text
        assert "NULL" in chunk.text

    def test_row_to_text_format(self):
        """Test the format of row-to-text conversion."""
        processor = DocumentProcessor()
        rows = [{"id": 1, "name": "Alice"}]
        chunks = processor.process_database_rows("users", rows)

        text = chunks[0].text
        lines = text.split("\n")

        # First line should be the table name
        assert lines[0] == "Table: users"

        # Subsequent lines should be column: value pairs
        assert any("id: 1" in line for line in lines)
        assert any("name: Alice" in line for line in lines)

    def test_chunking_with_various_text_sizes(self):
        """Test chunking behavior with various text sizes."""
        processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)

        # Test with text smaller than chunk_size
        small_text = "Small"
        small_chunks = processor.process_text_document(small_text, "http://test.com")
        assert len(small_chunks) == 1

        # Test with text exactly chunk_size
        exact_text = "x" * 50
        exact_chunks = processor.process_text_document(exact_text, "http://test.com")
        assert len(exact_chunks) == 1

        # Test with text slightly larger than chunk_size
        larger_text = "x" * 51
        larger_chunks = processor.process_text_document(larger_text, "http://test.com")
        assert len(larger_chunks) == 2

        # Test with text much larger than chunk_size
        large_text = "x" * 200
        large_chunks = processor.process_text_document(large_text, "http://test.com")
        assert len(large_chunks) > 2
