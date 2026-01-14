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
    def test_history_excludes_tool_messages(
        self, agent: Agent, user_message: str, final_response: str
    ):
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
                assert msg.role in ["user", "assistant"], (
                    f"Found unexpected role '{msg.role}' in history"
                )

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
                mock_responses.append({
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
                })

            # Final response with no tool calls
            mock_responses.append({
                "message": {
                    "role": "assistant",
                    "content": final_response,
                    "tool_calls": [],
                }
            })

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
    def test_final_response_is_streamed(
        self, agent: Agent, user_message: str, final_response: str
    ):
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
                result = asyncio.get_event_loop().run_until_complete(
                    session.start_async("test-agent")
                )

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
                loop = asyncio.get_event_loop()

                # Start session
                loop.run_until_complete(session.start_async("test-agent"))

                # End session
                loop.run_until_complete(session.end_async())

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
            result = asyncio.get_event_loop().run_until_complete(
                session.start_async("test-agent")
            )

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

    def __init__(self, return_value=None):
        self.return_value = return_value
        self.call_count = 0
        self.called = False

    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.called = True
        return self.return_value

    def assert_called_once(self):
        assert self.call_count == 1, f"Expected 1 call, got {self.call_count}"


# Register the AsyncMock helper with pytest
pytest.helpers = type("Helpers", (), {"AsyncMock": AsyncMock})()
