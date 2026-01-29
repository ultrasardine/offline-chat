"""Tests for History storage.

This module contains property-based tests and unit tests for the Message,
ConversationHistory, and HistoryStore classes.
"""

from datetime import datetime
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import ConversationHistory, HistoryStore, Message
from offline_chat.rag.models import SourceCitation


# Strategy for generating valid Message objects
def valid_message_strategy():
    """Generate valid Message objects for property testing."""
    return st.builds(
        Message,
        role=st.sampled_from(["user", "assistant"]),
        content=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
        sources=st.none(),  # Non-RAG messages have no sources
    )


# Strategy for generating SourceCitation objects
def valid_source_citation_strategy():
    """Generate valid SourceCitation objects for property testing."""
    return st.builds(
        SourceCitation,
        source_type=st.sampled_from(["web", "database"]),
        identifier=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        relevance_score=st.floats(min_value=0.0, max_value=1.0),
    )


# Strategy for generating Message objects with RAG sources
def valid_rag_message_strategy():
    """Generate valid RAG-enhanced Message objects for property testing."""
    return st.builds(
        Message,
        role=st.sampled_from(["user", "assistant"]),
        content=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
        sources=st.lists(valid_source_citation_strategy(), min_size=1, max_size=5),
    )


# Strategy for generating valid kebab-case agent names
def valid_agent_name_strategy():
    """Generate valid kebab-case agent names."""
    segment = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=1,
        max_size=10,
    )
    return st.lists(segment, min_size=1, max_size=3).map(lambda parts: "-".join(parts))


# Strategy for generating valid ConversationHistory objects
def valid_history_strategy():
    """Generate valid ConversationHistory objects for property testing."""
    return st.builds(
        ConversationHistory,
        agent_name=valid_agent_name_strategy(),
        messages=st.lists(valid_message_strategy(), min_size=0, max_size=20),
        last_updated=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestHistorySerializationRoundTrip:
    """Property 8: History Serialization Round-Trip.

    Feature: offline-chat, Property 8: History Serialization Round-Trip
    Validates: Requirements 5.1, 5.2, 5.3

    For any valid ConversationHistory object, saving it to JSON and then
    loading it SHALL produce an equivalent ConversationHistory with all
    messages, timestamps, and metadata preserved.
    """

    @settings(max_examples=100)
    @given(history=valid_history_strategy())
    def test_history_serialization_round_trip(self, history: ConversationHistory):
        """Saving and loading a ConversationHistory should preserve all fields."""
        import tempfile

        # Create a temporary directory for each test run
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a HistoryStore with the temp directory
            store = HistoryStore(history_dir=tmp_path)

            # Save the history
            store.save(history)

            # Load it back
            restored = store.load(history.agent_name)

            # Verify all fields are preserved
            assert restored.agent_name == history.agent_name
            assert restored.last_updated == history.last_updated
            assert len(restored.messages) == len(history.messages)

            # Verify each message is preserved
            for original_msg, restored_msg in zip(history.messages, restored.messages):
                assert restored_msg.role == original_msg.role
                assert restored_msg.content == original_msg.content
                assert restored_msg.timestamp == original_msg.timestamp

    @settings(max_examples=100)
    @given(history=valid_history_strategy())
    def test_to_dict_from_dict_round_trip(self, history: ConversationHistory):
        """to_dict and from_dict should preserve all fields."""
        # Serialize to dict
        data = history.to_dict()

        # Deserialize back
        restored = ConversationHistory.from_dict(data)

        # Verify all fields are preserved
        assert restored.agent_name == history.agent_name
        assert restored.last_updated == history.last_updated
        assert len(restored.messages) == len(history.messages)

        for original_msg, restored_msg in zip(history.messages, restored.messages):
            assert restored_msg.role == original_msg.role
            assert restored_msg.content == original_msg.content
            assert restored_msg.timestamp == original_msg.timestamp

    @settings(max_examples=100)
    @given(message=valid_message_strategy())
    def test_message_serialization_round_trip(self, message: Message):
        """Message to_dict and from_dict should preserve all fields."""
        data = message.to_dict()
        restored = Message.from_dict(data)

        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.timestamp == message.timestamp


class TestHistoryStoreOperations:
    """Unit tests for HistoryStore operations."""

    def test_load_nonexistent_returns_empty_history(self, tmp_path: Path):
        """Loading history for non-existent agent returns empty history."""
        store = HistoryStore(history_dir=tmp_path)

        history = store.load("nonexistent-agent")

        assert history.agent_name == "nonexistent-agent"
        assert len(history.messages) == 0

    def test_save_creates_directory_if_needed(self, tmp_path: Path):
        """Save should create the history directory if it doesn't exist."""
        history_dir = tmp_path / "nested" / "history"
        store = HistoryStore(history_dir=history_dir)

        history = ConversationHistory(agent_name="test-agent")
        store.save(history)

        assert history_dir.exists()
        assert (history_dir / "test-agent.json").exists()

    def test_delete_removes_history_file(self, tmp_path: Path):
        """Delete should remove the history file."""
        store = HistoryStore(history_dir=tmp_path)

        # Create and save a history
        history = ConversationHistory(
            agent_name="test-agent",
            messages=[Message(role="user", content="Hello")],
        )
        store.save(history)

        # Verify file exists
        history_path = tmp_path / "test-agent.json"
        assert history_path.exists()

        # Delete and verify
        store.delete("test-agent")
        assert not history_path.exists()

    def test_delete_nonexistent_does_nothing(self, tmp_path: Path):
        """Delete should not raise error for non-existent history."""
        store = HistoryStore(history_dir=tmp_path)

        # Should not raise
        store.delete("nonexistent-agent")

    def test_specific_round_trip_example(self, tmp_path: Path):
        """Unit test for a specific round-trip example."""
        store = HistoryStore(history_dir=tmp_path)

        original = ConversationHistory(
            agent_name="german-tutor",
            messages=[
                Message(
                    role="user",
                    content="How do I say hello?",
                    timestamp=datetime(2025, 1, 13, 10, 30, 0),
                ),
                Message(
                    role="assistant",
                    content="In German, you say 'Hallo' for a casual greeting.",
                    timestamp=datetime(2025, 1, 13, 10, 30, 5),
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 30, 5),
        )

        store.save(original)
        restored = store.load("german-tutor")

        assert restored.agent_name == original.agent_name
        assert restored.last_updated == original.last_updated
        assert len(restored.messages) == 2
        assert restored.messages[0].content == "How do I say hello?"
        assert restored.messages[1].content == "In German, you say 'Hallo' for a casual greeting."


class TestMessageWithSourceCitations:
    """Tests for Message dataclass with RAG source citations.

    Feature: rag-capabilities
    Validates: Requirements 11.1, 11.3, 11.4, 11.5
    """

    @settings(max_examples=100)
    @given(message=valid_rag_message_strategy())
    def test_rag_message_serialization_round_trip(self, message: Message):
        """RAG-enhanced Message to_dict and from_dict should preserve sources.

        Property 19: Conversation History Round-Trip with RAG Metadata
        Validates: Requirements 11.1, 11.3, 11.4
        """
        data = message.to_dict()
        restored = Message.from_dict(data)

        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.timestamp == message.timestamp

        # Verify sources are preserved
        assert restored.sources is not None
        assert len(restored.sources) == len(message.sources)

        for original_source, restored_source in zip(message.sources, restored.sources):
            assert restored_source.source_type == original_source.source_type
            assert restored_source.identifier == original_source.identifier
            assert restored_source.relevance_score == original_source.relevance_score

    def test_backward_compatibility_with_non_rag_messages(self):
        """Messages without sources field should deserialize correctly.

        Validates: Requirement 11.5 - Backward compatibility
        """
        # Simulate old message format without sources field
        old_format_data = {
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": "2025-01-13T10:30:00",
        }

        message = Message.from_dict(old_format_data)

        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.sources is None

    def test_message_with_none_sources_serializes_without_sources_field(self):
        """Non-RAG messages should not include sources in serialized output.

        Validates: Requirement 11.5 - Backward compatibility
        """
        message = Message(
            role="assistant",
            content="I'm doing well, thank you!",
            timestamp=datetime(2025, 1, 13, 10, 30, 5),
            sources=None,
        )

        data = message.to_dict()

        assert "sources" not in data
        assert data["role"] == "assistant"
        assert data["content"] == "I'm doing well, thank you!"

    def test_message_with_empty_sources_list(self):
        """Message with empty sources list should serialize correctly."""
        message = Message(
            role="assistant",
            content="No sources found.",
            timestamp=datetime(2025, 1, 13, 10, 30, 5),
            sources=[],
        )

        data = message.to_dict()

        # Empty list should still be included
        assert "sources" in data
        assert data["sources"] == []

        # Round-trip should preserve empty list
        restored = Message.from_dict(data)
        assert restored.sources == []

    def test_rag_message_with_multiple_source_types(self):
        """Message with mixed web and database sources should serialize correctly."""
        sources = [
            SourceCitation(
                source_type="web",
                identifier="https://example.com/article",
                relevance_score=0.95,
            ),
            SourceCitation(
                source_type="database",
                identifier="products_table",
                relevance_score=0.87,
            ),
        ]

        message = Message(
            role="assistant",
            content="Based on the documentation and database...",
            timestamp=datetime(2025, 1, 13, 10, 30, 5),
            sources=sources,
        )

        data = message.to_dict()
        restored = Message.from_dict(data)

        assert len(restored.sources) == 2
        assert restored.sources[0].source_type == "web"
        assert restored.sources[0].identifier == "https://example.com/article"
        assert restored.sources[1].source_type == "database"
        assert restored.sources[1].identifier == "products_table"


class TestConversationHistoryWithRAG:
    """Tests for ConversationHistory with RAG-enhanced messages.

    Feature: rag-capabilities
    Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
    """

    def test_mixed_rag_and_non_rag_messages(self, tmp_path: Path):
        """History with both RAG and non-RAG messages should serialize correctly.

        Validates: Requirement 11.5 - Backward compatibility
        """
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="test-agent",
            messages=[
                Message(
                    role="user",
                    content="What is Python?",
                    timestamp=datetime(2025, 1, 13, 10, 30, 0),
                    sources=None,  # User messages don't have sources
                ),
                Message(
                    role="assistant",
                    content="Python is a programming language...",
                    timestamp=datetime(2025, 1, 13, 10, 30, 5),
                    sources=[
                        SourceCitation(
                            source_type="web",
                            identifier="https://python.org/about",
                            relevance_score=0.92,
                        )
                    ],
                ),
                Message(
                    role="user",
                    content="Tell me more",
                    timestamp=datetime(2025, 1, 13, 10, 31, 0),
                    sources=None,
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 31, 0),
        )

        store.save(history)
        restored = store.load("test-agent")

        assert len(restored.messages) == 3
        assert restored.messages[0].sources is None
        assert restored.messages[1].sources is not None
        assert len(restored.messages[1].sources) == 1
        assert restored.messages[2].sources is None

    @settings(max_examples=50)
    @given(
        agent_name=valid_agent_name_strategy(),
        rag_messages=st.lists(valid_rag_message_strategy(), min_size=1, max_size=10),
    )
    def test_history_with_rag_messages_round_trip(self, agent_name: str, rag_messages: list[Message]):
        """History with RAG messages should preserve all source citations.

        Property 19: Conversation History Round-Trip with RAG Metadata
        Validates: Requirements 11.1, 11.3, 11.4
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            store = HistoryStore(history_dir=tmp_path)

            history = ConversationHistory(
                agent_name=agent_name,
                messages=rag_messages,
                last_updated=datetime.now(),
            )

            store.save(history)
            restored = store.load(agent_name)

            assert len(restored.messages) == len(history.messages)

            for original_msg, restored_msg in zip(history.messages, restored.messages):
                assert restored_msg.role == original_msg.role
                assert restored_msg.content == original_msg.content
                assert restored_msg.timestamp == original_msg.timestamp

                # Verify sources are preserved
                if original_msg.sources is not None:
                    assert restored_msg.sources is not None
                    assert len(restored_msg.sources) == len(original_msg.sources)

                    for orig_src, rest_src in zip(original_msg.sources, restored_msg.sources):
                        assert rest_src.source_type == orig_src.source_type
                        assert rest_src.identifier == orig_src.identifier
                        assert rest_src.relevance_score == orig_src.relevance_score

    def test_source_citation_completeness(self):
        """Source citations should include all required fields.

        Property 15: Source Citation Completeness
        Validates: Requirements 6.3, 6.4
        """
        # Test web source
        web_source = SourceCitation(
            source_type="web",
            identifier="https://example.com/docs",
            relevance_score=0.88,
        )

        assert web_source.source_type == "web"
        assert web_source.identifier == "https://example.com/docs"
        assert 0.0 <= web_source.relevance_score <= 1.0

        # Test database source
        db_source = SourceCitation(
            source_type="database",
            identifier="users_table",
            relevance_score=0.75,
        )

        assert db_source.source_type == "database"
        assert db_source.identifier == "users_table"
        assert 0.0 <= db_source.relevance_score <= 1.0

    def test_message_format_for_display_with_sources(self):
        """RAG-enhanced messages should format with source citations.

        Validates: Requirement 11.2 - Display includes sources
        """
        # Create a RAG-enhanced message
        message = Message(
            role="assistant",
            content="Python is a high-level programming language.",
            timestamp=datetime(2025, 1, 13, 14, 30, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://python.org/about",
                    relevance_score=0.92,
                ),
                SourceCitation(
                    source_type="database",
                    identifier="programming_languages",
                    relevance_score=0.85,
                ),
            ],
        )

        # Format for display
        formatted = message.format_for_display(agent_display_name="Python Expert")

        # Verify the formatted output includes the message content
        assert "Python is a high-level programming language." in formatted

        # Verify it includes the timestamp
        assert "14:30" in formatted

        # Verify it includes the agent name
        assert "Python Expert" in formatted

        # Verify it includes source citations
        assert "Sources:" in formatted
        assert "[Web] https://python.org/about" in formatted
        assert "[Database] programming_languages" in formatted

    def test_message_format_for_display_without_sources(self):
        """Non-RAG messages should format without source citations.

        Validates: Requirement 11.5 - Backward compatibility
        """
        # Create a non-RAG message
        message = Message(
            role="user",
            content="What is Python?",
            timestamp=datetime(2025, 1, 13, 14, 29, 0),
            sources=None,
        )

        # Format for display
        formatted = message.format_for_display()

        # Verify the formatted output includes the message content
        assert "What is Python?" in formatted

        # Verify it includes the timestamp
        assert "14:29" in formatted

        # Verify it includes "You:" for user messages
        assert "You:" in formatted

        # Verify it does NOT include source citations
        assert "Sources:" not in formatted
        assert "[Web]" not in formatted
        assert "[Database]" not in formatted
