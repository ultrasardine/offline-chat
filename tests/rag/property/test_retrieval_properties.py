"""
Property-based tests for context retrieval.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.rag.models import DocumentChunk
from offline_chat.rag.vector_store import VectorStore


# Hypothesis strategies for generating test data
@st.composite
def document_chunk_strategy(draw):
    """Generate a random DocumentChunk."""
    text = draw(st.text(min_size=1, max_size=500))
    source_type = draw(st.sampled_from(["web", "database"]))
    source_identifier = draw(st.text(min_size=1, max_size=100))
    chunk_index = draw(st.integers(min_value=0, max_value=1000))

    # Generate metadata with various types
    # Avoid very small floats that lose precision in ChromaDB
    metadata = {}
    num_metadata_fields = draw(st.integers(min_value=0, max_value=5))
    for i in range(num_metadata_fields):
        key = f"field_{i}"
        value_type = draw(st.sampled_from(["str", "int", "float", "bool"]))
        if value_type == "str":
            metadata[key] = draw(st.text(max_size=50))
        elif value_type == "int":
            metadata[key] = draw(st.integers(min_value=-1000000, max_value=1000000))
        elif value_type == "float":
            # Use reasonable float range to avoid precision issues
            metadata[key] = draw(st.floats(
                min_value=-1e6,
                max_value=1e6,
                allow_nan=False,
                allow_infinity=False
            ))
        else:
            metadata[key] = draw(st.booleans())

    return DocumentChunk(
        text=text,
        source_type=source_type,
        source_identifier=source_identifier,
        chunk_index=chunk_index,
        metadata=metadata
    )


@pytest.mark.property_test
class TestRetrievalProperties:
    """Property-based tests for context retrieval."""

    @given(
        chunks=st.lists(
            document_chunk_strategy(),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_vector_store_round_trip(self, chunks):
        """
        **Validates: Requirements 2.5, 7.5**

        Property 6: Vector Store Round-Trip

        For any set of document chunks with embeddings, storing them in the vector store
        then retrieving by exact match should return chunks with identical text and metadata.
        """
        # Create temporary directory for this test
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create vector store
            vector_store = VectorStore(temp_dir)
            collection_name = "test-agent"
            embedding_dim = 384

            # Create collection
            vector_store.create_collection(collection_name, embedding_dim)

            # Make chunks unique by modifying source_identifier to include index
            # This ensures ChromaDB IDs are unique
            unique_chunks = []
            for i, chunk in enumerate(chunks):
                unique_chunk = DocumentChunk(
                    text=chunk.text,
                    source_type=chunk.source_type,
                    source_identifier=f"{chunk.source_identifier}_unique_{i}",
                    chunk_index=chunk.chunk_index,
                    metadata=chunk.metadata
                )
                unique_chunks.append(unique_chunk)

            # Generate embeddings for each chunk (using unique embeddings for exact matching)
            embeddings = []
            for i, chunk in enumerate(unique_chunks):
                # Create a unique embedding for each chunk
                embedding = [float(i)] * embedding_dim
                embeddings.append(embedding)

            # Store chunks in vector store
            vector_store.add_documents(collection_name, unique_chunks, embeddings)

            # Retrieve each chunk by searching with its exact embedding
            for i, (original_chunk, embedding) in enumerate(zip(unique_chunks, embeddings)):
                # Search with the exact embedding used for this chunk
                results = vector_store.search(
                    collection_name,
                    embedding,
                    top_k=1,
                    min_similarity=0.0  # No threshold to ensure we get results
                )

                # Should get at least one result
                assert len(results) > 0, f"No results found for chunk {i}"

                # The top result should be our chunk
                retrieved_chunk = results[0].chunk

                # Verify text is identical
                assert retrieved_chunk.text == original_chunk.text, \
                    f"Text mismatch: expected '{original_chunk.text}', got '{retrieved_chunk.text}'"

                # Verify source_type is identical
                assert retrieved_chunk.source_type == original_chunk.source_type, \
                    f"Source type mismatch: expected '{original_chunk.source_type}', got '{retrieved_chunk.source_type}'"

                # Verify source_identifier is identical
                assert retrieved_chunk.source_identifier == original_chunk.source_identifier, \
                    f"Source identifier mismatch: expected '{original_chunk.source_identifier}', got '{retrieved_chunk.source_identifier}'"

                # Verify chunk_index is identical
                assert retrieved_chunk.chunk_index == original_chunk.chunk_index, \
                    f"Chunk index mismatch: expected {original_chunk.chunk_index}, got {retrieved_chunk.chunk_index}"

                # Verify metadata is identical (with tolerance for float precision)
                for key in original_chunk.metadata:
                    assert key in retrieved_chunk.metadata, \
                        f"Metadata key '{key}' missing in retrieved chunk"

                    original_value = original_chunk.metadata[key]
                    retrieved_value = retrieved_chunk.metadata[key]

                    if isinstance(original_value, float):
                        # Use approximate equality for floats due to ChromaDB precision
                        assert abs(original_value - retrieved_value) < 1e-6 or \
                               abs(original_value - retrieved_value) / max(abs(original_value), 1e-10) < 1e-6, \
                            f"Metadata float value mismatch for key '{key}': expected {original_value}, got {retrieved_value}"
                    else:
                        assert retrieved_value == original_value, \
                            f"Metadata value mismatch for key '{key}': expected {original_value}, got {retrieved_value}"

                # Verify no extra metadata keys
                assert set(retrieved_chunk.metadata.keys()) == set(original_chunk.metadata.keys()), \
                    f"Metadata keys mismatch: expected {set(original_chunk.metadata.keys())}, got {set(retrieved_chunk.metadata.keys())}"
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    @given(
        num_chunks=st.integers(min_value=0, max_value=50),
        top_k=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=20, deadline=None)
    def test_top_k_retrieval_limit(self, num_chunks, top_k):
        """
        **Validates: Requirements 4.2**

        Property 10: Top-K Retrieval Limit

        For any query and vector store with N chunks, retrieving top-k results
        should return at most min(k, N) results.
        """
        # Create temporary directory for this test
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create vector store
            vector_store = VectorStore(temp_dir)
            collection_name = "test-agent-topk"
            embedding_dim = 384

            # Create collection
            vector_store.create_collection(collection_name, embedding_dim)

            # Generate N chunks with unique embeddings
            chunks = []
            embeddings = []
            for i in range(num_chunks):
                chunk = DocumentChunk(
                    text=f"Test document chunk {i}",
                    source_type="web",
                    source_identifier=f"http://example.com/doc{i}",
                    chunk_index=i,
                    metadata={"doc_id": i}
                )
                chunks.append(chunk)

                # Create a unique embedding for each chunk
                embedding = [float(i * 10 + j) for j in range(embedding_dim)]
                embeddings.append(embedding)

            # Add chunks to vector store (only if we have chunks)
            if num_chunks > 0:
                vector_store.add_documents(collection_name, chunks, embeddings)

            # Create a query embedding
            query_embedding = [0.5] * embedding_dim

            # Search with top_k parameter
            results = vector_store.search(
                collection_name,
                query_embedding,
                top_k=top_k,
                min_similarity=0.0  # No threshold to test pure top-k behavior
            )

            # Verify the number of results is at most min(k, N)
            expected_max_results = min(top_k, num_chunks)
            assert len(results) <= expected_max_results, \
                f"Expected at most {expected_max_results} results, but got {len(results)}"

            # Additional verification: results should not exceed the number of chunks
            assert len(results) <= num_chunks, \
                f"Number of results ({len(results)}) exceeds number of chunks ({num_chunks})"

            # Additional verification: results should not exceed top_k
            assert len(results) <= top_k, \
                f"Number of results ({len(results)}) exceeds top_k ({top_k})"
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

    @given(
        num_chunks=st.integers(min_value=2, max_value=30),
        top_k=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=20, deadline=None)
    def test_search_results_ordering(self, num_chunks, top_k):
        """
        **Validates: Requirements 4.3**

        Property 11: Search Results Ordering

        For any search results returned by the context retriever, the results should be
        ordered by similarity score in descending order (highest similarity first).
        """
        from offline_chat.rag.context_retriever import ContextRetriever
        from offline_chat.rag.embedding_generator import EmbeddingGenerator

        # Create temporary directory for this test
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create vector store and embedding generator
            vector_store = VectorStore(temp_dir)
            embedding_generator = EmbeddingGenerator()
            context_retriever = ContextRetriever(vector_store, embedding_generator)

            collection_name = "test-agent-ordering"
            embedding_dim = embedding_generator.get_embedding_dimension()

            # Create collection
            vector_store.create_collection(collection_name, embedding_dim)

            # Generate N chunks with real embeddings
            chunks = []
            embeddings = []
            for i in range(num_chunks):
                # Create chunks with varying content to get different similarity scores
                chunk = DocumentChunk(
                    text=f"Document about topic {i % 5}. Content variation {i}. Additional text for diversity.",
                    source_type="web",
                    source_identifier=f"http://example.com/doc{i}",
                    chunk_index=i,
                    metadata={"doc_id": i}
                )
                chunks.append(chunk)

                # Generate real embeddings for each chunk
                embedding = embedding_generator.generate_embedding(chunk.text)
                embeddings.append(embedding)

            # Add chunks to vector store
            vector_store.add_documents(collection_name, chunks, embeddings)

            # Create a query that will match some documents better than others
            query = "topic 2 content"

            # Retrieve context using the context retriever
            retrieval_result = context_retriever.retrieve_context(
                collection_name=collection_name,
                query=query,
                top_k=top_k,
                min_similarity=0.0  # No threshold to test pure ordering
            )

            # Get the search results
            search_results = retrieval_result.chunks

            # If we have results, verify they are ordered by similarity score (descending)
            if len(search_results) > 1:
                for i in range(len(search_results) - 1):
                    current_score = search_results[i].similarity_score
                    next_score = search_results[i + 1].similarity_score

                    # Current score should be >= next score (descending order)
                    assert current_score >= next_score, \
                        f"Results not ordered correctly: result[{i}].similarity_score ({current_score}) " \
                        f"< result[{i+1}].similarity_score ({next_score})"

            # Additional verification: verify rank field is also in ascending order
            if len(search_results) > 1:
                for i in range(len(search_results) - 1):
                    current_rank = search_results[i].rank
                    next_rank = search_results[i + 1].rank

                    # Rank should be in ascending order (0, 1, 2, ...)
                    assert current_rank < next_rank, \
                        f"Rank not ordered correctly: result[{i}].rank ({current_rank}) " \
                        f">= result[{i+1}].rank ({next_rank})"
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
