"""
Property-based tests for document chunking.
"""

import pytest
from hypothesis import given, strategies as st

from offline_chat.rag.document_processor import DocumentProcessor


@pytest.mark.property_test
class TestChunkingProperties:
    """Property-based tests for document chunking."""
    
    @given(
        content=st.text(min_size=1, max_size=5000),
        chunk_size=st.integers(min_value=10, max_value=500),
        chunk_overlap=st.integers(min_value=0, max_value=50)
    )
    def test_document_chunking_preserves_content(
        self, content: str, chunk_size: int, chunk_overlap: int
    ):
        """
        Feature: rag-capabilities, Property 3: Document Chunking Preserves Content
        
        For any text document, the concatenation of all chunk texts (in order)
        should contain all the original content without loss.
        
        Validates: Requirements 2.2
        """
        # Ensure chunk_overlap < chunk_size
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size - 1
        
        processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = processor.process_text_document(content, source_url="http://test.com")
        
        # Concatenate all chunk texts
        if not chunks:
            # Empty content should produce no chunks
            assert content == ""
            return
        
        # Extract all characters from chunks in order
        all_chars_from_chunks = set()
        chunk_texts = [chunk.text for chunk in chunks]
        concatenated = "".join(chunk_texts)
        
        # Every character in the original content should appear in the chunks
        for char in content:
            assert char in concatenated, f"Character '{char}' from original content not found in chunks"
        
        # The first chunk should start with the beginning of the content
        assert content.startswith(chunks[0].text[:min(len(chunks[0].text), len(content))])
        
        # The last chunk should end with the end of the content
        if len(content) > chunk_size:
            # For multi-chunk documents, verify the last chunk contains the end
            assert content.endswith(chunks[-1].text[-min(len(chunks[-1].text), len(content)):])
    
    @given(
        content=st.text(min_size=1, max_size=5000),
        source_url=st.text(min_size=1, max_size=200)
    )
    def test_chunk_metadata_invariant(self, content: str, source_url: str):
        """
        Feature: rag-capabilities, Property 4: Chunk Metadata Invariant
        
        For any document processed into chunks, every chunk should contain
        the source identifier (URL or table name) in its metadata.
        
        Validates: Requirements 2.3, 3.5, 4.4
        """
        processor = DocumentProcessor()
        chunks = processor.process_text_document(content, source_url=source_url)
        
        # Every chunk must have the source identifier in metadata
        for chunk in chunks:
            assert chunk.source_identifier == source_url
            assert "source_url" in chunk.metadata
            assert chunk.metadata["source_url"] == source_url
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata
            assert chunk.metadata["total_chunks"] == len(chunks)
    
    @given(
        table_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_")),
        rows=st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_")),
                values=st.one_of(
                    st.none(),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.text(max_size=100)
                ),
                min_size=1,
                max_size=10
            ),
            min_size=1,
            max_size=50
        )
    )
    def test_database_row_text_completeness(
        self, table_name: str, rows: list[dict]
    ):
        """
        Feature: rag-capabilities, Property 8: Database Row Text Representation Completeness
        
        For any database row, the text representation should contain all column
        names and their corresponding values.
        
        Validates: Requirements 3.2, 3.3
        """
        processor = DocumentProcessor()
        chunks = processor.process_database_rows(table_name, rows)
        
        # Should have one chunk per row
        assert len(chunks) == len(rows)
        
        # Each chunk should contain all column names and values
        for idx, chunk in enumerate(chunks):
            row = rows[idx]
            
            # Check that table name is in the text
            assert table_name in chunk.text
            
            # Check that all column names appear in the text
            for column_name in row.keys():
                assert column_name in chunk.text
            
            # Check that all non-None values appear in the text
            for column_name, value in row.items():
                if value is None:
                    assert "NULL" in chunk.text
                else:
                    assert str(value) in chunk.text
            
            # Verify metadata
            assert chunk.source_type == "database"
            assert chunk.source_identifier == table_name
            assert "table_name" in chunk.metadata
            assert chunk.metadata["table_name"] == table_name
            
            # Verify row data is flattened into metadata with row_ prefix
            for column_name, value in row.items():
                metadata_key = f"row_{column_name}"
                assert metadata_key in chunk.metadata
                if value is None:
                    assert chunk.metadata[metadata_key] == "NULL"
                else:
                    assert chunk.metadata[metadata_key] == value
