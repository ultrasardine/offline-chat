"""Tests for ChatSession.

This module contains property-based tests and unit tests for the ChatSession class.
"""

import asyncio
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

    @settings(max_examples=100, deadline=None)
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


class TestToolRegistrationBasedOnConfiguration:
    """Property 4: Tool Registration Based on Configuration.

    Feature: web-search, Property 4: Tool Registration Based on Configuration
    Validates: Requirements 3.1, 4.3, 4.4

    For any Agent with web_search_enabled=True, starting a ChatSession SHALL
    result in tools being registered with Ollama. For any Agent with
    web_search_enabled=False, starting a ChatSession SHALL result in no tools
    being registered.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
            Agent,
            name=valid_agent_name_strategy(),
            display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
            system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            web_search_enabled=st.just(True),
            created_at=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
        ),
    )
    def test_web_search_enabled_registers_tools(self, agent: Agent):
        """Agents with web_search_enabled=True should have tools registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start(agent.name)

            # Get tools - should return web_search and web_fetch tools
            tools = session._get_tools()

            assert len(tools) == 2
            tool_names = [t["function"]["name"] for t in tools]
            assert "web_search" in tool_names
            assert "web_fetch" in tool_names

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
            Agent,
            name=valid_agent_name_strategy(),
            display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
            system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            web_search_enabled=st.just(False),
            created_at=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
        ),
    )
    def test_web_search_disabled_no_tools(self, agent: Agent):
        """Agents with web_search_enabled=False should have no tools registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start(agent.name)

            # Get tools - should return empty list
            tools = session._get_tools()

            assert len(tools) == 0


class TestHistoryPersistenceExcludesToolMessages:
    """Property 5: History Persistence Excludes Tool Messages.

    Feature: web-search, Property 5: History Persistence Excludes Tool Messages
    Validates: Requirements 3.6, 3.7

    For any conversation that includes tool calls, after the session ends and
    history is saved, the persisted history SHALL contain only user messages
    and final assistant responses, with no tool call or tool result messages.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
            Agent,
            name=valid_agent_name_strategy(),
            display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
            system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            web_search_enabled=st.just(True),
            created_at=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
        ),
        user_message=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        final_response=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    )
    def test_history_excludes_tool_messages(self, agent: Agent, user_message: str, final_response: str):
        """History should only contain user and final assistant messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start(agent.name)

            # Mock ollama.chat to simulate tool calling flow
            # First call returns tool call, second call returns final response
            with patch("ollama.chat") as mock_chat:
                # First response: tool call
                tool_call_response = {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "web_search",
                                    "arguments": {"query": "test query"},
                                }
                            }
                        ],
                    }
                }
                # Second response: final response (no tool calls)
                final_response_obj = {
                    "message": {
                        "role": "assistant",
                        "content": final_response,
                        "tool_calls": [],
                    }
                }
                mock_chat.side_effect = [tool_call_response, final_response_obj]

                # Mock the WebSearchTool.execute to avoid actual web requests
                with patch(
                    "offline_chat.tools.WebSearchTool.execute",
                    return_value="Mock search results",
                ):
                    # Send message and consume the response
                    list(session.send_message(user_message))

            # End session to save history
            session.end()

            # Load history from storage
            history_store = HistoryStore(history_dir=history_dir)
            loaded_history = history_store.load(agent.name)

            # Verify history contains only user and assistant messages
            for msg in loaded_history.messages:
                assert msg.role in ["user", "assistant"], f"Found unexpected role '{msg.role}' in history"

            # Verify no tool-related content in message roles
            roles = [msg.role for msg in loaded_history.messages]
            assert "tool" not in roles
            assert "function" not in roles

            # Verify we have the expected messages
            assert len(loaded_history.messages) == 2
            assert loaded_history.messages[0].role == "user"
            assert loaded_history.messages[0].content == user_message
            assert loaded_history.messages[1].role == "assistant"
            assert loaded_history.messages[1].content == final_response


class TestAgentLoopTermination:
    """Property 7: Agent Loop Termination.

    Feature: web-search, Property 7: Agent Loop Termination
    Validates: Requirements 3.4, 3.5

    For any conversation with a web-search-enabled agent, the agent loop SHALL
    terminate when the model returns a response without tool calls, and the
    final response SHALL be yielded to the caller.
    """

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
            Agent,
            name=valid_agent_name_strategy(),
            display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
            system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            web_search_enabled=st.just(True),
            created_at=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
        ),
        user_message=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        final_response=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        num_tool_calls=st.integers(min_value=0, max_value=3),
    )
    def test_agent_loop_terminates_on_no_tool_calls(
        self, agent: Agent, user_message: str, final_response: str, num_tool_calls: int
    ):
        """Agent loop should terminate when model returns no tool calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start(agent.name)

            # Build mock responses: N tool calls followed by final response
            mock_responses = []
            for i in range(num_tool_calls):
                mock_responses.append(
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "web_search",
                                        "arguments": {"query": f"test query {i}"},
                                    }
                                }
                            ],
                        }
                    }
                )

            # Final response with no tool calls
            mock_responses.append(
                {
                    "message": {
                        "role": "assistant",
                        "content": final_response,
                        "tool_calls": [],
                    }
                }
            )

            with patch("ollama.chat") as mock_chat:
                mock_chat.side_effect = mock_responses

                with patch(
                    "offline_chat.tools.WebSearchTool.execute",
                    return_value="Mock search results",
                ):
                    # Send message and collect the response
                    response_chars = list(session.send_message(user_message))

            # Verify the loop terminated and yielded the final response
            collected_response = "".join(response_chars)
            assert collected_response == final_response

            # Verify ollama.chat was called the expected number of times
            # (num_tool_calls + 1 for the final response)
            assert mock_chat.call_count == num_tool_calls + 1

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
            Agent,
            name=valid_agent_name_strategy(),
            display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            base_model=st.sampled_from(["llama3:latest", "mistral", "codellama"]),
            system_prompt=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
            temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            web_search_enabled=st.just(True),
            created_at=st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 12, 31),
            ),
        ),
        user_message=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        final_response=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    )
    def test_final_response_is_streamed(self, agent: Agent, user_message: str, final_response: str):
        """Final response should be yielded character by character."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start(agent.name)

            # Mock response with no tool calls (direct response)
            with patch("ollama.chat") as mock_chat:
                mock_chat.return_value = {
                    "message": {
                        "role": "assistant",
                        "content": final_response,
                        "tool_calls": [],
                    }
                }

                # Collect response characters
                response_chars = list(session.send_message(user_message))

            # Verify each character was yielded individually
            assert len(response_chars) == len(final_response)
            for i, char in enumerate(response_chars):
                assert char == final_response[i]


class TestChatSessionMCPIntegration:
    """Unit tests for ChatSession MCP integration.

    Tests for MCP server integration with ChatSession including:
    - Session start with MCP servers
    - Tool aggregation in session
    - Session without MCP servers (backward compatibility)

    Validates: Requirements 6.2, 6.3
    """

    def test_start_async_connects_mcp_servers(self):
        """start_async() should connect to MCP servers when configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Import MCP config
            from offline_chat.mcp_config import MCPServerConfig

            # Create agent with MCP servers
            mcp_config = MCPServerConfig(
                name="test-server",
                command="echo",
                args=["test"],
            )
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[mcp_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock the MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {}

                import asyncio

                result = asyncio.run(session.start_async("test-agent"))

                assert result is True
                assert session.agent is not None
                assert session.is_active
                MockManager.assert_called_once_with([mcp_config])
                mock_manager_instance.connect_all.assert_called_once()

    def test_end_async_disconnects_mcp_servers(self):
        """end_async() should disconnect from MCP servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            mcp_config = MCPServerConfig(
                name="test-server",
                command="echo",
                args=["test"],
            )
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[mcp_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock the MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {}

                import asyncio

                # Start session
                asyncio.run(session.start_async("test-agent"))

                # End session
                asyncio.run(session.end_async())

                mock_manager_instance.disconnect_all.assert_called_once()
                assert session.agent is None
                assert session.history is None
                assert session._mcp_manager is None

    def test_get_tools_includes_mcp_tools(self):
        """_get_tools() should include MCP tools when available."""
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

            # Mock MCP manager with tools
            from offline_chat.mcp_client import MCPClientManager

            mock_mcp_manager = MCPClientManager([])
            mock_mcp_manager.clients = {}
            mock_mcp_manager.tool_registry = {"mcp_tool": "test-server"}

            # Add mock tools
            mock_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "mcp_tool",
                        "description": "A test MCP tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]

            with patch.object(mock_mcp_manager, "get_all_tools", return_value=mock_tools):
                session._mcp_manager = mock_mcp_manager

                tools = session._get_tools()

                assert len(tools) == 1
                assert tools[0]["function"]["name"] == "mcp_tool"

    def test_get_tools_combines_mcp_and_web_search_tools(self):
        """_get_tools() should combine MCP tools with web search tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                web_search_enabled=True,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start("test-agent")

            # Mock MCP manager with tools
            from offline_chat.mcp_client import MCPClientManager

            mock_mcp_manager = MCPClientManager([])
            mock_mcp_manager.clients = {}
            mock_mcp_manager.tool_registry = {"mcp_tool": "test-server"}

            mock_mcp_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "mcp_tool",
                        "description": "A test MCP tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]

            with patch.object(mock_mcp_manager, "get_all_tools", return_value=mock_mcp_tools):
                session._mcp_manager = mock_mcp_manager

                tools = session._get_tools()

                # Should have MCP tool + web_search + web_fetch
                assert len(tools) == 3
                tool_names = [t["function"]["name"] for t in tools]
                assert "mcp_tool" in tool_names
                assert "web_search" in tool_names
                assert "web_fetch" in tool_names

    def test_session_without_mcp_servers_backward_compatible(self):
        """Session without MCP servers should work as before."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Agent without MCP servers
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

            # Use sync start
            result = session.start("test-agent")

            assert result is True
            assert session.agent is not None
            assert session.is_active
            assert session._mcp_manager is None

            # Get tools should return empty list
            tools = session._get_tools()
            assert len(tools) == 0

            # End session
            session.end()
            assert session.agent is None
            assert session.history is None

    def test_has_mcp_tools_property(self):
        """has_mcp_tools property should reflect MCP tool availability."""
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

            # No MCP manager
            assert session.has_mcp_tools is False

            # With MCP manager but no tools
            from offline_chat.mcp_client import MCPClientManager

            mock_mcp_manager = MCPClientManager([])
            mock_mcp_manager.tool_registry = {}
            session._mcp_manager = mock_mcp_manager
            assert session.has_mcp_tools is False

            # With MCP manager and tools
            mock_mcp_manager.tool_registry = {"tool1": "server1"}
            assert session.has_mcp_tools is True

    def test_start_async_without_mcp_servers(self):
        """start_async() should work for agents without MCP servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Agent without MCP servers
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

            import asyncio

            result = asyncio.run(session.start_async("test-agent"))

            assert result is True
            assert session.agent is not None
            assert session.is_active
            assert session._mcp_manager is None

    def test_web_search_still_works_independently(self):
        """Web search should work independently of MCP configuration.

        Validates: Requirement 6.3
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Agent with web search but no MCP servers
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                web_search_enabled=True,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)
            session.start("test-agent")

            # Should have web search tools without MCP
            tools = session._get_tools()
            assert len(tools) == 2
            tool_names = [t["function"]["name"] for t in tools]
            assert "web_search" in tool_names
            assert "web_fetch" in tool_names
            assert session._mcp_manager is None


# Helper for async mocks
class AsyncMock:
    """Simple async mock for testing."""

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.call_count = 0
        self.called = False

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.called = True
        if self.side_effect is not None:
            if isinstance(self.side_effect, Exception):
                raise self.side_effect
            elif callable(self.side_effect):
                return (
                    await self.side_effect(*args, **kwargs)
                    if asyncio.iscoroutinefunction(self.side_effect)
                    else self.side_effect(*args, **kwargs)
                )
            else:
                raise self.side_effect
        return self.return_value

    def assert_called_once(self):
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"


# Register the AsyncMock helper with pytest
pytest.helpers = type("Helpers", (), {"AsyncMock": AsyncMock})()


class TestConnectionLifecycleManagement:
    """Property tests for database connection lifecycle management.

    Feature: database-access
    Validates: Requirements 2.4, 2.5, 2.7
    """

    def test_property_7_oracle_audit_logging(self):
        """Property 7: Oracle audit logging.

        **Validates: Requirements 2.7**

        For any query executed against an Oracle database, the system should
        log the query execution for audit purposes (Oracle logs to DBTOOLS$MCP_LOG).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            # Create Oracle database MCP server config
            oracle_config = MCPServerConfig(
                name="oracle_db",
                command="sql",
                args=["-mcp", "-connection", "TEST_CONN"],
                database_type="oracle",
                oracle_connection_name="TEST_CONN",
            )

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[oracle_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock the MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {"run_sql": "oracle_db"}
                mock_manager_instance.call_tool = pytest.helpers.AsyncMock(return_value="Query result")
                # Add clients dict to indicate successful connection
                mock_client = type("MockClient", (), {"config": oracle_config})()
                mock_manager_instance.clients = {"oracle_db": mock_client}

                import asyncio

                # Start session - should log Oracle connection
                with patch("offline_chat.session.logger") as mock_logger:
                    asyncio.run(session.start_async("test-agent"))

                    # Verify Oracle audit logging message was logged
                    oracle_log_calls = [
                        call for call in mock_logger.info.call_args_list if "DBTOOLS$MCP_LOG" in str(call)
                    ]
                    assert len(oracle_log_calls) > 0, "Expected Oracle audit logging message"

                # Verify database connection was tracked
                assert session.has_database_connections
                db_connections = session.get_database_connections()
                assert "oracle_db" in db_connections
                assert db_connections["oracle_db"] == "oracle"

    def test_property_9_connection_cleanup(self):
        """Property 9: Connection cleanup.

        **Validates: Requirements 2.4**

        For any chat session with database access, ending the session should
        result in all database connections being closed with no resource leaks.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            # Create multiple database configs
            sqlite_config = MCPServerConfig(
                name="sqlite_db",
                command="uvx",
                args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
                database_type="sqlite",
                database_path="/tmp/test.db",
            )

            postgres_config = MCPServerConfig(
                name="postgres_db",
                command="npx",
                args=[
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    "postgresql://user:pass@localhost:5432/testdb",
                ],
                database_type="postgresql",
                database_host="localhost",
                database_port=5432,
                database_name="testdb",
                database_user="user",
                database_password="pass",
            )

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[sqlite_config, postgres_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock the MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {}
                # Add clients dict to indicate successful connections
                mock_sqlite_client = type("MockClient", (), {"config": sqlite_config})()
                mock_postgres_client = type("MockClient", (), {"config": postgres_config})()
                mock_manager_instance.clients = {
                    "sqlite_db": mock_sqlite_client,
                    "postgres_db": mock_postgres_client,
                }

                import asyncio

                # Start session
                asyncio.run(session.start_async("test-agent"))

                # Verify connections are tracked
                assert session.has_database_connections
                db_connections = session.get_database_connections()
                assert len(db_connections) == 2
                assert "sqlite_db" in db_connections
                assert "postgres_db" in db_connections

                # End session - should close all connections
                with patch("offline_chat.session.logger") as mock_logger:
                    asyncio.run(session.end_async())

                    # Verify cleanup logging
                    cleanup_calls = [
                        call
                        for call in mock_logger.info.call_args_list
                        if "Closing" in str(call) and "database connection" in str(call)
                    ]
                    assert len(cleanup_calls) > 0, "Expected connection cleanup logging"

                # Verify disconnect_all was called
                mock_manager_instance.disconnect_all.assert_called_once()

                # Verify session state is cleared
                assert not session.has_database_connections
                assert len(session.get_database_connections()) == 0
                assert session._mcp_manager is None

    def test_property_10_connection_reuse(self):
        """Property 10: Connection reuse.

        **Validates: Requirements 2.5**

        For any sequence of queries in a single session, the system should
        establish exactly one connection per database and reuse it for all queries.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            # Create database config
            db_config = MCPServerConfig(
                name="test_db",
                command="uvx",
                args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
                database_type="sqlite",
                database_path="/tmp/test.db",
            )

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[db_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock the MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {"query_database": "test_db"}
                mock_manager_instance.call_tool = pytest.helpers.AsyncMock(return_value="Query result")

                import asyncio

                # Start session - establishes connection
                asyncio.run(session.start_async("test-agent"))

                # Verify connection was established once
                mock_manager_instance.connect_all.assert_called_once()
                initial_call_count = mock_manager_instance.connect_all.call_count

                # Execute multiple queries
                for i in range(5):
                    asyncio.run(session._execute_tool_async("query_database", {"query": f"SELECT * FROM table{i}"}))

                # Verify connect_all was NOT called again (connection reused)
                assert mock_manager_instance.connect_all.call_count == initial_call_count

                # Verify call_tool was called for each query
                assert mock_manager_instance.call_tool.call_count == 5

                # End session
                asyncio.run(session.end_async())

                # Verify disconnect was called exactly once
                mock_manager_instance.disconnect_all.assert_called_once()

    @settings(max_examples=50, deadline=None)
    @given(
        db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]),
        num_queries=st.integers(min_value=1, max_value=10),
    )
    def test_connection_reuse_property_based(self, db_type: str, num_queries: int):
        """Property-based test for connection reuse across multiple queries.

        **Validates: Requirements 2.5**

        For any database type and any number of queries, the connection should
        be established once and reused for all queries.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            # Create database config based on type
            if db_type == "oracle":
                db_config = MCPServerConfig(
                    name="test_db",
                    command="sql",
                    args=["-mcp", "-connection", "TEST"],
                    database_type="oracle",
                    oracle_connection_name="TEST",
                )
            elif db_type == "sqlite":
                db_config = MCPServerConfig(
                    name="test_db",
                    command="uvx",
                    args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
                    database_type="sqlite",
                    database_path="/tmp/test.db",
                )
            elif db_type == "postgresql":
                db_config = MCPServerConfig(
                    name="test_db",
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-postgres",
                        "postgresql://user:pass@localhost:5432/testdb",
                    ],
                    database_type="postgresql",
                    database_host="localhost",
                    database_port=5432,
                    database_name="testdb",
                    database_user="user",
                    database_password="pass",
                )
            else:  # mysql
                db_config = MCPServerConfig(
                    name="test_db",
                    command="uvx",
                    args=["mysql-mcp-server"],
                    database_type="mysql",
                    database_host="localhost",
                    database_port=3306,
                )

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[db_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {"query": "test_db"}
                mock_manager_instance.call_tool = pytest.helpers.AsyncMock(return_value="Result")

                import asyncio

                # Start session
                asyncio.run(session.start_async("test-agent"))

                # Connection should be established once
                assert mock_manager_instance.connect_all.call_count == 1

                # Execute multiple queries
                for i in range(num_queries):
                    asyncio.run(session._execute_tool_async("query", {"query": f"SELECT {i}"}))

                # Connection should still be established only once (reused)
                assert mock_manager_instance.connect_all.call_count == 1

                # All queries should have been executed
                assert mock_manager_instance.call_tool.call_count == num_queries

                # End session
                asyncio.run(session.end_async())

                # Disconnect should be called once
                assert mock_manager_instance.disconnect_all.call_count == 1

    def test_database_tool_execution_logging(self):
        """Database tool execution should be logged for audit purposes.

        **Validates: Requirements 2.7**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            from offline_chat.mcp_config import MCPServerConfig

            # Create Oracle database config
            oracle_config = MCPServerConfig(
                name="oracle_db",
                command="sql",
                args=["-mcp", "-connection", "TEST"],
                database_type="oracle",
                oracle_connection_name="TEST",
            )

            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[oracle_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {"run_sql": "oracle_db"}
                mock_manager_instance.call_tool = pytest.helpers.AsyncMock(return_value="Query result")
                # Add clients dict to indicate successful connection
                mock_client = type("MockClient", (), {"config": oracle_config})()
                mock_manager_instance.clients = {"oracle_db": mock_client}

                import asyncio

                # Start session
                asyncio.run(session.start_async("test-agent"))

                # Execute database tool with logging
                with patch("offline_chat.session.logger") as mock_logger:
                    asyncio.run(session._execute_tool_async("run_sql", {"query": "SELECT * FROM users"}))

                    # Verify execution was logged
                    info_calls = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("Executing database tool" in call for call in info_calls)
                    assert any("oracle" in call for call in info_calls)
                    assert any("completed successfully" in call for call in info_calls)

                    # Verify Oracle-specific logging
                    debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
                    assert any("DBTOOLS$MCP_LOG" in call for call in debug_calls)

    def test_has_database_connections_property(self):
        """has_database_connections property should reflect connection state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Agent without database
            agent_no_db = Agent(
                name="test-agent-no-db",
                display_name="Test Agent No DB",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent_no_db)

            session = ChatSession(manager)

            import asyncio

            # Start session without database
            asyncio.run(session.start_async("test-agent-no-db"))
            assert not session.has_database_connections
            assert len(session.get_database_connections()) == 0

            # End session
            asyncio.run(session.end_async())

            # Now test with database
            from offline_chat.mcp_config import MCPServerConfig

            db_config = MCPServerConfig(
                name="test_db",
                command="uvx",
                args=["sqlite-mcp-server"],
                database_type="sqlite",
                database_path="/tmp/test.db",
            )

            agent_with_db = Agent(
                name="test-agent-with-db",
                display_name="Test Agent With DB",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                mcp_servers=[db_config],
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent_with_db)

            session2 = ChatSession(manager)

            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {}
                # Add clients dict to indicate successful connection
                mock_client = type("MockClient", (), {"config": db_config})()
                mock_manager_instance.clients = {"test_db": mock_client}

                # Start session with database
                asyncio.run(session2.start_async("test-agent-with-db"))
                assert session2.has_database_connections
                assert len(session2.get_database_connections()) == 1
                assert "test_db" in session2.get_database_connections()

                # End session
                asyncio.run(session2.end_async())
                assert not session2.has_database_connections


class TestErrorHandlingProperties:
    """Property tests for error handling and graceful degradation.

    Feature: database-access
    Validates: Requirements 9.1, 9.2
    """

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
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
        ),
    )
    def test_property_33_graceful_connection_failure(self, agent: Agent):
        """Property 33: Graceful connection failure.

        **Validates: Requirements 9.1**

        For any agent configuration with invalid database settings, starting
        a chat session should succeed and continue without database tools
        rather than crashing.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Import MCP config
            from offline_chat.mcp_config import MCPServerConfig

            # Create agent with invalid database configuration
            # (command that will fail to connect)
            invalid_db_config = MCPServerConfig(
                name="invalid_db",
                command="nonexistent-command",
                args=["--invalid"],
                database_type="sqlite",
                database_path="/nonexistent/path.db",
            )

            agent.mcp_servers = [invalid_db_config]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock MCPClientManager to simulate connection failure
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                # Simulate connection failure by raising an exception
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock(side_effect=Exception("Connection failed"))

                # Start session should succeed despite connection failure
                result = asyncio.run(session.start_async(agent.name))

                # Session should start successfully
                assert result is True
                assert session.is_active
                assert session.agent is not None

                # MCP manager should be None (graceful degradation)
                assert session._mcp_manager is None

                # No database connections should be tracked
                assert not session.has_database_connections
                assert len(session.get_database_connections()) == 0

    @settings(max_examples=100, deadline=None)
    @given(
        agent=st.builds(
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
        ),
        error_message=st.text(min_size=10, max_size=100).filter(lambda s: s.strip()),
    )
    def test_property_34_syntax_error_message_return(self, agent: Agent, error_message: str):
        """Property 34: Syntax error message return.

        **Validates: Requirements 9.2**

        For any query with syntax errors, the database tool should return
        the error message to the agent rather than raising an exception.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"

            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Import MCP config
            from offline_chat.mcp_config import MCPServerConfig

            # Create agent with database configuration
            db_config = MCPServerConfig(
                name="test_db",
                command="uvx",
                args=["sqlite-mcp-server"],
                database_type="sqlite",
                database_path="/tmp/test.db",
            )

            agent.mcp_servers = [db_config]

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            session = ChatSession(manager)

            # Mock MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.disconnect_all = pytest.helpers.AsyncMock()
                mock_manager_instance.get_all_tools.return_value = []
                mock_manager_instance.tool_registry = {"test_tool": "test_db"}

                # Mock call_tool to raise an exception (simulating syntax error)
                mock_manager_instance.call_tool = pytest.helpers.AsyncMock(side_effect=Exception(error_message))

                # Start session
                asyncio.run(session.start_async(agent.name))

                # Execute tool - should return error message, not raise exception
                result = asyncio.run(session._execute_tool_async("test_tool", {"query": "INVALID SQL"}))

                # Result should be an error message string, not an exception
                assert isinstance(result, str)
                assert "Error executing tool" in result
                assert error_message in result

                # Session should still be active
                assert session.is_active

                # End session
                asyncio.run(session.end_async())
