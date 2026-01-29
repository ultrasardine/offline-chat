"""
Integration tests for RAG fallback to non-RAG mode.

Tests the complete fallback workflow when vector store is unavailable.
"""

from unittest.mock import Mock

from offline_chat.agent import Agent
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import RAGConfig
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.vector_store import VectorStore


class TestRAGFallbackBehavior:
    """Test fallback to non-RAG mode when vector store is unavailable."""

    def test_fallback_when_collection_missing(self, tmp_path):
        """
        Test that RAG handles missing collection gracefully.

        When a collection doesn't exist, ChromaDB returns empty results,
        which is not a fallback scenario - it's just no matching context.
        The system should still return a RAGResponse (with no sources).
        """
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create real components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Try to process a query without creating the collection first
        # This should return a RAGResponse with no sources (not a fallback scenario)
        result = orchestrator.process_query("What is Python?")

        assert result is not None, "Should return RAGResponse even with empty collection"
        assert len(result.sources) == 0, "Should have no sources when collection is empty"
        assert result.retrieval_result.total_results == 0, "Should have no results"

    def test_fallback_when_chromadb_unavailable(self, tmp_path):
        """
        Test fallback when ChromaDB is completely unavailable.

        This simulates a scenario where the ChromaDB service is down or
        the database files are corrupted.
        """
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components with mocked vector store that simulates unavailability
        vector_store = Mock(spec=VectorStore)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Mock the search to raise a connection error
        vector_store.search.side_effect = Exception("ChromaDB connection failed")

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Try to process a query
        result = orchestrator.process_query("What is Python?")

        assert result is None, "Should return None to signal fallback to non-RAG mode"

    def test_normal_operation_when_vector_store_available(self, tmp_path):
        """
        Test that normal RAG operation works when vector store is available.

        This ensures our fallback logic doesn't interfere with normal operation.
        """
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create real components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Create the collection and add some test data
        from offline_chat.rag.models import DocumentChunk

        collection_name = agent.name
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        # Add a test document
        chunks = [
            DocumentChunk(
                text="Python is a high-level programming language.",
                source_type="web",
                source_identifier="https://example.com/python",
                chunk_index=0,
                metadata={"title": "Python Introduction"}
            )
        ]

        embeddings = embedding_generator.generate_embeddings_batch([c.text for c in chunks])
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Process a query - should work normally and return a RAGResponse
        result = orchestrator.process_query("What is Python?")

        assert result is not None, "Should return RAGResponse when vector store is available"
        assert hasattr(result, 'sources'), "Result should have sources attribute"
        assert hasattr(result, 'retrieval_result'), "Result should have retrieval_result"
        assert result.retrieval_result.total_results >= 0, "Should have retrieval results"

    def test_fallback_logs_appropriate_warning(self, caplog):
        """
        Test that fallback logs a warning with helpful information.

        This ensures operators can diagnose why RAG isn't working.
        """
        import logging
        caplog.set_level(logging.WARNING)

        # Create agent with RAG enabled
        agent = Agent(
            name="my-agent",
            display_name="My Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components that simulate vector store unavailability
        vector_store = Mock(spec=VectorStore)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Simulate ChromaDB connection failure
        vector_store.search.side_effect = Exception("ChromaDB connection failed")

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Try to process a query - should trigger fallback
        result = orchestrator.process_query("What is Python?")

        assert result is None, "Should return None when vector store is unavailable"

        # Check that a warning was logged with helpful information
        warning_found = False
        for record in caplog.records:
            if (record.levelname == "WARNING" and
                "Vector store unavailable" in record.message and
                "my-agent" in record.message and
                "Falling back to non-RAG mode" in record.message):
                warning_found = True
                break

        assert warning_found, "Should log a warning with agent name and fallback message"


class TestRAGFallbackIntegrationWithChatSession:
    """
    Test how fallback behavior integrates with chat session.

    Note: These are conceptual tests showing how ChatSession would use
    the fallback behavior. Actual ChatSession integration is in task 16.
    """

    def test_chat_session_can_detect_fallback(self):
        """
        Test that chat session can detect when RAG falls back to non-RAG mode.

        When process_query returns None, the chat session should use standard
        Ollama chat without RAG augmentation.
        """
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components with mocked vector store that simulates unavailability
        vector_store = Mock(spec=VectorStore)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Simulate vector store connection failure
        vector_store.search.side_effect = Exception("ChromaDB unavailable")

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Simulate what ChatSession would do:
        # 1. Try to use RAG
        rag_response = orchestrator.process_query("What is Python?")

        # 2. Check if RAG is available
        if rag_response is None:
            # 3. Fall back to standard Ollama chat
            use_standard_chat = True
        else:
            # 4. Use RAG-augmented prompt
            use_standard_chat = False

        # In this case, vector store is unavailable, so should fall back
        assert use_standard_chat is True, "Should fall back to standard chat"

    def test_chat_session_uses_rag_when_available(self, tmp_path):
        """
        Test that chat session uses RAG when it's available.

        When process_query returns a RAGResponse, the chat session should
        use the augmented prompt.
        """
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a helpful assistant.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components and set up vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Set up vector store with data
        from offline_chat.rag.models import DocumentChunk

        collection_name = agent.name
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        chunks = [
            DocumentChunk(
                text="Python is a programming language.",
                source_type="web",
                source_identifier="https://example.com/python",
                chunk_index=0,
            )
        ]

        embeddings = embedding_generator.generate_embeddings_batch([c.text for c in chunks])
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Simulate what ChatSession would do:
        rag_response = orchestrator.process_query("What is Python?")

        if rag_response is None:
            use_standard_chat = True
        else:
            use_standard_chat = False
            # Would use: orchestrator.get_augmented_prompt(query, rag_response.retrieval_result)

        # In this case, RAG is available
        assert use_standard_chat is False, "Should use RAG when available"
        assert rag_response is not None
        assert len(rag_response.sources) > 0, "Should have source citations"
