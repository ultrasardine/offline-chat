"""
Unit tests for EmbeddingGenerator.
"""

import pytest

from offline_chat.rag.embedding_generator import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Unit tests for the EmbeddingGenerator class."""

    def test_model_initialization(self):
        """Test that the model can be initialized with default and custom model names."""
        # Default model
        generator = EmbeddingGenerator()
        assert generator.model_name == "all-MiniLM-L6-v2"
        assert generator._model is None  # Model not loaded yet

        # Custom model
        custom_generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
        assert custom_generator.model_name == "all-MiniLM-L6-v2"

    def test_generate_embedding_single_text(self):
        """Test generating embedding for a single text."""
        generator = EmbeddingGenerator()
        text = "This is a test sentence."

        embedding = generator.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
        assert generator._model is not None  # Model should be loaded now

    def test_generate_embedding_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        generator = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Text cannot be empty or None"):
            generator.generate_embedding("")

        with pytest.raises(ValueError, match="Text cannot be empty or None"):
            generator.generate_embedding(None)

    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts."""
        generator = EmbeddingGenerator()
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence."
        ]

        embeddings = generator.generate_embeddings_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)
        assert all(isinstance(x, float) for emb in embeddings for x in emb)

    def test_generate_embeddings_batch_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        generator = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            generator.generate_embeddings_batch([])

    def test_generate_embeddings_batch_with_empty_string_raises_error(self):
        """Test that list containing empty strings raises ValueError."""
        generator = EmbeddingGenerator()

        with pytest.raises(ValueError, match="Texts list cannot contain empty strings"):
            generator.generate_embeddings_batch(["Valid text", "", "Another valid text"])

    def test_get_embedding_dimension(self):
        """Test retrieving embedding dimension."""
        generator = EmbeddingGenerator()

        dimension = generator.get_embedding_dimension()

        assert isinstance(dimension, int)
        assert dimension > 0
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        assert dimension == 384

    def test_embedding_dimension_consistency(self):
        """Test that all embeddings have the same dimension."""
        generator = EmbeddingGenerator()

        expected_dim = generator.get_embedding_dimension()

        # Single embedding
        single_emb = generator.generate_embedding("Test text")
        assert len(single_emb) == expected_dim

        # Batch embeddings
        batch_embs = generator.generate_embeddings_batch(["Text 1", "Text 2", "Text 3"])
        assert all(len(emb) == expected_dim for emb in batch_embs)

    def test_model_caching(self):
        """Test that the model is loaded once and cached."""
        generator = EmbeddingGenerator()

        # First call loads the model
        generator.generate_embedding("First call")
        first_model = generator._model
        assert first_model is not None

        # Second call reuses the cached model
        generator.generate_embedding("Second call")
        second_model = generator._model
        assert second_model is first_model  # Same object reference

    def test_embedding_with_special_characters(self):
        """Test that embeddings can be generated for text with special characters."""
        generator = EmbeddingGenerator()

        # Text with various special characters
        special_texts = [
            "Hello! How are you?",
            "Price: $100.50",
            "Email: test@example.com",
            "Math: 2 + 2 = 4",
            "Unicode: café, naïve, 日本語"
        ]

        for text in special_texts:
            embedding = generator.generate_embedding(text)
            assert isinstance(embedding, list)
            assert len(embedding) == generator.get_embedding_dimension()
            assert all(isinstance(x, float) for x in embedding)

    def test_embedding_with_long_text(self):
        """Test that embeddings can be generated for very long text."""
        generator = EmbeddingGenerator()

        # Create a long text (multiple sentences)
        long_text = " ".join([f"This is sentence number {i}." for i in range(100)])

        embedding = generator.generate_embedding(long_text)

        assert isinstance(embedding, list)
        assert len(embedding) == generator.get_embedding_dimension()
        assert all(isinstance(x, float) for x in embedding)

    def test_batch_vs_single_consistency(self):
        """Test that batch and single embedding generation produce the same results."""
        generator = EmbeddingGenerator()

        test_texts = ["First text", "Second text", "Third text"]

        # Generate embeddings individually
        single_embeddings = [generator.generate_embedding(text) for text in test_texts]

        # Generate embeddings in batch
        batch_embeddings = generator.generate_embeddings_batch(test_texts)

        # Compare results (should be very close, allowing for small floating point differences)
        assert len(single_embeddings) == len(batch_embeddings)
        for single, batch in zip(single_embeddings, batch_embeddings):
            assert len(single) == len(batch)
            # Check that embeddings are very similar (within small tolerance)
            for s_val, b_val in zip(single, batch):
                assert abs(s_val - b_val) < 1e-6

    def test_model_loading_on_dimension_query(self):
        """Test that querying dimension loads the model if not already loaded."""
        generator = EmbeddingGenerator()

        # Model should not be loaded initially
        assert generator._model is None

        # Querying dimension should load the model
        dimension = generator.get_embedding_dimension()
        assert generator._model is not None
        assert dimension == 384

    def test_multiple_generators_independent(self):
        """Test that multiple generator instances are independent."""
        generator1 = EmbeddingGenerator()
        generator2 = EmbeddingGenerator()

        # Load model in first generator
        generator1.generate_embedding("Test")

        # Second generator should have its own model instance
        assert generator1._model is not None
        assert generator2._model is None

        # Load model in second generator
        generator2.generate_embedding("Test")
        assert generator2._model is not None

        # They should be different instances
        assert generator1._model is not generator2._model
