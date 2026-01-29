"""
Context retriever for retrieving relevant context from the vector store.

This module coordinates the EmbeddingGenerator and VectorStore to retrieve
relevant context for user queries through similarity search.
"""

import time

from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import RetrievalResult
from offline_chat.rag.vector_store import VectorStore


class ContextRetriever:
    """
    Retrieve relevant context for queries from the vector store.

    This class coordinates the EmbeddingGenerator and VectorStore to:
    1. Generate embeddings for user queries
    2. Search the vector store for similar content
    3. Return ordered results with similarity scores
    """

    def __init__(self, vector_store: VectorStore, embedding_generator: EmbeddingGenerator):
        """
        Initialize with vector store and embedding generator.

        Args:
            vector_store: VectorStore instance for similarity search
            embedding_generator: EmbeddingGenerator instance for query embedding
        """
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

    def retrieve_context(
        self, collection_name: str, query: str, top_k: int = 5, min_similarity: float = 0.3
    ) -> RetrievalResult:
        """
        Retrieve relevant context for a query.

        This method:
        1. Generates an embedding for the query
        2. Searches the vector store for similar chunks
        3. Returns results ordered by similarity score (descending)
        4. Returns empty results if no chunks meet the minimum similarity threshold

        Args:
            collection_name: Agent's vector collection name
            query: User's query text
            top_k: Number of chunks to retrieve (default: 5)
            min_similarity: Minimum similarity threshold (default: 0.3)

        Returns:
            RetrievalResult with chunks ordered by similarity score and metadata

        Raises:
            ValueError: If query is empty or None
        """
        if not query:
            raise ValueError("Query cannot be empty or None")

        # Start timing
        start_time = time.time()

        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)

        # Search vector store for similar chunks
        search_results = self.vector_store.search(
            collection_name=collection_name, query_embedding=query_embedding, top_k=top_k, min_similarity=min_similarity
        )

        # Results are already ordered by similarity score (descending) from VectorStore
        # The VectorStore.search method returns results ordered by rank

        # Calculate retrieval time
        retrieval_time_ms = (time.time() - start_time) * 1000

        # Return retrieval result
        return RetrievalResult(
            chunks=search_results, query=query, total_results=len(search_results), retrieval_time_ms=retrieval_time_ms
        )
