"""
Integration tests for agent management with RAG capabilities.
"""

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from offline_chat.agent import Agent
from offline_chat.manager import AgentManager
from offline_chat.rag.models import KnowledgeSource, RAGConfig
from offline_chat.rag.vector_store import VectorStore


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_ollama(monkeypatch):
    """Mock Ollama subprocess calls."""

    def mock_run(*args, **kwargs):
        if args and len(args[0]) > 0 and args[0][0] == "ollama":

            class MockResult:
                returncode = 0
                stderr = ""
                stdout = "success"

            return MockResult()
        # For other commands, raise to avoid unexpected calls
        raise RuntimeError(f"Unexpected subprocess call: {args}")

    monkeypatch.setattr(subprocess, "run", mock_run)


def test_create_rag_enabled_agent(temp_data_dir, mock_ollama, monkeypatch):
    """
    Test creating a RAG-enabled agent.

    **Validates: Requirements 1.5, 7.2**

    This test verifies that:
    1. An agent with RAG configuration can be created
    2. The agent's configuration is saved correctly
    3. A vector collection is created for the agent
    4. The collection has the correct metadata
    """
    # Set environment variable to use temp directory
    monkeypatch.setenv("OFFLINE_CHAT_DATA_DIR", str(temp_data_dir))

    # Create agent manager
    manager = AgentManager()

    # Create a RAG-enabled agent
    agent = Agent(
        name="test-rag-agent",
        display_name="Test RAG Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant with RAG capabilities.",
        temperature=0.7,
        rag_config=RAGConfig(
            enabled=True,
            top_k=5,
            min_similarity=0.3,
            chunk_size=512,
            chunk_overlap=50,
            embedding_model="all-MiniLM-L6-v2",
            knowledge_sources=[
                KnowledgeSource(source_type="web", identifier="https://example.com/docs", status="pending")
            ],
        ),
        created_at=datetime.now(),
    )

    # Create the agent
    result = manager.create_agent(agent)
    assert result is True, "Agent creation should succeed"

    # Verify agent exists
    assert manager.agent_exists("test-rag-agent"), "Agent should exist after creation"

    # Load the agent and verify RAG config
    loaded_agent = manager.get_agent("test-rag-agent")
    assert loaded_agent is not None, "Should be able to load the agent"
    assert loaded_agent.rag_config is not None, "Agent should have RAG config"
    assert loaded_agent.rag_config.enabled is True, "RAG should be enabled"
    assert loaded_agent.rag_config.top_k == 5, "top_k should be preserved"
    assert loaded_agent.rag_config.min_similarity == 0.3, "min_similarity should be preserved"
    assert len(loaded_agent.rag_config.knowledge_sources) == 1, "Knowledge sources should be preserved"

    # Verify vector collection was created
    rag_dir = temp_data_dir / "rag"
    vector_store = VectorStore(rag_dir)
    collection_info = vector_store.get_collection_info("test-rag-agent")

    assert collection_info is not None, "Vector collection should be created"
    assert collection_info["name"] == "test-rag-agent", "Collection name should match agent name"
    assert "embedding_dimension" in collection_info["metadata"], "Collection should have embedding dimension"
    assert collection_info["count"] == 0, "Collection should be empty initially"


def test_load_rag_enabled_agent(temp_data_dir, mock_ollama, monkeypatch):
    """
    Test loading a RAG-enabled agent and initializing RAG components.

    **Validates: Requirements 1.5**

    This test verifies that:
    1. A RAG-enabled agent can be loaded
    2. RAG orchestrator can be initialized for the agent
    3. All RAG components are properly configured
    """
    # Set environment variable to use temp directory
    monkeypatch.setenv("OFFLINE_CHAT_DATA_DIR", str(temp_data_dir))

    # Create agent manager
    manager = AgentManager()

    # Create a RAG-enabled agent
    agent = Agent(
        name="test-load-agent",
        display_name="Test Load Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        rag_config=RAGConfig(
            enabled=True,
            top_k=10,
            min_similarity=0.5,
            chunk_size=256,
            chunk_overlap=25,
            embedding_model="all-MiniLM-L6-v2",
            knowledge_sources=[],
        ),
        created_at=datetime.now(),
    )

    # Create the agent
    manager.create_agent(agent)

    # Load the agent
    loaded_agent = manager.get_agent("test-load-agent")
    assert loaded_agent is not None, "Should be able to load the agent"

    # Initialize RAG orchestrator
    orchestrator = manager.get_rag_orchestrator(loaded_agent)

    assert orchestrator is not None, "Should be able to initialize RAG orchestrator"
    assert orchestrator.agent_config.name == "test-load-agent", "Orchestrator should have correct agent config"
    assert orchestrator.vector_store is not None, "Orchestrator should have vector store"
    assert orchestrator.embedding_generator is not None, "Orchestrator should have embedding generator"
    assert orchestrator.context_retriever is not None, "Orchestrator should have context retriever"
    assert orchestrator.document_processor is not None, "Orchestrator should have document processor"
    assert orchestrator.prompt_augmenter is not None, "Orchestrator should have prompt augmenter"


def test_delete_rag_enabled_agent_with_cleanup(temp_data_dir, mock_ollama, monkeypatch):
    """
    Test deleting a RAG-enabled agent with vector collection cleanup.

    **Validates: Requirements 7.4**

    This test verifies that:
    1. A RAG-enabled agent can be deleted
    2. The vector collection is deleted when requested
    3. Agent files are removed
    4. History is removed
    """
    # Set environment variable to use temp directory
    monkeypatch.setenv("OFFLINE_CHAT_DATA_DIR", str(temp_data_dir))

    # Create agent manager
    manager = AgentManager()

    # Create a RAG-enabled agent
    agent = Agent(
        name="test-delete-agent",
        display_name="Test Delete Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
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
        created_at=datetime.now(),
    )

    # Create the agent
    manager.create_agent(agent)

    # Verify agent and collection exist
    assert manager.agent_exists("test-delete-agent"), "Agent should exist"

    rag_dir = temp_data_dir / "rag"
    vector_store = VectorStore(rag_dir)
    collection_info = vector_store.get_collection_info("test-delete-agent")
    assert collection_info is not None, "Collection should exist"

    # Delete the agent with collection cleanup
    result = manager.delete_agent("test-delete-agent", delete_rag_collection=True)
    assert result is True, "Agent deletion should succeed"

    # Verify agent no longer exists
    assert not manager.agent_exists("test-delete-agent"), "Agent should not exist after deletion"

    # Verify collection was deleted
    collection_info = vector_store.get_collection_info("test-delete-agent")
    assert collection_info is None, "Collection should be deleted"


def test_delete_rag_enabled_agent_keep_collection(temp_data_dir, mock_ollama, monkeypatch):
    """
    Test deleting a RAG-enabled agent while keeping the vector collection.

    **Validates: Requirements 7.4**

    This test verifies that:
    1. A RAG-enabled agent can be deleted
    2. The vector collection is preserved when requested
    3. Agent files are removed but collection remains
    """
    # Set environment variable to use temp directory
    monkeypatch.setenv("OFFLINE_CHAT_DATA_DIR", str(temp_data_dir))

    # Create agent manager
    manager = AgentManager()

    # Create a RAG-enabled agent
    agent = Agent(
        name="test-keep-collection",
        display_name="Test Keep Collection",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
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
        created_at=datetime.now(),
    )

    # Create the agent
    manager.create_agent(agent)

    # Verify agent and collection exist
    assert manager.agent_exists("test-keep-collection"), "Agent should exist"

    rag_dir = temp_data_dir / "rag"
    vector_store = VectorStore(rag_dir)
    collection_info = vector_store.get_collection_info("test-keep-collection")
    assert collection_info is not None, "Collection should exist"

    # Delete the agent WITHOUT collection cleanup
    result = manager.delete_agent("test-keep-collection", delete_rag_collection=False)
    assert result is True, "Agent deletion should succeed"

    # Verify agent no longer exists
    assert not manager.agent_exists("test-keep-collection"), "Agent should not exist after deletion"

    # Verify collection still exists
    collection_info = vector_store.get_collection_info("test-keep-collection")
    assert collection_info is not None, "Collection should still exist when delete_rag_collection=False"


def test_create_non_rag_agent_no_collection(temp_data_dir, mock_ollama, monkeypatch):
    """
    Test that creating a non-RAG agent does not create a vector collection.

    **Validates: Requirements 7.2**

    This test verifies that:
    1. An agent without RAG can be created
    2. No vector collection is created for non-RAG agents
    """
    # Set environment variable to use temp directory
    monkeypatch.setenv("OFFLINE_CHAT_DATA_DIR", str(temp_data_dir))

    # Create agent manager
    manager = AgentManager()

    # Create a non-RAG agent
    agent = Agent(
        name="test-non-rag",
        display_name="Test Non-RAG Agent",
        base_model="llama3:latest",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        rag_config=None,  # No RAG config
        created_at=datetime.now(),
    )

    # Create the agent
    result = manager.create_agent(agent)
    assert result is True, "Agent creation should succeed"

    # Verify agent exists
    assert manager.agent_exists("test-non-rag"), "Agent should exist after creation"

    # Verify NO vector collection was created
    rag_dir = temp_data_dir / "rag"
    vector_store = VectorStore(rag_dir)
    collection_info = vector_store.get_collection_info("test-non-rag")

    assert collection_info is None, "No collection should be created for non-RAG agent"

    # Verify get_rag_orchestrator returns None for non-RAG agent
    loaded_agent = manager.get_agent("test-non-rag")
    orchestrator = manager.get_rag_orchestrator(loaded_agent)
    assert orchestrator is None, "RAG orchestrator should be None for non-RAG agent"
