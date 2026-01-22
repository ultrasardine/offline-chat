"""Unit tests for Agent RAG configuration serialization.

This module tests the integration of RAGConfig with the Agent class.
"""

from datetime import datetime

from offline_chat.agent import Agent
from offline_chat.rag.models import KnowledgeSource, RAGConfig


class TestAgentRAGConfigSerialization:
    """Unit tests for Agent with RAG configuration."""

    def test_agent_with_rag_config(self):
        """Unit test: agent with RAG configuration."""
        rag_config = RAGConfig(
            enabled=True,
            top_k=10,
            min_similarity=0.5,
            chunk_size=256,
            chunk_overlap=25,
            embedding_model="all-mpnet-base-v2",
            knowledge_sources=[
                KnowledgeSource(
                    source_type="web",
                    identifier="https://example.com/docs",
                    status="active",
                ),
                KnowledgeSource(
                    source_type="database",
                    identifier="employees",
                    status="pending",
                ),
            ],
        )

        agent = Agent(
            name="rag-agent",
            display_name="RAG Agent",
            base_model="llama3:latest",
            system_prompt="You are a RAG-enabled assistant.",
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        assert agent.rag_config is not None
        assert agent.rag_config.enabled is True
        assert agent.rag_config.top_k == 10
        assert len(agent.rag_config.knowledge_sources) == 2

    def test_agent_rag_config_serialization(self):
        """Unit test: RAG config round-trip serialization."""
        rag_config = RAGConfig(
            enabled=True,
            top_k=7,
            min_similarity=0.4,
            knowledge_sources=[
                KnowledgeSource(
                    source_type="web",
                    identifier="https://docs.python.org",
                    last_indexed=datetime(2025, 1, 10, 12, 0, 0),
                    status="active",
                ),
            ],
        )

        original = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        # Serialize
        data = original.to_dict()
        assert "rag_config" in data
        assert data["rag_config"]["enabled"] is True
        assert data["rag_config"]["top_k"] == 7
        assert data["rag_config"]["min_similarity"] == 0.4
        assert len(data["rag_config"]["knowledge_sources"]) == 1
        assert data["rag_config"]["knowledge_sources"][0]["source_type"] == "web"
        assert data["rag_config"]["knowledge_sources"][0]["identifier"] == "https://docs.python.org"

        # Deserialize
        restored = Agent.from_dict(data)
        assert restored.rag_config is not None
        assert restored.rag_config.enabled is True
        assert restored.rag_config.top_k == 7
        assert restored.rag_config.min_similarity == 0.4
        assert len(restored.rag_config.knowledge_sources) == 1
        assert restored.rag_config.knowledge_sources[0].source_type == "web"
        assert restored.rag_config.knowledge_sources[0].identifier == "https://docs.python.org"
        assert restored.rag_config.knowledge_sources[0].status == "active"

    def test_agent_without_rag_config(self):
        """Unit test: agent without RAG config."""
        agent = Agent(
            name="simple-agent",
            display_name="Simple Agent",
            base_model="llama3:latest",
            system_prompt="You are a simple agent.",
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        assert agent.rag_config is None

        # Serialize
        data = agent.to_dict()
        assert "rag_config" not in data

        # Deserialize
        restored = Agent.from_dict(data)
        assert restored.rag_config is None

    def test_backward_compatibility_missing_rag_config(self):
        """Unit test: legacy agent config without rag_config field."""
        legacy_data = {
            "name": "legacy-agent",
            "display_name": "Legacy Agent",
            "base_model": "llama3:latest",
            "system_prompt": "You are a legacy agent.",
            "temperature": 0.7,
            "language": "English",
            "web_search_enabled": False,
            "created_at": datetime.now().isoformat(),
            # rag_config intentionally omitted
        }

        agent = Agent.from_dict(legacy_data)

        assert agent.name == "legacy-agent"
        assert agent.rag_config is None

    def test_rag_config_with_all_defaults(self):
        """Unit test: RAG config with default values."""
        rag_config = RAGConfig()

        agent = Agent(
            name="default-rag-agent",
            display_name="Default RAG Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = agent.to_dict()
        restored = Agent.from_dict(data)

        assert restored.rag_config is not None
        assert restored.rag_config.enabled is False
        assert restored.rag_config.top_k == 5
        assert restored.rag_config.min_similarity == 0.3
        assert restored.rag_config.chunk_size == 512
        assert restored.rag_config.chunk_overlap == 50
        assert restored.rag_config.embedding_model == "all-MiniLM-L6-v2"
        assert restored.rag_config.knowledge_sources == []

    def test_rag_config_knowledge_source_with_error(self):
        """Unit test: knowledge source with error message."""
        rag_config = RAGConfig(
            enabled=True,
            knowledge_sources=[
                KnowledgeSource(
                    source_type="web",
                    identifier="https://invalid-url.com",
                    status="failed",
                    error_message="Connection timeout",
                ),
            ],
        )

        agent = Agent(
            name="error-agent",
            display_name="Error Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = agent.to_dict()
        restored = Agent.from_dict(data)

        assert len(restored.rag_config.knowledge_sources) == 1
        source = restored.rag_config.knowledge_sources[0]
        assert source.status == "failed"
        assert source.error_message == "Connection timeout"

    def test_rag_config_knowledge_source_last_indexed(self):
        """Unit test: knowledge source with last_indexed timestamp."""
        indexed_time = datetime(2025, 1, 10, 15, 30, 0)
        rag_config = RAGConfig(
            enabled=True,
            knowledge_sources=[
                KnowledgeSource(
                    source_type="database",
                    identifier="products",
                    last_indexed=indexed_time,
                    status="active",
                ),
            ],
        )

        agent = Agent(
            name="indexed-agent",
            display_name="Indexed Agent",
            base_model="llama3:latest",
            system_prompt="Test prompt",
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = agent.to_dict()
        restored = Agent.from_dict(data)

        assert len(restored.rag_config.knowledge_sources) == 1
        source = restored.rag_config.knowledge_sources[0]
        assert source.last_indexed == indexed_time
        assert source.status == "active"
