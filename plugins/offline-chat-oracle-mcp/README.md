# Offline Chat Oracle MCP Plugin

Oracle Database MCP server plugin for [Offline Chat](https://github.com/yourusername/offline-chat).

## Installation

```bash
# Install from the plugins directory
cd plugins/offline-chat-oracle-mcp
uv pip install -e .

# Or install directly with uv
uv pip install -e plugins/offline-chat-oracle-mcp
```

## Usage

After installation, the Oracle MCP server will be available in Offline Chat:

1. Create or update an agent
2. Add MCP server with:
   - Command: `python`
   - Args: `["-m", "oracle_mcp_server"]`
   - Database type: `oracle`

Or add to your MCP presets file (`~/.offline-chat/mcp_presets.json`):

```json
{
  "servers": [
    {
      "name": "oracle-db",
      "command": "python",
      "args": ["-m", "oracle_mcp_server"],
      "env": {},
      "disabled": false,
      "database_type": "oracle",
      "description": "Oracle Database integration"
    }
  ]
}
```

## Features

- **Persistent database connections**: Connection stays active across multiple queries
- **Auto-connect on session start**: Database connection is automatically established when chat begins
- **No manual connection required**: Agents can immediately use database tools without calling `connect` first
- **Read-only query validation**: Prevents destructive operations (INSERT, UPDATE, DELETE, DROP)
- **User-friendly error messages**: Clear, actionable error descriptions
- **CSV-formatted query results**: Easy-to-parse output format

## Tools Provided

- `connect` - Establish database connection (called automatically on session start)
- `disconnect` - Close database connection (called automatically on session end)
- `run-sql` - Execute SQL queries (ready to use immediately)
- `schema-information` - Get database schema info (ready to use immediately)
- `list-connections` - Show active connections

**Note**: When using this Oracle MCP server, agents receive special instructions indicating the connection is already established. Unlike other database types, agents can immediately execute queries without manually calling `connect` or `list-connections` first.

## Requirements

- Python 3.10+
- `oracledb>=2.0.0` (installed automatically)
- `mcp>=1.0.0` (installed automatically)
- Oracle database access

## License

MIT
