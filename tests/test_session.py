"""Tests for ChatSession.

This module contains property-based tests and unit tests for the ChatSession class.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import (
    Agent,
    AgentManager,
    AgentNotFoundError,
    ChatSession,
    HistoryStore,
    Message,
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


# Strategy for generating valid message content
def valid_message_content_strategy():
    """Generate valid message content."""
    return st.text(min_size=1, max_size=200).filter(lambda s: s.strip())


# Strategy for generating valid Agent objects
def valid_agent_strategy():
    """Generate valid Agent objects for property testing."""
    return st.builds(
        Agent,
        name=valid_agent_name_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
        system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


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


class TestMessagePersistence:
    """Property 5: Message Persistence.

    Feature: offline-chat, Property 5: Message Persistence
    Validates: Requirements 3.2, 3.4, 5.1, 5.2

    For any message sent during a chat session (user or assistant), after
    the session ends and history is saved, loading the history SHALL contain
    that message with correct role, content, and timestamp.
    """

    @settings(max_examples=100)
    @given(
        agent=valid_agent_strategy(),
        user_messages=st.lists(valid_message_content_strategy(), min_size=1, max_size=5),
    )
    def test_message_persistence_property(self, agent: Agent, user_messages: list[str]):
        """Messages sent during a session should persist after session ends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Mock ollama create to succeed
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                # Create the agent
                manager.create_agent(agent)

            # Create a chat session
            session = ChatSession(manager)

            # Start the session
            session.start(agent.name)

            # Simulate sending messages and receiving responses
            # We'll manually add messages to history to avoid actual Ollama calls
            for i, content in enumerate(user_messages):
                # Add user message
                user_msg = Message(
                    role="user",
                    content=content,
                    timestamp=datetime.now(),
                )
                session.history.messages.append(user_msg)

                # Add simulated assistant response
                assistant_msg = Message(
                    role="assistant",
                    content=f"Response to: {content}",
                    timestamp=datetime.now(),
                )
                session.history.messages.append(assistant_msg)

            # End the session (saves history)
            session.end()

            # Load history from storage
            history_store = HistoryStore(history_dir=history_dir)
            loaded_history = history_store.load(agent.name)

            # Verify all messages are persisted
            assert len(loaded_history.messages) == len(user_messages) * 2

            # Verify user messages are preserved
            for i, content in enumerate(user_messages):
                user_idx = i * 2
                assert loaded_history.messages[user_idx].role == "user"
                assert loaded_history.messages[user_idx].content == content

                # Verify assistant response is preserved
                assistant_idx = user_idx + 1
                assert loaded_history.messages[assistant_idx].role == "assistant"
                assert loaded_history.messages[assistant_idx].content == f"Response to: {content}"


class TestHistoryClearResetsState:
    """Property 6: History Clear Resets State.

    Feature: offline-chat, Property 6: History Clear Resets State
    Validates: Requirements 3.6

    For any conversation history with one or more messages, after calling
    clear, the history SHALL contain zero messages.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        agent=valid_agent_strategy(),
        messages=st.lists(valid_message_strategy(), min_size=1, max_size=20),
    )
    def test_history_clear_resets_state_property(self, agent: Agent, messages: list[Message]):
        """Clearing history should result in zero messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Mock ollama create to succeed
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""

                # Create the agent
                manager.create_agent(agent)

            # Create a chat session
            session = ChatSession(manager)

            # Start the session
            session.start(agent.name)

            # Add messages to history
            session.history.messages = list(messages)
            assert len(session.history.messages) >= 1

            # Record timestamp before clear
            before_clear = datetime.now()

            # Clear history
            session.clear_history()

            # Verify history is empty
            assert len(session.history.messages) == 0

            # Verify last_updated was updated
            assert session.history.last_updated >= before_clear


class TestChatSessionBasicOperations:
    """Unit tests for basic ChatSession operations."""

    def test_start_loads_agent_and_history(self):
        """start() should load the agent and history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Before start
            assert session.agent is None
            assert session.history is None
            assert not session.is_active

            # Start session
            result = session.start("test-agent")

            assert result is True
            assert session.agent is not None
            assert session.agent.name == "test-agent"
            assert session.history is not None
            assert session.history.agent_name == "test-agent"
            assert session.is_active

    def test_start_raises_error_for_nonexistent_agent(self):
        """start() should raise AgentNotFoundError for non-existent agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )

            session = ChatSession(manager)

            with pytest.raises(AgentNotFoundError) as exc_info:
                session.start("nonexistent-agent")

            assert exc_info.value.name == "nonexistent-agent"

    def test_end_saves_history(self):
        """end() should save the conversation history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start("test-agent")

            # Add a message
            session.history.messages.append(Message(role="user", content="Hello"))

            # End session
            session.end()

            # Verify session is cleared
            assert session.agent is None
            assert session.history is None

            # Verify history was saved
            history_store = HistoryStore(history_dir=history_dir)
            loaded = history_store.load("test-agent")
            assert len(loaded.messages) == 1
            assert loaded.messages[0].content == "Hello"

    def test_clear_history_empties_messages(self):
        """clear_history() should empty the messages list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start("test-agent")

            # Add messages
            session.history.messages = [
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
            ]

            assert len(session.history.messages) == 2

            # Clear history
            session.clear_history()

            assert len(session.history.messages) == 0

    def test_clear_history_raises_error_without_active_session(self):
        """clear_history() should raise RuntimeError without active session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )

            session = ChatSession(manager)

            with pytest.raises(RuntimeError, match="No active session"):
                session.clear_history()

    def test_get_display_name_returns_agent_display_name(self):
        """get_display_name() should return the agent's display name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="My Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Before start
            assert session.get_display_name() == ""

            # After start
            session.start("test-agent")
            assert session.get_display_name() == "My Test Agent"

    def test_send_message_raises_error_without_active_session(self):
        """send_message() should raise RuntimeError without active session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AgentManager(
                agents_dir=Path(tmpdir) / "agents",
                history_dir=Path(tmpdir) / "history",
            )

            session = ChatSession(manager)

            with pytest.raises(RuntimeError, match="No active session"):
                list(session.send_message("Hello"))
