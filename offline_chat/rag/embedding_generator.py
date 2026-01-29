"""
Embedding generator for converting text to vector embeddings using sentence-transformers.
"""

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Generate vector embeddings for text using local sentence-transformers models.

    This class provides methods for generating embeddings for single texts or batches,
    using a configurable sentence-transformers model that runs entirely locally.

    The model is loaded lazily on first use and cached in memory for subsequent calls.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with specified sentence-transformers model.

        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        """
        Load the sentence-transformers model lazily.

        Returns:
            Loaded SentenceTransformer model
        """
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty or None
        """
        if not text:
            raise ValueError("Text cannot be empty or None")

        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(
        self,
        texts: list[str],
        show_progress: bool = False
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        This method processes texts in batch for better performance compared to
        generating embeddings individually.

        Args:
            texts: List of input texts
            show_progress: If True, display a progress bar during encoding (default: False)

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty or contains empty strings
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        if any(not text for text in texts):
            raise ValueError("Texts list cannot contain empty strings")

        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=show_progress)
        return [embedding.tolist() for embedding in embeddings]

    def get_embedding_dimension(self) -> int:
        """
        Return the dimensionality of embeddings produced by this model.

        Returns:
            Integer dimension of the embedding vectors
        """
        model = self._load_model()
        return model.get_sentence_embedding_dimension()
