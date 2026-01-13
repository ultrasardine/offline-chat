"""Tests for History storage.

This module contains property-based tests and unit tests for the Message,
ConversationHistory, and HistoryStore classes.
"""

from datetime import datetime
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import ConversationHistory, HistoryStore, Message


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
