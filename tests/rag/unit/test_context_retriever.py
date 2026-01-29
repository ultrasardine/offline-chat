"""
Unit tests for ContextRetriever.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import DocumentChunk, RetrievalResult
from offline_chat.rag.vector_store import VectorStore


class TestContextRetriever:
    """Unit tests for the ContextRetriever class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def vector_store(self, temp_dir):
        """Create a VectorStore instance."""
        return VectorStore(temp_dir)

    @pytest.fixture
    def embedding_generator(self):
        """Create an EmbeddingGenerator instance."""
        return EmbeddingGenerator()

    @pytest.fixture
    def context_retriever(self, vector_store, embedding_generator):
        """Create a ContextRetriever instance."""
        return ContextRetriever(vector_store, embedding_generator)

    @pytest.fixture
    def sample_chunks(self):
        """Create sample document chunks for testing."""
        return [
            DocumentChunk(
                text="Python is a high-level programming language.",
                source_type="web",
                source_identifier="https://example.com/python",
                chunk_index=0,
                metadata={"topic": "programming"}
            ),
            DocumentChunk(
                text="Machine learning is a subset of artificial intelligence.",
                source_type="web",
                source_identifier="https://example.com/ml",
                chunk_index=0,
                metadata={"topic": "ai"}
            ),
            DocumentChunk(
                text="Databases store and organize data efficiently.",
                source_type="database",
                source_identifier="tech_docs",
                chunk_index=0,
                metadata={"topic": "databases"}
            )
        ]

    def test_initialization(self, vector_store, embedding_generator):
        """Test that ContextRetriever can be initialized with required components."""
        retriever = ContextRetriever(vector_store, embedding_generator)

        assert retriever.vector_store is vector_store
        assert retriever.embedding_generator is embedding_generator

    def test_retrieve_context_with_results(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test retrieving context when relevant chunks exist."""
        collection_name = "test-agent"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve context for a query
        query = "What is Python?"
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query=query,
            top_k=2,
            min_similarity=0.0
        )

        # Verify result structure
        assert isinstance(result, RetrievalResult)
        assert result.query == query
        assert isinstance(result.chunks, list)
        assert result.total_results == len(result.chunks)
        assert result.retrieval_time_ms > 0

        # Should get at least one result
        assert len(result.chunks) > 0
        assert len(result.chunks) <= 2  # Respects top_k

    def test_retrieve_context_empty_query_raises_error(self, context_retriever):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty or None"):
            context_retriever.retrieve_context(
                collection_name="test-agent",
                query="",
                top_k=5
            )

        with pytest.raises(ValueError, match="Query cannot be empty or None"):
            context_retriever.retrieve_context(
                collection_name="test-agent",
                query=None,
                top_k=5
            )

    def test_retrieve_context_nonexistent_collection(self, context_retriever):
        """Test retrieving from a collection that doesn't exist returns empty results."""
        result = context_retriever.retrieve_context(
            collection_name="nonexistent-collection",
            query="test query",
            top_k=5
        )

        assert isinstance(result, RetrievalResult)
        assert result.query == "test query"
        assert len(result.chunks) == 0
        assert result.total_results == 0
        assert result.retrieval_time_ms > 0

    def test_retrieve_context_empty_collection(
        self, context_retriever, vector_store
    ):
        """Test retrieving from an empty collection returns empty results."""
        collection_name = "empty-collection"
        vector_store.create_collection(collection_name, 384)

        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="test query",
            top_k=5
        )

        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) == 0
        assert result.total_results == 0

    def test_retrieve_context_respects_top_k(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that top_k parameter limits the number of results."""
        collection_name = "test-agent-topk"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve with top_k=1
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="programming",
            top_k=1,
            min_similarity=0.0
        )

        assert len(result.chunks) <= 1

        # Retrieve with top_k=2
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="programming",
            top_k=2,
            min_similarity=0.0
        )

        assert len(result.chunks) <= 2

    def test_retrieve_context_respects_min_similarity(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that min_similarity threshold filters results."""
        collection_name = "test-agent-threshold"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve with very high threshold (should get fewer or no results)
        result_high_threshold = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="completely unrelated query about quantum physics",
            top_k=10,
            min_similarity=0.9  # Very high threshold
        )

        # Retrieve with low threshold (should get more results)
        result_low_threshold = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="completely unrelated query about quantum physics",
            top_k=10,
            min_similarity=0.0  # No threshold
        )

        # Low threshold should return at least as many results as high threshold
        assert len(result_low_threshold.chunks) >= len(result_high_threshold.chunks)

    def test_retrieve_context_results_ordered_by_similarity(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that results are ordered by similarity score (descending)."""
        collection_name = "test-agent-ordering"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve context
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="Python programming language",
            top_k=3,
            min_similarity=0.0
        )

        # Verify results are ordered by similarity (descending)
        if len(result.chunks) > 1:
            for i in range(len(result.chunks) - 1):
                assert result.chunks[i].similarity_score >= result.chunks[i + 1].similarity_score

    def test_retrieve_context_includes_metadata(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that retrieved chunks include all metadata."""
        collection_name = "test-agent-metadata"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve context
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="programming",
            top_k=1,
            min_similarity=0.0
        )

        # Verify metadata is preserved
        assert len(result.chunks) > 0
        retrieved_chunk = result.chunks[0].chunk
        assert retrieved_chunk.source_type in ["web", "database"]
        assert retrieved_chunk.source_identifier is not None
        assert isinstance(retrieved_chunk.chunk_index, int)
        assert isinstance(retrieved_chunk.metadata, dict)

    def test_retrieve_context_with_various_query_types(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test retrieval with various types of queries."""
        collection_name = "test-agent-queries"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Test different query types
        queries = [
            "Python",  # Single word
            "What is machine learning?",  # Question
            "programming language features",  # Multiple words
            "AI and ML",  # Abbreviations
        ]

        for query in queries:
            result = context_retriever.retrieve_context(
                collection_name=collection_name,
                query=query,
                top_k=3,
                min_similarity=0.0
            )

            assert isinstance(result, RetrievalResult)
            assert result.query == query
            assert isinstance(result.chunks, list)

    def test_retrieve_context_timing(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that retrieval time is measured and reasonable."""
        collection_name = "test-agent-timing"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve context
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="test query",
            top_k=5
        )

        # Verify timing is recorded and reasonable
        assert result.retrieval_time_ms > 0
        assert result.retrieval_time_ms < 10000  # Should be less than 10 seconds

    def test_retrieve_context_with_special_characters_in_query(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that queries with special characters are handled correctly."""
        collection_name = "test-agent-special"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Queries with special characters
        special_queries = [
            "What's Python?",
            "C++ vs Python",
            "Price: $100",
            "Email: test@example.com"
        ]

        for query in special_queries:
            result = context_retriever.retrieve_context(
                collection_name=collection_name,
                query=query,
                top_k=3,
                min_similarity=0.0
            )

            assert isinstance(result, RetrievalResult)
            assert result.query == query

    def test_retrieve_context_default_parameters(
        self, context_retriever, vector_store, embedding_generator, sample_chunks
    ):
        """Test that default parameters work correctly."""
        collection_name = "test-agent-defaults"

        # Create collection and add documents
        vector_store.create_collection(collection_name, 384)
        embeddings = embedding_generator.generate_embeddings_batch(
            [chunk.text for chunk in sample_chunks]
        )
        vector_store.add_documents(collection_name, sample_chunks, embeddings)

        # Retrieve with default parameters (top_k=5, min_similarity=0.3)
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query="programming"
        )

        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) <= 5  # Default top_k
        # All results should meet default min_similarity threshold
        for search_result in result.chunks:
            assert search_result.similarity_score >= 0.3
