#!/usr/bin/env python3
"""Custom Oracle MCP Server.

A Model Context Protocol server for Oracle Database that actually works.
Uses python-oracledb for reliable database connections.
"""

import asyncio
import logging
import sys
from typing import Any

import oracledb
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("oracle-mcp-server")


class OracleMCPServer:
    """Oracle MCP Server with persistent connection management."""

    def __init__(self):
        """Initialize the Oracle MCP server."""
        self.server = Server("oracle-mcp-server")
        self.connection = None
        self.connection_params = {}
        
        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

    async def list_tools(self) -> list[Tool]:
        """List available tools.

        Returns:
            List of tool definitions
        """
        return [
            Tool(
                name="connect",
                description="Connect to Oracle database. Must be called before running queries.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "Database username"},
                        "password": {"type": "string", "description": "Database password"},
                        "host": {"type": "string", "description": "Database host"},
                        "port": {"type": "integer", "description": "Database port", "default": 1521},
                        "service_name": {"type": "string", "description": "Oracle service name"},
                    },
                    "required": ["username", "password", "host", "service_name"],
                },
            ),
            Tool(
                name="disconnect",
                description="Disconnect from Oracle database",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="run-sql",
                description="Execute a SQL query and return results in CSV format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"},
                    },
                    "required": ["sql"],
                },
            ),
            Tool(
                name="schema-information",
                description="Get database schema information (tables, columns, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_type": {
                            "type": "string",
                            "description": "Type of object (TABLE, VIEW, INDEX, etc.)",
                            "default": "TABLE",
                        }
                    },
                },
            ),
            Tool(
                name="list-connections",
                description="List active database connections",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of text content with results
        """
        try:
            if name == "connect":
                result = await self._connect(arguments)
            elif name == "disconnect":
                result = await self._disconnect()
            elif name == "run-sql":
                result = await self._run_sql(arguments)
            elif name == "schema-information":
                result = await self._schema_information(arguments)
            elif name == "list-connections":
                result = await self._list_connections()
            else:
                result = f"Unknown tool: {name}"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _connect(self, args: dict[str, Any]) -> str:
        """Connect to Oracle database.

        Args:
            args: Connection parameters

        Returns:
            Success message
        """
        try:
            # Close existing connection if any
            if self.connection:
                self.connection.close()

            # Store connection params
            self.connection_params = args

            # Create DSN
            dsn = oracledb.makedsn(
                host=args["host"],
                port=args.get("port", 1521),
                service_name=args["service_name"],
            )

            # Connect
            self.connection = oracledb.connect(
                user=args["username"],
                password=args["password"],
                dsn=dsn,
            )

            logger.info(f"Connected to Oracle database: {args['host']}:{args.get('port', 1521)}/{args['service_name']}")
            return f"Connected to Oracle database successfully"

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise Exception(f"Failed to connect to Oracle database: {str(e)}")

    async def _disconnect(self) -> str:
        """Disconnect from Oracle database.

        Returns:
            Success message
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.connection_params = {}
            logger.info("Disconnected from Oracle database")
            return "Disconnected successfully"
        return "No active connection"

    async def _run_sql(self, args: dict[str, Any]) -> str:
        """Execute SQL query.

        Args:
            args: Query arguments

        Returns:
            Query results in CSV format
        """
        if not self.connection:
            return "ERROR: Not connected to database. Please reconnect."

        sql = args["sql"].strip()

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)

            # Check if this is a SELECT query
            if sql.upper().startswith("SELECT"):
                # Fetch results
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                # Format as CSV
                result_lines = [",".join(columns)]
                for row in rows:
                    # Convert values to strings, handling None
                    row_values = [str(val) if val is not None else "" for val in row]
                    result_lines.append(",".join(row_values))

                cursor.close()
                
                # Check if no results
                if len(rows) == 0:
                    return f"{','.join(columns)}\n(No rows returned)"
                
                return "\n".join(result_lines)
            else:
                # Non-SELECT query (INSERT, UPDATE, DELETE, etc.)
                self.connection.commit()
                rowcount = cursor.rowcount
                cursor.close()
                return f"Query executed successfully. {rowcount} row(s) affected."

        except Exception as e:
            error_str = str(e)
            logger.error(f"Query execution failed: {error_str}")
            
            # Parse Oracle errors and provide user-friendly messages
            if "ORA-00942" in error_str:
                return "ERROR: Table or view does not exist. Use 'schema-information' to see available tables."
            elif "ORA-00904" in error_str:
                return "ERROR: Invalid column name. Check the table structure with 'schema-information'."
            elif "ORA-01031" in error_str:
                return "ERROR: Insufficient privileges. You may not have access to this table."
            elif "ORA-00933" in error_str or "ORA-00936" in error_str:
                return "ERROR: SQL syntax error. Please check your query syntax."
            elif "ORA-01722" in error_str:
                return "ERROR: Invalid number format in query."
            elif "ORA-00001" in error_str:
                return "ERROR: Unique constraint violation."
            else:
                # Generic error - extract just the ORA code and message
                if "ORA-" in error_str:
                    # Extract first line of Oracle error
                    first_line = error_str.split('\n')[0]
                    return f"ERROR: {first_line}"
                return f"ERROR: Query failed - {error_str[:200]}"

    async def _schema_information(self, args: dict[str, Any]) -> str:
        """Get schema information.

        Args:
            args: Schema query arguments

        Returns:
            Schema information
        """
        if not self.connection:
            return "ERROR: Not connected to database. Please reconnect."

        object_type = args.get("object_type", "TABLE")

        try:
            cursor = self.connection.cursor()

            # Query to get schema objects
            query = """
                SELECT object_name, object_type, status, created, last_ddl_time
                FROM user_objects
                WHERE object_type = :object_type
                ORDER BY object_name
            """

            cursor.execute(query, {"object_type": object_type})
            rows = cursor.fetchall()

            if not rows:
                cursor.close()
                return f"No {object_type} objects found in your schema. You may need to query a different schema or check permissions."

            # Format results
            result_lines = ["OBJECT_NAME,OBJECT_TYPE,STATUS,CREATED,LAST_DDL_TIME"]
            for row in rows:
                row_values = [str(val) if val is not None else "" for val in row]
                result_lines.append(",".join(row_values))

            cursor.close()
            return "\n".join(result_lines)

        except Exception as e:
            error_str = str(e)
            logger.error(f"Schema query failed: {error_str}")
            
            if "ORA-" in error_str:
                first_line = error_str.split('\n')[0]
                return f"ERROR: {first_line}"
            return f"ERROR: Schema query failed - {error_str[:200]}"

    async def _list_connections(self) -> str:
        """List active connections.

        Returns:
            Connection information
        """
        if self.connection:
            return f"Connected to: {self.connection_params.get('host')}:{self.connection_params.get('port', 1521)}/{self.connection_params.get('service_name')}"
        return "No active connections"

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Main entry point."""
    logger.info("Starting Oracle MCP Server...")
    server = OracleMCPServer()
    logger.info("Server initialized, starting run loop...")
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
