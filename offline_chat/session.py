"""Chat session for Offline Chat application.

This module provides the ChatSession class for managing conversations
with AI agents, including message handling and history persistence.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

import ollama

from offline_chat.agent import Agent
from offline_chat.database.access_validator import AccessLevelValidator
from offline_chat.database.result import is_err, unwrap_err
from offline_chat.exceptions import AgentNotFoundError, OllamaConnectionError
from offline_chat.fetch import WebFetchTool
from offline_chat.history import ConversationHistory, HistoryStore, Message
from offline_chat.manager import AgentManager
from offline_chat.mcp_client import MCPClientManager
from offline_chat.rag.context_retriever import ContextRetriever
from offline_chat.rag.database_integration import DatabaseIntegration
from offline_chat.rag.document_processor import DocumentProcessor
from offline_chat.rag.embedding_generator import EmbeddingGenerator
from offline_chat.rag.orchestrator import RAGOrchestrator
from offline_chat.rag.prompt_augmenter import PromptAugmenter
from offline_chat.rag.vector_store import VectorStore
from offline_chat.rag.web_scraper import WebScraper
from offline_chat.tools import WebSearchTool

logger = logging.getLogger(__name__)


class ChatSession:
    """Manages a chat session with an AI agent.

    This class handles starting and ending chat sessions, sending messages,
    receiving streaming responses, and managing conversation history.
    Supports tool calling for web search, web fetch, and MCP server capabilities.

    Attributes:
        manager: AgentManager instance for agent operations.
        history_store: HistoryStore instance for history persistence.
        agent: The current agent (set after start()).
        history: The current conversation history (set after start()).
        custom_tools: Optional list of custom tools to use.
    """

    def __init__(
        self,
        manager: AgentManager,
        history_store: Optional[HistoryStore] = None,
        tools: Optional[list] = None,
    ):
        """Initialize the ChatSession.

        Args:
            manager: AgentManager instance for agent operations.
            history_store: Optional HistoryStore instance. If not provided,
                uses the manager's history_store.
            tools: Optional list of tools to use regardless of agent config.
        """
        self.manager = manager
        self.history_store = history_store or manager.history_store
        self.custom_tools = tools
        self.agent: Optional[Agent] = None
        self.history: Optional[ConversationHistory] = None
        self._web_search_tool: Optional[WebSearchTool] = None
        self._web_fetch_tool: Optional[WebFetchTool] = None
        self._mcp_manager: Optional[MCPClientManager] = None
        self._on_tool_call: Optional[Callable[[str], None]] = None
        self._database_connections: dict[str, str] = {}  # Maps server name to database type
        self._rag_orchestrator: Optional[RAGOrchestrator] = None

    def start(self, agent_name: str) -> bool:
        """Start a chat session with the specified agent.

        Loads the agent configuration and existing conversation history.
        For agents with MCP servers, use start_async() instead.

        Args:
            agent_name: The name of the agent to chat with.

        Returns:
            True if the session started successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
        """
        # Load the agent
        self.agent = self.manager.get_agent(agent_name)
        if self.agent is None:
            raise AgentNotFoundError(agent_name)

        # Load existing conversation history
        self.history = self.history_store.load(agent_name)

        # Initialize RAG orchestrator if RAG is enabled
        self._initialize_rag_orchestrator()

        return True

    def _initialize_rag_orchestrator(self) -> None:
        """Initialize RAG orchestrator if RAG is enabled for the agent.

        This method sets up all RAG components:
        - Vector store
        - Embedding generator
        - Context retriever
        - Document processor
        - Prompt augmenter
        - Web scraper (if MCP client available)
        - Database integration (if database path available)

        If initialization fails, logs a warning and continues without RAG
        (graceful degradation to non-RAG mode).
        """
        if not self.agent or not self.agent.rag_config or not self.agent.rag_config.enabled:
            self._rag_orchestrator = None
            return

        try:
            logger.info(f"Initializing RAG orchestrator for agent '{self.agent.name}'")

            # Get data directory from manager
            data_dir = self.manager.data_dir / "rag"

            # Initialize vector store
            vector_store = VectorStore(data_dir)

            # Initialize embedding generator
            embedding_generator = EmbeddingGenerator(
                model_name=self.agent.rag_config.embedding_model
            )

            # Initialize context retriever
            context_retriever = ContextRetriever(
                vector_store=vector_store,
                embedding_generator=embedding_generator
            )

            # Initialize document processor
            document_processor = DocumentProcessor(
                chunk_size=self.agent.rag_config.chunk_size,
                chunk_overlap=self.agent.rag_config.chunk_overlap
            )

            # Initialize prompt augmenter
            prompt_augmenter = PromptAugmenter()

            # Initialize web scraper if MCP client is available
            web_scraper = None
            if self._mcp_manager:
                web_scraper = WebScraper(self._mcp_manager)

            # Initialize database integration
            # For now, we'll use a simple SQLite integration
            # This can be extended to support other database types
            database_integration = None
            # Check if there's a database path we can use
            # This is a simplified approach - in production, you'd want to
            # properly configure database connections
            db_path = self.manager.data_dir / "sample_company.db"
            if db_path.exists():
                database_integration = DatabaseIntegration(str(db_path))

            # Create RAG orchestrator
            self._rag_orchestrator = RAGOrchestrator(
                agent_config=self.agent,
                vector_store=vector_store,
                embedding_generator=embedding_generator,
                context_retriever=context_retriever,
                document_processor=document_processor,
                prompt_augmenter=prompt_augmenter,
                web_scraper=web_scraper,
                database_integration=database_integration
            )

            logger.info(f"RAG orchestrator initialized successfully for agent '{self.agent.name}'")

        except Exception as e:
            logger.warning(
                f"Failed to initialize RAG orchestrator for agent '{self.agent.name}': {e}. "
                f"Continuing without RAG capabilities."
            )
            self._rag_orchestrator = None

    async def start_async(self, agent_name: str) -> bool:
        """Start a chat session with async MCP server connections.

        Loads the agent configuration, existing conversation history,
        and connects to any configured MCP servers. Tracks database
        connections for lifecycle management.

        If database connections fail, logs the error and continues
        the session without database tools (graceful degradation).

        Args:
            agent_name: The name of the agent to chat with.

        Returns:
            True if the session started successfully.

        Raises:
            AgentNotFoundError: If the agent does not exist.
        """
        # Load the agent and history using sync method
        self.start(agent_name)

        # Connect to MCP servers if configured
        if self.agent and self.agent.mcp_servers:
            try:
                self._mcp_manager = MCPClientManager(self.agent.mcp_servers)
                await self._mcp_manager.connect_all()

                # Track database connections for lifecycle management
                # Only track successfully connected database servers
                self._database_connections.clear()
                for config in self.agent.mcp_servers:
                    if config.database_type:
                        # Check if this server actually connected
                        if config.name in self._mcp_manager.clients:
                            self._database_connections[config.name] = config.database_type
                            logger.info(
                                f"Database connection established: {config.name} "
                                f"(type: {config.database_type})"
                            )
                        else:
                            logger.warning(
                                f"Database connection failed: {config.name} "
                                f"(type: {config.database_type}). "
                                f"Continuing session without this database."
                            )

                # Log Oracle-specific connection info for audit purposes
                for server_name, db_type in self._database_connections.items():
                    if db_type == "oracle":
                        logger.info(
                            f"Oracle database connection active: {server_name}. "
                            f"Queries will be logged in DBTOOLS$MCP_LOG table."
                        )
            except Exception as e:
                # Log the error but continue the session without database tools
                logger.error(
                    f"Failed to connect to MCP servers: {e}. "
                    f"Continuing session without database tools."
                )
                self._mcp_manager = None
                self._database_connections.clear()

        return True

    def set_tool_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for tool call notifications.

        Args:
            callback: Function called with tool name when a tool is invoked.
        """
        self._on_tool_call = callback

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get tools to register with Ollama.

        Returns custom tools if provided, MCP tools if configured,
        web search and fetch tools if agent.web_search_enabled is True,
        or empty list otherwise.

        Returns:
            List of tool schemas.
        """
        if self.custom_tools:
            return [t.get_tool_schema() for t in self.custom_tools]

        tools: list[dict[str, Any]] = []

        # Add MCP tools if available
        if self._mcp_manager:
            tools.extend(self._mcp_manager.get_all_tools())

        # Add web search tools if enabled
        if self.agent and self.agent.web_search_enabled:
            if self._web_search_tool is None:
                self._web_search_tool = WebSearchTool()
            if self._web_fetch_tool is None:
                self._web_fetch_tool = WebFetchTool()
            tools.append(self._web_search_tool.get_tool_schema())
            tools.append(self._web_fetch_tool.get_tool_schema())

        return tools

    def _get_system_prompt(self) -> str:
        """Get the system prompt, enhanced with tool usage instructions if tools are available.

        Returns:
            The system prompt string.
        """
        if self.agent is None:
            return ""

        base_prompt = self.agent.system_prompt
        tools = self._get_tools()

        if not tools:
            return base_prompt

        # Build tool usage instructions
        tool_names = [t["function"]["name"] for t in tools]
        tool_list = ", ".join(tool_names)

        tool_instructions = (
            f"\n\n=== AVAILABLE TOOLS ===\n"
            f"{tool_list}\n\n"
            "=== CRITICAL RULES ===\n"
            "1. Call tools silently - NEVER announce what you're doing\n"
            "2. After calling a tool, wait for results before responding\n"
            "3. When you get results, answer directly without explaining the process\n"
            "4. NEVER say: 'Let me', 'I'll call', 'Using tool', 'I will query'\n"
            "5. NEVER write SQL or JSON in your response\n\n"
            "Remember: You are an analyst having a conversation. The tools work invisibly. "
            "Just think about what data you need, and answer based on the results you receive."
        )

        return base_prompt + tool_instructions

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name (synchronous).

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        if self._on_tool_call:
            self._on_tool_call(name)

        if name == "web_search":
            tool = self._web_search_tool or WebSearchTool()
            # Ensure max_results is an integer (model may pass it as string)
            if "max_results" in arguments:
                arguments["max_results"] = int(arguments["max_results"])
            return tool.execute(**arguments)
        elif name == "web_fetch":
            tool = self._web_fetch_tool or WebFetchTool()
            return tool.execute(**arguments)

        return f"Unknown tool: {name}"

    async def _execute_tool_async(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute tool, routing to MCP or built-in handlers.

        For database tools, logs the operation for audit purposes
        (especially important for Oracle databases which log to DBTOOLS$MCP_LOG).

        Validates database queries against access level restrictions before execution.

        Handles errors gracefully by catching exceptions and returning error
        messages to the agent, allowing the agent to understand and potentially
        correct issues (e.g., syntax errors in SQL queries).

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result or error message.
        """
        if self._on_tool_call:
            self._on_tool_call(name)

        # Check MCP tools first
        if self._mcp_manager and name in self._mcp_manager.tool_registry:
            server_name = self._mcp_manager.tool_registry[name]

            # Validate database queries against access level
            if server_name in self._database_connections:
                validation_error = self._validate_database_query(name, arguments, server_name)
                if validation_error:
                    return validation_error

            # Log database operations for audit purposes
            if server_name in self._database_connections:
                db_type = self._database_connections[server_name]
                logger.info(
                    f"Executing database tool '{name}' on {db_type} database '{server_name}'"
                )

                # For Oracle, note that query will be logged in DBTOOLS$MCP_LOG
                if db_type == "oracle" and "sql" in name.lower():
                    logger.debug(
                        f"Oracle query will be logged in DBTOOLS$MCP_LOG table "
                        f"for database '{server_name}'"
                    )

            try:
                result = await self._mcp_manager.call_tool(name, arguments)

                # Log completion of database operations
                if server_name in self._database_connections:
                    logger.info(f"Database tool '{name}' completed successfully")

                return result
            except Exception as e:
                # Catch and return errors to the agent instead of raising
                # This allows the agent to understand syntax errors, execution errors, etc.
                error_msg = str(e)

                # Log the error for debugging
                if server_name in self._database_connections:
                    logger.warning(f"Database tool '{name}' failed on '{server_name}': {error_msg}")
                else:
                    logger.warning(f"Tool '{name}' failed: {error_msg}")

                # Return a formatted error message to the agent
                return f"Error executing tool '{name}': {error_msg}"

        # Fall back to built-in tools
        return self._execute_tool(name, arguments)

    def _validate_database_query(
        self, tool_name: str, arguments: dict[str, Any], server_name: str
    ) -> str | None:
        """Validate a database query against access level restrictions.

        This method checks if the tool is a query execution tool, extracts the SQL
        query from the arguments, finds the connection assignment for the server,
        and validates the query using AccessLevelValidator.

        Args:
            tool_name: Name of the tool being executed.
            arguments: Tool arguments containing the SQL query.
            server_name: Name of the MCP server (database connection).

        Returns:
            Error message if validation fails, None if validation succeeds or
            if the tool is not a query tool.
        """
        # Check if this is a query execution tool
        query_tool_names = ["run-sql", "query_database", "query", "execute_query", "run_query"]

        # Handle namespaced tool names (e.g., "db_name_run_sql")
        base_tool_name = tool_name
        if tool_name.startswith(f"{server_name}_"):
            base_tool_name = tool_name[len(server_name) + 1 :].replace("_", "-")

        if base_tool_name not in query_tool_names:
            # Not a query tool, no validation needed
            return None

        # Extract SQL query from arguments
        # Different tools use different parameter names
        sql_query = None
        for param_name in ["sql", "query", "statement"]:
            if param_name in arguments:
                sql_query = arguments[param_name]
                break

        if not sql_query:
            # No SQL query found in arguments, can't validate
            logger.warning(
                f"Query tool '{tool_name}' called without recognizable SQL parameter"
            )
            return None

        # Find the connection assignment for this server
        if not self.agent or not self.agent.connection_assignments:
            # No connection assignments configured
            logger.warning(
                f"No connection assignments found for agent '{self.agent.name if self.agent else 'unknown'}'"
            )
            return None

        # Find the assignment that matches this server name
        # The server name in MCP config should match the connection name
        assignment = None
        for ca in self.agent.connection_assignments:
            if ca.connection_name == server_name:
                assignment = ca
                break

        if not assignment:
            # No assignment found for this server
            logger.warning(
                f"No connection assignment found for server '{server_name}' "
                f"in agent '{self.agent.name}'"
            )
            return None

        # Validate the query using AccessLevelValidator
        allowed_tables = assignment.allowed_tables or []
        validation_result = AccessLevelValidator.validate_query(
            sql_query, assignment.access_level, allowed_tables
        )

        if is_err(validation_result):
            error_msg = unwrap_err(validation_result)
            logger.info(
                f"Query validation failed for agent '{self.agent.name}' "
                f"on server '{server_name}': {error_msg}"
            )
            return f"Access denied: {error_msg}"

        # Validation succeeded
        logger.debug(
            f"Query validation passed for agent '{self.agent.name}' "
            f"on server '{server_name}' with access level '{assignment.access_level.value}'"
        )
        return None

    def end(self) -> None:
        """End the session and save history.

        Saves the current conversation history to persistent storage.
        For sessions with MCP servers, use end_async() instead.
        """
        if self.history is not None:
            self.history.last_updated = datetime.now()
            self.history_store.save(self.history)

        # Clear session state
        self.agent = None
        self.history = None
        self._mcp_manager = None
        self._database_connections.clear()
        self._rag_orchestrator = None

    async def end_async(self) -> None:
        """End session and disconnect MCP servers.

        Saves the current conversation history and disconnects
        from all MCP servers, ensuring database connections are
        properly closed with no resource leaks.
        """
        # Log database connection cleanup
        if self._database_connections:
            logger.info(
                f"Closing {len(self._database_connections)} database connection(s): "
                f"{', '.join(self._database_connections.keys())}"
            )

        # Disconnect MCP servers (which closes database connections)
        if self._mcp_manager:
            await self._mcp_manager.disconnect_all()

            # Verify all database connections were closed
            for server_name, db_type in self._database_connections.items():
                logger.info(f"Database connection closed: {server_name} (type: {db_type})")

        # Save history and clear state using sync method
        self.end()

    def send_message(self, content: str) -> Iterator[str]:
        """Send a message and yield response chunks.

        Implements agent loop for tool calling. Appends the user message to
        history, sends it to Ollama, handles tool calls if any, and streams
        the final response. Only user messages and final assistant responses
        are persisted to history.

        If RAG is enabled for the agent, routes the query through the RAG
        orchestrator for context retrieval and prompt augmentation. Falls back
        to standard Ollama chat if RAG is disabled or unavailable.

        For sessions with MCP tools, use send_message_async() instead.

        Args:
            content: The message content to send.

        Yields:
            Response chunks as they are received from Ollama.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
            RuntimeError: If no session is active.
        """
        if self.agent is None or self.history is None:
            raise RuntimeError("No active session. Call start() first.")

        # Append user message to history
        user_message = Message(
            role="user",
            content=content,
            timestamp=datetime.now(),
        )
        self.history.messages.append(user_message)

        # Check if RAG is enabled and orchestrator is available
        if self._rag_orchestrator is not None:
            # Use RAG-enhanced query processing
            yield from self._send_message_with_rag(content)
        else:
            # Use standard Ollama chat
            yield from self._send_message_standard(content)

    def _send_message_with_rag(self, content: str) -> Iterator[str]:
        """Send a message using RAG-enhanced query processing.

        This method:
        1. Processes the query through RAG orchestrator to retrieve context
        2. Gets the augmented prompt with context and RAG instructions
        3. Sends the augmented prompt to Ollama for generation
        4. Stores source citations in conversation history
        5. Falls back to standard mode if RAG fails

        Args:
            content: The user's query

        Yields:
            Response chunks as they are received from Ollama
        """
        try:
            # Process query through RAG orchestrator
            logger.info(f"Processing query with RAG for agent '{self.agent.name}'")
            rag_response = self._rag_orchestrator.process_query(
                query=content,
                conversation_history=self.history.messages,
                generate_response=False  # We'll handle generation ourselves for streaming
            )

            # Check if RAG returned None (fallback to non-RAG mode)
            if rag_response is None:
                logger.warning("RAG orchestrator returned None, falling back to standard mode")
                yield from self._send_message_standard(content)
                return

            # Get the augmented prompt
            augmented_prompt = self._rag_orchestrator.get_augmented_prompt(
                query=content,
                retrieval_result=rag_response.retrieval_result
            )

            # Build messages for Ollama
            # Use the augmented prompt as the user message
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": self._get_system_prompt()},
            ]

            # Add conversation history (excluding the last user message we just added)
            for msg in self.history.messages[:-1]:
                messages.append({"role": msg.role, "content": msg.content})

            # Add the augmented prompt as the current user message
            messages.append({"role": "user", "content": augmented_prompt})

            # Stream the response
            full_response = ""
            for chunk in self._stream_response_no_history(messages):
                full_response += chunk
                yield chunk

            # Save to history with source citations
            assistant_message = Message(
                role="assistant",
                content=full_response,
                timestamp=datetime.now(),
                sources=rag_response.sources  # Store source citations
            )
            self.history.messages.append(assistant_message)

            logger.info(
                f"RAG-enhanced response generated with {len(rag_response.sources)} source(s)"
            )

        except Exception as e:
            logger.error(f"Error in RAG-enhanced message processing: {e}", exc_info=True)
            logger.warning("Falling back to standard mode due to RAG error")
            # Fall back to standard mode
            yield from self._send_message_standard(content)

    def _send_message_standard(self, content: str) -> Iterator[str]:
        """Send a message using standard Ollama chat (no RAG).

        This is the original send_message logic extracted into a separate method.

        Args:
            content: The user's query

        Yields:
            Response chunks as they are received from Ollama
        """

        # Build messages list for Ollama with enhanced system prompt
        messages: list[dict[str, Any]] = [{"role": "system", "content": self._get_system_prompt()}]
        messages.extend({"role": msg.role, "content": msg.content} for msg in self.history.messages)

        tools = self._get_tools()

        # Agent loop - continue until no more tool calls
        # Add a safety limit to prevent infinite loops
        max_iterations = 20
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1

                if not tools:
                    # No tools - use streaming directly
                    yield from self._stream_response(messages)
                    return

                # Use non-streaming for tool detection
                # Use base_model for tool calls since custom models may not support tools properly
                try:
                    response = ollama.chat(
                        model=self.agent.base_model,
                        messages=messages,
                        tools=tools,
                        stream=False,
                    )
                except Exception as tool_error:
                    # Check if model doesn't support tools
                    error_msg = str(tool_error).lower()
                    if "does not support tools" in error_msg:
                        # Fall back to streaming without tools
                        tools = []
                        yield from self._stream_response(messages)
                        return
                    raise

                message = response.get("message", {})
                tool_calls = message.get("tool_calls", []) or []  # Handle None

                # Debug: Check if response is complete
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Iteration {iteration}: done={response.get('done')}, "
                               f"content_len={len(message.get('content', ''))}, "
                               f"tool_calls={len(tool_calls)}")

                if not tool_calls:
                    # No tool calls - this is the final response
                    response_content = message.get("content", "")

                    # Response is complete - yield and save to history
                    if response_content:
                        # Filter out any JSON tool call syntax
                        response_content = self._filter_json_tool_calls(response_content)

                        # Stream the response character by character
                        for char in response_content:
                            yield char
                        # Save to history (only final assistant response)
                        self.history.messages.append(
                            Message(
                                role="assistant",
                                content=response_content,
                                timestamp=datetime.now(),
                            )
                        )
                    return

                # Execute tool calls
                # Add assistant message with tool calls to messages (not to history)
                messages.append(message)

                for call in tool_calls:
                    func = call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", {})

                    # Check if this is an MCP tool - if so, run async in event loop
                    if self._mcp_manager and name in self._mcp_manager.tool_registry:
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(self._execute_tool_async(name, args))
                    else:
                        result = self._execute_tool(name, args)

                    # Add tool result to messages (not to history)
                    # Use tool_name as per Ollama's tool calling format
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": name,
                            "content": result if result else "No results returned",
                        }
                    )

            # If we exit the loop due to max iterations, prompt agent to summarize
            if iteration >= max_iterations:
                # Add a system message asking the agent to summarize findings
                messages.append({
                    "role": "user",
                    "content": "Please summarize what you've found so far based on the tool results above."
                })

                # Get summary response
                response = ollama.chat(
                    model=self.agent.base_model,
                    messages=messages,
                    stream=False,
                )

                summary_content = response.get("message", {}).get("content", "")
                if summary_content:
                    # Add note about complex query
                    note = "\n\n[Note: This was a complex query. Feel free to ask follow-up questions for more details.]"
                    full_response = summary_content + note

                    # Stream the response
                    for char in full_response:
                        yield char

                    # Save to history
                    self.history.messages.append(
                        Message(
                            role="assistant",
                            content=full_response,
                            timestamp=datetime.now(),
                        )
                    )
                return

        except Exception as e:
            # Check for connection errors
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str or "connect" in error_str:
                raise OllamaConnectionError()
            raise

    async def send_message_async(self, content: str) -> list[str]:
        """Send a message asynchronously and return response chunks.

        Async version of send_message() for use with MCP tools.
        Implements agent loop for tool calling with async MCP tool execution.

        If RAG is enabled for the agent, routes the query through the RAG
        orchestrator for context retrieval and prompt augmentation. Falls back
        to standard Ollama chat if RAG is disabled or unavailable.

        Args:
            content: The message content to send.

        Returns:
            List of response chunks.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
            RuntimeError: If no session is active.
        """
        if self.agent is None or self.history is None:
            raise RuntimeError("No active session. Call start_async() first.")

        # Append user message to history
        user_message = Message(
            role="user",
            content=content,
            timestamp=datetime.now(),
        )
        self.history.messages.append(user_message)

        # Check if RAG is enabled and orchestrator is available
        if self._rag_orchestrator is not None:
            # Use RAG-enhanced query processing
            return await self._send_message_async_with_rag(content)
        else:
            # Use standard Ollama chat
            return await self._send_message_async_standard(content)

    async def _send_message_async_with_rag(self, content: str) -> list[str]:
        """Send a message asynchronously using RAG-enhanced query processing.

        This method:
        1. Processes the query through RAG orchestrator to retrieve context
        2. Gets the augmented prompt with context and RAG instructions
        3. Sends the augmented prompt to Ollama for generation
        4. Stores source citations in conversation history
        5. Falls back to standard mode if RAG fails

        Args:
            content: The user's query

        Returns:
            List of response chunks
        """
        try:
            # Process query through RAG orchestrator
            logger.info(f"Processing query with RAG for agent '{self.agent.name}'")
            rag_response = self._rag_orchestrator.process_query(
                query=content,
                conversation_history=self.history.messages,
                generate_response=False  # We'll handle generation ourselves
            )

            # Check if RAG returned None (fallback to non-RAG mode)
            if rag_response is None:
                logger.warning("RAG orchestrator returned None, falling back to standard mode")
                return await self._send_message_async_standard(content)

            # Get the augmented prompt
            augmented_prompt = self._rag_orchestrator.get_augmented_prompt(
                query=content,
                retrieval_result=rag_response.retrieval_result
            )

            # Build messages for Ollama
            # Use the augmented prompt as the user message
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": self._get_system_prompt()},
            ]

            # Add conversation history (excluding the last user message we just added)
            for msg in self.history.messages[:-1]:
                messages.append({"role": msg.role, "content": msg.content})

            # Add the augmented prompt as the current user message
            messages.append({"role": "user", "content": augmented_prompt})

            # Collect the response
            response_chunks: list[str] = []
            for chunk in self._stream_response_no_history(messages):
                response_chunks.append(chunk)

            # Save to history with source citations
            full_response = "".join(response_chunks)
            assistant_message = Message(
                role="assistant",
                content=full_response,
                timestamp=datetime.now(),
                sources=rag_response.sources  # Store source citations
            )
            self.history.messages.append(assistant_message)

            logger.info(
                f"RAG-enhanced response generated with {len(rag_response.sources)} source(s)"
            )

            return response_chunks

        except Exception as e:
            logger.error(f"Error in RAG-enhanced message processing: {e}", exc_info=True)
            logger.warning("Falling back to standard mode due to RAG error")
            # Fall back to standard mode
            return await self._send_message_async_standard(content)

    async def _send_message_async_standard(self, content: str) -> list[str]:
        """Send a message asynchronously using standard Ollama chat (no RAG).

        This is the original send_message_async logic extracted into a separate method.

        Args:
            content: The user's query

        Returns:
            List of response chunks
        """

        # Build messages list for Ollama with enhanced system prompt
        messages: list[dict[str, Any]] = [{"role": "system", "content": self._get_system_prompt()}]
        messages.extend({"role": msg.role, "content": msg.content} for msg in self.history.messages)

        tools = self._get_tools()
        response_chunks: list[str] = []

        # Agent loop - continue until no more tool calls
        # Add a safety limit to prevent infinite loops
        max_iterations = 20
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1

                if not tools:
                    # No tools - use streaming directly
                    for chunk in self._stream_response(messages):
                        response_chunks.append(chunk)
                    return response_chunks

                # Use non-streaming for tool detection
                # Use base_model for tool calls since custom models may not support tools properly
                try:
                    response = ollama.chat(
                        model=self.agent.base_model,
                        messages=messages,
                        tools=tools,
                        stream=False,
                    )
                except Exception as tool_error:
                    # Check if model doesn't support tools
                    error_msg = str(tool_error).lower()
                    if "does not support tools" in error_msg:
                        # Fall back to streaming without tools
                        tools = []
                        for chunk in self._stream_response(messages):
                            response_chunks.append(chunk)
                        return response_chunks
                    raise

                message = response.get("message", {})
                tool_calls = message.get("tool_calls", []) or []  # Handle None

                # Debug logging
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Iteration {iteration}: tool_calls={len(tool_calls)}, "
                               f"content_len={len(message.get('content', ''))}")
                    if not tool_calls and message.get('content'):
                        logger.debug(f"No tool calls. Content preview: {message.get('content')[:100]}...")

                if not tool_calls:
                    # No tool calls - collect the final response
                    response_content = message.get("content", "")
                    if response_content:
                        # Filter out any JSON tool call syntax that the model might output
                        response_content = self._filter_json_tool_calls(response_content)

                        # Collect response character by character
                        for char in response_content:
                            response_chunks.append(char)
                        # Save to history (only final assistant response)
                        self.history.messages.append(
                            Message(
                                role="assistant",
                                content=response_content,
                                timestamp=datetime.now(),
                            )
                        )
                    return response_chunks

                # Execute tool calls
                # Add assistant message with tool calls to messages (not to history)
                messages.append(message)

                for call in tool_calls:
                    func = call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", {})

                    # Use async tool execution
                    result = await self._execute_tool_async(name, args)

                    # Add tool result to messages (not to history)
                    # Use tool_name as per Ollama's tool calling format
                    messages.append(
                        {
                            "role": "tool",
                            "tool_name": name,
                            "content": result if result else "No results returned",
                        }
                    )

            # If we exit the loop due to max iterations, prompt agent to summarize
            if iteration >= max_iterations:
                # Add a system message asking the agent to summarize findings
                messages.append({
                    "role": "user",
                    "content": "Please summarize what you've found so far based on the tool results above."
                })

                # Get summary response
                response = ollama.chat(
                    model=self.agent.base_model,
                    messages=messages,
                    stream=False,
                )

                summary_content = response.get("message", {}).get("content", "")
                if summary_content:
                    # Add note about complex query
                    note = "\n\n[Note: This was a complex query. Feel free to ask follow-up questions for more details.]"
                    full_response = summary_content + note

                    # Collect response character by character
                    for char in full_response:
                        response_chunks.append(char)

                    # Save to history
                    self.history.messages.append(
                        Message(
                            role="assistant",
                            content=full_response,
                            timestamp=datetime.now(),
                        )
                    )
                return response_chunks

        except Exception as e:
            # Check for connection errors
            error_str = str(e).lower()
            if "connection" in error_str or "refused" in error_str or "connect" in error_str:
                raise OllamaConnectionError()
            raise

    def _filter_json_tool_calls(self, content: str) -> str:
        """Filter out JSON tool call syntax and SQL code blocks from model responses.

        Some models output JSON like {"name": "tool_name", "parameters": {...}}
        or SQL code blocks like ```sql SELECT * FROM table``` as part of their
        response even when they shouldn't. This method removes such blocks and
        related explanatory text from the response.

        Args:
            content: The response content to filter.

        Returns:
            Filtered content with JSON tool calls and SQL blocks removed.
        """
        import re

        # Pattern to match JSON tool call syntax
        # Matches: {"name": "...", "parameters": {...}}
        json_pattern = r'\{["\']name["\']\s*:\s*["\'][^"\']+["\']\s*,\s*["\']parameters["\']\s*:\s*\{[^}]*\}\s*\}'

        # Pattern to match SQL code blocks
        # Matches: ```sql ... ``` or ```SQL ... ```
        sql_block_pattern = r'```[sS][qQ][lL]\s*\n.*?\n```'

        # Patterns for phrases that indicate the model is about to output JSON or execute a tool
        json_intro_patterns = [
            r'Here is the JSON object for the function call:?\s*$',
            r'I\'ll call the `\w+` function with (?:a|the) (?:query|parameters):?\s*$',
            r'Let me call the `\w+` function:?\s*$',
            r'I need to call the `\w+` function:?\s*$',
            r'To (?:answer|get) .+, I (?:need to|will|\'ll) call the `\w+` function.+:?\s*$',
            r'Let me execute (?:this|the) query now\.?\s*$',
            r'I\'ll execute (?:this|the) query now\.?\s*$',
            r'Let me (?:try|run) (?:this|that|the) query\.?\s*$',
            r'Here is the refined query:?\s*$',
            r'Let me run (?:this|the) following SQL query:?\s*$',
            r'I will run (?:this|the) following SQL query:?\s*$',
            r'To find out .+, I\'ll run (?:a|the) query .+:?\s*$',
            r'Here\'s the query:?\s*$',
            r'This will give us .+\.?\s*$',
        ]

        # Remove SQL code blocks first
        filtered = re.sub(sql_block_pattern, '', content, flags=re.DOTALL)

        # Remove JSON tool calls
        filtered = re.sub(json_pattern, '', filtered)

        # Remove JSON introduction phrases (at end of text)
        for pattern in json_intro_patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.IGNORECASE | re.MULTILINE)

        # Clean up extra whitespace and newlines left behind
        filtered = re.sub(r'\n\s*\n\s*\n+', '\n\n', filtered)

        # Only strip if we actually removed something
        if filtered != content:
            filtered = filtered.strip()

            # If after filtering we're left with very little meaningful content,
            # it means the model was just trying to explain a tool call
            # In this case, don't show anything (empty response will trigger retry)
            if len(filtered) < 20 and any(phrase in content.lower() for phrase in ['json', 'function call', 'call the', 'execute', 'query', 'sql']):
                return ""

        return filtered

    def _stream_response_no_history(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        """Stream response without saving to history.

        This is a helper method for RAG-enhanced responses where we want to
        control when and how the response is saved to history (with source citations).

        Args:
            messages: Messages to send to Ollama.

        Yields:
            Response chunks.
        """
        stream = ollama.chat(
            model=self.agent.name,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            chunk_content = chunk.get("message", {}).get("content", "")
            yield chunk_content

    def _stream_response(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        """Stream response without tools.

        Args:
            messages: Messages to send to Ollama.

        Yields:
            Response chunks.
        """
        stream = ollama.chat(
            model=self.agent.name,
            messages=messages,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            chunk_content = chunk.get("message", {}).get("content", "")
            full_response += chunk_content
            yield chunk_content

        self.history.messages.append(
            Message(
                role="assistant",
                content=full_response,
                timestamp=datetime.now(),
            )
        )

    def clear_history(self) -> None:
        """Clear the conversation history.

        Resets the messages list and updates the last_updated timestamp.

        Raises:
            RuntimeError: If no session is active.
        """
        if self.history is None:
            raise RuntimeError("No active session. Call start() first.")

        self.history.messages = []
        self.history.last_updated = datetime.now()

    @property
    def is_active(self) -> bool:
        """Check if a session is currently active.

        Returns:
            True if a session is active, False otherwise.
        """
        return self.agent is not None and self.history is not None

    @property
    def has_mcp_tools(self) -> bool:
        """Check if MCP tools are available in this session.

        Returns:
            True if MCP manager is connected with tools, False otherwise.
        """
        return self._mcp_manager is not None and len(self._mcp_manager.tool_registry) > 0

    @property
    def has_database_connections(self) -> bool:
        """Check if there are active database connections in this session.

        This property is useful for determining if the agent has database
        capabilities available during the current chat session. Database
        connections are established when the session starts and tracked
        throughout the session lifecycle.

        Returns:
            True if database connections are active, False otherwise.

        Examples:
            >>> session = ChatSession(manager)
            >>> await session.start_async("data-analyst")
            >>>
            >>> if session.has_database_connections:
            ...     print("Agent can query databases")
            ... else:
            ...     print("Agent has no database access")
        """
        return len(self._database_connections) > 0

    def get_database_connections(self) -> dict[str, str]:
        """Get information about active database connections.

        Returns a dictionary mapping MCP server names to their database types.
        This is useful for understanding which databases are available to the
        agent during the current session.

        Returns:
            Dictionary mapping server names to database types.
            Example: {"prod_db": "oracle", "analytics_db": "postgresql"}

        Examples:
            >>> session = ChatSession(manager)
            >>> await session.start_async("data-analyst")
            >>>
            >>> connections = session.get_database_connections()
            >>> for server_name, db_type in connections.items():
            ...     print(f"{server_name}: {db_type}")
            prod_db: oracle
            analytics_db: postgresql
            >>>
            >>> # Check for specific database type
            >>> has_oracle = any(
            ...     db_type == "oracle"
            ...     for db_type in connections.values()
            ... )
            >>> if has_oracle:
            ...     print("Oracle database available - queries logged in DBTOOLS$MCP_LOG")
        """
        return self._database_connections.copy()

    def get_display_name(self) -> str:
        """Get the display name of the current agent.

        Returns:
            The agent's display name, or empty string if no session is active.
        """
        if self.agent is None:
            return ""
        return self.agent.display_name
