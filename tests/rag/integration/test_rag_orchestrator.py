"""
Integration tests for RAG orchestrator.

Tests the complete RAG workflow including:
- Knowledge source ingestion (web and database)
- Query processing pipeline
- Error handling and fallback behavior
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offline_chat.agent import Agent
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.database_integration import DatabaseIntegration
from offline_chat.rag.document_processor import DocumentProcessor
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.models import KnowledgeSource, RAGConfig, ScrapedContent
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.prompt_augmenter import PromptAugmenter
from offline_chat.rag.vector_store import VectorStore
from offline_chat.rag.web_scraper import WebScraper
from tests.rag.fixtures.sample_documents import (
    SAMPLE_DATABASE_ROWS,
    SAMPLE_QUERIES,
    SAMPLE_WEB_CONTENT,
)


@pytest.fixture
def temp_rag_dir():
    """Create a temporary directory for RAG data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_rag_dir):
    """Create a temporary SQLite database with test data."""
    db_path = temp_rag_dir / "test.db"
    
    # Create database with sample table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department TEXT NOT NULL
        )
    """)
    
    # Insert sample data
    for row in SAMPLE_DATABASE_ROWS:
        cursor.execute(
            "INSERT INTO employees (id, name, email, department) VALUES (?, ?, ?, ?)",
            (row["id"], row["name"], row["email"], row["department"])
        )
    
    conn.commit()
    conn.close()
    
    return db_path


@pytest.fixture
def rag_agent():
    """Create a test agent with RAG enabled."""
    return Agent(
        name="test-rag-agent",
        display_name="Test RAG Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        created_at=datetime.now(),
        rag_config=RAGConfig(
            enabled=True,
            top_k=3,
            min_similarity=0.3,
            chunk_size=512,
            chunk_overlap=50,
            embedding_model="all-MiniLM-L6-v2",
            knowledge_sources=[]
        )
    )


@pytest.fixture
def embedding_generator():
    """Create an embedding generator for tests."""
    return EmbeddingGenerator(model_name="all-MiniLM-L6-v2")


@pytest.fixture
def vector_store(temp_rag_dir):
    """Create a vector store for tests."""
    return VectorStore(data_dir=temp_rag_dir)


@pytest.fixture
def document_processor():
    """Create a document processor for tests."""
    return DocumentProcessor(chunk_size=512, chunk_overlap=50)


@pytest.fixture
def context_retriever(vector_store, embedding_generator):
    """Create a context retriever for tests."""
    return ContextRetriever(
        vector_store=vector_store,
        embedding_generator=embedding_generator
    )


@pytest.fixture
def prompt_augmenter():
    """Create a prompt augmenter for tests."""
    return PromptAugmenter()


@pytest.fixture
def mock_web_scraper():
    """Create a mock web scraper for tests."""
    scraper = MagicMock(spec=WebScraper)
    
    # Mock the scrape_url method to return sample content
    async def mock_scrape_url(url, max_retries=3, max_length=50000):
        return ScrapedContent(
            url=url,
            text=SAMPLE_WEB_CONTENT,
            metadata={"fetch_timestamp": 1234567890},
            success=True,
            error_message=None
        )
    
    scraper.scrape_url = AsyncMock(side_effect=mock_scrape_url)
    return scraper


@pytest.fixture
def database_integration(temp_db_path, document_processor):
    """Create a database integration for tests."""
    return DatabaseIntegration(
        db_path=temp_db_path,
        document_processor=document_processor
    )


@pytest.fixture
def rag_orchestrator(
    rag_agent,
    vector_store,
    embedding_generator,
    context_retriever,
    document_processor,
    prompt_augmenter,
    mock_web_scraper,
    database_integration
):
    """Create a RAG orchestrator with all components."""
    return RAGOrchestrator(
        agent_config=rag_agent,
        vector_store=vector_store,
        embedding_generator=embedding_generator,
        context_retriever=context_retriever,
        document_processor=document_processor,
        prompt_augmenter=prompt_augmenter,
        web_scraper=mock_web_scraper,
        database_integration=database_integration
    )


class TestRAGOrchestratorIngestion:
    """Test knowledge source ingestion workflows."""
    
    def test_ingest_web_source_success(self, rag_orchestrator):
        """Test successful ingestion of a web source."""
        # Create a web knowledge source
        web_source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/python-guide",
            status="pending"
        )
        
        # Ingest the source
        results = rag_orchestrator.ingest_knowledge_sources([web_source])
        
        # Verify ingestion succeeded
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chunks_processed > 0
        assert results[0].error_message is None
        
        # Verify source status was updated
        status = rag_orchestrator.get_ingestion_status(web_source.identifier)
        assert status is not None
        assert status.status == "active"
        assert status.last_indexed is not None
    
    def test_ingest_database_source_success(self, rag_orchestrator):
        """Test successful ingestion of a database source."""
        # Create a database knowledge source
        db_source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        
        # Ingest the source
        results = rag_orchestrator.ingest_knowledge_sources([db_source])
        
        # Verify ingestion succeeded
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chunks_processed == len(SAMPLE_DATABASE_ROWS)
        assert results[0].error_message is None
        
        # Verify source status was updated
        status = rag_orchestrator.get_ingestion_status(db_source.identifier)
        assert status is not None
        assert status.status == "active"
    
    def test_ingest_multiple_sources(self, rag_orchestrator):
        """Test ingestion of multiple knowledge sources."""
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/guide1",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            ),
        ]
        
        # Ingest all sources
        results = rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Verify both succeeded
        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.chunks_processed > 0 for r in results)
    
    def test_ingest_invalid_database_table(self, rag_orchestrator):
        """Test ingestion fails gracefully for non-existent table."""
        db_source = KnowledgeSource(
            source_type="database",
            identifier="nonexistent_table",
            status="pending"
        )
        
        # Ingest the source
        results = rag_orchestrator.ingest_knowledge_sources([db_source])
        
        # Verify ingestion failed
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].chunks_processed == 0
        assert results[0].error_message is not None
        
        # Verify source status was updated to failed
        status = rag_orchestrator.get_ingestion_status(db_source.identifier)
        assert status is not None
        assert status.status == "failed"
    
    def test_ingest_web_source_scraping_failure(self, rag_orchestrator):
        """Test ingestion handles web scraping failures gracefully."""
        # Mock scraper to return failure
        async def mock_scrape_failure(url, max_retries=3, max_length=50000):
            return ScrapedContent(
                url=url,
                text="",
                metadata={},
                success=False,
                error_message="Network error"
            )
        
        rag_orchestrator.web_scraper.scrape_url = AsyncMock(
            side_effect=mock_scrape_failure
        )
        
        web_source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/failing",
            status="pending"
        )
        
        # Ingest the source
        results = rag_orchestrator.ingest_knowledge_sources([web_source])
        
        # Verify ingestion failed
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_message is not None
    
    def test_ingest_without_rag_enabled(self, rag_agent, vector_store, 
                                       embedding_generator, context_retriever):
        """Test ingestion fails when RAG is not enabled."""
        # Create agent without RAG enabled
        agent = Agent(
            name="no-rag-agent",
            display_name="No RAG Agent",
            base_model="llama3:latest",
            system_prompt="Test",
            rag_config=None
        )
        
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever
        )
        
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com",
            status="pending"
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="RAG is not enabled"):
            orchestrator.ingest_knowledge_sources([source])


class TestRAGOrchestratorQueryProcessing:
    """Test query processing workflows."""
    
    def test_process_query_with_context(self, rag_orchestrator):
        """Test end-to-end query processing with context retrieval."""
        # First ingest some knowledge sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            ),
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process a query
        query = "What is Python?"
        response = rag_orchestrator.process_query(query)
        
        # Verify response structure
        assert response is not None
        assert response.retrieval_result is not None
        assert response.retrieval_result.query == query
        assert response.sources is not None
        assert len(response.sources) > 0
        
        # Verify retrieval metadata
        assert response.retrieval_result.retrieval_time_ms > 0
        assert response.generation_time_ms > 0
    
    def test_process_query_no_relevant_context(self, rag_orchestrator):
        """Test query processing when no relevant context is found."""
        # Ingest sources
        sources = [
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            )
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Query about something completely unrelated
        query = "What is quantum physics?"
        response = rag_orchestrator.process_query(query)
        
        # Should return empty or very low relevance results
        assert response is not None
        assert response.retrieval_result.total_results >= 0
    
    def test_get_augmented_prompt(self, rag_orchestrator):
        """Test augmented prompt generation."""
        # Ingest sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            )
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process query to get retrieval result
        query = "What is Python?"
        response = rag_orchestrator.process_query(query)
        
        # Get augmented prompt
        augmented_prompt = rag_orchestrator.get_augmented_prompt(
            query=query,
            retrieval_result=response.retrieval_result
        )
        
        # Verify prompt contains key elements
        assert query in augmented_prompt
        assert "CONTEXT INFORMATION" in augmented_prompt or len(response.retrieval_result.chunks) == 0
        assert rag_orchestrator.agent_config.system_prompt in augmented_prompt
    
    def test_process_query_without_rag_enabled(self, vector_store, 
                                               embedding_generator, 
                                               context_retriever):
        """Test query processing fails when RAG is not enabled."""
        # Create agent without RAG
        agent = Agent(
            name="no-rag-agent",
            display_name="No RAG Agent",
            base_model="llama3:latest",
            system_prompt="Test",
            rag_config=None
        )
        
        orchestrator = RAGOrchestrator(
            agent_config=agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="RAG is not enabled"):
            orchestrator.process_query("test query")
    
    def test_process_empty_query(self, rag_orchestrator):
        """Test processing empty query raises error."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            rag_orchestrator.process_query("")
    
    def test_source_citation_extraction(self, rag_orchestrator):
        """Test that source citations are correctly extracted."""
        # Ingest multiple sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            ),
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process query
        query = "Tell me about Python and employees"
        response = rag_orchestrator.process_query(query)
        
        # Verify citations
        assert len(response.sources) > 0
        for citation in response.sources:
            assert citation.source_type in ["web", "database"]
            assert citation.identifier is not None
            assert 0.0 <= citation.relevance_score <= 1.0
    
    def test_process_query_with_ollama_generation(self, rag_orchestrator):
        """Test complete query processing pipeline with Ollama generation."""
        # Ingest knowledge sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            )
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process query with Ollama generation enabled
        query = "What is Python?"
        
        # Mock Ollama response
        with patch('ollama.chat') as mock_chat:
            mock_chat.return_value = {
                "message": {
                    "content": "Python is a high-level programming language. [Source: https://example.com/python]"
                }
            }
            
            response = rag_orchestrator.process_query(query, generate_response=True)
            
            # Verify response structure
            assert response is not None
            assert response.content != ""  # Should have generated content
            assert "Python" in response.content
            assert response.sources is not None
            assert len(response.sources) > 0
            
            # Verify Ollama was called
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args
            assert call_args[1]["model"] == rag_orchestrator.agent_config.base_model
            assert call_args[1]["stream"] is False
            
            # Verify the augmented prompt was used
            messages = call_args[1]["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            # The augmented prompt should contain RAG instructions
            assert "CONTEXT INFORMATION" in messages[0]["content"] or len(response.retrieval_result.chunks) == 0
    
    def test_process_query_without_ollama_generation(self, rag_orchestrator):
        """Test query processing without Ollama generation (default behavior)."""
        # Ingest knowledge sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            )
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process query without generation (default)
        query = "What is Python?"
        response = rag_orchestrator.process_query(query, generate_response=False)
        
        # Verify response structure
        assert response is not None
        assert response.content == ""  # Should NOT have generated content
        assert response.sources is not None
        assert response.retrieval_result is not None


class TestRAGOrchestratorErrorHandling:
    """Test error handling and resilience."""
    
    def test_ingest_with_missing_web_scraper(self, rag_agent, vector_store,
                                             embedding_generator, context_retriever):
        """Test ingestion fails gracefully when web scraper is not configured."""
        orchestrator = RAGOrchestrator(
            agent_config=rag_agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            web_scraper=None  # No web scraper
        )
        
        web_source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com",
            status="pending"
        )
        
        results = orchestrator.ingest_knowledge_sources([web_source])
        
        # Should fail gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "not configured" in results[0].error_message.lower()
    
    def test_ingest_with_missing_database_integration(self, rag_agent, vector_store,
                                                      embedding_generator, 
                                                      context_retriever):
        """Test ingestion fails gracefully when database integration is not configured."""
        orchestrator = RAGOrchestrator(
            agent_config=rag_agent,
            vector_store=vector_store,
            embedding_generator=embedding_generator,
            context_retriever=context_retriever,
            database_integration=None  # No database integration
        )
        
        db_source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        
        results = orchestrator.ingest_knowledge_sources([db_source])
        
        # Should fail gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "not configured" in results[0].error_message.lower()
    
    def test_partial_ingestion_failure(self, rag_orchestrator):
        """Test that partial failures don't prevent other sources from being ingested."""
        sources = [
            KnowledgeSource(
                source_type="database",
                identifier="employees",  # Valid
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="nonexistent",  # Invalid
                status="pending"
            ),
        ]
        
        results = rag_orchestrator.ingest_knowledge_sources(sources)
        
        # One should succeed, one should fail
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
    
    def test_ingestion_status_tracking(self, rag_orchestrator):
        """Test that ingestion status is correctly tracked."""
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        
        # Before ingestion
        status = rag_orchestrator.get_ingestion_status(source.identifier)
        assert status is None
        
        # After ingestion
        rag_orchestrator.ingest_knowledge_sources([source])
        status = rag_orchestrator.get_ingestion_status(source.identifier)
        assert status is not None
        assert status.status == "active"
        assert status.last_indexed is not None
    
    def test_ollama_generation_failure_handling(self, rag_orchestrator):
        """Test that Ollama generation failures are handled gracefully."""
        # Ingest knowledge sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            )
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Mock Ollama to raise an exception
        with patch('ollama.chat') as mock_chat:
            mock_chat.side_effect = Exception("Ollama connection failed")
            
            # Should raise exception when generation is requested
            with pytest.raises(Exception, match="Ollama connection failed"):
                rag_orchestrator.process_query(
                    "What is Python?",
                    generate_response=True
                )
    
    def test_empty_sources_list_error(self, rag_orchestrator):
        """Test that empty sources list raises appropriate error."""
        with pytest.raises(ValueError, match="Sources list cannot be empty"):
            rag_orchestrator.ingest_knowledge_sources([])
    
    def test_unknown_source_type_error(self, rag_orchestrator):
        """Test that unknown source type is handled gracefully."""
        # Create a source with invalid type (bypassing validation)
        source = KnowledgeSource(
            source_type="unknown",  # Invalid type
            identifier="test",
            status="pending"
        )
        
        results = rag_orchestrator.ingest_knowledge_sources([source])
        
        # Should fail gracefully
        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown source type" in results[0].error_message


class TestRAGOrchestratorEndToEnd:
    """
    Comprehensive end-to-end integration tests for RAG orchestrator.
    
    These tests validate complete workflows from ingestion through query
    processing with multiple knowledge sources and various scenarios.
    
    **Validates: Requirements 2.6, 14.1, 14.2, 14.3**
    """
    
    def test_complete_rag_workflow_mixed_sources(self, rag_orchestrator):
        """
        Test complete RAG workflow with mixed web and database sources.
        
        This test validates:
        - Ingestion of multiple source types
        - Query processing with context from multiple sources
        - Source citation extraction
        - End-to-end timing and performance
        """
        # Step 1: Ingest multiple knowledge sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python-guide",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            ),
        ]
        
        ingestion_results = rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Verify all sources ingested successfully
        assert len(ingestion_results) == 2
        assert all(r.success for r in ingestion_results)
        total_chunks = sum(r.chunks_processed for r in ingestion_results)
        assert total_chunks > 0
        
        # Step 2: Process queries that should match different sources
        queries = [
            "What is Python?",  # Should match web source
            "Who works in Engineering?",  # Should match database source
            "Tell me about Python and employees",  # Should match both
        ]
        
        for query in queries:
            response = rag_orchestrator.process_query(query)
            
            # Verify response structure
            assert response is not None
            assert response.retrieval_result is not None
            assert response.retrieval_result.query == query
            assert response.sources is not None
            
            # Verify timing information
            assert response.retrieval_result.retrieval_time_ms > 0
            assert response.generation_time_ms > 0
            
            # Verify source citations are present
            if response.retrieval_result.total_results > 0:
                assert len(response.sources) > 0
                for citation in response.sources:
                    assert citation.source_type in ["web", "database"]
                    assert citation.identifier in [s.identifier for s in sources]
                    assert 0.0 <= citation.relevance_score <= 1.0
    
    def test_rag_workflow_with_re_ingestion(self, rag_orchestrator):
        """
        Test RAG workflow with re-ingestion of knowledge sources.
        
        This validates that sources can be updated and re-indexed.
        """
        # Initial ingestion
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        
        results1 = rag_orchestrator.ingest_knowledge_sources([source])
        assert results1[0].success is True
        first_indexed = rag_orchestrator.get_ingestion_status(source.identifier).last_indexed
        
        # Re-ingest the same source
        import time
        time.sleep(0.1)  # Ensure timestamp difference
        
        results2 = rag_orchestrator.ingest_knowledge_sources([source])
        assert results2[0].success is True
        second_indexed = rag_orchestrator.get_ingestion_status(source.identifier).last_indexed
        
        # Verify timestamp was updated
        assert second_indexed > first_indexed
    
    def test_rag_workflow_with_no_matching_context(self, rag_orchestrator):
        """
        Test RAG workflow when query has no matching context.
        
        This validates fallback behavior when similarity threshold is not met.
        """
        # Ingest a specific knowledge source
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        rag_orchestrator.ingest_knowledge_sources([source])
        
        # Query about something completely unrelated
        query = "What is the capital of France?"
        response = rag_orchestrator.process_query(query)
        
        # Should return response with no or very few results
        assert response is not None
        assert response.retrieval_result is not None
        # Results may be 0 or very low relevance
        assert response.retrieval_result.total_results >= 0
        
        # Get augmented prompt to verify it handles no context gracefully
        augmented_prompt = rag_orchestrator.get_augmented_prompt(
            query=query,
            retrieval_result=response.retrieval_result
        )
        assert augmented_prompt is not None
        assert query in augmented_prompt
    
    def test_rag_workflow_with_high_top_k(self, rag_orchestrator):
        """
        Test RAG workflow with high top_k value.
        
        This validates that retrieval respects the top_k parameter even
        when requesting more results than available.
        """
        # Ingest a source
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        results = rag_orchestrator.ingest_knowledge_sources([source])
        chunks_available = results[0].chunks_processed
        
        # Update RAG config to request more chunks than available
        rag_orchestrator.agent_config.rag_config.top_k = chunks_available + 10
        
        # Process query
        query = "Tell me about employees"
        response = rag_orchestrator.process_query(query)
        
        # Should return at most the number of chunks available
        assert response.retrieval_result.total_results <= chunks_available
    
    def test_rag_workflow_with_strict_similarity_threshold(self, rag_orchestrator):
        """
        Test RAG workflow with strict similarity threshold.
        
        This validates that the min_similarity parameter filters results correctly.
        """
        # Ingest a source
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        rag_orchestrator.ingest_knowledge_sources([source])
        
        # Set very high similarity threshold
        rag_orchestrator.agent_config.rag_config.min_similarity = 0.95
        
        # Query about something loosely related
        query = "What is the weather?"
        response = rag_orchestrator.process_query(query)
        
        # Should return very few or no results due to high threshold
        assert response is not None
        # All returned results should meet the threshold
        for search_result in response.retrieval_result.chunks:
            assert search_result.similarity_score >= 0.95
    
    def test_rag_workflow_performance_with_large_dataset(self, rag_orchestrator, temp_db_path):
        """
        Test RAG workflow performance with larger dataset.
        
        This validates that the system performs adequately with more data.
        """
        # Add more data to the database
        import sqlite3
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Insert 50 more employees
        for i in range(4, 54):
            cursor.execute(
                "INSERT INTO employees (id, name, email, department) VALUES (?, ?, ?, ?)",
                (i, f"Employee {i}", f"emp{i}@example.com", f"Department {i % 5}")
            )
        conn.commit()
        conn.close()
        
        # Ingest the larger dataset
        source = KnowledgeSource(
            source_type="database",
            identifier="employees",
            status="pending"
        )
        results = rag_orchestrator.ingest_knowledge_sources([source])
        assert results[0].success is True
        assert results[0].chunks_processed >= 50
        
        # Process query and verify performance
        query = "Who works in Department 1?"
        response = rag_orchestrator.process_query(query)
        
        # Verify retrieval is reasonably fast (should be well under 500ms per requirements)
        assert response.retrieval_result.retrieval_time_ms < 500
        assert response.retrieval_result.total_results > 0
    
    def test_rag_workflow_with_conversation_history(self, rag_orchestrator):
        """
        Test RAG workflow with conversation history context.
        
        This validates that conversation history can be passed through
        the workflow (even if not currently used in retrieval).
        """
        # Ingest sources
        source = KnowledgeSource(
            source_type="web",
            identifier="https://example.com/python",
            status="pending"
        )
        rag_orchestrator.ingest_knowledge_sources([source])
        
        # Create mock conversation history
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you?"},
        ]
        
        # Process query with conversation history
        query = "What is Python?"
        response = rag_orchestrator.process_query(
            query=query,
            conversation_history=conversation_history
        )
        
        # Should process successfully
        assert response is not None
        assert response.retrieval_result is not None
    
    def test_rag_workflow_source_citation_deduplication(self, rag_orchestrator):
        """
        Test that source citations are deduplicated correctly.
        
        When multiple chunks come from the same source, only one citation
        should be created with the highest relevance score.
        """
        # Ingest sources
        sources = [
            KnowledgeSource(
                source_type="web",
                identifier="https://example.com/python",
                status="pending"
            ),
            KnowledgeSource(
                source_type="database",
                identifier="employees",
                status="pending"
            ),
        ]
        rag_orchestrator.ingest_knowledge_sources(sources)
        
        # Process query that should match multiple chunks from same source
        query = "Tell me about Python programming"
        response = rag_orchestrator.process_query(query)
        
        # Verify citations are deduplicated
        citation_keys = [(c.source_type, c.identifier) for c in response.sources]
        assert len(citation_keys) == len(set(citation_keys))  # No duplicates
        
        # Verify citations are sorted by relevance
        if len(response.sources) > 1:
            for i in range(len(response.sources) - 1):
                assert response.sources[i].relevance_score >= response.sources[i + 1].relevance_score
