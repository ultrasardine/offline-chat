# Design Document: Database Access for Agents

## Overview

This design extends the Offline Chat application to support database access through MCP (Model Context Protocol) servers. The implementation leverages the existing MCP infrastructure (`mcp_client.py`, `mcp_config.py`) to provide agents with database query and schema discovery capabilities.

**Primary Database**: Oracle Database is the main target database system, accessed through Oracle SQLcl's built-in MCP server. Additional support is provided for PostgreSQL, MySQL, and SQLite to enable multi-database access patterns.

The design follows the established pattern where agents can have multiple MCP servers configured, and the `ChatSession` class routes tool calls through the `MCPClientManager`. Database access will be provided through:
- **Oracle SQLcl MCP Server** (built-in, official Oracle support)
- Community MCP servers for PostgreSQL and MySQL
- Custom or community SQLite MCP servers

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Agent Config                                          │  │
│  │  - name, display_name, base_model                    │  │
│  │  - system_prompt, temperature                        │  │
│  │  - mcp_servers: List[MCPServerConfig]                │  │
│  │    └─ Database MCP Server Configs                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chat Session                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ MCPClientManager                                      │  │
│  │  - Manages MCP server connections                    │  │
│  │  - Routes tool calls to appropriate servers          │  │
│  │  - Handles tool discovery and execution              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database MCP Servers                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   SQLite     │  │  PostgreSQL  │  │    MySQL     │     │
│  │ MCP Server   │  │  MCP Server  │  │  MCP Server  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Databases                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   SQLite     │  │  PostgreSQL  │  │    MySQL     │     │
│  │   Database   │  │   Database   │  │   Database   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Agent Creation/Configuration**: User configures database access during agent creation
2. **MCP Server Registration**: Database MCP server configs are added to agent's `mcp_servers` list
3. **Session Initialization**: `ChatSession` starts and `MCPClientManager` connects to all configured MCP servers
4. **Tool Discovery**: Database tools are discovered and registered with the tool calling system
5. **Query Execution**: Agent requests database operation → routed through MCPClientManager → executed by database MCP server → results returned to agent

## Components and Interfaces

### 1. Database Configuration Extension

Extend the existing `MCPServerConfig` to support database-specific configurations:

```python
@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    
    # Database-specific fields (optional, used when server is a database)
    database_type: Optional[str] = None  # "oracle", "postgresql", "mysql", "sqlite"
    
    # Oracle-specific fields
    oracle_connection_name: Optional[str] = None  # SQLcl connection name
    oracle_tns_name: Optional[str] = None  # TNS alias
    
    # Common database fields
    database_path: Optional[str] = None  # For SQLite
    database_host: Optional[str] = None  # For Oracle/PostgreSQL/MySQL
    database_port: Optional[int] = None
    database_name: Optional[str] = None  # Service name for Oracle
    database_user: Optional[str] = None
    database_password: Optional[str] = None
```

### 2. Database MCP Server Factory

Create a factory function to generate MCP server configurations for different database types:

```python
def create_database_mcp_config(
    db_type: str,
    name: str,
    **kwargs
) -> MCPServerConfig:
    """
    Create an MCP server configuration for a database.
    
    Args:
        db_type: Database type ("oracle", "postgresql", "mysql", "sqlite")
        name: Unique name for this database connection
        **kwargs: Database-specific connection parameters
        
    Returns:
        MCPServerConfig configured for the specified database
        
    Raises:
        ValueError: If db_type is unsupported or required params missing
    """
    if db_type == "oracle":
        return _create_oracle_config(name, **kwargs)
    elif db_type == "sqlite":
        return _create_sqlite_config(name, kwargs["path"])
    elif db_type == "postgresql":
        return _create_postgresql_config(name, **kwargs)
    elif db_type == "mysql":
        return _create_mysql_config(name, **kwargs)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
```

#### Oracle Configuration Builder

```python
def _create_oracle_config(
    name: str,
    connection_name: Optional[str] = None,
    host: Optional[str] = None,
    port: int = 1521,
    service_name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    tns_name: Optional[str] = None
) -> MCPServerConfig:
    """
    Create Oracle Database MCP server config using SQLcl.
    
    Priority:
    1. Use existing SQLcl connection_name if provided
    2. Use TNS alias if provided
    3. Use full connection details
    """
    if connection_name:
        # Use existing SQLcl connection
        return MCPServerConfig(
            name=name,
            command="sql",  # SQLcl command
            args=["-mcp", "-connection", connection_name],
            database_type="oracle",
            oracle_connection_name=connection_name
        )
    elif tns_name:
        # Use TNS alias
        return MCPServerConfig(
            name=name,
            command="sql",
            args=["-mcp", f"{username}/{password}@{tns_name}"],
            database_type="oracle",
            oracle_tns_name=tns_name,
            database_user=username
        )
    else:
        # Use full connection details
        conn_string = f"{username}/{password}@{host}:{port}/{service_name}"
        return MCPServerConfig(
            name=name,
            command="sql",
            args=["-mcp", conn_string],
            database_type="oracle",
            database_host=host,
            database_port=port,
            database_name=service_name,
            database_user=username
        )
```

### 3. Database Tool Interface

Database MCP servers will provide these standard tools:

```python
# Tool: query_database (or run-sql for Oracle SQLcl)
{
    "name": "query_database",  # "run-sql" for Oracle
    "description": "Execute a read-only SQL query against the database",
    "parameters": {
        "query": {
            "type": "string",
            "description": "SQL SELECT query to execute"
        },
        "max_rows": {
            "type": "integer",
            "description": "Maximum number of rows to return (default: 100)",
            "default": 100
        }
    }
}

# Tool: list_tables (or list-connections for Oracle SQLcl)
{
    "name": "list_tables",  # "list-connections" for Oracle
    "description": "List all tables in the database or available connections",
    "parameters": {}
}

# Tool: describe_table
{
    "name": "describe_table",
    "description": "Get schema information for a specific table",
    "parameters": {
        "table_name": {
            "type": "string",
            "description": "Name of the table to describe"
        }
    }
}

# Tool: get_schema
{
    "name": "get_schema",
    "description": "Get the complete database schema",
    "parameters": {}
}
```

**Note**: Oracle SQLcl MCP server uses slightly different tool names:
- `run-sql` instead of `query_database`
- `list-connections` to show available SQLcl connections
- Additional Oracle-specific tools for Data Pump, Data Guard, AWR, etc.

### 4. CLI Extension for Database Configuration

Extend the agent creation flow in the CLI:

```python
def configure_database_access(agent_name: str) -> List[MCPServerConfig]:
    """
    Interactive CLI flow for configuring database access.
    
    Returns:
        List of database MCP server configurations
    """
    configs = []
    
    while True:
        add_db = input("Add database access? (y/n): ").strip().lower()
        if add_db != 'y':
            break
            
        db_type = select_database_type()  # Oracle shown first
        db_name = input("Database connection name: ").strip()
        
        if db_type == "oracle":
            config = configure_oracle(db_name)
        elif db_type == "sqlite":
            config = configure_sqlite(db_name)
        elif db_type == "postgresql":
            config = configure_postgresql(db_name)
        elif db_type == "mysql":
            config = configure_mysql(db_name)
            
        # Test connection
        if test_database_connection(config):
            configs.append(config)
            print(f"✓ Database '{db_name}' configured successfully")
        else:
            print(f"✗ Connection test failed. Skip this database? (y/n)")
            
    return configs

def configure_oracle(db_name: str) -> MCPServerConfig:
    """
    Configure Oracle Database connection.
    
    First checks for existing SQLcl connections, then prompts for details.
    """
    # Check for existing SQLcl connections
    existing_connections = list_sqlcl_connections()
    
    if existing_connections:
        print("\nExisting SQLcl connections:")
        for i, conn in enumerate(existing_connections, 1):
            print(f"  {i}. {conn}")
        print(f"  {len(existing_connections) + 1}. Create new connection")
        
        choice = input(f"Select connection (1-{len(existing_connections) + 1}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(existing_connections):
            conn_name = existing_connections[int(choice) - 1]
            return create_database_mcp_config(
                "oracle",
                db_name,
                connection_name=conn_name
            )
    
    # Prompt for new connection details
    print("\nOracle Database Connection Details:")
    use_tns = input("Use TNS alias? (y/n): ").strip().lower() == 'y'
    
    if use_tns:
        tns_name = input("TNS alias: ").strip()
        username = input("Username: ").strip()
        password = getpass("Password: ")
        return create_database_mcp_config(
            "oracle",
            db_name,
            tns_name=tns_name,
            username=username,
            password=password
        )
    else:
        host = input("Host [localhost]: ").strip() or "localhost"
        port = input("Port [1521]: ").strip() or "1521"
        service_name = input("Service name: ").strip()
        username = input("Username: ").strip()
        password = getpass("Password: ")
        return create_database_mcp_config(
            "oracle",
            db_name,
            host=host,
            port=int(port),
            service_name=service_name,
            username=username,
            password=password
        )

def list_sqlcl_connections() -> List[str]:
    """
    List available SQLcl connections.
    
    Returns:
        List of connection names from SQLcl configuration
    """
    # Implementation to read SQLcl connections.json file
    # Typically located at ~/.sqlcl/connections.json
    pass
```

### 5. Query Result Formatter

Format database query results for agent consumption:

```python
@dataclass
class QueryResult:
    """Formatted database query result."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: float
    
    def to_markdown_table(self) -> str:
        """Format result as a markdown table."""
        # Implementation details
        pass
    
    def to_json(self) -> str:
        """Format result as JSON."""
        # Implementation details
        pass
```

### 6. Database Connection Validator

Validate database connections before saving configuration:

```python
def validate_database_connection(config: MCPServerConfig) -> Tuple[bool, Optional[str]]:
    """
    Test database connection.
    
    Args:
        config: Database MCP server configuration
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Start MCP server temporarily
        # Execute a simple query (e.g., SELECT 1)
        # Return success
        return (True, None)
    except Exception as e:
        return (False, str(e))
```

### 7. Query Safety Validator

Ensure queries are read-only:

```python
def is_read_only_query(query: str) -> bool:
    """
    Check if a SQL query is read-only.
    
    Args:
        query: SQL query string
        
    Returns:
        True if query is read-only (SELECT only), False otherwise
    """
    # Normalize query
    normalized = query.strip().upper()
    
    # Check for write operations
    write_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", 
        "ALTER", "CREATE", "TRUNCATE", "REPLACE"
    ]
    
    for keyword in write_keywords:
        if keyword in normalized:
            return False
            
    # Must start with SELECT (after comments/whitespace)
    return normalized.startswith("SELECT")
```

## Data Models

### Extended Agent Configuration

The existing `Agent` dataclass already supports `mcp_servers`, so no changes needed:

```python
@dataclass
class Agent:
    name: str
    display_name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7
    created_at: datetime = field(default_factory=datetime.now)
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)  # Already exists
```

### Database MCP Server Configuration Storage

Database configurations are stored as part of the agent's config.json:

```json
{
  "name": "data-analyst",
  "display_name": "Data Analyst",
  "base_model": "llama3:latest",
  "system_prompt": "You are a data analyst...",
  "temperature": 0.7,
  "created_at": "2025-01-13T10:00:00Z",
  "mcp_servers": [
    {
      "name": "production_db",
      "command": "sql",
      "args": ["-mcp", "-connection", "PROD_ANALYTICS"],
      "env": {},
      "database_type": "oracle",
      "oracle_connection_name": "PROD_ANALYTICS"
    },
    {
      "name": "sales_db",
      "command": "uvx",
      "args": ["sqlite-mcp-server", "--db-path", "/path/to/sales.db"],
      "env": {},
      "database_type": "sqlite",
      "database_path": "/path/to/sales.db"
    },
    {
      "name": "analytics_db",
      "command": "uvx",
      "args": [
        "postgres-mcp-server",
        "--host", "localhost",
        "--port", "5432",
        "--database", "analytics",
        "--user", "analyst"
      ],
      "env": {
        "PGPASSWORD": "secure_password"
      },
      "database_type": "postgresql",
      "database_host": "localhost",
      "database_port": 5432,
      "database_name": "analytics",
      "database_user": "analyst",
      "database_password": "secure_password"
    }
  ]
}
```

### Query Result Schema

```python
{
  "columns": ["id", "name", "amount"],
  "rows": [
    [1, "Product A", 99.99],
    [2, "Product B", 149.99]
  ],
  "row_count": 2,
  "truncated": false,
  "execution_time_ms": 45.2
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Configuration Properties

**Property 1: Database type validation**
*For any* database configuration, the system should accept only "oracle", "postgresql", "mysql", or "sqlite" as valid database types and reject all other values.
**Validates: Requirements 1.1**

**Property 2: Oracle configuration acceptance**
*For any* valid Oracle connection (TNS name, SQLcl connection name, or full connection details), when configuring an Oracle database, the system should accept the configuration and create a valid MCP server configuration.
**Validates: Requirements 1.2, 1.3**

**Property 3: SQLite configuration acceptance**
*For any* valid file path string, when configuring a SQLite database, the system should accept the path and create a valid MCP server configuration.
**Validates: Requirements 1.4**

**Property 4: PostgreSQL/MySQL configuration acceptance**
*For any* set of connection parameters (host, port, database name, username, password), when configuring PostgreSQL or MySQL, the system should accept all parameters and create a valid MCP server configuration.
**Validates: Requirements 1.5**

**Property 5: MCP server config generation**
*For any* valid database configuration, providing it to the system should result in exactly one MCP server configuration entry being created.
**Validates: Requirements 1.6**

**Property 6: Configuration serialization round-trip**
*For any* agent with database MCP server configurations, saving and then loading the agent configuration should preserve all database settings including credentials.
**Validates: Requirements 1.8**

### Connection Management Properties

**Property 7: Oracle audit logging**
*For any* query executed against an Oracle database, the system should log the query in the DBTOOLS$MCP_LOG table for audit purposes.
**Validates: Requirements 2.7**

**Property 8: Connection failure error messages**
*For any* invalid database connection parameters, attempting to connect should return a descriptive error message containing information about the failure.
**Validates: Requirements 2.3**

**Property 9: Connection cleanup**
*For any* chat session with database access, ending the session should result in all database connections being closed with no resource leaks.
**Validates: Requirements 2.4**

**Property 10: Connection reuse**
*For any* sequence of queries in a single session, the system should establish exactly one connection per database and reuse it for all queries.
**Validates: Requirements 2.5**

### Query Execution Properties

**Property 11: Read-only query validation**
*For any* SQL query containing INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or REPLACE keywords, the query validator should reject it as non-read-only.
**Validates: Requirements 3.6**

**Property 12: SELECT query acceptance**
*For any* valid SELECT query, the database tool should execute it and return formatted results without errors.
**Validates: Requirements 3.2**

**Property 13: Result truncation at 100 rows**
*For any* query result, if the row count exceeds 100, the returned result should contain exactly 100 rows and have the truncated flag set to true.
**Validates: Requirements 3.3**

**Property 14: Query error propagation**
*For any* invalid SQL query, executing it should return an error message that describes the syntax or execution problem.
**Validates: Requirements 3.4**

### Schema Discovery Properties

**Property 15: Table listing completeness**
*For any* database with N tables, calling list_tables should return exactly N table names (excluding system tables for Oracle/PostgreSQL/MySQL).
**Validates: Requirements 4.1, 4.4**

**Property 16: Oracle table listing**
*For any* Oracle database, calling list_tables should query USER_TABLES or ALL_TABLES based on user permissions and filter out system schemas.
**Validates: Requirements 4.5**

**Property 17: Table description completeness**
*For any* existing table, calling describe_table should return information containing all column names, their data types, and constraints.
**Validates: Requirements 4.2**

**Property 18: Non-existent table error**
*For any* table name that doesn't exist in the database, calling describe_table should return an error message indicating the table was not found.
**Validates: Requirements 4.3**

**Property 19: Complete schema retrieval**
*For any* database, calling get_schema should return schema information for all tables in a single response.
**Validates: Requirements 4.6**

### Security Properties

**Property 20: Credential storage**
*For any* database configuration with credentials, saving the configuration should result in credentials being stored in the MCP server config section.
**Validates: Requirements 5.1**

**Property 21: Password masking in display**
*For any* agent configuration with database passwords, displaying the configuration should show masked passwords (e.g., "****") instead of actual values.
**Validates: Requirements 5.2**

**Property 22: Credential location in serialization**
*For any* agent configuration with database credentials, serializing to JSON should place credentials only in the mcp_servers section, not in any other location.
**Validates: Requirements 5.3**

**Property 23: Credential exclusion from error messages**
*For any* database configuration validation error, the error message should not contain password or other credential values.
**Validates: Requirements 5.5**

### CLI Validation Properties

**Property 24: Oracle connection detection**
*For any* system with SQLcl installed, the CLI should detect and list existing SQLcl connections when configuring Oracle database access.
**Validates: Requirements 6.3**

**Property 25: SQLite file path validation**
*For any* file path, the SQLite configuration validator should accept it if the file exists and reject it with an error message if it doesn't.
**Validates: Requirements 6.5**

**Property 26: Database status display**
*For any* agent, the CLI display should show database access status that accurately reflects whether the agent has database configurations.
**Validates: Requirements 7.1**

**Property 27: Password masking in CLI display**
*For any* agent with database configurations, the CLI detail view should display connection information with passwords masked.
**Validates: Requirements 7.2**

**Property 28: Multiple database display**
*For any* agent with N database configurations where N > 0, the CLI should list all N databases in the display.
**Validates: Requirements 7.3**

### Result Formatting Properties

**Property 29: Table formatting with headers**
*For any* query result with columns and rows, formatting should produce a structured table that includes all column headers.
**Validates: Requirements 8.1**

**Property 30: NULL value representation**
*For any* query result containing NULL values, the formatted output should represent each NULL as the string "NULL".
**Validates: Requirements 8.2**

**Property 31: Text field truncation**
*For any* query result containing text fields longer than 200 characters, the formatted output should truncate them to 200 characters with an ellipsis.
**Validates: Requirements 8.3**

**Property 32: Row count metadata**
*For any* query result, the result object should include a row_count field that equals the actual number of rows returned.
**Validates: Requirements 8.5**

### Error Handling Properties

**Property 33: Graceful connection failure**
*For any* agent configuration with invalid database settings, starting a chat session should succeed and continue without database tools rather than crashing.
**Validates: Requirements 9.1**

**Property 34: Syntax error message return**
*For any* query with syntax errors, the database tool should return the error message to the agent rather than raising an exception.
**Validates: Requirements 9.2**

### Tool Discovery Properties

**Property 35: Tool registration on session start**
*For any* agent with database access, starting a chat session should result in database tools being registered with the tool calling system.
**Validates: Requirements 10.1**

**Property 36: Database tools in tool list**
*For any* agent session with database access, requesting available tools should return a list that includes all database tools.
**Validates: Requirements 10.2**

**Property 37: Tool descriptions present**
*For any* registered database tool, the tool definition should include a non-empty description field.
**Validates: Requirements 10.3**

**Property 38: Tool namespacing for multiple databases**
*For any* agent with N databases configured where N > 1, the registered tools should be namespaced by database name to prevent conflicts.
**Validates: Requirements 10.4**

**Property 39: Parameter schemas present**
*For any* registered database tool, the tool definition should include a parameter schema that describes all required and optional parameters.
**Validates: Requirements 10.5**

## Error Handling

### Connection Errors

**Error Type**: Database connection failure
**Handling**: 
- Log the error with full details
- Return user-friendly error message to agent
- Continue chat session without database tools
- Suggest checking configuration

**Error Type**: Connection lost during session
**Handling**:
- Attempt reconnection once
- If reconnection fails, disable database tools for remainder of session
- Notify agent that database is unavailable

### Query Errors

**Error Type**: SQL syntax error
**Handling**:
- Return database error message to agent
- Include query that caused the error (for debugging)
- Suggest corrections if possible

**Error Type**: Query timeout
**Handling**:
- Cancel query execution
- Return timeout error with elapsed time
- Suggest optimizing query or increasing timeout

**Error Type**: Write operation attempted
**Handling**:
- Reject query before execution
- Return error explaining read-only mode
- List rejected keywords found in query

### Configuration Errors

**Error Type**: Invalid database type
**Handling**:
- Reject configuration
- List supported database types
- Prompt user to select valid type

**Error Type**: Missing required parameters
**Handling**:
- Reject configuration
- List missing parameters
- Prompt user to provide values

**Error Type**: Invalid file path (SQLite)
**Handling**:
- Reject configuration
- Explain that file doesn't exist
- Suggest creating database or correcting path

### Schema Discovery Errors

**Error Type**: Table not found
**Handling**:
- Return error message with table name
- Suggest using list_tables to see available tables

**Error Type**: Permission denied
**Handling**:
- Return error explaining permission issue
- Suggest checking database user permissions

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific examples of database configurations (SQLite with valid path, PostgreSQL with all parameters)
- Edge cases like empty query results, NULL values, very long text fields
- Error conditions like invalid credentials, non-existent tables
- Integration points between CLI, agent config, and MCP client manager

**Property-Based Tests** focus on:
- Universal properties that hold for all inputs (query safety validation, result formatting)
- Configuration round-trip consistency
- Tool registration and discovery across different agent configurations
- Result truncation behavior across various row counts

### Property-Based Testing Configuration

**Testing Library**: Use `hypothesis` for Python property-based testing

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: database-access, Property N: [property text]**
- Custom generators for database configs, SQL queries, query results

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import pytest

@given(
    db_type=st.sampled_from(["sqlite", "postgresql", "mysql"]),
    name=st.text(min_size=1, max_size=50)
)
@pytest.mark.property_test
def test_database_type_validation(db_type, name):
    """
    Feature: database-access, Property 1: Database type validation
    
    For any database configuration, the system should accept only 
    "sqlite", "postgresql", or "mysql" as valid database types.
    """
    config = create_database_mcp_config(db_type, name, path="/tmp/test.db")
    assert config.database_type in ["sqlite", "postgresql", "mysql"]
```

### Test Coverage Goals

- Configuration management: 90%+ coverage
- Query validation: 100% coverage (critical for security)
- Result formatting: 85%+ coverage
- Error handling: 80%+ coverage
- CLI integration: 70%+ coverage (harder to test)

### Integration Testing

**Database Setup**:
- Use in-memory SQLite for fast tests
- Use Docker containers for PostgreSQL/MySQL integration tests
- Seed test databases with known schemas and data

**MCP Server Testing**:
- Mock MCP server responses for unit tests
- Use actual MCP servers for integration tests
- Test tool discovery and execution flows

**End-to-End Testing**:
- Create agent with database access
- Start chat session
- Execute queries through tool calling
- Verify results and error handling
- Clean up resources
