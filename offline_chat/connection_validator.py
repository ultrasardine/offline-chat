"""Database connection validation utilities.

This module provides functions to validate database connections by temporarily
starting MCP servers and executing test queries.
"""

import asyncio
import logging
from typing import Optional, Tuple

from offline_chat.mcp_client import MCPClient
from offline_chat.mcp_config import MCPServerConfig

logger = logging.getLogger(__name__)


def validate_database_connection(config: MCPServerConfig) -> Tuple[bool, Optional[str]]:
    """Test database connection by starting MCP server and executing a test query.
    
    This function temporarily starts an MCP server with the provided configuration,
    executes a simple test query to verify connectivity, and then cleans up the
    connection. The test query is database-specific:
    - Oracle: SELECT 1 FROM DUAL
    - PostgreSQL/MySQL/SQLite: SELECT 1
    
    Args:
        config: Database MCP server configuration to validate
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        - (True, None) if connection successful
        - (False, error_message) if connection failed
        
    Examples:
        >>> config = MCPServerConfig(
        ...     name="test_db",
        ...     command="uvx",
        ...     args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
        ...     database_type="sqlite"
        ... )
        >>> success, error = validate_database_connection(config)
        >>> if success:
        ...     print("Connection successful!")
        ... else:
        ...     print(f"Connection failed: {error}")
    """
    # Run the async validation in a new event loop
    try:
        return asyncio.run(_validate_connection_async(config))
    except Exception as e:
        logger.error(f"Unexpected error during connection validation: {e}")
        return (False, f"Unexpected error: {str(e)}")


async def _validate_connection_async(
    config: MCPServerConfig
) -> Tuple[bool, Optional[str]]:
    """Async implementation of connection validation.
    
    This function performs the actual connection validation by:
    1. Starting the MCP server process
    2. Connecting to it via the MCP protocol
    3. Discovering available tools
    4. Executing a simple test query
    5. Cleaning up the connection
    
    Args:
        config: Database MCP server configuration to validate
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        
    Examples:
        >>> import asyncio
        >>> from offline_chat.mcp_config import MCPServerConfig
        >>> 
        >>> config = MCPServerConfig(
        ...     name="test_db",
        ...     command="uvx",
        ...     args=["sqlite-mcp-server", "--db-path", "/tmp/test.db"],
        ...     database_type="sqlite"
        ... )
        >>> 
        >>> # Run validation
        >>> success, error = asyncio.run(_validate_connection_async(config))
        >>> if success:
        ...     print("Connection validated successfully!")
        ... else:
        ...     print(f"Validation failed: {error}")
    """
    client = MCPClient(config)
    
    try:
        # Attempt to connect to the MCP server
        logger.info(f"Validating connection to database '{config.name}'...")
        success = await client.connect()
        
        if not success:
            error_msg = f"Failed to connect to MCP server for database '{config.name}'"
            logger.warning(error_msg)
            return (False, error_msg)
        
        # Determine the appropriate test query based on database type
        test_query = _get_test_query(config.database_type)
        
        # Look for a query tool in the available tools
        query_tool_name = _find_query_tool(client.tools)
        
        if not query_tool_name:
            error_msg = (
                f"No query tool found for database '{config.name}'. "
                f"Available tools: {[t['function']['name'] for t in client.tools]}"
            )
            logger.warning(error_msg)
            return (False, error_msg)
        
        # Execute the test query
        logger.info(
            f"Executing test query '{test_query}' using tool '{query_tool_name}'..."
        )
        result = await client.call_tool(
            query_tool_name,
            {"query": test_query}
        )
        
        # Check if the result indicates an error
        if result.startswith("Error:"):
            error_msg = f"Test query failed: {result}"
            logger.warning(error_msg)
            return (False, error_msg)
        
        logger.info(f"Connection validation successful for database '{config.name}'")
        return (True, None)
        
    except Exception as e:
        error_msg = f"Connection validation error: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)
        
    finally:
        # Always clean up the connection
        try:
            await client.disconnect()
            logger.info(f"Cleaned up test connection for database '{config.name}'")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


def _get_test_query(database_type: Optional[str]) -> str:
    """Get the appropriate test query for the database type.
    
    Args:
        database_type: Type of database ("oracle", "postgresql", "mysql", "sqlite")
        
    Returns:
        SQL test query string
    """
    if database_type == "oracle":
        return "SELECT 1 FROM DUAL"
    else:
        # PostgreSQL, MySQL, SQLite all support SELECT 1
        return "SELECT 1"


def _find_query_tool(tools: list[dict]) -> Optional[str]:
    """Find the query execution tool from the list of available tools.
    
    Different MCP servers use different tool names for query execution:
    - Oracle SQLcl: "run-sql"
    - Generic database servers: "query_database", "query", "execute_query"
    
    Args:
        tools: List of tool schemas in Ollama format
        
    Returns:
        Tool name if found, None otherwise
    """
    # Common query tool names to look for
    query_tool_names = [
        "run-sql",          # Oracle SQLcl
        "query_database",   # Generic
        "query",            # Generic
        "execute_query",    # Generic
        "run_query",        # Generic
    ]
    
    # Extract tool names from the tool schemas
    available_tools = {tool["function"]["name"] for tool in tools}
    
    # Find the first matching query tool
    for tool_name in query_tool_names:
        if tool_name in available_tools:
            return tool_name
    
    return None
