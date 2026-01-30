# Oracle MCP Server

A reliable Model Context Protocol server for Oracle Database using `python-oracledb`.

## Why This Server?

Oracle's SQLcl MCP server has a critical limitation - it doesn't maintain database connections when started in MCP mode. This custom server solves that problem by:

- ✅ Maintaining persistent database connections
- ✅ Proper connection lifecycle management
- ✅ Reliable query execution
- ✅ Schema discovery
- ✅ CSV-formatted results
- ✅ Pure Python implementation (no Oracle Client required for most cases)

## Installation

```bash
cd oracle_mcp_server
uv pip install -e .
```

Or install from the parent project with Oracle support:

```bash
uv pip install -e ".[oracle]"
```

## Usage

### As MCP Server

The server is designed to be used with MCP clients. Connection is established via the `connect` tool:

```json
{
  "name": "connect",
  "arguments": {
    "username": "your_username",
    "password": "your_password",
    "host": "your_host",
    "port": 1521,
    "service_name": "your_service"
  }
}
```

### Configuration in Offline Chat

Update your agent's MCP server configuration:

```json
{
  "name": "oracle_db",
  "command": "python",
  "args": ["-m", "oracle_mcp_server"],
  "env": {},
  "disabled": false,
  "database_type": "oracle"
}
```

## Available Tools

### connect
Connect to Oracle database. Must be called before running queries.

**Parameters:**
- `username` (string, required): Database username
- `password` (string, required): Database password
- `host` (string, required): Database host
- `port` (integer, optional): Database port (default: 1521)
- `service_name` (string, required): Oracle service name

**Returns:**
- Success message confirming connection

**Example:**
```json
{
  "name": "connect",
  "arguments": {
    "username": "app_user",
    "password": "secret",
    "host": "db.example.com",
    "port": 1521,
    "service_name": "PRODDB"
  }
}
```

### disconnect
Disconnect from Oracle database and close the connection.

**Parameters:** None

**Returns:**
- Success message or "No active connection" if not connected

### run-sql
Execute a SQL query and return results in CSV format.

**Parameters:**
- `sql` (string, required): SQL query to execute

**Returns:**
- For SELECT queries: CSV-formatted results with column headers
- For DML queries (INSERT, UPDATE, DELETE): Success message with row count

**Example:**
```json
{
  "name": "run-sql",
  "arguments": {
    "sql": "SELECT employee_id, name, department FROM employees WHERE department = 'Sales'"
  }
}
```

**Output:**
```
EMPLOYEE_ID,NAME,DEPARTMENT
101,John Smith,Sales
102,Jane Doe,Sales
```

### schema-information
Get database schema information (tables, views, indexes, etc.).

**Parameters:**
- `object_type` (string, optional): Type of object to query (TABLE, VIEW, INDEX, etc.) (default: TABLE)

**Returns:**
- CSV-formatted list of schema objects with metadata

**Example:**
```json
{
  "name": "schema-information",
  "arguments": {
    "object_type": "TABLE"
  }
}
```

**Output:**
```
OBJECT_NAME,OBJECT_TYPE,STATUS,CREATED,LAST_DDL_TIME
EMPLOYEES,TABLE,VALID,2024-01-15,2024-01-20
DEPARTMENTS,TABLE,VALID,2024-01-15,2024-01-15
```

### list-connections
List active database connections.

**Parameters:** None

**Returns:**
- Connection information if connected, or "No active connections"

**Example Output:**
```
Connected to: db.example.com:1521/PRODDB
```

## Features

- **Persistent Connections**: Connection stays active across multiple queries using `oracledb.connect()`
- **CSV Output**: Query results formatted as CSV for easy parsing by LLMs
- **Error Handling**: Clear error messages with full exception details logged
- **Schema Discovery**: Query database metadata via `user_objects` system view
- **Connection Management**: Explicit connect/disconnect lifecycle with connection state tracking
- **Automatic Commit**: Non-SELECT queries (INSERT, UPDATE, DELETE) are automatically committed
- **Pure Python**: Uses `python-oracledb` library - no Oracle Client installation required for most cases

## Implementation Details

### Connection Management
- Connections are stored in the `OracleMCPServer` instance
- DSN (Data Source Name) is constructed using `oracledb.makedsn()`
- Connection parameters are cached for reference
- Existing connections are closed before establishing new ones

### Query Execution
- SELECT queries return CSV-formatted results with column headers
- DML queries (INSERT, UPDATE, DELETE) return row count
- All queries use cursor objects that are properly closed after execution
- Non-SELECT queries trigger automatic `connection.commit()`

### Error Handling
- All tool calls are wrapped in try-except blocks
- Errors are logged with full stack traces
- User-friendly error messages are returned to the MCP client (no exceptions raised)
- Connection failures include detailed connection parameter information (excluding passwords)
- Oracle error codes are parsed and translated to helpful messages:
  - **ORA-00942**: "Table or view does not exist" - suggests using schema-information tool
  - **ORA-00904**: "Invalid column name" - suggests checking table structure
  - **ORA-01031**: "Insufficient privileges" - indicates access permission issues
  - **ORA-00933/00936**: "SQL syntax error" - indicates query syntax problems
  - **ORA-01722**: "Invalid number format" - indicates data type mismatch
  - **ORA-00001**: "Unique constraint violation" - indicates duplicate key error
- Empty query results return "(No rows returned)" message instead of just headers
- Connection errors return "ERROR: Not connected" message with reconnection guidance

## Requirements

- Python 3.10+
- `oracledb` library (pure Python, no Oracle Client needed for most cases)
- `mcp` library (Model Context Protocol)

## Differences from SQLcl MCP Server

| Feature | SQLcl MCP | This Server |
|---------|-----------|-------------|
| Connection persistence | ❌ Broken | ✅ Works |
| Setup complexity | High (named connections) | Low (direct connect) |
| Dependencies | SQLcl + Java | Python only |
| Connection management | Unclear | Explicit |
| Error messages | Cryptic | Clear |
| Query results | Various formats | Consistent CSV |
| Commit behavior | Manual | Automatic for DML |

## Development

To run the server directly for testing:

```bash
python -m oracle_mcp_server
```

The server communicates via stdio (standard input/output) using the MCP protocol. It expects JSON-RPC messages on stdin and writes responses to stdout.

### Logging

The server uses Python's `logging` module with INFO level by default. Logs include:
- Connection establishment and disconnection
- Query execution (without sensitive data)
- Error details with stack traces

### Testing

You can test the server manually by sending MCP protocol messages via stdin, or integrate it with an MCP client like the offline-chat agents.

## Troubleshooting

### "ERROR: Not connected to database. Please reconnect."
**Cause:** Attempting to run queries before establishing a connection, or connection was lost.

**Solution:** Call the `connect` tool to establish or re-establish the database connection.

### "Failed to connect to Oracle database"
**Cause:** Invalid connection parameters or network issues.

**Solution:** 
- Verify host, port, and service_name are correct
- Check that the database is accessible from your network
- Confirm username and password are valid
- Review the error message for specific details (e.g., "ORA-12154: TNS:could not resolve the connect identifier")

### "ERROR: Table or view does not exist"
**Cause:** Query references a table that doesn't exist or you don't have access to.

**Solution:**
- Use the `schema-information` tool to see available tables
- Check the table name spelling and case
- Verify you have access to the schema containing the table
- Prefix table name with schema if needed (e.g., `SCHEMA.TABLE_NAME`)

### "ERROR: Invalid column name"
**Cause:** Query references a column that doesn't exist in the table.

**Solution:**
- Use `schema-information` tool to check table structure
- Verify column name spelling and case
- Use `DESC table_name` query to see column definitions

### "ERROR: Insufficient privileges"
**Cause:** Your database user doesn't have permission to access the table or perform the operation.

**Solution:**
- Contact your database administrator to grant necessary permissions
- Verify you're using the correct database user
- Check if the table exists in a different schema you don't have access to

### "ERROR: SQL syntax error"
**Cause:** The SQL query has invalid syntax.

**Solution:**
- Review Oracle SQL syntax documentation
- Check for missing or extra keywords, commas, or parentheses
- Verify function names and usage are correct for Oracle
- Test the query in a SQL client to get more detailed error information

### "(No rows returned)"
**Cause:** Query executed successfully but returned no results.

**Solution:** This is not an error - the query is valid but no data matches your criteria. Review your WHERE clause conditions if you expected results.

### Connection hangs or times out
**Cause:** Network issues or firewall blocking the connection.

**Solution:**
- Verify the database host is reachable: `ping <host>`
- Check if the port is open: `telnet <host> <port>`
- Ensure no firewall is blocking Oracle connections (default port 1521)

### "No module named 'oracledb'"
**Cause:** The `oracledb` library is not installed.

**Solution:**
```bash
uv pip install oracledb
```

## Architecture

The server is implemented as an async MCP server using the `mcp` library:

```
┌─────────────────────────────────────┐
│   MCP Client (e.g., Agent)          │
└──────────────┬──────────────────────┘
               │ JSON-RPC over stdio
               ▼
┌─────────────────────────────────────┐
│   OracleMCPServer                   │
│   ├── list_tools()                  │
│   ├── call_tool()                   │
│   └── Connection Management         │
└──────────────┬──────────────────────┘
               │ python-oracledb
               ▼
┌─────────────────────────────────────┐
│   Oracle Database                   │
└─────────────────────────────────────┘
```

### Key Components

- **OracleMCPServer**: Main server class that handles MCP protocol
- **Connection Management**: Stores active connection and parameters
- **Tool Handlers**: Individual methods for each tool (connect, run-sql, etc.)
- **Error Handling**: Comprehensive exception catching and logging

## Code Structure

```python
class OracleMCPServer:
    def __init__(self):
        self.server = Server("oracle-mcp-server")
        self.connection = None  # Active oracledb connection
        self.connection_params = {}  # Cached connection parameters
        
    async def list_tools(self) -> list[Tool]:
        # Returns tool definitions with input schemas
        
    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        # Routes tool calls to appropriate handlers
        
    async def _connect(self, args: dict) -> str:
        # Establishes database connection using oracledb.connect()
        
    async def _run_sql(self, args: dict) -> str:
        # Executes SQL and returns CSV results
        
    async def _schema_information(self, args: dict) -> str:
        # Queries user_objects for schema metadata
```

### CSV Formatting

Query results are formatted as CSV with:
- First line: Column names from `cursor.description`
- Subsequent lines: Row values (None converted to empty string)
- Values are converted to strings and comma-separated
- No escaping or quoting (assumes simple data types)

**Example:**
```python
# Query: SELECT id, name FROM users
# Result:
ID,NAME
1,Alice
2,Bob
```

## License

MIT
