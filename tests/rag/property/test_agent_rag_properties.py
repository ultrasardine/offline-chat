"""
Property-based tests for agent RAG integration.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.agent import Agent
from offline_chat.rag.models import KnowledgeSource, RAGConfig


# Strategy for generating valid agent names (kebab-case)
@st.composite
def agent_name_strategy(draw):
    """Generate valid agent names in kebab-case format."""
    # Generate 1-3 words, each at least 2 characters
    num_words = draw(st.integers(min_value=1, max_value=3))
    words = []
    for _ in range(num_words):
        word = draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll",), min_codepoint=97, max_codepoint=122),
            min_size=2,
            max_size=10
        ))
        words.append(word)

    name = "-".join(words)

    # Ensure the name is at least 3 characters (ChromaDB requirement)
    if len(name) < 3:
        name = name + "abc"

    return name


# Strategy for generating RAGConfig objects
@st.composite
def rag_config_strategy(draw):
    """Generate valid RAGConfig objects."""
    # Always enable RAG for this test
    enabled = True

    # Generate RAG parameters
    top_k = draw(st.integers(min_value=1, max_value=20))
    min_similarity = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    chunk_size = draw(st.integers(min_value=100, max_value=2000))
    chunk_overlap = draw(st.integers(min_value=0, max_value=200))
    embedding_model = draw(st.sampled_from([
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2",
        "paraphrase-MiniLM-L6-v2"
    ]))

    # Generate 0-3 knowledge sources
    num_sources = draw(st.integers(min_value=0, max_value=3))
    knowledge_sources = []

    for i in range(num_sources):
        source_type = draw(st.sampled_from(["web", "database"]))

        if source_type == "web":
            # Generate a simple URL
            domain = draw(st.text(
                alphabet=st.characters(whitelist_categories=("Ll",), min_codepoint=97, max_codepoint=122),
                min_size=3,
                max_size=15
            ))
            identifier = f"https://{domain}.com"
        else:  # database
            # Generate a table name
            identifier = draw(st.text(
                alphabet=st.characters(whitelist_categories=("Ll",), min_codepoint=97, max_codepoint=122),
                min_size=3,
                max_size=30
            ))

        knowledge_sources.append(KnowledgeSource(
            source_type=source_type,
            identifier=identifier,
            status="pending"
        ))

    return RAGConfig(
        enabled=enabled,
        top_k=top_k,
        min_similarity=min_similarity,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        knowledge_sources=knowledge_sources
    )


# Strategy for generating Agent objects with RAG config
@st.composite
def agent_with_rag_strategy(draw):
    """Generate valid Agent objects with RAG configuration."""
    name = draw(agent_name_strategy())
    display_name = draw(st.text(min_size=1, max_size=50))
    base_model = draw(st.sampled_from(["llama3:latest", "mistral:latest", "llama2:latest"]))
    system_prompt = draw(st.text(min_size=10, max_size=200))
    temperature = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    rag_config = draw(rag_config_strategy())

    return Agent(
        name=name,
        display_name=display_name,
        base_model=base_model,
        system_prompt=system_prompt,
        temperature=temperature,
        rag_config=rag_config,
        created_at=datetime.now()
    )


@pytest.mark.property_test
class TestAgentRAGProperties:
    """Property-based tests for agent RAG integration."""

    @given(agent=agent_with_rag_strategy())
    @settings(max_examples=10, deadline=None)
    def test_agent_collection_creation(self, agent):
        """
        **Validates: Requirements 7.2**

        Property 16: Agent Collection Creation

        For any agent created with RAG enabled, a corresponding vector store
        collection should be created with the agent's name.

        This property ensures that when an agent is configured with RAG capabilities,
        the necessary vector storage infrastructure is automatically provisioned,
        allowing the agent to store and retrieve knowledge from its configured sources.
        """
        # RAG is always enabled by the strategy
        assert agent.rag_config and agent.rag_config.enabled, \
            "Test expects RAG to be enabled"

        # Create temporary directories for testing
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Set environment variable to override data directory
            import os
            original_env = os.environ.get("OFFLINE_CHAT_DATA_DIR")
            os.environ["OFFLINE_CHAT_DATA_DIR"] = str(temp_dir)

            # Create agent manager (will use temp_dir as data directory)
            from offline_chat.manager import AgentManager
            manager = AgentManager()

            # Mock the Ollama create command to avoid actual model creation
            import subprocess
            original_run = subprocess.run

            def mock_run(*args, **kwargs):
                # Check if this is an ollama create command
                if args and len(args[0]) > 0 and args[0][0] == "ollama":
                    # Return success
                    class MockResult:
                        returncode = 0
                        stderr = ""
                        stdout = "success"
                    return MockResult()
                # For other commands, use original
                return original_run(*args, **kwargs)

            subprocess.run = mock_run

            try:
                # Create the agent
                manager.create_agent(agent)

                # Verify that the agent was created
                assert manager.agent_exists(agent.name), \
                    f"Agent '{agent.name}' should exist after creation"

                # Verify that the vector collection was created
                # Import vector store to check collection
                from offline_chat.rag.vector_store import VectorStore

                rag_dir = temp_dir / "rag"
                vector_store = VectorStore(rag_dir)

                # Get collection info
                collection_info = vector_store.get_collection_info(agent.name)

                # Requirement 7.2: Collection should be created with agent's name
                assert collection_info is not None, \
                    f"Vector collection should be created for RAG-enabled agent '{agent.name}'"

                assert collection_info["name"] == agent.name, \
                    f"Collection name should match agent name '{agent.name}'"

                # Verify that the collection has the correct metadata
                assert "metadata" in collection_info, \
                    "Collection should have metadata"

                # The collection should have embedding_dimension in metadata
                assert "embedding_dimension" in collection_info["metadata"], \
                    "Collection metadata should include embedding_dimension"

                # Verify that the embedding dimension is valid (positive integer)
                embedding_dim = collection_info["metadata"]["embedding_dimension"]
                assert isinstance(embedding_dim, int), \
                    "Embedding dimension should be an integer"
                assert embedding_dim > 0, \
                    f"Embedding dimension should be positive, got {embedding_dim}"

                # Verify that the collection is initially empty (no documents ingested yet)
                assert collection_info["count"] == 0, \
                    "Newly created collection should be empty (no documents ingested yet)"

            finally:
                # Restore original subprocess.run
                subprocess.run = original_run

                # Restore original environment variable
                if original_env is not None:
                    os.environ["OFFLINE_CHAT_DATA_DIR"] = original_env
                elif "OFFLINE_CHAT_DATA_DIR" in os.environ:
                    del os.environ["OFFLINE_CHAT_DATA_DIR"]

        finally:
            # Clean up temporary directories
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    @given(agent=agent_with_rag_strategy())
    @settings(max_examples=10, deadline=None)
    def test_agent_without_rag_no_collection(self, agent):
        """
        Test that agents without RAG enabled do not create vector collections.

        This ensures that the vector store infrastructure is only created when
        needed, avoiding unnecessary resource usage for non-RAG agents.
        """
        # Force RAG to be disabled
        if agent.rag_config:
            agent.rag_config.enabled = False
        else:
            agent.rag_config = RAGConfig(enabled=False)

        # Create temporary directories for testing
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Set environment variable to override data directory
            import os
            original_env = os.environ.get("OFFLINE_CHAT_DATA_DIR")
            os.environ["OFFLINE_CHAT_DATA_DIR"] = str(temp_dir)

            # Create agent manager
            from offline_chat.manager import AgentManager
            manager = AgentManager()

            # Mock the Ollama create command
            import subprocess
            original_run = subprocess.run

            def mock_run(*args, **kwargs):
                if args and len(args[0]) > 0 and args[0][0] == "ollama":
                    class MockResult:
                        returncode = 0
                        stderr = ""
                        stdout = "success"
                    return MockResult()
                return original_run(*args, **kwargs)

            subprocess.run = mock_run

            try:
                # Create the agent
                manager.create_agent(agent)

                # Verify that the agent was created
                assert manager.agent_exists(agent.name), \
                    f"Agent '{agent.name}' should exist after creation"

                # Verify that NO vector collection was created
                from offline_chat.rag.vector_store import VectorStore

                rag_dir = temp_dir / "rag"
                vector_store = VectorStore(rag_dir)

                # Get collection info
                collection_info = vector_store.get_collection_info(agent.name)

                # Collection should NOT exist for non-RAG agents
                assert collection_info is None, \
                    f"Vector collection should NOT be created for non-RAG agent '{agent.name}'"

            finally:
                # Restore original subprocess.run
                subprocess.run = original_run

                # Restore original environment variable
                if original_env is not None:
                    os.environ["OFFLINE_CHAT_DATA_DIR"] = original_env
                elif "OFFLINE_CHAT_DATA_DIR" in os.environ:
                    del os.environ["OFFLINE_CHAT_DATA_DIR"]

        finally:
            # Clean up temporary directories
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
