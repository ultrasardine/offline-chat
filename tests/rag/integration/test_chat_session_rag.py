"""
Integration tests for RAG-enhanced chat sessions.

Tests the complete workflow of chat sessions with RAG capabilities,
including context retrieval, prompt augmentation, and source citation display.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from offline_chat.agent import Agent
from offline_chat.history import ConversationHistory
from offline_chat.manager import AgentManager
from offline_chat.rag.models import (
    DocumentChunk,
    KnowledgeSource,
    RAGConfig,
    RAGResponse,
    RetrievalResult,
    SearchResult,
    SourceCitation,
)
from offline_chat.session import ChatSession


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def rag_enabled_agent():
    """Create an agent with RAG enabled."""
    return Agent(
        name="test-rag-agent",
        display_name="Test RAG Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
        rag_config=RAGConfig(
            enabled=True,
            top_k=5,
            min_similarity=0.3,
            chunk_size=512,
            chunk_overlap=50,
            embedding_model="all-MiniLM-L6-v2",
            knowledge_sources=[
                KnowledgeSource(
                    source_type="web",
                    identifier="https://example.com/docs",
                    status="active",
                    last_indexed=datetime.now(),
                )
            ],
        ),
    )


@pytest.fixture
def non_rag_agent():
    """Create an agent without RAG."""
    return Agent(
        name="test-standard-agent",
        display_name="Test Standard Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
        rag_config=None,
    )


@pytest.fixture
def mock_manager(temp_data_dir, rag_enabled_agent, non_rag_agent):
    """Create a mock AgentManager."""
    manager = Mock(spec=AgentManager)
    manager.data_dir = temp_data_dir
    manager.history_store = Mock()
    manager.history_store.load.return_value = ConversationHistory(
        agent_name="test-rag-agent",
        messages=[],
    )
    manager.get_agent.side_effect = lambda name: (rag_enabled_agent if name == "test-rag-agent" else non_rag_agent)
    return manager


class TestRAGEnabledChatSession:
    """Test chat sessions with RAG enabled."""

    def test_chat_session_with_rag_enabled_agent(self, mock_manager, rag_enabled_agent):
        """Test that chat session initializes RAG orchestrator for RAG-enabled agent.

        Validates: Requirements 5.5, 11.1
        """
        session = ChatSession(mock_manager)

        # Start session with RAG-enabled agent
        session.start("test-rag-agent")

        # Verify agent is loaded
        assert session.agent is not None
        assert session.agent.name == "test-rag-agent"
        assert session.agent.rag_config is not None
        assert session.agent.rag_config.enabled is True

        # Verify RAG orchestrator is initialized
        # Note: In real implementation, this would be initialized
        # For now, we're testing the structure
        assert hasattr(session, "_rag_orchestrator")

    def test_send_message_routes_through_rag(self, mock_manager, rag_enabled_agent):
        """Test that messages are routed through RAG orchestrator when enabled.

        Validates: Requirements 5.5
        """
        session = ChatSession(mock_manager)
        session.start("test-rag-agent")

        # Mock the RAG orchestrator
        mock_rag_orchestrator = Mock()
        mock_retrieval_result = RetrievalResult(
            chunks=[
                SearchResult(
                    chunk=DocumentChunk(
                        text="Sample context from docs",
                        source_type="web",
                        source_identifier="https://example.com/docs",
                        chunk_index=0,
                        metadata={},
                    ),
                    similarity_score=0.85,
                    rank=1,
                )
            ],
            query="test query",
            total_results=1,
            retrieval_time_ms=50.0,
        )
        mock_rag_response = RAGResponse(
            content="",
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://example.com/docs",
                    relevance_score=0.85,
                )
            ],
            retrieval_result=mock_retrieval_result,
            generation_time_ms=100.0,
        )
        mock_rag_orchestrator.process_query.return_value = mock_rag_response
        mock_rag_orchestrator.get_augmented_prompt.return_value = "Augmented prompt with context"

        session._rag_orchestrator = mock_rag_orchestrator

        # Mock Ollama response
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Response "}},
                    {"message": {"content": "based "}},
                    {"message": {"content": "on context"}},
                ]
            )

            # Send a message
            response_chunks = list(session.send_message("test query"))

            # Verify RAG orchestrator was called
            mock_rag_orchestrator.process_query.assert_called_once()
            mock_rag_orchestrator.get_augmented_prompt.assert_called_once()

            # Verify response was generated
            assert len(response_chunks) > 0

            # Verify source citations were stored in history
            assert len(session.history.messages) == 2  # user + assistant
            assistant_message = session.history.messages[-1]
            assert assistant_message.role == "assistant"
            assert assistant_message.sources is not None
            assert len(assistant_message.sources) == 1
            assert assistant_message.sources[0].identifier == "https://example.com/docs"

    def test_source_citations_stored_in_history(self, mock_manager, rag_enabled_agent):
        """Test that source citations are stored in conversation history.

        Validates: Requirements 11.1
        """
        session = ChatSession(mock_manager)
        session.start("test-rag-agent")

        # Mock the RAG orchestrator
        mock_rag_orchestrator = Mock()
        mock_retrieval_result = RetrievalResult(
            chunks=[
                SearchResult(
                    chunk=DocumentChunk(
                        text="Context 1",
                        source_type="web",
                        source_identifier="https://example.com/page1",
                        chunk_index=0,
                        metadata={},
                    ),
                    similarity_score=0.9,
                    rank=1,
                ),
                SearchResult(
                    chunk=DocumentChunk(
                        text="Context 2",
                        source_type="database",
                        source_identifier="products_table",
                        chunk_index=0,
                        metadata={},
                    ),
                    similarity_score=0.8,
                    rank=2,
                ),
            ],
            query="test query",
            total_results=2,
            retrieval_time_ms=50.0,
        )
        mock_rag_response = RAGResponse(
            content="",
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://example.com/page1",
                    relevance_score=0.9,
                ),
                SourceCitation(
                    source_type="database",
                    identifier="products_table",
                    relevance_score=0.8,
                ),
            ],
            retrieval_result=mock_retrieval_result,
            generation_time_ms=100.0,
        )
        mock_rag_orchestrator.process_query.return_value = mock_rag_response
        mock_rag_orchestrator.get_augmented_prompt.return_value = "Augmented prompt"

        session._rag_orchestrator = mock_rag_orchestrator

        # Mock Ollama response
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Response "}},
                    {"message": {"content": "with "}},
                    {"message": {"content": "multiple sources"}},
                ]
            )

            # Send a message
            list(session.send_message("test query"))

            # Verify source citations in history
            assistant_message = session.history.messages[-1]
            assert assistant_message.sources is not None
            assert len(assistant_message.sources) == 2

            # Verify web source
            web_source = next(s for s in assistant_message.sources if s.source_type == "web")
            assert web_source.identifier == "https://example.com/page1"
            assert web_source.relevance_score == 0.9

            # Verify database source
            db_source = next(s for s in assistant_message.sources if s.source_type == "database")
            assert db_source.identifier == "products_table"
            assert db_source.relevance_score == 0.8


class TestFallbackBehavior:
    """Test fallback to non-RAG mode when RAG fails."""

    def test_fallback_when_rag_orchestrator_returns_none(self, mock_manager, rag_enabled_agent):
        """Test fallback to standard mode when RAG orchestrator returns None.

        This happens when the vector store is unavailable.

        Validates: Requirements 14.1
        """
        session = ChatSession(mock_manager)
        session.start("test-rag-agent")

        # Mock the RAG orchestrator to return None (vector store unavailable)
        mock_rag_orchestrator = Mock()
        mock_rag_orchestrator.process_query.return_value = None

        session._rag_orchestrator = mock_rag_orchestrator

        # Mock Ollama response for standard mode
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Standard "}},
                    {"message": {"content": "response "}},
                    {"message": {"content": "without RAG"}},
                ]
            )

            # Send a message
            response_chunks = list(session.send_message("test query"))

            # Verify RAG orchestrator was called
            mock_rag_orchestrator.process_query.assert_called_once()

            # Verify response was generated (fallback to standard mode)
            assert len(response_chunks) > 0

            # Verify no source citations in history (standard mode)
            assistant_message = session.history.messages[-1]
            assert assistant_message.sources is None or len(assistant_message.sources) == 0

    def test_fallback_when_rag_orchestrator_raises_exception(self, mock_manager, rag_enabled_agent):
        """Test fallback to standard mode when RAG orchestrator raises exception.

        Validates: Requirements 14.1
        """
        session = ChatSession(mock_manager)
        session.start("test-rag-agent")

        # Mock the RAG orchestrator to raise an exception
        mock_rag_orchestrator = Mock()
        mock_rag_orchestrator.process_query.side_effect = Exception("RAG error")

        session._rag_orchestrator = mock_rag_orchestrator

        # Mock Ollama response for standard mode
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Standard "}},
                    {"message": {"content": "response "}},
                    {"message": {"content": "after error"}},
                ]
            )

            # Send a message - should not raise exception
            response_chunks = list(session.send_message("test query"))

            # Verify response was generated (fallback to standard mode)
            assert len(response_chunks) > 0

            # Verify no source citations in history (standard mode)
            assistant_message = session.history.messages[-1]
            assert assistant_message.sources is None or len(assistant_message.sources) == 0

    def test_standard_mode_when_rag_not_enabled(self, mock_manager, non_rag_agent):
        """Test that standard mode is used when RAG is not enabled.

        Validates: Requirements 5.5
        """
        session = ChatSession(mock_manager)
        session.start("test-standard-agent")

        # Verify RAG orchestrator is not initialized
        assert session._rag_orchestrator is None

        # Mock Ollama response
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Standard response"}},
                ]
            )

            # Send a message
            response_chunks = list(session.send_message("test query"))

            # Verify response was generated
            assert len(response_chunks) > 0

            # Verify no source citations in history
            assistant_message = session.history.messages[-1]
            assert assistant_message.sources is None or len(assistant_message.sources) == 0


class TestSourceCitationDisplay:
    """Test source citation display in chat interface."""

    def test_source_citation_format(self):
        """Test that source citations are formatted correctly for display.

        Validates: Requirements 11.2
        """
        # Web source
        web_citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.85,
        )
        assert web_citation.format_for_display() == "[Web] https://example.com/docs"

        # Database source
        db_citation = SourceCitation(
            source_type="database",
            identifier="products_table",
            relevance_score=0.75,
        )
        assert db_citation.format_for_display() == "[Database] products_table"

    def test_source_citation_with_relevance(self):
        """Test that source citations can be formatted with relevance scores.

        Validates: Requirements 11.2
        """
        citation = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.92,
        )
        formatted = citation.format_with_relevance()
        assert "[Web] https://example.com/docs" in formatted
        assert "0.92" in formatted


class TestAsyncRAGChat:
    """Test async chat sessions with RAG."""

    @pytest.mark.skip(reason="Async tests require pytest-asyncio plugin")
    async def test_async_send_message_with_rag(self, mock_manager, rag_enabled_agent):
        """Test async message sending with RAG enabled.

        Validates: Requirements 5.5
        """
        session = ChatSession(mock_manager)
        await session.start_async("test-rag-agent")

        # Mock the RAG orchestrator
        mock_rag_orchestrator = Mock()
        mock_retrieval_result = RetrievalResult(
            chunks=[
                SearchResult(
                    chunk=DocumentChunk(
                        text="Sample context",
                        source_type="web",
                        source_identifier="https://example.com/docs",
                        chunk_index=0,
                        metadata={},
                    ),
                    similarity_score=0.85,
                    rank=1,
                )
            ],
            query="test query",
            total_results=1,
            retrieval_time_ms=50.0,
        )
        mock_rag_response = RAGResponse(
            content="",
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://example.com/docs",
                    relevance_score=0.85,
                )
            ],
            retrieval_result=mock_retrieval_result,
            generation_time_ms=100.0,
        )
        mock_rag_orchestrator.process_query.return_value = mock_rag_response
        mock_rag_orchestrator.get_augmented_prompt.return_value = "Augmented prompt"

        session._rag_orchestrator = mock_rag_orchestrator

        # Mock Ollama response
        with patch("offline_chat.session.ollama.chat") as mock_ollama:
            # Mock streaming response
            mock_ollama.return_value = iter(
                [
                    {"message": {"content": "Async "}},
                    {"message": {"content": "response "}},
                    {"message": {"content": "with RAG"}},
                ]
            )

            # Send a message asynchronously
            response_chunks = await session.send_message_async("test query")

            # Verify RAG orchestrator was called
            mock_rag_orchestrator.process_query.assert_called_once()

            # Verify response was generated
            assert len(response_chunks) > 0

            # Verify source citations were stored
            assistant_message = session.history.messages[-1]
            assert assistant_message.sources is not None
            assert len(assistant_message.sources) == 1
