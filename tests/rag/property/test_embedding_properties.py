"""
Property-based tests for embedding generation.
"""

import pytest
from hypothesis import given, strategies as st, settings
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import DocumentChunk


# Strategy for generating valid text strings
text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=200
).filter(lambda x: x.strip())  # Ensure non-empty after stripping


# Strategy for generating DocumentChunk objects
@st.composite
def document_chunk_strategy(draw):
    """Generate a valid DocumentChunk."""
    text = draw(text_strategy)
    source_type = draw(st.sampled_from(["web", "database"]))
    source_identifier = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    chunk_index = draw(st.integers(min_value=0, max_value=1000))
    
    return DocumentChunk(
        text=text,
        source_type=source_type,
        source_identifier=source_identifier,
        chunk_index=chunk_index,
        metadata={"source_identifier": source_identifier}
    )


@pytest.fixture(scope="module")
def embedding_generator():
    """Shared embedding generator instance for all tests to avoid reloading model."""
    return EmbeddingGenerator()


@pytest.mark.property_test
class TestEmbeddingProperties:
    """Property-based tests for embedding generation."""
    
    @given(texts=st.lists(text_strategy, min_size=1, max_size=10))
    @settings(max_examples=20, deadline=None)
    def test_batch_embedding_consistency(self, embedding_generator, texts):
        """
        **Validates: Requirements 8.4**
        
        Property 17: Batch Embedding Consistency
        
        For any list of texts, generating embeddings in batch should produce
        the same results as generating embeddings individually for each text.
        
        This property ensures that the batch processing optimization doesn't
        change the actual embedding values compared to individual processing.
        """
        # Generate embeddings in batch
        batch_embeddings = embedding_generator.generate_embeddings_batch(texts)
        
        # Generate embeddings individually
        individual_embeddings = [embedding_generator.generate_embedding(text) for text in texts]
        
        # Verify same number of embeddings
        assert len(batch_embeddings) == len(individual_embeddings) == len(texts)
        
        # Verify each embedding matches
        for i, (batch_emb, individual_emb) in enumerate(zip(batch_embeddings, individual_embeddings)):
            assert len(batch_emb) == len(individual_emb), \
                f"Embedding {i}: dimension mismatch"
            
            # Compare embeddings element-wise with small tolerance for floating point
            for j, (b_val, i_val) in enumerate(zip(batch_emb, individual_emb)):
                assert abs(b_val - i_val) < 1e-6, \
                    f"Embedding {i}, element {j}: batch={b_val}, individual={i_val}"
    
    @given(query=text_strategy)
    @settings(max_examples=20, deadline=None)
    def test_query_embedding_generation(self, embedding_generator, query):
        """
        **Validates: Requirements 4.1**
        
        Property 9: Query Embedding Generation
        
        For any non-empty query string, the embedding generator should produce
        a vector of the expected dimensionality.
        
        This property ensures that query embeddings are always generated with
        the correct dimension, which is critical for vector similarity search.
        """
        # Get the expected dimension for this model
        expected_dimension = embedding_generator.get_embedding_dimension()
        
        # Generate embedding for the query
        embedding = embedding_generator.generate_embedding(query)
        
        # Verify embedding is a list
        assert isinstance(embedding, list), \
            f"Embedding should be a list, got {type(embedding)}"
        
        # Verify embedding has expected dimension
        assert len(embedding) == expected_dimension, \
            f"Embedding dimension mismatch: expected {expected_dimension}, got {len(embedding)}"
        
        # Verify all elements are floats
        assert all(isinstance(val, float) for val in embedding), \
            "All embedding values should be floats"
        
        # Verify no NaN or infinite values
        assert all(not (val != val or abs(val) == float('inf')) for val in embedding), \
            "Embedding should not contain NaN or infinite values"
    
    @given(chunks=st.lists(document_chunk_strategy(), min_size=1, max_size=20))
    @settings(max_examples=20, deadline=None)
    def test_embedding_count_matches_chunk_count(self, embedding_generator, chunks):
        """
        **Validates: Requirements 2.4, 3.4**
        
        Property 5: Embedding Count Matches Chunk Count
        
        For any list of document chunks, generating embeddings should produce
        exactly one embedding vector per chunk.
        
        This property ensures that the embedding generation process maintains
        a 1:1 correspondence between input chunks and output embeddings, which
        is critical for correctly storing and retrieving document chunks in the
        vector store.
        """
        # Extract text from all chunks
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings for all chunk texts
        embeddings = embedding_generator.generate_embeddings_batch(texts)
        
        # Verify the count matches exactly
        assert len(embeddings) == len(chunks), \
            f"Embedding count mismatch: expected {len(chunks)} embeddings for {len(chunks)} chunks, got {len(embeddings)}"
        
        # Verify each embedding has the correct dimension
        expected_dimension = embedding_generator.get_embedding_dimension()
        for i, embedding in enumerate(embeddings):
            assert len(embedding) == expected_dimension, \
                f"Embedding {i} has incorrect dimension: expected {expected_dimension}, got {len(embedding)}"
        
        # Verify all embeddings are valid (no NaN or infinite values)
        for i, embedding in enumerate(embeddings):
            assert all(not (val != val or abs(val) == float('inf')) for val in embedding), \
                f"Embedding {i} contains NaN or infinite values"
