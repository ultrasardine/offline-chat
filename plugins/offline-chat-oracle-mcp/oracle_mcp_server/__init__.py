"""Oracle MCP Server package.

A Model Context Protocol server for Oracle Database using python-oracledb.
Can be run as a module: python -m oracle_mcp_server
"""

__version__ = "0.1.0"

from oracle_mcp_server.server import OracleMCPServer, main

__all__ = ["OracleMCPServer", "main", "__version__"]
