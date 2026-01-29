"""
Integration tests for RAG management commands.

Tests the add_knowledge_source, reindex_knowledge_source, and list_knowledge_sources
methods in AgentManager.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from offline_chat.agent import Agent
from offline_chat.database.result import is_err, is_ok, unwrap, unwrap_err
from offline_chat.manager import AgentManager
from offline_chat.rag.models import RAGConfig


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as agents_dir, tempfile.TemporaryDirectory() as history_dir:
        yield Path(agents_dir), Path(history_dir)


@pytest.fixture
def manager(temp_dirs):
    """Create an AgentManager with temporary directories."""
    agents_dir, history_dir = temp_dirs
    return AgentManager(agents_dir=agents_dir, history_dir=history_dir)


@pytest.fixture
def rag_agent():
    """Create a test agent with RAG enabled."""
    return Agent(
        name="test-rag-agent",
        display_name="Test RAG Agent",
        base_model="llama3:latest",
        system_prompt="Test agent with RAG",
        temperature=0.7,
        rag_config=RAGConfig(
            enabled=True,
            top_k=5,
            min_similarity=0.3,
            chunk_size=512,
            chunk_overlap=50,
            embedding_model="all-MiniLM-L6-v2",
            knowledge_sources=[],
        ),
    )


@pytest.fixture
def non_rag_agent():
    """Create a test agent without RAG."""
    return Agent(
        name="test-non-rag-agent",
        display_name="Test Non-RAG Agent",
        base_model="llama3:latest",
        system_prompt="Test agent without RAG",
        temperature=0.7,
    )


class TestAddKnowledgeSource:
    """Tests for adding knowledge sources to agents."""

    def test_add_web_source_without_ingestion(self, manager, rag_agent):
        """Test adding a web source without immediate ingestion."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add web source without ingestion
        result = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )

        assert is_ok(result)

        # Verify source was added
        agent = manager.get_agent(rag_agent.name)
        assert len(agent.rag_config.knowledge_sources) == 1

        source = agent.rag_config.knowledge_sources[0]
        assert source.source_type == "web"
        assert source.identifier == "https://example.com/docs"
        assert source.status == "pending"

    def test_add_web_source_with_ingestion(self, manager, rag_agent):
        """Test adding a web source with immediate ingestion."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Mock the RAG orchestrator
        mock_orchestrator = Mock()
        mock_result = Mock(success=True, chunks_processed=10, error_message=None)
        mock_orchestrator.ingest_knowledge_sources.return_value = [mock_result]

        with patch.object(manager, "get_rag_orchestrator", return_value=mock_orchestrator):
            result = manager.add_knowledge_source(
                agent_name=rag_agent.name,
                source_type="web",
                identifier="https://example.com/docs",
                ingest=True,
            )

        assert is_ok(result)

        # Verify source was added and ingested
        agent = manager.get_agent(rag_agent.name)
        assert len(agent.rag_config.knowledge_sources) == 1

        source = agent.rag_config.knowledge_sources[0]
        assert source.source_type == "web"
        assert source.identifier == "https://example.com/docs"
        assert source.status == "active"
        assert source.last_indexed is not None

        # Verify orchestrator was called
        mock_orchestrator.ingest_knowledge_sources.assert_called_once()

    def test_add_database_source(self, manager, rag_agent):
        """Test adding a database source."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add database source without ingestion
        result = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="database",
            identifier="products_table",
            ingest=False,
        )

        assert is_ok(result)

        # Verify source was added
        agent = manager.get_agent(rag_agent.name)
        assert len(agent.rag_config.knowledge_sources) == 1

        source = agent.rag_config.knowledge_sources[0]
        assert source.source_type == "database"
        assert source.identifier == "products_table"
        assert source.status == "pending"

    def test_add_source_to_non_rag_agent(self, manager, non_rag_agent):
        """Test that adding a source to a non-RAG agent fails."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(non_rag_agent)

        # Try to add source
        result = manager.add_knowledge_source(
            agent_name=non_rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "RAG is not" in error_msg

    def test_add_duplicate_source(self, manager, rag_agent):
        """Test that adding a duplicate source fails."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add first source
        result1 = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )
        assert is_ok(result1)

        # Try to add duplicate
        result2 = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )

        assert is_err(result2)
        error_msg = unwrap_err(result2)
        assert "already exists" in error_msg

    def test_add_source_invalid_url(self, manager, rag_agent):
        """Test that adding an invalid URL fails."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Try to add invalid URL
        result = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="not-a-valid-url",
            ingest=False,
        )

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "Invalid URL" in error_msg

    def test_add_source_with_progress_callback(self, manager, rag_agent):
        """Test adding a source with progress callback."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Mock the RAG orchestrator
        mock_orchestrator = Mock()
        mock_result = Mock(success=True, chunks_processed=10, error_message=None)
        mock_orchestrator.ingest_knowledge_sources.return_value = [mock_result]

        # Track progress messages
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        with patch.object(manager, "get_rag_orchestrator", return_value=mock_orchestrator):
            result = manager.add_knowledge_source(
                agent_name=rag_agent.name,
                source_type="web",
                identifier="https://example.com/docs",
                ingest=True,
                progress_callback=progress_callback,
            )

        assert is_ok(result)
        assert len(progress_messages) >= 2  # At least start and end messages
        assert any("Ingesting" in msg for msg in progress_messages)
        assert any("Successfully ingested" in msg for msg in progress_messages)


class TestReindexKnowledgeSource:
    """Tests for re-indexing knowledge sources."""

    def test_reindex_existing_source(self, manager, rag_agent):
        """Test re-indexing an existing knowledge source."""
        # Create agent with a source
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add source
        manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )

        # Mock the RAG orchestrator
        mock_orchestrator = Mock()
        mock_result = Mock(success=True, chunks_processed=15, error_message=None)
        mock_orchestrator.ingest_knowledge_sources.return_value = [mock_result]

        with patch.object(manager, "get_rag_orchestrator", return_value=mock_orchestrator):
            result = manager.reindex_knowledge_source(
                agent_name=rag_agent.name,
                source_identifier="https://example.com/docs",
            )

        assert is_ok(result)

        # Verify source was updated
        agent = manager.get_agent(rag_agent.name)
        source = agent.rag_config.knowledge_sources[0]
        assert source.status == "active"
        assert source.last_indexed is not None
        assert source.error_message is None

    def test_reindex_nonexistent_source(self, manager, rag_agent):
        """Test that re-indexing a non-existent source fails."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Try to re-index non-existent source
        result = manager.reindex_knowledge_source(
            agent_name=rag_agent.name,
            source_identifier="https://example.com/nonexistent",
        )

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg

    def test_reindex_with_progress_callback(self, manager, rag_agent):
        """Test re-indexing with progress callback."""
        # Create agent with a source
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add source
        manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )

        # Mock the RAG orchestrator
        mock_orchestrator = Mock()
        mock_result = Mock(success=True, chunks_processed=15, error_message=None)
        mock_orchestrator.ingest_knowledge_sources.return_value = [mock_result]

        # Track progress messages
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        with patch.object(manager, "get_rag_orchestrator", return_value=mock_orchestrator):
            result = manager.reindex_knowledge_source(
                agent_name=rag_agent.name,
                source_identifier="https://example.com/docs",
                progress_callback=progress_callback,
            )

        assert is_ok(result)
        assert len(progress_messages) >= 2  # At least start and end messages
        assert any("Re-indexing" in msg for msg in progress_messages)


class TestListKnowledgeSources:
    """Tests for listing knowledge sources."""

    def test_list_sources_for_agent_with_sources(self, manager, rag_agent):
        """Test listing sources for an agent with knowledge sources."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add multiple sources
        manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )
        manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="database",
            identifier="products_table",
            ingest=False,
        )

        # List sources
        result = manager.list_knowledge_sources(rag_agent.name)

        assert is_ok(result)
        sources = unwrap(result)
        assert len(sources) == 2

        # Verify sources
        assert sources[0].source_type == "web"
        assert sources[0].identifier == "https://example.com/docs"
        assert sources[1].source_type == "database"
        assert sources[1].identifier == "products_table"

    def test_list_sources_for_agent_without_sources(self, manager, rag_agent):
        """Test listing sources for an agent with no knowledge sources."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # List sources
        result = manager.list_knowledge_sources(rag_agent.name)

        assert is_ok(result)
        sources = unwrap(result)
        assert len(sources) == 0

    def test_list_sources_for_non_rag_agent(self, manager, non_rag_agent):
        """Test that listing sources for a non-RAG agent fails."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(non_rag_agent)

        # Try to list sources
        result = manager.list_knowledge_sources(non_rag_agent.name)

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "RAG is not" in error_msg

    def test_list_sources_for_nonexistent_agent(self, manager):
        """Test that listing sources for a non-existent agent fails."""
        result = manager.list_knowledge_sources("nonexistent-agent")

        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "not found" in error_msg


class TestEndToEndWorkflow:
    """End-to-end tests for RAG management workflow."""

    def test_complete_workflow(self, manager, rag_agent):
        """Test complete workflow: add, list, re-index."""
        # Create agent
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            manager.create_agent(rag_agent)

        # Add source without ingestion
        result = manager.add_knowledge_source(
            agent_name=rag_agent.name,
            source_type="web",
            identifier="https://example.com/docs",
            ingest=False,
        )
        assert is_ok(result)

        # List sources
        result = manager.list_knowledge_sources(rag_agent.name)
        assert is_ok(result)
        sources = unwrap(result)
        assert len(sources) == 1
        assert sources[0].status == "pending"

        # Mock the RAG orchestrator for re-indexing
        mock_orchestrator = Mock()
        mock_result = Mock(success=True, chunks_processed=10, error_message=None)
        mock_orchestrator.ingest_knowledge_sources.return_value = [mock_result]

        with patch.object(manager, "get_rag_orchestrator", return_value=mock_orchestrator):
            result = manager.reindex_knowledge_source(
                agent_name=rag_agent.name,
                source_identifier="https://example.com/docs",
            )
        assert is_ok(result)

        # List sources again to verify status update
        result = manager.list_knowledge_sources(rag_agent.name)
        assert is_ok(result)
        sources = unwrap(result)
        assert len(sources) == 1
        assert sources[0].status == "active"
        assert sources[0].last_indexed is not None
