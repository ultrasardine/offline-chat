"""Unit tests for extended conversation history with RAG support.

This module contains unit tests specifically for task 13.6:
- Backward compatibility with old history files
- Source citation display formatting
- History with mixed RAG/non-RAG messages

Feature: rag-capabilities
Validates: Requirement 11.5
"""

import json
from datetime import datetime
from pathlib import Path

from offline_chat import ConversationHistory, HistoryStore, Message
from offline_chat.rag.models import SourceCitation


class TestBackwardCompatibility:
    """Unit tests for backward compatibility with old history files.

    Validates: Requirement 11.5 - Backward compatibility with non-RAG histories
    """

    def test_load_old_history_file_without_sources_field(self, tmp_path: Path):
        """Loading an old history file without sources field should work correctly.

        This simulates loading a history file created before RAG support was added.
        The file format doesn't include the 'sources' field in messages.
        """
        store = HistoryStore(history_dir=tmp_path)

        # Create an old-format history file manually (without sources field)
        old_format_data = {
            "agent_name": "legacy-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, how are you?",
                    "timestamp": "2025-01-10T10:00:00",
                },
                {
                    "role": "assistant",
                    "content": "I'm doing well, thank you!",
                    "timestamp": "2025-01-10T10:00:05",
                },
            ],
            "last_updated": "2025-01-10T10:00:05",
        }

        # Write the old format file
        history_path = tmp_path / "legacy-agent.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(old_format_data, f, indent=2)

        # Load the history using HistoryStore
        history = store.load("legacy-agent")

        # Verify the history loaded correctly
        assert history.agent_name == "legacy-agent"
        assert len(history.messages) == 2

        # Verify messages have no sources (backward compatibility)
        assert history.messages[0].sources is None
        assert history.messages[1].sources is None

        # Verify message content is preserved
        assert history.messages[0].role == "user"
        assert history.messages[0].content == "Hello, how are you?"
        assert history.messages[1].role == "assistant"
        assert history.messages[1].content == "I'm doing well, thank you!"

    def test_save_non_rag_message_maintains_old_format(self, tmp_path: Path):
        """Saving non-RAG messages should not add sources field to JSON.

        This ensures that agents without RAG continue to produce history files
        in the same format as before, maintaining backward compatibility.
        """
        store = HistoryStore(history_dir=tmp_path)

        # Create a history with non-RAG messages
        history = ConversationHistory(
            agent_name="non-rag-agent",
            messages=[
                Message(
                    role="user",
                    content="What is the weather?",
                    timestamp=datetime(2025, 1, 13, 10, 0, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="I don't have access to weather data.",
                    timestamp=datetime(2025, 1, 13, 10, 0, 5),
                    sources=None,
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 0, 5),
        )

        # Save the history
        store.save(history)

        # Read the JSON file directly
        history_path = tmp_path / "non-rag-agent.json"
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Verify sources field is NOT present in messages
        for message_data in data["messages"]:
            assert "sources" not in message_data

    def test_upgrade_old_history_to_rag_format(self, tmp_path: Path):
        """Old history can be loaded, modified with RAG messages, and saved.

        This tests the upgrade path where an existing agent gets RAG enabled
        and starts adding source citations to new messages.
        """
        store = HistoryStore(history_dir=tmp_path)

        # Create an old-format history file
        old_format_data = {
            "agent_name": "upgrade-agent",
            "messages": [
                {
                    "role": "user",
                    "content": "Tell me about Python",
                    "timestamp": "2025-01-10T10:00:00",
                },
                {
                    "role": "assistant",
                    "content": "Python is a programming language.",
                    "timestamp": "2025-01-10T10:00:05",
                },
            ],
            "last_updated": "2025-01-10T10:00:05",
        }

        history_path = tmp_path / "upgrade-agent.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(old_format_data, f, indent=2)

        # Load the old history
        history = store.load("upgrade-agent")

        # Add a new RAG-enhanced message (simulating RAG being enabled)
        history.messages.append(
            Message(
                role="user",
                content="What are Python's features?",
                timestamp=datetime(2025, 1, 13, 10, 0, 0),
                sources=None,
            )
        )
        history.messages.append(
            Message(
                role="assistant",
                content="Python has dynamic typing, automatic memory management...",
                timestamp=datetime(2025, 1, 13, 10, 0, 5),
                sources=[
                    SourceCitation(
                        source_type="web",
                        identifier="https://python.org/about",
                        relevance_score=0.92,
                    )
                ],
            )
        )
        history.last_updated = datetime(2025, 1, 13, 10, 0, 5)

        # Save the upgraded history
        store.save(history)

        # Load it back and verify
        restored = store.load("upgrade-agent")

        assert len(restored.messages) == 4
        # Old messages have no sources
        assert restored.messages[0].sources is None
        assert restored.messages[1].sources is None
        # New messages have sources
        assert restored.messages[2].sources is None  # User message
        assert restored.messages[3].sources is not None
        assert len(restored.messages[3].sources) == 1


class TestSourceCitationDisplayFormatting:
    """Unit tests for source citation display formatting.

    Validates: Requirement 11.2 - Display includes sources
    """

    def test_format_single_web_source(self):
        """Message with single web source should format correctly."""
        message = Message(
            role="assistant",
            content="Python was created by Guido van Rossum.",
            timestamp=datetime(2025, 1, 13, 14, 30, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://python.org/about",
                    relevance_score=0.95,
                )
            ],
        )

        formatted = message.format_for_display(agent_display_name="Python Expert")

        # Verify structure
        assert "[14:30] Python Expert: Python was created by Guido van Rossum." in formatted
        assert "Sources:" in formatted
        assert "[Web] https://python.org/about" in formatted

    def test_format_single_database_source(self):
        """Message with single database source should format correctly."""
        message = Message(
            role="assistant",
            content="Found 42 active users in the system.",
            timestamp=datetime(2025, 1, 13, 15, 45, 0),
            sources=[
                SourceCitation(
                    source_type="database",
                    identifier="users_table",
                    relevance_score=0.88,
                )
            ],
        )

        formatted = message.format_for_display(agent_display_name="DB Assistant")

        # Verify structure
        assert "[15:45] DB Assistant: Found 42 active users in the system." in formatted
        assert "Sources:" in formatted
        assert "[Database] users_table" in formatted

    def test_format_multiple_sources(self):
        """Message with multiple sources should list all sources."""
        message = Message(
            role="assistant",
            content="Based on documentation and database records...",
            timestamp=datetime(2025, 1, 13, 16, 20, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://docs.example.com/api",
                    relevance_score=0.92,
                ),
                SourceCitation(
                    source_type="database",
                    identifier="api_logs",
                    relevance_score=0.85,
                ),
                SourceCitation(
                    source_type="web",
                    identifier="https://stackoverflow.com/questions/12345",
                    relevance_score=0.78,
                ),
            ],
        )

        formatted = message.format_for_display(agent_display_name="API Expert")

        # Verify all sources are listed
        assert "Sources:" in formatted
        assert "[Web] https://docs.example.com/api" in formatted
        assert "[Database] api_logs" in formatted
        assert "[Web] https://stackoverflow.com/questions/12345" in formatted

        # Verify sources are on separate lines with proper indentation
        lines = formatted.split("\n")
        source_lines = [line for line in lines if line.strip().startswith("-")]
        assert len(source_lines) == 3

    def test_format_user_message_no_sources(self):
        """User messages should not show sources section."""
        message = Message(
            role="user",
            content="What is Python?",
            timestamp=datetime(2025, 1, 13, 14, 29, 0),
            sources=None,
        )

        formatted = message.format_for_display()

        # Verify structure
        assert "[14:29] You: What is Python?" in formatted
        assert "Sources:" not in formatted

    def test_format_assistant_message_no_sources(self):
        """Assistant messages without sources should not show sources section."""
        message = Message(
            role="assistant",
            content="I don't have information about that.",
            timestamp=datetime(2025, 1, 13, 14, 30, 0),
            sources=None,
        )

        formatted = message.format_for_display(agent_display_name="Helper")

        # Verify structure
        assert "[14:30] Helper: I don't have information about that." in formatted
        assert "Sources:" not in formatted

    def test_format_empty_sources_list(self):
        """Message with empty sources list should not show sources section."""
        message = Message(
            role="assistant",
            content="No relevant sources found.",
            timestamp=datetime(2025, 1, 13, 14, 30, 0),
            sources=[],
        )

        formatted = message.format_for_display(agent_display_name="Searcher")

        # Verify structure
        assert "[14:30] Searcher: No relevant sources found." in formatted
        # Empty sources list should not show sources section
        assert "Sources:" not in formatted

    def test_source_citation_format_for_display(self):
        """SourceCitation.format_for_display should format correctly."""
        # Test web source
        web_source = SourceCitation(
            source_type="web",
            identifier="https://example.com/article",
            relevance_score=0.92,
        )
        assert web_source.format_for_display() == "[Web] https://example.com/article"

        # Test database source
        db_source = SourceCitation(
            source_type="database",
            identifier="products_table",
            relevance_score=0.85,
        )
        assert db_source.format_for_display() == "[Database] products_table"


class TestMixedRAGNonRAGMessages:
    """Unit tests for history with mixed RAG and non-RAG messages.

    Validates: Requirement 11.5 - Backward compatibility
    """

    def test_conversation_with_mixed_messages(self, tmp_path: Path):
        """Conversation can have both RAG and non-RAG messages."""
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="mixed-agent",
            messages=[
                # Initial conversation without RAG
                Message(
                    role="user",
                    content="Hello!",
                    timestamp=datetime(2025, 1, 13, 10, 0, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Hello! How can I help you?",
                    timestamp=datetime(2025, 1, 13, 10, 0, 5),
                    sources=None,
                ),
                # RAG gets enabled, subsequent messages have sources
                Message(
                    role="user",
                    content="What is Python?",
                    timestamp=datetime(2025, 1, 13, 10, 1, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Python is a high-level programming language.",
                    timestamp=datetime(2025, 1, 13, 10, 1, 5),
                    sources=[
                        SourceCitation(
                            source_type="web",
                            identifier="https://python.org/about",
                            relevance_score=0.92,
                        )
                    ],
                ),
                # Continue with RAG
                Message(
                    role="user",
                    content="Who created it?",
                    timestamp=datetime(2025, 1, 13, 10, 2, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Python was created by Guido van Rossum.",
                    timestamp=datetime(2025, 1, 13, 10, 2, 5),
                    sources=[
                        SourceCitation(
                            source_type="web",
                            identifier="https://python.org/about",
                            relevance_score=0.95,
                        ),
                        SourceCitation(
                            source_type="database",
                            identifier="programming_languages",
                            relevance_score=0.88,
                        ),
                    ],
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 2, 5),
        )

        # Save and reload
        store.save(history)
        restored = store.load("mixed-agent")

        # Verify all messages preserved correctly
        assert len(restored.messages) == 6

        # First two messages: no sources
        assert restored.messages[0].sources is None
        assert restored.messages[1].sources is None

        # Third message: user message, no sources
        assert restored.messages[2].sources is None

        # Fourth message: RAG-enhanced, has sources
        assert restored.messages[3].sources is not None
        assert len(restored.messages[3].sources) == 1

        # Fifth message: user message, no sources
        assert restored.messages[4].sources is None

        # Sixth message: RAG-enhanced, has multiple sources
        assert restored.messages[5].sources is not None
        assert len(restored.messages[5].sources) == 2

    def test_display_mixed_conversation(self):
        """Displaying mixed conversation should format correctly."""
        messages = [
            Message(
                role="user",
                content="Hello!",
                timestamp=datetime(2025, 1, 13, 10, 0, 0),
                sources=None,
            ),
            Message(
                role="assistant",
                content="Hello! How can I help?",
                timestamp=datetime(2025, 1, 13, 10, 0, 5),
                sources=None,
            ),
            Message(
                role="user",
                content="What is Python?",
                timestamp=datetime(2025, 1, 13, 10, 1, 0),
                sources=None,
            ),
            Message(
                role="assistant",
                content="Python is a programming language.",
                timestamp=datetime(2025, 1, 13, 10, 1, 5),
                sources=[
                    SourceCitation(
                        source_type="web",
                        identifier="https://python.org",
                        relevance_score=0.92,
                    )
                ],
            ),
        ]

        # Format all messages
        formatted_messages = [msg.format_for_display("Assistant") for msg in messages]

        # First two messages: no sources section
        assert "Sources:" not in formatted_messages[0]
        assert "Sources:" not in formatted_messages[1]

        # Third message: user message, no sources
        assert "Sources:" not in formatted_messages[2]

        # Fourth message: RAG-enhanced, has sources
        assert "Sources:" in formatted_messages[3]
        assert "[Web] https://python.org" in formatted_messages[3]

    def test_serialize_mixed_conversation(self, tmp_path: Path):
        """Serializing mixed conversation should handle both formats correctly."""
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="serialize-test",
            messages=[
                Message(
                    role="user",
                    content="Non-RAG message",
                    timestamp=datetime(2025, 1, 13, 10, 0, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="RAG message",
                    timestamp=datetime(2025, 1, 13, 10, 0, 5),
                    sources=[
                        SourceCitation(
                            source_type="web",
                            identifier="https://example.com",
                            relevance_score=0.9,
                        )
                    ],
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 0, 5),
        )

        # Save the history
        store.save(history)

        # Read the JSON file directly
        history_path = tmp_path / "serialize-test.json"
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # First message: no sources field
        assert "sources" not in data["messages"][0]

        # Second message: has sources field
        assert "sources" in data["messages"][1]
        assert len(data["messages"][1]["sources"]) == 1
        assert data["messages"][1]["sources"][0]["source_type"] == "web"

    def test_alternating_rag_non_rag_messages(self, tmp_path: Path):
        """History can alternate between RAG and non-RAG messages.

        This tests a scenario where RAG might be selectively used
        (e.g., only when relevant context is found).
        """
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="alternating-agent",
            messages=[
                Message(
                    role="user",
                    content="Question 1",
                    timestamp=datetime(2025, 1, 13, 10, 0, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Answer with sources",
                    timestamp=datetime(2025, 1, 13, 10, 0, 5),
                    sources=[
                        SourceCitation(
                            source_type="web",
                            identifier="https://example.com/1",
                            relevance_score=0.9,
                        )
                    ],
                ),
                Message(
                    role="user",
                    content="Question 2",
                    timestamp=datetime(2025, 1, 13, 10, 1, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Answer without sources (no relevant context found)",
                    timestamp=datetime(2025, 1, 13, 10, 1, 5),
                    sources=None,
                ),
                Message(
                    role="user",
                    content="Question 3",
                    timestamp=datetime(2025, 1, 13, 10, 2, 0),
                    sources=None,
                ),
                Message(
                    role="assistant",
                    content="Answer with sources again",
                    timestamp=datetime(2025, 1, 13, 10, 2, 5),
                    sources=[
                        SourceCitation(
                            source_type="database",
                            identifier="data_table",
                            relevance_score=0.85,
                        )
                    ],
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 2, 5),
        )

        # Save and reload
        store.save(history)
        restored = store.load("alternating-agent")

        # Verify alternating pattern
        assert restored.messages[1].sources is not None  # Has sources
        assert restored.messages[3].sources is None  # No sources
        assert restored.messages[5].sources is not None  # Has sources again


class TestEdgeCases:
    """Unit tests for edge cases in extended conversation history."""

    def test_message_with_very_long_url(self):
        """Message with very long URL should serialize and display correctly."""
        long_url = "https://example.com/" + "a" * 500 + "/article"

        message = Message(
            role="assistant",
            content="Found information.",
            timestamp=datetime(2025, 1, 13, 10, 0, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier=long_url,
                    relevance_score=0.9,
                )
            ],
        )

        # Should serialize without error
        data = message.to_dict()
        assert data["sources"][0]["identifier"] == long_url

        # Should deserialize without error
        restored = Message.from_dict(data)
        assert restored.sources[0].identifier == long_url

        # Should format without error
        formatted = message.format_for_display()
        assert long_url in formatted

    def test_message_with_special_characters_in_identifier(self):
        """Message with special characters in source identifier should work."""
        special_identifier = "table_name_with_$pecial_ch@rs_123"

        message = Message(
            role="assistant",
            content="Query results.",
            timestamp=datetime(2025, 1, 13, 10, 0, 0),
            sources=[
                SourceCitation(
                    source_type="database",
                    identifier=special_identifier,
                    relevance_score=0.85,
                )
            ],
        )

        # Should serialize and deserialize correctly
        data = message.to_dict()
        restored = Message.from_dict(data)
        assert restored.sources[0].identifier == special_identifier

    def test_message_with_zero_relevance_score(self):
        """Message with zero relevance score should be valid."""
        message = Message(
            role="assistant",
            content="Low relevance result.",
            timestamp=datetime(2025, 1, 13, 10, 0, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://example.com",
                    relevance_score=0.0,
                )
            ],
        )

        data = message.to_dict()
        restored = Message.from_dict(data)
        assert restored.sources[0].relevance_score == 0.0

    def test_message_with_max_relevance_score(self):
        """Message with maximum relevance score should be valid."""
        message = Message(
            role="assistant",
            content="Perfect match.",
            timestamp=datetime(2025, 1, 13, 10, 0, 0),
            sources=[
                SourceCitation(
                    source_type="web",
                    identifier="https://example.com",
                    relevance_score=1.0,
                )
            ],
        )

        data = message.to_dict()
        restored = Message.from_dict(data)
        assert restored.sources[0].relevance_score == 1.0

    def test_empty_history_with_rag_enabled(self, tmp_path: Path):
        """Empty history for RAG-enabled agent should work correctly."""
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="rag-agent",
            messages=[],
            last_updated=datetime(2025, 1, 13, 10, 0, 0),
        )

        store.save(history)
        restored = store.load("rag-agent")

        assert restored.agent_name == "rag-agent"
        assert len(restored.messages) == 0

    def test_history_with_only_user_messages(self, tmp_path: Path):
        """History with only user messages (no assistant responses) should work."""
        store = HistoryStore(history_dir=tmp_path)

        history = ConversationHistory(
            agent_name="user-only",
            messages=[
                Message(
                    role="user",
                    content="Question 1",
                    timestamp=datetime(2025, 1, 13, 10, 0, 0),
                    sources=None,
                ),
                Message(
                    role="user",
                    content="Question 2",
                    timestamp=datetime(2025, 1, 13, 10, 1, 0),
                    sources=None,
                ),
            ],
            last_updated=datetime(2025, 1, 13, 10, 1, 0),
        )

        store.save(history)
        restored = store.load("user-only")

        assert len(restored.messages) == 2
        assert all(msg.role == "user" for msg in restored.messages)
        assert all(msg.sources is None for msg in restored.messages)
