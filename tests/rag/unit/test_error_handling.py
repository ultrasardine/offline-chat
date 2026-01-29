"""
Unit tests for RAG error handling and resilience.

Tests the fallback to non-RAG mode when vector store is unavailable.
"""

from unittest.mock import Mock

import pytest

from offline_chat.agent import Agent
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import RAGConfig
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.vector_store import VectorStore


class TestVectorStoreUnavailableFallback:
    """Test fallback to non-RAG mode when vector store is unavailable."""

    def test_process_query_returns_none_when_collection_not_found(self):
        """Test that process_query returns None when collection doesn't exist."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate collection not found error
        context_retriever.retrieve_context.side_effect = Exception(
            "Collection 'test-agent' does not exist"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query should return None (fallback to non-RAG)
        result = orchestrator.process_query("What is Python?")

        assert result is None
        context_retriever.retrieve_context.assert_called_once()

    def test_process_query_returns_none_when_chromadb_unavailable(self):
        """Test that process_query returns None when ChromaDB is unavailable."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate ChromaDB connection error
        context_retriever.retrieve_context.side_effect = Exception(
            "ChromaDB connection unavailable"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query should return None (fallback to non-RAG)
        result = orchestrator.process_query("What is Python?")

        assert result is None

    def test_process_query_returns_none_when_database_unavailable(self):
        """Test that process_query returns None when database is unavailable."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate database unavailable error
        context_retriever.retrieve_context.side_effect = Exception(
            "Database connection failed"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query should return None (fallback to non-RAG)
        result = orchestrator.process_query("What is Python?")

        assert result is None

    def test_process_query_raises_on_non_storage_errors(self):
        """Test that process_query raises exception for non-storage errors."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate a different kind of error (not storage-related)
        context_retriever.retrieve_context.side_effect = ValueError(
            "Invalid query format"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query should raise the exception (not fallback)
        with pytest.raises(ValueError, match="Invalid query format"):
            orchestrator.process_query("What is Python?")

    def test_fallback_logs_warning(self, caplog):
        """Test that fallback to non-RAG mode logs a warning."""
        import logging
        caplog.set_level(logging.WARNING)

        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate vector store unavailable
        context_retriever.retrieve_context.side_effect = Exception(
            "Collection not found"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query
        result = orchestrator.process_query("What is Python?")

        # Check that warning was logged
        assert result is None
        assert any(
            "Vector store unavailable" in record.message and
            "Falling back to non-RAG mode" in record.message
            for record in caplog.records
        )

    def test_fallback_includes_agent_name_in_log(self, caplog):
        """Test that fallback log includes agent name for debugging."""
        import logging
        caplog.set_level(logging.WARNING)

        # Create agent with RAG enabled
        agent = Agent(
            name="my-special-agent",
            display_name="My Special Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Simulate vector store unavailable
        context_retriever.retrieve_context.side_effect = Exception(
            "Collection unavailable"
        )

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Process query
        orchestrator.process_query("What is Python?")

        # Check that agent name is in the log
        assert any(
            "my-special-agent" in record.message
            for record in caplog.records
        )


class TestIngestionErrorHandling:
    """Test error handling during knowledge source ingestion."""

    def test_ingest_logs_error_and_continues_on_exception(self, caplog):
        """Test that ingestion logs errors and continues with other sources."""
        import logging
        caplog.set_level(logging.ERROR)

        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Create orchestrator
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
        )

        # Create knowledge sources
        from offline_chat.rag.models import KnowledgeSource
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/doc1",
            ),
        ]

        # Mock web scraper to raise an exception
        web_scraper = Mock()
        orchestrator.web_scraper = web_scraper

        # Simulate async scrape_url that raises an exception
        async def failing_scrape(url):
            raise Exception("Network error")

        web_scraper.scrape_url = failing_scrape

        # Ingest sources
        results = orchestrator.ingest_knowledge_sources(sources)

        # Check that we got a result
        assert len(results) == 1

        # Source should have failed
        assert results[0].success is False
        assert "Network error" in results[0].error_message

        # Check that error was logged
        assert any(
            "Error ingesting" in record.message and
            "https://example.com/doc1" in record.message
            for record in caplog.records
        )


class TestCorruptedCollectionDetection:
    """Test detection of corrupted ChromaDB collections."""

    def test_is_collection_corrupted_returns_false_for_healthy_collection(self, tmp_path):
        """Test that a healthy collection is not detected as corrupted."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a healthy collection
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        # Check if corrupted
        is_corrupted, error_msg = vector_store.is_collection_corrupted(collection_name)

        assert is_corrupted is False
        assert error_msg is None

    def test_is_collection_corrupted_returns_false_for_missing_collection(self, tmp_path):
        """Test that a missing collection is not considered corrupted."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Check a collection that doesn't exist
        is_corrupted, error_msg = vector_store.is_collection_corrupted("nonexistent")

        assert is_corrupted is False
        assert error_msg is None

    def test_is_collection_corrupted_detects_access_errors(self, tmp_path):
        """Test that collection access errors are detected as corruption."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a collection
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        # Mock the get_collection to simulate corruption
        original_get_collection = vector_store.client.get_collection

        def corrupted_get_collection(name):
            collection = original_get_collection(name)
            # Mock the get method to raise an error
            def failing_get(*args, **kwargs):
                raise Exception("SQLite database is corrupted")
            collection.get = failing_get
            return collection

        vector_store.client.get_collection = corrupted_get_collection

        # Check if corrupted
        is_corrupted, error_msg = vector_store.is_collection_corrupted(collection_name)

        assert is_corrupted is True
        assert error_msg is not None
        assert "corrupt" in error_msg.lower()

    def test_is_collection_corrupted_detects_database_errors(self, tmp_path):
        """Test that database errors are detected as corruption."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a collection
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        # Mock to simulate database error
        original_get_collection = vector_store.client.get_collection

        def corrupted_get_collection(name):
            collection = original_get_collection(name)
            def failing_get(*args, **kwargs):
                raise Exception("Database disk I/O error")
            collection.get = failing_get
            return collection

        vector_store.client.get_collection = corrupted_get_collection

        # Check if corrupted
        is_corrupted, error_msg = vector_store.is_collection_corrupted(collection_name)

        assert is_corrupted is True
        assert error_msg is not None
        assert "disk i/o error" in error_msg.lower()


class TestCorruptedCollectionRecovery:
    """Test recovery from corrupted ChromaDB collections."""

    def test_rebuild_collection_refuses_to_rebuild_healthy_collection(self, tmp_path):
        """Test that rebuild refuses to rebuild a healthy collection without force."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a healthy collection
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        # Try to rebuild without force
        success, message = vector_store.rebuild_collection(collection_name, 384, force=False)

        assert success is False
        assert "not corrupted" in message.lower()
        assert "force=True" in message

    def test_rebuild_collection_rebuilds_with_force(self, tmp_path):
        """Test that rebuild works with force=True even for healthy collections."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a healthy collection with some data
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        from offline_chat.rag.models import DocumentChunk
        chunks = [
            DocumentChunk(
                text="Test content",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0,
            )
        ]
        embeddings = [[0.1] * 384]
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Verify data exists
        info_before = vector_store.get_collection_info(collection_name)
        assert info_before is not None
        assert info_before["count"] == 1

        # Rebuild with force
        success, message = vector_store.rebuild_collection(collection_name, 384, force=True)

        assert success is True
        assert "successfully rebuilt" in message.lower()
        assert "re-index" in message.lower()

        # Verify collection is empty after rebuild
        info_after = vector_store.get_collection_info(collection_name)
        assert info_after is not None
        assert info_after["count"] == 0

    def test_rebuild_collection_rebuilds_corrupted_collection(self, tmp_path):
        """Test that rebuild successfully rebuilds a corrupted collection."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a collection
        collection_name = "test-collection"
        vector_store.create_collection(collection_name, 384)

        # Simulate corruption by mocking is_collection_corrupted
        original_is_corrupted = vector_store.is_collection_corrupted
        vector_store.is_collection_corrupted = lambda name: (True, "Simulated corruption")

        # Rebuild the corrupted collection
        success, message = vector_store.rebuild_collection(collection_name, 384, force=False)

        # Restore original method
        vector_store.is_collection_corrupted = original_is_corrupted

        assert success is True
        assert "successfully rebuilt" in message.lower()

        # Verify collection is healthy after rebuild
        is_corrupted, _ = vector_store.is_collection_corrupted(collection_name)
        assert is_corrupted is False

    def test_rebuild_collection_handles_rebuild_failure(self, tmp_path):
        """Test that rebuild handles failures gracefully."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Mock create_collection to fail
        original_create = vector_store.create_collection
        def failing_create(name, dim):
            raise Exception("Cannot create collection")

        vector_store.create_collection = failing_create

        # Try to rebuild
        success, message = vector_store.rebuild_collection("test-collection", 384, force=True)

        # Restore original method
        vector_store.create_collection = original_create

        assert success is False
        assert "failed to rebuild" in message.lower()
        assert "cannot create collection" in message.lower()


class TestEmbeddingGenerationFailure:
    """Test error handling when embedding generation fails."""

    def test_context_retriever_handles_embedding_failure(self):
        """Test that context retriever handles embedding generation failures."""
        # Create mock components
        vector_store = Mock(spec=VectorStore)
        embedding_generator = Mock(spec=EmbeddingGenerator)

        # Simulate embedding generation failure
        embedding_generator.generate_embedding.side_effect = Exception(
            "Model loading failed"
        )

        # Create context retriever
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Try to retrieve context - should raise the exception
        with pytest.raises(Exception, match="Model loading failed"):
            context_retriever.retrieve_context(
                collection_name="test-collection",
                query="What is Python?",
                top_k=5,
                min_similarity=0.3,
            )

    def test_orchestrator_handles_embedding_failure_during_ingestion(self, tmp_path):
        """Test that orchestrator handles embedding failures during ingestion."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create mock components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Simulate embedding generation failure
        embedding_generator.generate_embeddings_batch.side_effect = Exception(
            "CUDA out of memory"
        )

        # Create orchestrator with web scraper
        from offline_chat.rag.models import KnowledgeSource, ScrapedContent

        web_scraper = Mock()

        async def mock_scrape(url):
            return ScrapedContent(
                url=url,
                text="Test content for embedding",
                success=True,
            )

        web_scraper.scrape_url = mock_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Try to ingest a web source
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/doc",
            )
        ]

        results = orchestrator.ingest_knowledge_sources(sources)

        # Should handle the error gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "CUDA out of memory" in results[0].error_message

    def test_embedding_failure_updates_source_status(self, tmp_path):
        """Test that embedding failures update knowledge source status correctly."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create mock components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Simulate embedding generation failure
        embedding_generator.generate_embeddings_batch.side_effect = RuntimeError(
            "Embedding model not available"
        )

        # Create orchestrator with web scraper
        from offline_chat.rag.models import KnowledgeSource, ScrapedContent

        web_scraper = Mock()

        async def mock_scrape(url):
            return ScrapedContent(
                url=url,
                text="Test content",
                success=True,
            )

        web_scraper.scrape_url = mock_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Create knowledge source
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/doc",
        )

        # Try to ingest
        orchestrator.ingest_knowledge_sources([source])

        # Check that source status was updated
        assert source.status == "failed"
        assert source.error_message is not None
        assert "Embedding model not available" in source.error_message


class TestWebScrapingFailure:
    """Test error handling when web scraping fails."""

    def test_orchestrator_handles_web_scraping_failure(self, tmp_path):
        """Test that orchestrator handles web scraping failures gracefully."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Create orchestrator with failing web scraper
        from offline_chat.rag.models import KnowledgeSource, ScrapedContent

        web_scraper = Mock()

        async def failing_scrape(url):
            return ScrapedContent(
                url=url,
                text="",
                success=False,
                error_message="HTTP 404: Page not found",
            )

        web_scraper.scrape_url = failing_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Try to ingest a web source
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/nonexistent",
            )
        ]

        results = orchestrator.ingest_knowledge_sources(sources)

        # Should handle the error gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "404" in results[0].error_message

    def test_web_scraping_network_error(self, tmp_path):
        """Test handling of network errors during web scraping."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Create orchestrator with web scraper that raises network error
        from offline_chat.rag.models import KnowledgeSource

        web_scraper = Mock()

        async def network_error_scrape(url):
            raise Exception("Network timeout after 30 seconds")

        web_scraper.scrape_url = network_error_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Try to ingest a web source
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/slow-page",
            )
        ]

        results = orchestrator.ingest_knowledge_sources(sources)

        # Should handle the error gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "Network timeout" in results[0].error_message

    def test_web_scraping_failure_updates_source_status(self, tmp_path):
        """Test that web scraping failures update knowledge source status."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = Mock(spec=EmbeddingGenerator)
        context_retriever = Mock(spec=ContextRetriever)

        # Mock embedding dimension
        embedding_generator.get_embedding_dimension.return_value = 384

        # Create orchestrator with failing web scraper
        from offline_chat.rag.models import KnowledgeSource, ScrapedContent

        web_scraper = Mock()

        async def failing_scrape(url):
            return ScrapedContent(
                url=url,
                text="",
                success=False,
                error_message="Connection refused",
            )

        web_scraper.scrape_url = failing_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Create knowledge source
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/doc",
        )

        # Try to ingest
        orchestrator.ingest_knowledge_sources([source])

        # Check that source status was updated
        assert source.status == "failed"
        assert source.error_message is not None
        assert "Connection refused" in source.error_message

    def test_multiple_sources_with_mixed_failures(self, tmp_path):
        """Test that orchestrator continues with other sources when one fails."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                knowledge_sources=[],
            )
        )

        # Create components
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)

        vector_store = VectorStore(data_dir)
        embedding_generator = EmbeddingGenerator()
        context_retriever = ContextRetriever(vector_store, embedding_generator)

        # Create orchestrator with web scraper that fails for specific URLs
        from offline_chat.rag.models import KnowledgeSource, ScrapedContent

        web_scraper = Mock()

        async def conditional_scrape(url):
            if "fail" in url:
                return ScrapedContent(
                    url=url,
                    text="",
                    success=False,
                    error_message="Scraping failed",
                )
            else:
                return ScrapedContent(
                    url=url,
                    text="This is valid content that can be indexed.",
                    success=True,
                )

        web_scraper.scrape_url = conditional_scrape

        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=web_scraper,
        )

        # Try to ingest multiple sources, one of which will fail
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/fail-page",
            ),
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/good-page",
            ),
        ]

        results = orchestrator.ingest_knowledge_sources(sources)

        # Should have results for both sources
        assert len(results) == 2

        # First source should have failed
        assert results[0].success is False
        assert "Scraping failed" in results[0].error_message

        # Second source should have succeeded
        assert results[1].success is True
        assert results[1].chunks_processed > 0


class TestCollectionInfo:
    """Test getting collection information."""

    def test_get_collection_info_returns_info_for_existing_collection(self, tmp_path):
        """Test that get_collection_info returns correct information."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create a collection with metadata
        collection_name = "test-collection"
        embedding_dim = 384
        vector_store.create_collection(collection_name, embedding_dim)

        # Add some documents
        from offline_chat.rag.models import DocumentChunk
        chunks = [
            DocumentChunk(
                text="Test content 1",
                source_type="web",
                source_identifier="https://example.com/1",
                chunk_index=0,
            ),
            DocumentChunk(
                text="Test content 2",
                source_type="web",
                source_identifier="https://example.com/2",
                chunk_index=0,
            ),
        ]
        embeddings = [[0.1] * 384, [0.2] * 384]
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Get collection info
        info = vector_store.get_collection_info(collection_name)

        assert info is not None
        assert info["name"] == collection_name
        assert info["count"] == 2
        assert "metadata" in info
        assert info["metadata"]["embedding_dimension"] == embedding_dim

    def test_get_collection_info_returns_none_for_missing_collection(self, tmp_path):
        """Test that get_collection_info returns None for missing collections."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Get info for non-existent collection
        info = vector_store.get_collection_info("nonexistent")

        assert info is None

    def test_get_collection_info_returns_zero_count_for_empty_collection(self, tmp_path):
        """Test that get_collection_info returns zero count for empty collections."""
        # Create vector store
        data_dir = tmp_path / "data" / "rag"
        data_dir.mkdir(parents=True)
        vector_store = VectorStore(data_dir)

        # Create an empty collection
        collection_name = "empty-collection"
        vector_store.create_collection(collection_name, 384)

        # Get collection info
        info = vector_store.get_collection_info(collection_name)

        assert info is not None
        assert info["name"] == collection_name
        assert info["count"] == 0


class TestOrchestratorCollectionHealth:
    """Test orchestrator's collection health checking and rebuilding."""

    def test_check_collection_health_returns_healthy_for_populated_collection(self, tmp_path):
        """Test that check_collection_health returns healthy for a good collection."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
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

        # Set up collection with data
        from offline_chat.rag.models import DocumentChunk

        collection_name = agent.name
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        chunks = [
            DocumentChunk(
                text="Test content",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0,
            )
        ]
        embeddings = embedding_generator.generate_embeddings_batch([c.text for c in chunks])
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Check health
        is_healthy, error_msg = orchestrator.check_collection_health()

        assert is_healthy is True
        assert error_msg is None

    def test_check_collection_health_returns_unhealthy_for_missing_collection(self, tmp_path):
        """Test that check_collection_health detects missing collections."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components without creating collection
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

        # Check health - should detect missing collection
        is_healthy, error_msg = orchestrator.check_collection_health()

        assert is_healthy is False
        assert error_msg is not None
        assert "does not exist" in error_msg.lower()

    def test_check_collection_health_returns_unhealthy_for_empty_collection(self, tmp_path):
        """Test that check_collection_health detects empty collections."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components and empty collection
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

        # Create empty collection
        collection_name = agent.name
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        # Check health - should detect empty collection
        is_healthy, error_msg = orchestrator.check_collection_health()

        assert is_healthy is False
        assert error_msg is not None
        assert "empty" in error_msg.lower()

    def test_check_collection_health_detects_corrupted_collection(self, tmp_path):
        """Test that check_collection_health detects corrupted collections."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components
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

        # Mock is_collection_corrupted to simulate corruption
        original_is_corrupted = vector_store.is_collection_corrupted
        vector_store.is_collection_corrupted = lambda name: (True, "Simulated corruption")

        # Check health - should detect corruption
        is_healthy, error_msg = orchestrator.check_collection_health()

        # Restore original method
        vector_store.is_collection_corrupted = original_is_corrupted

        assert is_healthy is False
        assert error_msg is not None
        assert "corrupt" in error_msg.lower()

    def test_orchestrator_rebuild_collection_rebuilds_successfully(self, tmp_path):
        """Test that orchestrator can rebuild collections."""
        # Create agent with RAG enabled
        agent = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            rag_config=RAGConfig(
                enabled=True,
                top_k=5,
                min_similarity=0.3,
            )
        )

        # Create components
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

        # Create a collection with data
        from offline_chat.rag.models import DocumentChunk

        collection_name = agent.name
        embedding_dim = embedding_generator.get_embedding_dimension()
        vector_store.create_collection(collection_name, embedding_dim)

        chunks = [
            DocumentChunk(
                text="Test content",
                source_type="web",
                source_identifier="https://example.com",
                chunk_index=0,
            )
        ]
        embeddings = embedding_generator.generate_embeddings_batch([c.text for c in chunks])
        vector_store.add_documents(collection_name, chunks, embeddings)

        # Rebuild with force
        success, message = orchestrator.rebuild_collection(force=True)

        assert success is True
        assert "successfully rebuilt" in message.lower()

        # Verify collection is empty after rebuild
        info = vector_store.get_collection_info(collection_name)
        assert info is not None
        assert info["count"] == 0
