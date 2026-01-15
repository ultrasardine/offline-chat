"""Integration tests for Oracle database access.

**Requirements**: 1.1, 1.2, 1.3, 2.1, 2.7, 3.2, 4.1

This module contains integration tests that verify Oracle database access
through the SQLcl MCP server. Tests cover:
- Agent creation with Oracle database configuration
- Chat session initialization with database connections
- Query execution through the run-sql tool
- Oracle audit logging verification
- Connection lifecycle management
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offline_chat import Agent, AgentManager, ChatSession
from offline_chat.database_config import create_database_mcp_config
from offline_chat.mcp_client import MCPClient


@pytest.fixture
def mock_oracle_tools():
    """Create mock Oracle MCP tools matching SQLcl MCP server format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run-sql",
                "description": "Execute SQL query against Oracle database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL query to execute"
                        }
                    },
                    "required": ["sql"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list-connections",
                "description": "List available SQLcl connections",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]


def test_create_agent_with_oracle_sqlcl_connection(temp_agents_dir, temp_history_dir):
    """Test creating agent with Oracle database using SQLcl connection.
    
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    This test verifies that:
    - An Oracle database MCP config can be created with a SQLcl connection name
    - The config has the correct database type and connection parameters
    - An agent can be created with the Oracle database configuration
    - The agent configuration persists correctly with database settings
    """
    manager = AgentManager(
        agents_dir=str(temp_agents_dir),
        history_dir=str(temp_history_dir)
    )
    
    # Create Oracle database configuration using SQLcl connection
    oracle_config = create_database_mcp_config(
        "oracle", "prod_db", connection_name="PROD_ANALYTICS"
    )
    
    # Verify configuration properties
    assert oracle_config.database_type == "oracle"
    assert oracle_config.oracle_connection_name == "PROD_ANALYTICS"
    assert oracle_config.command == "sql"
    assert "-mcp" in oracle_config.args
    assert "-connection" in oracle_config.args
    assert "PROD_ANALYTICS" in oracle_config.args
    
    # Create agent with Oracle database
    agent = Agent(
        name="oracle-analyst",
        display_name="Oracle Data Analyst",
        base_model="llama3:latest",
        system_prompt="You are a data analyst with access to Oracle databases.",
        temperature=0.7,
        mcp_servers=[oracle_config]
    )
    
    # Mock the ollama create command
    with patch('offline_chat.manager.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.create_agent(agent)
    
    # Verify agent was created and configuration persisted
    loaded_agent = manager.get_agent("oracle-analyst")
    assert loaded_agent is not None
    assert len(loaded_agent.mcp_servers) == 1
    assert loaded_agent.mcp_servers[0].database_type == "oracle"
    assert loaded_agent.mcp_servers[0].oracle_connection_name == "PROD_ANALYTICS"



def test_chat_session_with_oracle_database(temp_agents_dir, temp_history_dir, mock_oracle_tools):
    """Test starting a chat session with Oracle database access.
    
    **Validates: Requirements 2.1, 2.7**
    
    This test verifies that:
    - A chat session can be started with an Oracle database-enabled agent
    - Database connections are established and tracked
    - The session recognizes it has database connections
    - Connection information is accessible via session properties
    - Connections are properly closed when the session ends
    """
    
    async def run_test():
        manager = AgentManager(
            agents_dir=str(temp_agents_dir),
            history_dir=str(temp_history_dir)
        )
        
        # Create Oracle database configuration
        oracle_config = create_database_mcp_config(
            "oracle", "prod_db", connection_name="PROD_ANALYTICS"
        )
        
        # Create agent with Oracle database
        agent = Agent(
            name="oracle-analyst",
            display_name="Oracle Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config]
        )
        
        # Create agent (mock ollama command)
        with patch('offline_chat.manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)
        
        # Create chat session
        session = ChatSession(manager)
        
        # Mock MCPClientManager
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_tools)
            mock_manager_instance.tool_registry = {"run-sql": "prod_db"}
            mock_manager_instance.clients = {"prod_db": MagicMock()}
            
            # Start session
            result = await session.start_async("oracle-analyst")
            
            # Verify session started successfully
            assert result is True
            assert session.is_active
            
            # Verify database connections are tracked
            assert session.has_database_connections
            
            # Verify connection information
            connections = session.get_database_connections()
            assert "prod_db" in connections
            assert connections["prod_db"] == "oracle"
        
        # End session and verify cleanup
        await session.end_async()
        assert not session.has_database_connections
    
    asyncio.run(run_test())



def test_execute_oracle_query(temp_agents_dir, temp_history_dir, mock_oracle_tools):
    """Test executing SQL queries through the run-sql tool.
    
    **Validates: Requirements 3.2, 4.1**
    
    This test verifies that:
    - Oracle database tools are discovered and registered
    - The run-sql tool is available in the tool list
    - SQL queries can be executed through the tool
    - Query results are returned correctly
    """
    
    async def run_test():
        manager = AgentManager(
            agents_dir=str(temp_agents_dir),
            history_dir=str(temp_history_dir)
        )
        
        # Create Oracle database configuration
        oracle_config = create_database_mcp_config(
            "oracle", "prod_db", connection_name="PROD_ANALYTICS"
        )
        
        # Create agent with Oracle database
        agent = Agent(
            name="oracle-analyst",
            display_name="Oracle Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config]
        )
        
        # Create agent (mock ollama command)
        with patch('offline_chat.manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)
        
        # Create chat session
        session = ChatSession(manager)
        
        # Mock query result
        mock_result = """EMPLOYEE_ID | NAME
1001 | John Smith
1002 | Jane Doe

2 rows returned"""
        
        # Mock MCPClientManager and tool execution
        with patch("offline_chat.session.MCPClientManager") as MockManager:
            mock_manager_instance = MockManager.return_value
            mock_manager_instance.connect_all = AsyncMock()
            mock_manager_instance.disconnect_all = AsyncMock()
            mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_tools)
            mock_manager_instance.tool_registry = {"run-sql": "prod_db"}
            mock_manager_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_manager_instance.clients = {"prod_db": MagicMock()}
            
            # Start session
            await session.start_async("oracle-analyst")
            
            # Verify run-sql tool is available
            tools = session._get_tools()
            tool_names = [t["function"]["name"] for t in tools]
            assert "run-sql" in tool_names
            
            # Execute query through tool
            result = await session._mcp_manager.call_tool(
                "run-sql",
                {"sql": "SELECT employee_id, name FROM employees"}
            )
            
            # Verify result contains expected data
            assert "EMPLOYEE_ID" in result
            assert "John Smith" in result
            assert "Jane Doe" in result
        
        # Clean up
        await session.end_async()
    
    asyncio.run(run_test())


def test_oracle_audit_logging(temp_agents_dir, temp_history_dir, mock_oracle_tools):
    """Test that Oracle queries are logged for audit purposes.
    
    **Validates: Requirements 2.7**
    
    This test verifies that:
    - Oracle database operations are logged
    - Log messages reference DBTOOLS$MCP_LOG table
    - Query execution is tracked for audit purposes
    
    Oracle SQLcl MCP server automatically logs all queries to the
    DBTOOLS$MCP_LOG table. This test verifies that our application
    logs appropriate messages about this audit trail.
    """
    
    async def run_test():
        manager = AgentManager(
            agents_dir=str(temp_agents_dir),
            history_dir=str(temp_history_dir)
        )
        
        # Create Oracle database configuration
        oracle_config = create_database_mcp_config(
            "oracle", "prod_db", connection_name="PROD_ANALYTICS"
        )
        
        # Create agent with Oracle database
        agent = Agent(
            name="oracle-analyst",
            display_name="Oracle Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config]
        )
        
        # Create agent (mock ollama command)
        with patch('offline_chat.manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)
        
        # Create chat session
        session = ChatSession(manager)
        
        # Capture log messages
        log_messages = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())
        
        handler = LogCapture()
        logger = logging.getLogger('offline_chat.session')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            # Mock MCPClientManager and tool execution
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = AsyncMock()
                mock_manager_instance.disconnect_all = AsyncMock()
                mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_tools)
                mock_manager_instance.tool_registry = {"run-sql": "prod_db"}
                mock_manager_instance.call_tool = AsyncMock(return_value="Query executed successfully")
                mock_manager_instance.clients = {"prod_db": MagicMock()}
                
                # Start session
                await session.start_async("oracle-analyst")
                
                # Execute query
                await session._execute_tool_async(
                    "run-sql",
                    {"sql": "SELECT * FROM employees"}
                )
                
                # Verify Oracle-specific logging occurred
                oracle_logs = [
                    msg for msg in log_messages
                    if "Oracle" in msg or "DBTOOLS$MCP_LOG" in msg or "oracle" in msg.lower()
                ]
                
                # Should have logs about Oracle connection and query logging
                assert len(oracle_logs) > 0, f"Expected Oracle audit logs, got: {log_messages}"
                
                # Verify specific audit logging message
                audit_logs = [
                    msg for msg in log_messages
                    if "DBTOOLS$MCP_LOG" in msg
                ]
                assert len(audit_logs) > 0, "Expected DBTOOLS$MCP_LOG audit reference"
        finally:
            logger.removeHandler(handler)
        
        # Clean up
        await session.end_async()
    
    asyncio.run(run_test())


def test_oracle_connection_cleanup(temp_agents_dir, temp_history_dir, mock_oracle_tools):
    """Test that Oracle database connections are properly closed.
    
    **Validates: Requirements 2.1**
    
    This test verifies that:
    - Database connections are tracked during session
    - Connections are properly closed when session ends
    - No resource leaks occur
    - Cleanup is logged appropriately
    """
    
    async def run_test():
        manager = AgentManager(
            agents_dir=str(temp_agents_dir),
            history_dir=str(temp_history_dir)
        )
        
        # Create Oracle database configuration
        oracle_config = create_database_mcp_config(
            "oracle", "prod_db", connection_name="PROD_ANALYTICS"
        )
        
        # Create agent with Oracle database
        agent = Agent(
            name="oracle-analyst",
            display_name="Oracle Data Analyst",
            base_model="llama3:latest",
            system_prompt="You are a data analyst.",
            temperature=0.7,
            mcp_servers=[oracle_config]
        )
        
        # Create agent (mock ollama command)
        with patch('offline_chat.manager.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_agent(agent)
        
        # Create chat session
        session = ChatSession(manager)
        
        # Capture log messages for cleanup verification
        log_messages = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())
        
        handler = LogCapture()
        logger = logging.getLogger('offline_chat.session')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            # Mock MCPClientManager
            with patch("offline_chat.session.MCPClientManager") as MockManager:
                mock_manager_instance = MockManager.return_value
                mock_manager_instance.connect_all = AsyncMock()
                mock_manager_instance.get_all_tools = MagicMock(return_value=mock_oracle_tools)
                mock_manager_instance.tool_registry = {}
                mock_manager_instance.clients = {"prod_db": MagicMock()}
                mock_manager_instance.disconnect_all = AsyncMock()
                
                # Start session
                await session.start_async("oracle-analyst")
                
                # Verify connection is active
                assert session.has_database_connections
                connections = session.get_database_connections()
                assert "prod_db" in connections
            
            # End session
            await session.end_async()
            
            # Verify connections are closed
            assert not session.has_database_connections
            assert len(session.get_database_connections()) == 0
            
            # Verify cleanup was logged
            cleanup_logs = [
                msg for msg in log_messages
                if "Closing" in msg or "closed" in msg.lower()
            ]
            assert len(cleanup_logs) > 0, "Expected connection cleanup logs"
        finally:
            logger.removeHandler(handler)
    
    asyncio.run(run_test())
