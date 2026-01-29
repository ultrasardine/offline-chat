"""
Vector store for persisting and searching vector embeddings using ChromaDB.
"""

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from .models import DocumentChunk, SearchResult


class VectorStore:
    """
    Persist and search vector embeddings using ChromaDB.

    This class provides methods for creating collections, adding documents with embeddings,
    and performing similarity searches.
    """

    def __init__(self, data_dir: Path):
        """
        Initialize ChromaDB client with persistent storage.

        Args:
            data_dir: Directory for persistent storage
        """
        self.data_dir = data_dir
        self.chroma_dir = data_dir / "chroma"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

    def create_collection(self, agent_name: str, embedding_dimension: int) -> None:
        """
        Create a new collection for an agent's knowledge base.

        Args:
            agent_name: Name of the agent
            embedding_dimension: Dimensionality of embeddings (not used by ChromaDB but kept for API consistency)
        """
        # ChromaDB automatically handles embedding dimensions
        # If collection exists, get_or_create_collection will return it
        self.client.get_or_create_collection(
            name=agent_name,
            metadata={"embedding_dimension": embedding_dimension}
        )

    def add_documents(
        self,
        collection_name: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]]
    ) -> None:
        """
        Add document chunks with embeddings to a collection.

        Args:
            collection_name: Name of the collection
            chunks: Document chunks with text and metadata
            embeddings: Corresponding embedding vectors
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})"
            )

        if not chunks:
            return  # Nothing to add

        collection = self.client.get_collection(name=collection_name)

        # Prepare data for ChromaDB
        ids = [f"{chunk.source_identifier}_{chunk.chunk_index}" for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "source_type": chunk.source_type,
                "source_identifier": chunk.source_identifier,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata
            }
            for chunk in chunks
        ]

        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> list[SearchResult]:
        """
        Search for similar documents in a collection.

        Args:
            collection_name: Name of the collection to search
            query_embedding: Query vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1, where 1 is most similar)

        Returns:
            List of search results with text, metadata, and similarity scores
        """
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, return empty results
            return []

        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # ChromaDB returns distances (lower is more similar)
        # Convert to similarity scores (higher is more similar)
        # Using cosine distance: similarity = 1 - distance
        search_results = []

        if not results['ids'] or not results['ids'][0]:
            return []

        for rank, (doc_id, document, metadata, distance) in enumerate(
            zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ):
            # Convert distance to similarity score
            # ChromaDB uses L2 (Euclidean) distance by default
            # For normalized embeddings, we can approximate cosine similarity
            similarity_score = 1.0 / (1.0 + distance)

            # Filter by minimum similarity threshold
            if similarity_score < min_similarity:
                continue

            # Reconstruct DocumentChunk from metadata
            chunk = DocumentChunk(
                text=document,
                source_type=metadata['source_type'],
                source_identifier=metadata['source_identifier'],
                chunk_index=metadata['chunk_index'],
                metadata={k: v for k, v in metadata.items()
                         if k not in ['source_type', 'source_identifier', 'chunk_index']}
            )

            search_results.append(
                SearchResult(
                    chunk=chunk,
                    similarity_score=similarity_score,
                    rank=rank
                )
            )

        return search_results

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection and all its data.

        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, nothing to delete
            pass

    def is_collection_corrupted(self, collection_name: str) -> tuple[bool, str | None]:
        """
        Check if a collection is corrupted.

        A collection is considered corrupted if:
        - It exists but cannot be accessed
        - Basic operations (get, query) fail with unexpected errors
        - The collection metadata is inconsistent

        Args:
            collection_name: Name of the collection to check

        Returns:
            Tuple of (is_corrupted, error_message)
            - is_corrupted: True if collection is corrupted, False otherwise
            - error_message: Description of the corruption if detected, None otherwise
        """
        try:
            # Try to get the collection
            collection = self.client.get_collection(name=collection_name)

            # Try to perform a basic operation (get with limit 1)
            # This will fail if the collection is corrupted
            collection.get(limit=1, include=['embeddings', 'documents', 'metadatas'])

            # If we get here, collection is healthy
            return False, None

        except ValueError as e:
            # Collection doesn't exist - not corrupted, just missing
            error_str = str(e).lower()
            if "does not exist" in error_str or "not found" in error_str:
                return False, None
            # Other ValueError might indicate corruption
            return True, f"Collection validation error: {str(e)}"

        except Exception as e:
            # Check if this is just a "collection doesn't exist" error
            error_str = str(e).lower()
            if "does not exist" in error_str or "not found" in error_str:
                return False, None

            # Any other exception during basic operations indicates corruption
            error_msg = str(e)

            # Check for common corruption indicators
            corruption_indicators = [
                "sqlite",
                "database",
                "corrupt",
                "integrity",
                "malformed",
                "disk i/o error",
                "unable to open",
            ]

            if any(indicator in error_msg.lower() for indicator in corruption_indicators):
                return True, f"Collection appears corrupted: {error_msg}"

            # Generic error that might indicate corruption
            return True, f"Collection access error: {error_msg}"

    def rebuild_collection(
        self,
        collection_name: str,
        embedding_dimension: int,
        force: bool = False
    ) -> tuple[bool, str]:
        """
        Rebuild a corrupted collection.

        This method attempts to recover from collection corruption by:
        1. Deleting the corrupted collection
        2. Creating a fresh collection with the same name

        Note: This will lose all data in the collection. The collection
        will need to be re-indexed from the original knowledge sources.

        Args:
            collection_name: Name of the collection to rebuild
            embedding_dimension: Dimensionality of embeddings for the new collection
            force: If True, rebuild even if collection appears healthy

        Returns:
            Tuple of (success, message)
            - success: True if rebuild succeeded, False otherwise
            - message: Description of the result
        """
        try:
            # Check if collection is corrupted (unless force=True)
            if not force:
                is_corrupted, error_msg = self.is_collection_corrupted(collection_name)
                if not is_corrupted:
                    return False, f"Collection '{collection_name}' is not corrupted. Use force=True to rebuild anyway."

            # Delete the corrupted collection
            # We need to be more aggressive here - delete even if it fails
            try:
                self.client.delete_collection(name=collection_name)
            except Exception:
                # Log but continue - we'll try to create a new one anyway
                pass

            # Create a fresh collection
            self.create_collection(collection_name, embedding_dimension)

            return True, f"Collection '{collection_name}' successfully rebuilt. Re-index knowledge sources to restore data."

        except Exception as e:
            return False, f"Failed to rebuild collection '{collection_name}': {str(e)}"

    def get_collection_info(self, collection_name: str) -> dict[str, Any] | None:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information, or None if collection doesn't exist
            Contains: name, count (number of documents), metadata
        """
        try:
            collection = self.client.get_collection(name=collection_name)

            # Get document count
            count = collection.count()

            # Get metadata
            metadata = collection.metadata or {}

            return {
                "name": collection_name,
                "count": count,
                "metadata": metadata,
            }

        except Exception:
            # Collection doesn't exist or is inaccessible
            return None
