"""Integration tests for Agent with RAG configuration.

This module tests the complete integration of RAG config with agent persistence.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from offline_chat.agent import Agent
from offline_chat.rag.models import KnowledgeSource, RAGConfig


class TestAgentRAGIntegration:
    """Integration tests for Agent with RAG configuration persistence."""

    def test_agent_rag_config_file_persistence(self):
        """Integration test: RAG config persists to and loads from JSON file."""
        # Create agent with RAG config
        rag_config = RAGConfig(
            enabled=True,
            top_k=8,
            min_similarity=0.35,
            chunk_size=1024,
            chunk_overlap=100,
            embedding_model="all-mpnet-base-v2",
            knowledge_sources=[
                KnowledgeSource(
                    source_type="web",
                    identifier="https://example.com/api",
                    last_indexed=datetime(2025, 1, 12, 14, 30, 0),
                    status="active",
                ),
                KnowledgeSource(
                    source_type="database",
                    identifier="customers",
                    status="pending",
                ),
            ],
        )

        original = Agent(
            name="rag-test-agent",
            display_name="RAG Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent with RAG.",
            temperature=0.8,
            rag_config=rag_config,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(original.to_dict(), f, indent=2)
            temp_path = Path(f.name)

        try:
            # Read from file
            with open(temp_path) as f:
                data = json.load(f)

            # Deserialize
            restored = Agent.from_dict(data)

            # Verify all fields including RAG config
            assert restored.name == original.name
            assert restored.display_name == original.display_name
            assert restored.rag_config is not None
            assert restored.rag_config.enabled is True
            assert restored.rag_config.top_k == 8
            assert restored.rag_config.min_similarity == 0.35
            assert restored.rag_config.chunk_size == 1024
            assert restored.rag_config.chunk_overlap == 100
            assert restored.rag_config.embedding_model == "all-mpnet-base-v2"
            assert len(restored.rag_config.knowledge_sources) == 2

            # Verify knowledge sources
            web_source = restored.rag_config.knowledge_sources[0]
            assert web_source.source_type == "web"
            assert web_source.identifier == "https://example.com/api"
            assert web_source.status == "active"
            assert web_source.last_indexed == datetime(2025, 1, 12, 14, 30, 0)

            db_source = restored.rag_config.knowledge_sources[1]
            assert db_source.source_type == "database"
            assert db_source.identifier == "customers"
            assert db_source.status == "pending"
            assert db_source.last_indexed is None

        finally:
            # Clean up
            temp_path.unlink()

    def test_agent_without_rag_config_file_persistence(self):
        """Integration test: Agent without RAG config persists correctly."""
        original = Agent(
            name="simple-agent",
            display_name="Simple Agent",
            base_model="llama3:latest",
            system_prompt="You are a simple agent.",
            temperature=0.7,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(original.to_dict(), f, indent=2)
            temp_path = Path(f.name)

        try:
            # Read from file
            with open(temp_path) as f:
                data = json.load(f)

            # Verify rag_config is not in the JSON
            assert "rag_config" not in data

            # Deserialize
            restored = Agent.from_dict(data)

            # Verify rag_config is None
            assert restored.rag_config is None

        finally:
            # Clean up
            temp_path.unlink()

    def test_mixed_agents_file_persistence(self):
        """Integration test: Mix of agents with and without RAG config."""
        agents = [
            Agent(
                name="rag-agent",
                display_name="RAG Agent",
                base_model="llama3:latest",
                system_prompt="RAG enabled",
                rag_config=RAGConfig(enabled=True, top_k=10),
                created_at=datetime(2025, 1, 13, 10, 0, 0),
            ),
            Agent(
                name="simple-agent",
                display_name="Simple Agent",
                base_model="llama3:latest",
                system_prompt="No RAG",
                created_at=datetime(2025, 1, 13, 10, 0, 0),
            ),
        ]

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([agent.to_dict() for agent in agents], f, indent=2)
            temp_path = Path(f.name)

        try:
            # Read from file
            with open(temp_path) as f:
                data = json.load(f)

            # Deserialize
            restored_agents = [Agent.from_dict(d) for d in data]

            # Verify first agent has RAG config
            assert restored_agents[0].rag_config is not None
            assert restored_agents[0].rag_config.enabled is True
            assert restored_agents[0].rag_config.top_k == 10

            # Verify second agent has no RAG config
            assert restored_agents[1].rag_config is None

        finally:
            # Clean up
            temp_path.unlink()
