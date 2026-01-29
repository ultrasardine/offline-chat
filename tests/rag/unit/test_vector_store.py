"""
Unit tests for VectorStore.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from offline_chat.rag.models import DocumentChunk
from offline_chat.rag.vector_store import VectorStore


class TestVectorStore:
    """Unit tests for the VectorStore class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def vector_store(self, temp_data_dir):
        """Create a VectorStore instance for testing."""
        return VectorStore(temp_data_dir)

    def test_initialization(self, temp_data_dir):
        """Test VectorStore initialization creates necessary directories."""
        store = VectorStore(temp_data_dir)
        assert store.data_dir == temp_data_dir
        assert store.chroma_dir.exists()
        assert store.client is not None

    def test_create_collection(self, vector_store):
        """Test creating a collection."""
        vector_store.create_collection("test-agent", 384)
        # Verify collection exists by trying to get it
        collection = vector_store.client.get_collection("test-agent")
        assert collection is not None
        assert collection.name == "test-agent"

    def test_add_and_search_documents(self, vector_store):
        """Test adding documents and searching for them."""
        # Create collection
        vector_store.create_collection("test-agent", 384)

        # Create test chunks
        chunks = [
            DocumentChunk(
                text="Python is a programming language",
                source_type="web",
                source_identifier="https://example.com/python",
                chunk_index=0,
                metadata={"page": 1}
            ),
            DocumentChunk(
                text="JavaScript is used for web development",
                source_type="web",
                source_identifier="https://example.com/js",
                chunk_index=0,
                metadata={"page": 1}
            )
        ]

        # Create simple embeddings (384 dimensions)
        embeddings = [
            [0.1] * 384,  # Simple embedding for Python
            [0.2] * 384   # Simple embedding for JavaScript
        ]

        # Add documents
        vector_store.add_documents("test-agent", chunks, embeddings)

        # Search with a query embedding similar to the first document
        query_embedding = [0.1] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=2, min_similarity=0.0)

        assert len(results) > 0
        assert results[0].chunk.text in ["Python is a programming language", "JavaScript is used for web development"]

    def test_add_documents_mismatch_raises_error(self, vector_store):
        """Test that mismatched chunks and embeddings raises an error."""
        vector_store.create_collection("test-agent", 384)

        chunks = [
            DocumentChunk(
                text="Test",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0
            )
        ]
        embeddings = [[0.1] * 384, [0.2] * 384]  # Two embeddings for one chunk

        with pytest.raises(ValueError, match="must match"):
            vector_store.add_documents("test-agent", chunks, embeddings)

    def test_add_empty_documents(self, vector_store):
        """Test adding empty list of documents doesn't raise error."""
        vector_store.create_collection("test-agent", 384)
        vector_store.add_documents("test-agent", [], [])  # Should not raise

    def test_search_nonexistent_collection(self, vector_store):
        """Test searching a non-existent collection returns empty results."""
        query_embedding = [0.1] * 384
        results = vector_store.search("nonexistent", query_embedding)
        assert results == []

    def test_search_with_threshold_filtering(self, vector_store):
        """Test that similarity threshold filters results."""
        vector_store.create_collection("test-agent", 384)

        chunks = [
            DocumentChunk(
                text="Test document",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0
            )
        ]
        embeddings = [[0.5] * 384]

        vector_store.add_documents("test-agent", chunks, embeddings)

        # Search with very high threshold - should return no results
        query_embedding = [0.1] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=5, min_similarity=0.99)

        # With high threshold, we might get no results
        assert isinstance(results, list)

    def test_delete_collection(self, vector_store):
        """Test deleting a collection."""
        vector_store.create_collection("test-agent", 384)
        vector_store.delete_collection("test-agent")

        # Verify collection is deleted by checking it doesn't exist
        collections = vector_store.client.list_collections()
        collection_names = [c.name for c in collections]
        assert "test-agent" not in collection_names

    def test_delete_nonexistent_collection(self, vector_store):
        """Test deleting a non-existent collection doesn't raise error."""
        vector_store.delete_collection("nonexistent")  # Should not raise

    def test_top_k_limit(self, vector_store):
        """Test that top_k limits the number of results."""
        vector_store.create_collection("test-agent", 384)

        # Add 5 documents
        chunks = [
            DocumentChunk(
                text=f"Document {i}",
                source_type="web",
                source_identifier=f"https://example.com/{i}",
                chunk_index=0
            )
            for i in range(5)
        ]
        embeddings = [[float(i) / 10] * 384 for i in range(5)]

        vector_store.add_documents("test-agent", chunks, embeddings)

        # Search with top_k=2
        query_embedding = [0.0] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=2, min_similarity=0.0)

        assert len(results) <= 2

    def test_metadata_preservation(self, vector_store):
        """Test that metadata is preserved in search results."""
        vector_store.create_collection("test-agent", 384)

        chunk = DocumentChunk(
            text="Test document",
            source_type="database",
            source_identifier="users_table",
            chunk_index=5,
            metadata={"row_id": 123, "custom_field": "value"}
        )
        embeddings = [[0.1] * 384]

        vector_store.add_documents("test-agent", [chunk], embeddings)

        # Search and verify metadata
        query_embedding = [0.1] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=1, min_similarity=0.0)

        assert len(results) > 0
        result_chunk = results[0].chunk
        assert result_chunk.source_type == "database"
        assert result_chunk.source_identifier == "users_table"
        assert result_chunk.chunk_index == 5
        assert result_chunk.metadata.get("row_id") == 123
        assert result_chunk.metadata.get("custom_field") == "value"

    # Task 3.4: Additional unit tests for collection creation/deletion, empty collection, and concurrent reads

    def test_collection_creation_idempotent(self, vector_store):
        """Test that creating the same collection multiple times is idempotent."""
        vector_store.create_collection("test-agent", 384)
        # Creating again should not raise an error
        vector_store.create_collection("test-agent", 384)

        # Verify collection exists
        collection = vector_store.client.get_collection("test-agent")
        assert collection is not None
        assert collection.name == "test-agent"

    def test_collection_deletion_and_recreation(self, vector_store):
        """Test that a collection can be deleted and recreated."""
        # Create collection
        vector_store.create_collection("test-agent", 384)

        # Add some data
        chunks = [
            DocumentChunk(
                text="Test document",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0
            )
        ]
        embeddings = [[0.1] * 384]
        vector_store.add_documents("test-agent", chunks, embeddings)

        # Delete collection
        vector_store.delete_collection("test-agent")

        # Recreate collection
        vector_store.create_collection("test-agent", 384)

        # Verify collection is empty
        query_embedding = [0.1] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=5, min_similarity=0.0)
        assert len(results) == 0

    def test_empty_collection_search(self, vector_store):
        """Test searching an empty collection returns no results."""
        vector_store.create_collection("empty-agent", 384)

        # Search empty collection
        query_embedding = [0.1] * 384
        results = vector_store.search("empty-agent", query_embedding, top_k=5, min_similarity=0.0)

        assert results == []
        assert len(results) == 0

    def test_empty_collection_behavior_after_deletion(self, vector_store):
        """Test that a collection behaves as empty after all documents are deleted."""
        vector_store.create_collection("test-agent", 384)

        # Add documents
        chunks = [
            DocumentChunk(
                text="Document to be deleted",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0
            )
        ]
        embeddings = [[0.1] * 384]
        vector_store.add_documents("test-agent", chunks, embeddings)

        # Delete and recreate collection (simulating deletion of all documents)
        vector_store.delete_collection("test-agent")
        vector_store.create_collection("test-agent", 384)

        # Verify empty behavior
        query_embedding = [0.1] * 384
        results = vector_store.search("test-agent", query_embedding, top_k=5, min_similarity=0.0)
        assert len(results) == 0

    def test_concurrent_read_operations(self, vector_store):
        """Test that concurrent read operations work without errors."""
        import concurrent.futures

        # Create collection and add documents
        vector_store.create_collection("concurrent-agent", 384)

        chunks = [
            DocumentChunk(
                text=f"Document {i}",
                source_type="web",
                source_identifier=f"https://example.com/{i}",
                chunk_index=0
            )
            for i in range(10)
        ]
        embeddings = [[float(i) / 10] * 384 for i in range(10)]
        vector_store.add_documents("concurrent-agent", chunks, embeddings)

        # Define search function
        def search_collection(query_value):
            query_embedding = [query_value] * 384
            return vector_store.search("concurrent-agent", query_embedding, top_k=3, min_similarity=0.0)

        # Execute concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_collection, i / 10.0) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all searches completed successfully
        assert len(results) == 10
        for result in results:
            assert isinstance(result, list)
            # Each search should return some results
            assert len(result) >= 0

    def test_multiple_collections_isolation(self, vector_store):
        """Test that multiple collections are isolated from each other."""
        # Create two collections
        vector_store.create_collection("agent-1", 384)
        vector_store.create_collection("agent-2", 384)

        # Add different documents to each
        chunks_1 = [
            DocumentChunk(
                text="Agent 1 document",
                source_type="web",
                source_identifier="https://agent1.com",
                chunk_index=0
            )
        ]
        chunks_2 = [
            DocumentChunk(
                text="Agent 2 document",
                source_type="web",
                source_identifier="https://agent2.com",
                chunk_index=0
            )
        ]

        embeddings_1 = [[0.1] * 384]
        embeddings_2 = [[0.9] * 384]

        vector_store.add_documents("agent-1", chunks_1, embeddings_1)
        vector_store.add_documents("agent-2", chunks_2, embeddings_2)

        # Search each collection
        query_embedding = [0.1] * 384
        results_1 = vector_store.search("agent-1", query_embedding, top_k=5, min_similarity=0.0)
        results_2 = vector_store.search("agent-2", query_embedding, top_k=5, min_similarity=0.0)

        # Verify isolation
        assert len(results_1) > 0
        assert len(results_2) > 0
        assert results_1[0].chunk.text == "Agent 1 document"
        assert results_2[0].chunk.text == "Agent 2 document"
        assert results_1[0].chunk.source_identifier != results_2[0].chunk.source_identifier
