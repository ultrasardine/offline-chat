"""
Unit tests for PromptAugmenter.
"""

import pytest

from offline_chat.rag.models import DocumentChunk, SearchResult
from offline_chat.rag.prompt_augmenter import PromptAugmenter


class TestPromptAugmenter:
    """Unit tests for the PromptAugmenter class."""

    @pytest.fixture
    def augmenter(self):
        """Create a PromptAugmenter instance."""
        return PromptAugmenter()

    @pytest.fixture
    def sample_chunks(self):
        """Create sample document chunks."""
        return [
            DocumentChunk(
                text="Python is a high-level programming language.",
                source_type="web",
                source_identifier="https://example.com/python",
                chunk_index=0,
                metadata={},
            ),
            DocumentChunk(
                text="It was created by Guido van Rossum in 1991.",
                source_type="database",
                source_identifier="programming_languages",
                chunk_index=1,
                metadata={"row_id": 42},
            ),
        ]

    @pytest.fixture
    def sample_search_results(self, sample_chunks):
        """Create sample search results."""
        return [
            SearchResult(chunk=sample_chunks[0], similarity_score=0.95, rank=1),
            SearchResult(chunk=sample_chunks[1], similarity_score=0.87, rank=2),
        ]

    def test_format_context_chunk_web_source(self, augmenter):
        """Test formatting a web source chunk."""
        chunk = DocumentChunk(
            text="Test content from web",
            source_type="web",
            source_identifier="https://example.com/test",
            chunk_index=0,
            metadata={},
        )

        result = augmenter.format_context_chunk(chunk, 1)

        assert "[Context 1]" in result
        assert "Source Type: web" in result
        assert "Web Source: https://example.com/test" in result
        assert "Test content from web" in result

    def test_format_context_chunk_database_source(self, augmenter):
        """Test formatting a database source chunk."""
        chunk = DocumentChunk(
            text="Test content from database",
            source_type="database",
            source_identifier="users_table",
            chunk_index=0,
            metadata={"row_id": 123},
        )

        result = augmenter.format_context_chunk(chunk, 2)

        assert "[Context 2]" in result
        assert "Source Type: database" in result
        assert "Database Table: users_table" in result
        assert "Test content from database" in result

    def test_augment_prompt_with_document_chunks(self, augmenter, sample_chunks):
        """Test augmenting prompt with DocumentChunk objects."""
        query = "What is Python?"
        system_prompt = "You are a helpful assistant."

        result = augmenter.augment_prompt(query, sample_chunks, system_prompt)

        # Check system prompt is included
        assert system_prompt in result

        # Check RAG instructions are included
        assert "IMPORTANT INSTRUCTIONS FOR RESPONDING:" in result
        assert "respond ONLY based on the context provided" in result
        assert "cite the sources" in result
        assert "NOT fabricate" in result

        # Check context chunks are included
        assert "Python is a high-level programming language." in result
        assert "It was created by Guido van Rossum in 1991." in result

        # Check source attribution
        assert "Web Source: https://example.com/python" in result
        assert "Database Table: programming_languages" in result

        # Check query is included
        assert query in result

    def test_augment_prompt_with_search_results(self, augmenter, sample_search_results):
        """Test augmenting prompt with SearchResult objects."""
        query = "Tell me about Python"
        system_prompt = "You are a programming expert."

        result = augmenter.augment_prompt(query, sample_search_results, system_prompt)

        # Check system prompt is included
        assert system_prompt in result

        # Check RAG instructions are included
        assert "IMPORTANT INSTRUCTIONS FOR RESPONDING:" in result

        # Check context chunks are included (extracted from SearchResult)
        assert "Python is a high-level programming language." in result
        assert "It was created by Guido van Rossum in 1991." in result

        # Check query is included
        assert query in result

    def test_augment_prompt_with_empty_context(self, augmenter):
        """Test augmenting prompt when no context is available."""
        query = "What is the meaning of life?"
        system_prompt = "You are a helpful assistant."

        result = augmenter.augment_prompt(query, [], system_prompt)

        # Check system prompt is included
        assert system_prompt in result

        # Check no context message is included
        assert "No relevant context was found" in result
        assert "don't have information available" in result

        # Check query is included
        assert query in result

        # Check RAG instructions are NOT included (different prompt for no context)
        assert "IMPORTANT INSTRUCTIONS FOR RESPONDING:" not in result

    def test_augment_prompt_multiple_chunks_formatting(self, augmenter):
        """Test that multiple chunks are formatted clearly with separators."""
        chunks = [
            DocumentChunk(
                text="First chunk",
                source_type="web",
                source_identifier="https://example.com/1",
                chunk_index=0,
                metadata={},
            ),
            DocumentChunk(
                text="Second chunk",
                source_type="web",
                source_identifier="https://example.com/2",
                chunk_index=1,
                metadata={},
            ),
            DocumentChunk(
                text="Third chunk", source_type="database", source_identifier="test_table", chunk_index=2, metadata={}
            ),
        ]

        result = augmenter.augment_prompt("Test query", chunks, "System prompt")

        # Check all chunks are present
        assert "First chunk" in result
        assert "Second chunk" in result
        assert "Third chunk" in result

        # Check context numbering
        assert "[Context 1]" in result
        assert "[Context 2]" in result
        assert "[Context 3]" in result

        # Check separators are present
        assert "=" * 80 in result
        assert "-" * 80 in result

    def test_rag_instructions_completeness(self, augmenter, sample_chunks):
        """
        Test that all required RAG instructions are included.

        **Validates: Requirements 5.3, 5.4, 12.1, 12.3, 12.4, 12.5**
        """
        result = augmenter.augment_prompt("Test", sample_chunks, "System")
        result_lower = result.lower()

        # Requirement 5.3: Respond only based on provided context
        assert "respond only based on the context provided" in result_lower

        # Requirement 5.4: Cite sources
        assert "cite the sources" in result_lower

        # Requirement 12.1: Context-only responses
        assert "do not use any external knowledge" in result_lower

        # Requirement 12.3: Acknowledge uncertainty
        assert "uncertain" in result_lower

        # Requirement 12.4: Never fabricate information
        assert "not fabricate" in result_lower

        # Requirement 12.5: Quote or paraphrase from context
        assert "quote or paraphrase" in result_lower

    def test_prompt_formatting_with_single_chunk(self, augmenter):
        """Test prompt formatting with a single context chunk."""
        chunk = DocumentChunk(
            text="Single chunk content",
            source_type="web",
            source_identifier="https://example.com/single",
            chunk_index=0,
            metadata={},
        )

        result = augmenter.augment_prompt("Query", [chunk], "System prompt")

        # Check that the chunk is properly formatted
        assert "[Context 1]" in result
        assert "Single chunk content" in result
        assert "https://example.com/single" in result

        # Check that there's no [Context 2]
        assert "[Context 2]" not in result

    def test_prompt_formatting_with_many_chunks(self, augmenter):
        """Test prompt formatting with many context chunks (stress test)."""
        chunks = [
            DocumentChunk(
                text=f"Content for chunk {i}",
                source_type="web" if i % 2 == 0 else "database",
                source_identifier=f"source_{i}",
                chunk_index=i,
                metadata={},
            )
            for i in range(10)
        ]

        result = augmenter.augment_prompt("Query", chunks, "System prompt")

        # Check that all chunks are present and numbered correctly
        for i in range(10):
            assert f"[Context {i + 1}]" in result
            assert f"Content for chunk {i}" in result
            assert f"source_{i}" in result

    def test_no_context_prompt_structure(self, augmenter):
        """
        Test the structure of the prompt when no context is available.

        **Validates: Requirements 6.5, 12.2**
        """
        query = "What is quantum computing?"
        system_prompt = "You are a helpful assistant."

        result = augmenter.augment_prompt(query, [], system_prompt)

        # Check system prompt is included
        assert system_prompt in result

        # Check no context message is clear
        assert "No relevant context was found" in result

        # Check instruction to not make up information
        assert "don't have information available" in result.lower() or "do not have information" in result.lower()
        assert "Do NOT attempt to answer from general knowledge" in result or "not attempt to answer" in result.lower()

        # Check query is included
        assert query in result

        # Check that RAG instructions for context-based responses are NOT included
        # (since there's no context, different instructions apply)
        assert "IMPORTANT INSTRUCTIONS FOR RESPONDING:" not in result
        assert "CONTEXT INFORMATION:" not in result

    def test_prompt_includes_query_and_system_prompt(self, augmenter, sample_chunks):
        """Test that both query and system prompt are included in augmented prompt."""
        query = "What programming language should I learn?"
        system_prompt = "You are an expert programming advisor."

        result = augmenter.augment_prompt(query, sample_chunks, system_prompt)

        # Both should be present in the final prompt
        assert query in result
        assert system_prompt in result

    def test_chunk_formatting_with_special_characters(self, augmenter):
        """Test that chunks with special characters are formatted correctly."""
        chunk = DocumentChunk(
            text="Content with special chars: @#$%^&*()[]{}|\\<>?/~`",
            source_type="web",
            source_identifier="https://example.com/special?param=value&other=123",
            chunk_index=0,
            metadata={"key": "value with spaces"},
        )

        result = augmenter.format_context_chunk(chunk, 1)

        # Check that special characters are preserved
        assert "@#$%^&*()[]{}|\\<>?/~`" in result
        assert "https://example.com/special?param=value&other=123" in result

    def test_chunk_formatting_with_empty_metadata(self, augmenter):
        """Test chunk formatting when metadata is empty."""
        chunk = DocumentChunk(
            text="Content without metadata",
            source_type="database",
            source_identifier="test_table",
            chunk_index=0,
            metadata={},
        )

        result = augmenter.format_context_chunk(chunk, 1)

        # Should still format correctly
        assert "Content without metadata" in result
        assert "test_table" in result
        assert "[Context 1]" in result

    def test_augment_prompt_preserves_chunk_order(self, augmenter):
        """Test that chunks appear in the augmented prompt in the order provided."""
        chunks = [
            DocumentChunk(
                text="First chunk", source_type="web", source_identifier="source_1", chunk_index=0, metadata={}
            ),
            DocumentChunk(
                text="Second chunk", source_type="web", source_identifier="source_2", chunk_index=1, metadata={}
            ),
            DocumentChunk(
                text="Third chunk", source_type="web", source_identifier="source_3", chunk_index=2, metadata={}
            ),
        ]

        result = augmenter.augment_prompt("Query", chunks, "System")

        # Find positions of each chunk in the result
        pos_first = result.find("First chunk")
        pos_second = result.find("Second chunk")
        pos_third = result.find("Third chunk")

        # Verify order is preserved
        assert pos_first < pos_second < pos_third, "Chunks are not in the correct order"
