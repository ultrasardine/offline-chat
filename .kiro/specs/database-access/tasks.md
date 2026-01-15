# Implementation Plan: Database Access for Agents

## Overview

This implementation plan adds database access capabilities to agents through MCP server integration. The approach leverages the existing MCP infrastructure (`mcp_client.py`, `mcp_config.py`) and extends agent configuration to support database connections.

**Primary Database**: Oracle Database is the main target, accessed through Oracle SQLcl's built-in MCP server. Additional support for PostgreSQL, MySQL, and SQLite enables multi-database access patterns.

Implementation will be incremental, starting with core configuration and building up to full CLI integration.

## Tasks

- [x] 1. Extend MCP server configuration for database support
  - Add optional database-specific fields to `MCPServerConfig` dataclass in `offline_chat/mcp_config.py`
  - Fields: `database_type`, `oracle_connection_name`, `oracle_tns_name`, `database_path`, `database_host`, `database_port`, `database_name`, `database_user`, `database_password`
  - Update serialization/deserialization to handle new fields
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 1.1 Write property test for configuration serialization round-trip
  - **Property 6: Configuration serialization round-trip**
  - **Validates: Requirements 1.8**

- [x] 2. Create database MCP configuration factory
  - [x] 2.1 Implement `create_database_mcp_config()` factory function in new file `offline_chat/database_config.py`
    - Accept database type and connection parameters
    - Return configured `MCPServerConfig` for the database
    - Support "oracle", "postgresql", "mysql", "sqlite"
    - _Requirements: 1.6_

  - [x] 2.2 Implement Oracle-specific config builder
    - `_create_oracle_config()` - accepts connection_name, tns_name, or full connection details
    - Support existing SQLcl connections (highest priority)
    - Support TNS aliases (second priority)
    - Support full connection details (host, port, service_name, username, password)
    - _Requirements: 1.2, 1.3_

  - [x] 2.3 Implement database-specific config builders
    - `_create_sqlite_config()` - accepts file path
    - `_create_postgresql_config()` - accepts host, port, database, user, password
    - `_create_mysql_config()` - accepts host, port, database, user, password
    - _Requirements: 1.4, 1.5_

  - [x] 2.4 Write property tests for database config generation
    - **Property 1: Database type validation**
    - **Property 2: Oracle configuration acceptance**
    - **Property 3: SQLite configuration acceptance**
    - **Property 4: PostgreSQL/MySQL configuration acceptance**
    - **Property 5: MCP server config generation**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

- [x] 3. Implement query safety validator
  - [x] 3.1 Create `offline_chat/query_validator.py` with `is_read_only_query()` function
    - Check for write operation keywords (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE)
    - Return True only for SELECT queries
    - _Requirements: 3.6_

  - [x] 3.2 Write property test for query safety validation
    - **Property 11: Read-only query validation**
    - **Validates: Requirements 3.6**

  - [x] 3.3 Write unit tests for edge cases
    - Test queries with comments containing write keywords
    - Test case-insensitive detection
    - Test queries with multiple statements
    - _Requirements: 3.6_

- [x] 4. Implement database connection validator
  - [x] 4.1 Create `offline_chat/connection_validator.py` with `validate_database_connection()` function
    - Start MCP server temporarily with provided config
    - Execute simple test query (SELECT 1 for most DBs, SELECT 1 FROM DUAL for Oracle)
    - Return (success: bool, error_message: Optional[str])
    - Clean up temporary server connection
    - _Requirements: 2.3, 6.7_

  - [x] 4.2 Write property test for connection validation
    - **Property 8: Connection failure error messages**
    - **Validates: Requirements 2.3**

- [x] 5. Implement query result formatter
  - [x] 5.1 Create `QueryResult` dataclass in `offline_chat/query_result.py`
    - Fields: columns, rows, row_count, truncated, execution_time_ms
    - Implement `to_markdown_table()` method
    - Implement `to_json()` method
    - _Requirements: 8.1, 8.5_

  - [x] 5.2 Add result formatting logic
    - Handle NULL values (represent as "NULL" string)
    - Truncate long text fields to 200 characters with ellipsis
    - Handle empty results with appropriate message
    - _Requirements: 8.2, 8.3, 8.4_

  - [x] 5.3 Write property tests for result formatting
    - **Property 29: Table formatting with headers**
    - **Property 30: NULL value representation**
    - **Property 31: Text field truncation**
    - **Property 32: Row count metadata**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.5**

  - [x] 5.4 Write unit test for empty result edge case
    - Test that empty results return "No rows found" message
    - _Requirements: 8.4_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement credential masking utilities
  - [x] 7.1 Create `offline_chat/credential_utils.py` with masking functions
    - `mask_password()` - replace password with "****"
    - `sanitize_config_for_display()` - mask all sensitive fields in config
    - `sanitize_error_message()` - remove credentials from error messages
    - _Requirements: 5.2, 5.5_

  - [x] 7.2 Write property tests for credential masking
    - **Property 21: Password masking in display**
    - **Property 23: Credential exclusion from error messages**
    - **Validates: Requirements 5.2, 5.5**

- [x] 8. Extend CLI for database configuration
  - [x] 8.1 Create `offline_chat/database_config_cli.py` with interactive configuration functions
    - `configure_database_access()` - main entry point for adding databases
    - `select_database_type()` - prompt for database type selection (Oracle first)
    - `configure_oracle()` - prompt for Oracle connection (check SQLcl connections first)
    - `list_sqlcl_connections()` - list existing SQLcl connections from ~/.sqlcl/connections.json
    - `configure_sqlite()` - prompt for SQLite file path
    - `configure_postgresql()` - prompt for PostgreSQL connection params
    - `configure_mysql()` - prompt for MySQL connection params
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 8.2 Add file path validation for SQLite
    - Check if file exists before accepting configuration
    - Provide helpful error message if file not found
    - _Requirements: 6.5_

  - [x] 8.3 Write property tests for CLI validation
    - **Property 24: Oracle connection detection**
    - **Property 25: SQLite file path validation**
    - **Validates: Requirements 6.3, 6.5**

  - [x] 8.4 Integrate database configuration into agent creation flow
    - Modify agent creation in `offline_chat/cli.py` to call `configure_database_access()`
    - Test connection before saving agent
    - Handle connection test failures with retry/skip options
    - _Requirements: 6.7, 6.8_

- [x] 9. Extend CLI for database status display
  - [x] 9.1 Update agent listing display in `offline_chat/cli.py`
    - Show database access status for each agent
    - Format: "Databases: oracle(prod_db), postgresql(analytics_db)" or "No database access"
    - _Requirements: 7.1, 7.4_

  - [x] 9.2 Update agent detail display
    - Show full database configuration with masked passwords
    - List all configured databases with connection info
    - _Requirements: 7.2, 7.3_

  - [x] 9.3 Write property tests for CLI display formatting
    - **Property 26: Database status display**
    - **Property 27: Password masking in CLI display**
    - **Property 28: Multiple database display**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 9.4 Write unit test for no database access display
    - Test that agents without databases show "No database access"
    - _Requirements: 7.4_

- [x] 10. Implement database tool integration with MCPClientManager
  - [x] 10.1 Verify tool registration in `offline_chat/mcp_client.py`
    - Ensure database tools are discovered when MCP server connects
    - Verify tools are registered with tool calling system
    - Handle Oracle SQLcl tool names (run-sql, list-connections)
    - _Requirements: 10.1, 10.2_

  - [x] 10.2 Add tool namespacing for multiple databases
    - When multiple databases configured, prefix tool names with database name
    - Example: `prod_db_run_sql`, `analytics_db_query_database`
    - _Requirements: 10.4_

  - [x] 10.3 Write property tests for tool discovery
    - **Property 35: Tool registration on session start**
    - **Property 36: Database tools in tool list**
    - **Property 37: Tool descriptions present**
    - **Property 38: Tool namespacing for multiple databases**
    - **Property 39: Parameter schemas present**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

- [x] 11. Implement connection lifecycle management
  - [x] 11.1 Add connection tracking to `ChatSession` in `offline_chat/session.py`
    - Track active database connections per session
    - Implement connection reuse for multiple queries
    - Handle Oracle audit logging (queries logged in DBTOOLS$MCP_LOG)
    - _Requirements: 2.5, 2.7_

  - [x] 11.2 Add connection cleanup on session end
    - Close all database connections when session ends
    - Ensure no resource leaks
    - _Requirements: 2.4_

  - [x] 11.3 Write property tests for connection management
    - **Property 7: Oracle audit logging**
    - **Property 9: Connection cleanup**
    - **Property 10: Connection reuse**
    - **Validates: Requirements 2.4, 2.5, 2.7**

- [x] 12. Implement error handling and graceful degradation
  - [x] 12.1 Add connection failure handling in `ChatSession`
    - Log connection errors
    - Continue session without database tools if connection fails
    - _Requirements: 9.1_

  - [x] 12.2 Add query error handling
    - Catch and return syntax errors to agent
    - Catch and return execution errors to agent
    - _Requirements: 9.2_

  - [x] 12.3 Write property tests for error handling
    - **Property 33: Graceful connection failure**
    - **Property 34: Syntax error message return**
    - **Validates: Requirements 9.1, 9.2**

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Add integration tests
  - [x] 14.1 Write integration test for Oracle database access
    - Create agent with Oracle database using SQLcl MCP server
    - Start chat session
    - Execute queries through tool calling (run-sql)
    - Verify results
    - Check DBTOOLS$MCP_LOG for audit entries
    - Clean up
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.7, 3.2, 4.1_

  - [x] 14.2 Write integration test for SQLite database access
    - Create agent with SQLite database
    - Start chat session
    - Execute queries through tool calling
    - Verify results
    - Clean up
    - _Requirements: 1.1, 1.4, 2.1, 3.2, 4.1_

  - [x] 14.3 Write integration test for schema discovery
    - Test list_tables tool (list-connections for Oracle)
    - Test describe_table tool
    - Test get_schema tool
    - Verify Oracle system table filtering
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6_

  - [x] 14.4 Write integration test for error scenarios
    - Test connection failure handling
    - Test invalid query handling
    - Test non-existent table handling
    - _Requirements: 2.3, 3.4, 4.3_

- [x] 15. Update documentation
  - [x] 15.1 Add database access section to README
    - Explain how to configure database access
    - Provide examples for Oracle (primary), PostgreSQL, MySQL, and SQLite
    - Document Oracle SQLcl MCP server setup
    - Document available database tools (run-sql, list-connections, etc.)
    - Include Oracle-specific features (audit logging, V$SESSION tracking)

  - [x] 15.2 Add inline code documentation
    - Ensure all new functions have docstrings
    - Add usage examples for complex functions
    - Document Oracle-specific configuration options

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end functionality with actual database connections
- The implementation leverages existing MCP infrastructure to minimize changes
- **Oracle Database is the primary target** using SQLcl's built-in MCP server
- Oracle SQLcl provides official MCP support with audit logging and session tracking
- Database credentials are stored in MCP server configs following existing patterns
- Query safety is enforced through validation before execution
- Oracle-specific features include TNS support, SQLcl connection reuse, and DBTOOLS$MCP_LOG audit table
