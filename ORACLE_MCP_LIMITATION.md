# Oracle SQLcl MCP Server Limitation

## Issue

The Oracle SQLcl MCP server has a known limitation: **it does not maintain an active database connection when started in MCP mode**, even when a connection string is provided in the command-line arguments.

### Symptoms

- MCP server starts successfully
- Tools are registered (7 tools available)
- Queries fail with error: `ERROR: null connection not allowed`
- Agent reports "lost connection to database"

### Root Cause

When SQLcl is started with:
```bash
sql "username/password@host:port/service" -mcp
```

The connection is established initially, but when the MCP server starts, it doesn't keep the connection active for subsequent tool calls.

## Attempted Solutions

We tried multiple approaches:

1. ❌ **Named connections via CONNMGR**: SQLcl's connection manager requires complex JSON import format
2. ❌ **Connection string in args**: Connects initially but doesn't persist for MCP queries  
3. ❌ **Auto-connect via `connect` tool**: Requires pre-configured named connections

## Current Status

**Oracle database connections via SQLcl MCP server are not functional** due to this limitation.

## Recommended Solution: Custom Oracle MCP Server ✅

**We've built a custom Oracle MCP server that solves this problem!**

The custom server is located in `oracle_mcp_server/` and provides:
- ✅ Persistent database connections
- ✅ Direct connection without named connection setup  
- ✅ Clear error messages
- ✅ CSV-formatted query results
- ✅ Schema discovery tools

**Installation:**
```bash
cd oracle_mcp_server
uv pip install -e .
```

**Usage:**
```python
oracle_config = {
    "name": "oracle_db",
    "command": "python",
    "args": ["-m", "oracle_mcp_server.server"],
    "env": {},
    "disabled": False,
    "database_type": "oracle"
}
```

See [oracle_mcp_server/README.md](oracle_mcp_server/README.md) for full documentation.

## Alternative Solutions (If Not Using Custom Server)

### Option 1: Use a Different Oracle MCP Server

Consider using a Python-based Oracle MCP server that doesn't have this limitation:
- Build a custom MCP server using `cx_Oracle` or `oracledb` Python library
- Use `@modelcontextprotocol/server-postgres` as a template and adapt for Oracle

### Option 2: Use Oracle REST Data Services (ORDS)

If your Oracle database has ORDS enabled:
- Access via REST API
- Create a custom MCP server that wraps ORDS endpoints
- More reliable than SQLcl MCP server

### Option 3: Use SQLite for Development/Testing

For development and testing:
- Use the included sample SQLite database
- Much simpler setup, no connection issues
- See `SAMPLE_DATABASE_GUIDE.md`

## For Oracle Users

**Recommended**: Use the custom Oracle MCP server in `oracle_mcp_server/` for reliable database access.

If you still want to use SQLcl directly:

1. **Short term**: Use SQLcl directly (not via MCP) for database queries
2. **Long term**: Consider the custom Oracle MCP server or alternative implementations

## Technical Details

The issue appears to be in how SQLcl's MCP server manages connection state. When started in MCP mode, the connection context from command-line args is not propagated to the MCP tool execution context.

This would need to be fixed in Oracle SQLcl itself, which is closed-source.

## Updates

We'll update this document as we find solutions or workarounds.

Last updated: 2026-01-30
