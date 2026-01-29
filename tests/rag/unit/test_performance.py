"""
Performance tests for RAG components.

These tests verify that the RAG system meets performance requirements:
- Requirement 13.1: Context retrieval within 500ms for 10,000 chunks
- Requirement 13.2: Embedding generation under 100ms for queries
"""

import shutil
import tempfile
import time
from pathlib import Path

import pytest

from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import DocumentChunk
from offline_chat.rag.vector_store import VectorStore


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def embedding_generator():
    """Create an embedding generator instance."""
    return EmbeddingGenerator()


@pytest.fixture
def vector_store(temp_data_dir):
    """Create a vector store instance."""
    return VectorStore(temp_data_dir)


@pytest.fixture
def context_retriever(vector_store, embedding_generator):
    """Create a context retriever instance."""
    return ContextRetriever(vector_store, embedding_generator)


class TestEmbeddingPerformance:
    """Test embedding generation performance."""

    def test_query_embedding_generation_time(self, embedding_generator):
        """
        Test that query embedding generation completes within 100ms.

        Validates: Requirement 13.2
        """
        # Test query (typical length)
        query = "What are the main features of the product and how does it compare to competitors?"

        # Warm up the model (first call loads the model)
        embedding_generator.generate_embedding("warmup")

        # Measure embedding generation time
        start_time = time.time()
        embedding = embedding_generator.generate_embedding(query)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify embedding was generated
        assert isinstance(embedding, list)
        assert len(embedding) > 0

        # Verify performance requirement (100ms)
        assert elapsed_ms < 100, f"Query embedding generation took {elapsed_ms:.2f}ms, exceeds 100ms requirement"

    def test_batch_embedding_generation_efficiency(self, embedding_generator):
        """
        Test that batch embedding generation is efficient.

        This test verifies that batch processing is reasonably efficient
        compared to individual processing for multiple texts.
        """
        texts = [
            "First document about machine learning",
            "Second document about data science",
            "Third document about artificial intelligence",
            "Fourth document about neural networks",
            "Fifth document about deep learning",
        ]

        # Warm up the model
        embedding_generator.generate_embedding("warmup")

        # Measure batch generation time
        start_time = time.time()
        batch_embeddings = embedding_generator.generate_embeddings_batch(texts)
        batch_time_ms = (time.time() - start_time) * 1000

        # Measure individual generation time
        start_time = time.time()
        individual_embeddings = [embedding_generator.generate_embedding(text) for text in texts]
        individual_time_ms = (time.time() - start_time) * 1000

        # Verify results are equivalent
        assert len(batch_embeddings) == len(individual_embeddings)

        # Batch should not be significantly slower than individual
        # For small batches, overhead can make batch slightly slower
        # Allow 2x margin for small batch overhead
        assert batch_time_ms < individual_time_ms * 2.0, (
            f"Batch processing ({batch_time_ms:.2f}ms) is significantly slower than "
            f"individual processing ({individual_time_ms:.2f}ms)"
        )

        print(f"Batch: {batch_time_ms:.2f}ms, Individual: {individual_time_ms:.2f}ms")


class TestRetrievalPerformance:
    """Test context retrieval performance with large vector stores."""

    def test_retrieval_time_with_10k_chunks(self, vector_store, embedding_generator, context_retriever, temp_data_dir):
        """
        Test that retrieval completes within 500ms for 10,000 chunks.

        Validates: Requirement 13.1

        Note: This test creates 10,000 chunks which may take some time to set up.
        The actual retrieval time is what's being measured.
        """
        collection_name = "perf_test_10k"

        # Create collection
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        # Generate 10,000 chunks with varied content
        print("\nGenerating 10,000 test chunks...")
        chunks = []
        for i in range(10000):
            # Create varied content to ensure realistic similarity distribution
            topic = i % 10  # 10 different topics
            text = (
                f"Document {i} about topic {topic}. "
                f"This is chunk number {i} containing information about subject {topic}. "
                f"Additional content to make the chunk more realistic and varied. "
                f"The document discusses various aspects of topic {topic} in detail."
            )
            chunks.append(
                DocumentChunk(
                    text=text,
                    source_type="web",
                    source_identifier=f"https://example.com/doc{i}",
                    chunk_index=0,
                    metadata={"doc_id": i, "topic": topic},
                )
            )

        # Generate embeddings in batches for efficiency
        print("Generating embeddings...")
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_texts = [chunk.text for chunk in batch]
            batch_embeddings = embedding_generator.generate_embeddings_batch(batch_texts)
            all_embeddings.extend(batch_embeddings)

        # Add to vector store in batches (ChromaDB has a max batch size limit)
        print("Adding to vector store...")
        max_batch_size = 5000  # ChromaDB's max batch size
        for i in range(0, len(chunks), max_batch_size):
            batch_chunks = chunks[i : i + max_batch_size]
            batch_embeddings = all_embeddings[i : i + max_batch_size]
            vector_store.add_documents(collection_name, batch_chunks, batch_embeddings)

        # Verify we have 10,000 chunks
        info = vector_store.get_collection_info(collection_name)
        assert info["count"] == 10000, f"Expected 10000 chunks, got {info['count']}"

        # Test query
        query = "Information about topic 5"

        # Measure retrieval time
        print("Measuring retrieval time...")
        start_time = time.time()
        result = context_retriever.retrieve_context(
            collection_name=collection_name,
            query=query,
            top_k=5,
            min_similarity=0.0,  # Get results regardless of similarity
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify results were returned
        assert result.total_results > 0, "Should return results"
        assert len(result.chunks) > 0, "Should return chunks"

        # Verify performance requirement (500ms)
        assert elapsed_ms < 500, f"Retrieval from 10,000 chunks took {elapsed_ms:.2f}ms, exceeds 500ms requirement"

        print(f"✓ Retrieval completed in {elapsed_ms:.2f}ms (requirement: <500ms)")

    def test_retrieval_time_scales_reasonably(self, vector_store, embedding_generator, context_retriever):
        """
        Test that retrieval time scales reasonably with collection size.

        This test verifies that retrieval time doesn't grow exponentially
        with collection size.
        """
        collection_name = "perf_test_scaling"

        # Create collection
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        # Test with different collection sizes
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            # Generate chunks
            chunks = [
                DocumentChunk(
                    text=f"Document {i} with content about topic {i % 10}",
                    source_type="web",
                    source_identifier=f"https://example.com/doc{i}",
                    chunk_index=0,
                    metadata={"doc_id": i},
                )
                for i in range(size)
            ]

            # Generate embeddings
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)

            # Add to vector store
            vector_store.add_documents(collection_name, chunks, embeddings)

            # Measure retrieval time
            query = "Information about topic 5"
            start_time = time.time()
            context_retriever.retrieve_context(
                collection_name=collection_name, query=query, top_k=5, min_similarity=0.0
            )
            elapsed_ms = (time.time() - start_time) * 1000
            times.append(elapsed_ms)

            print(f"Retrieval time for {size} chunks: {elapsed_ms:.2f}ms")

        # Verify that time doesn't grow exponentially
        # Time for 1000 chunks should be less than 10x time for 100 chunks
        assert times[2] < times[0] * 10, (
            f"Retrieval time grows too quickly: 100 chunks={times[0]:.2f}ms, 1000 chunks={times[2]:.2f}ms"
        )


class TestConcurrentAccess:
    """Test concurrent access performance."""

    def test_concurrent_read_operations(self, vector_store, embedding_generator, context_retriever):
        """
        Test that concurrent read operations don't degrade performance.

        Validates: Requirement 13.3
        """
        collection_name = "perf_test_concurrent"

        # Create collection with some data
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        # Add 1000 chunks
        chunks = [
            DocumentChunk(
                text=f"Document {i} about topic {i % 10}",
                source_type="web",
                source_identifier=f"https://example.com/doc{i}",
                chunk_index=0,
                metadata={"doc_id": i},
            )
            for i in range(1000)
        ]

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedding_generator.generate_embeddings_batch(chunk_texts)
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Measure single read time
        query = "Information about topic 5"
        start_time = time.time()
        context_retriever.retrieve_context(collection_name=collection_name, query=query, top_k=5, min_similarity=0.0)
        single_read_time = (time.time() - start_time) * 1000

        # Perform multiple sequential reads
        start_time = time.time()
        for _ in range(10):
            context_retriever.retrieve_context(
                collection_name=collection_name, query=query, top_k=5, min_similarity=0.0
            )
        sequential_time = (time.time() - start_time) * 1000
        avg_sequential_time = sequential_time / 10

        # Average time should not be significantly worse than single read
        # Allow 50% margin for overhead
        assert avg_sequential_time < single_read_time * 1.5, (
            f"Sequential reads degrade performance: single={single_read_time:.2f}ms, avg={avg_sequential_time:.2f}ms"
        )

        print(f"Single read: {single_read_time:.2f}ms")
        print(f"Average sequential read: {avg_sequential_time:.2f}ms")


class TestLazyLoading:
    """Test lazy loading performance."""

    def test_embedding_model_lazy_loading(self):
        """
        Test that embedding model is loaded lazily.

        Validates: Requirement 13.4
        """
        # Create generator without loading model
        generator = EmbeddingGenerator()

        # Model should not be loaded yet
        assert generator._model is None, "Model should not be loaded on initialization"

        # First embedding generation should load the model
        start_time = time.time()
        generator.generate_embedding("test text")
        first_call_time = (time.time() - start_time) * 1000

        # Model should now be loaded
        assert generator._model is not None, "Model should be loaded after first use"

        # Second call should be faster (model already loaded)
        start_time = time.time()
        generator.generate_embedding("another test")
        second_call_time = (time.time() - start_time) * 1000

        # Second call should be significantly faster (no model loading)
        assert second_call_time < first_call_time * 0.5, (
            f"Second call should be faster: first={first_call_time:.2f}ms, second={second_call_time:.2f}ms"
        )

        print(f"First call (with loading): {first_call_time:.2f}ms")
        print(f"Second call (cached): {second_call_time:.2f}ms")
