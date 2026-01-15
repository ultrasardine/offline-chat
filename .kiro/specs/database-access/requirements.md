# Requirements Document: Database Access for Agents

## Introduction

This feature adds database access capabilities to agents in the Offline Chat application through MCP (Model Context Protocol) server integration. Agents will be able to query databases (Oracle, PostgreSQL, MySQL, SQLite) using the existing MCP infrastructure, enabling them to retrieve and analyze data from configured databases during conversations.

**Primary Focus**: Oracle Database is the main database system for this implementation, with additional support for PostgreSQL, MySQL, and SQLite to enable multi-database access patterns.

## Glossary

- **Agent**: A customized Ollama model with a unique name, persona, and configuration
- **MCP_Server**: A Model Context Protocol server that provides tools and resources to agents
- **Database_Tool**: An MCP tool that enables database operations (query, schema discovery)
- **Database_Config**: Configuration specifying database type, connection parameters, and credentials
- **Query_Result**: The output from executing a database query, formatted for agent consumption
- **Schema_Discovery**: The process of retrieving database structure information (tables, columns)
- **Connection_String**: A formatted string containing database connection parameters
- **Read_Only_Mode**: A safety constraint that prevents write operations to databases
- **SQLcl**: Oracle SQL Command Line tool that provides the MCP server for Oracle Database
- **TNS_Connection**: Oracle's Transparent Network Substrate connection identifier
- **Oracle_Wallet**: Secure credential storage mechanism for Oracle Database connections

## Requirements

### Requirement 1: Database MCP Server Configuration

**User Story:** As a user, I want to configure database MCP servers for my agents, so that they can access specific databases during conversations.

#### Acceptance Criteria

1. WHEN a user creates or updates an agent with database access, THE System SHALL allow specification of database type (Oracle, PostgreSQL, MySQL, SQLite)
2. WHEN configuring an Oracle database, THE System SHALL accept either a TNS connection name or full connection details (host, port, service name, username, password)
3. WHEN configuring an Oracle database with SQLcl, THE System SHALL use existing SQLcl connections if available
4. WHEN configuring a SQLite database, THE System SHALL accept a file path to the database file
5. WHEN configuring PostgreSQL or MySQL databases, THE System SHALL accept connection parameters (host, port, database name, username, password)
6. WHEN database configuration is provided, THE System SHALL create an MCP server configuration entry for the database
7. WHEN multiple agents need the same database, THE System SHALL allow sharing of database MCP server configurations
8. WHEN saving agent configuration, THE System SHALL persist database MCP server settings to the agent's config file

### Requirement 2: Database Connection Management

**User Story:** As a user, I want database connections to be managed safely and efficiently, so that my agents can reliably access data without resource leaks.

#### Acceptance Criteria

1. WHEN an agent starts a chat session with database access, THE System SHALL establish database connections through the configured MCP server
2. WHEN an Oracle database connection is established, THE System SHALL use SQLcl MCP server with the specified connection
3. WHEN a database connection fails, THE System SHALL return a descriptive error message to the agent
4. WHEN a chat session ends, THE System SHALL close all database connections gracefully
5. WHEN multiple queries are executed in a session, THE System SHALL reuse existing connections
6. IF a database connection is lost during a session, THEN THE System SHALL attempt to reconnect before failing
7. WHEN using Oracle Database, THE System SHALL log all queries in the DBTOOLS$MCP_LOG table for audit purposes

### Requirement 3: Database Query Execution

**User Story:** As an agent, I want to execute SQL queries against configured databases, so that I can retrieve data to answer user questions.

#### Acceptance Criteria

1. WHEN an agent requests to execute a query, THE Database_Tool SHALL validate the SQL syntax
2. WHEN a valid SELECT query is provided, THE Database_Tool SHALL execute it and return formatted results
3. WHEN query results exceed 100 rows, THE Database_Tool SHALL return the first 100 rows with a truncation notice
4. WHEN a query execution fails, THE Database_Tool SHALL return an error message with details
5. WHEN a query takes longer than 30 seconds, THE Database_Tool SHALL timeout and return an error
6. THE Database_Tool SHALL operate in read-only mode by default, rejecting INSERT, UPDATE, DELETE, DROP, and ALTER statements

### Requirement 4: Database Schema Discovery

**User Story:** As an agent, I want to discover database schema information, so that I can construct appropriate queries without prior knowledge of the database structure.

#### Acceptance Criteria

1. WHEN an agent requests to list tables, THE Database_Tool SHALL return all table names in the database
2. WHEN an agent requests to describe a table, THE Database_Tool SHALL return column names, data types, and constraints
3. WHEN an agent requests schema for a non-existent table, THE Database_Tool SHALL return an error message
4. WHEN listing tables in Oracle, PostgreSQL or MySQL, THE Database_Tool SHALL filter out system tables by default
5. WHEN listing tables in Oracle, THE Database_Tool SHALL query USER_TABLES or ALL_TABLES based on permissions
6. THE Database_Tool SHALL provide a tool to retrieve the complete database schema in a single call

### Requirement 5: Secure Credential Management

**User Story:** As a user, I want database credentials to be stored securely, so that sensitive information is protected.

#### Acceptance Criteria

1. WHEN database credentials are provided, THE System SHALL store them in the MCP server configuration file
2. WHEN displaying agent configuration, THE System SHALL mask password fields in the output
3. WHEN serializing agent configuration to JSON, THE System SHALL include database credentials only in the MCP server config section
4. THE System SHALL store MCP server configurations with appropriate file permissions (readable only by owner)
5. WHEN validating database configuration, THE System SHALL not log or display credentials in error messages

### Requirement 6: CLI Integration for Database Configuration

**User Story:** As a user, I want to configure database access through the CLI, so that I can easily set up agents with database capabilities.

#### Acceptance Criteria

1. WHEN creating a new agent, THE CLI SHALL prompt whether to add database access
2. WHEN the user chooses to add database access, THE CLI SHALL prompt for database type selection with Oracle as the first option
3. WHEN Oracle is selected, THE CLI SHALL first check for existing SQLcl connections and offer to use them
4. WHEN Oracle is selected and no SQLcl connections exist, THE CLI SHALL prompt for connection details (host, port, service name, username, password)
5. WHEN SQLite is selected, THE CLI SHALL prompt for the database file path and validate it exists
6. WHEN PostgreSQL or MySQL is selected, THE CLI SHALL prompt for host, port, database name, username, and password
7. WHEN database configuration is complete, THE CLI SHALL test the connection before saving
8. IF the connection test fails, THEN THE CLI SHALL display the error and allow the user to retry or skip

### Requirement 7: Database Status Display

**User Story:** As a user, I want to see which databases are configured for each agent, so that I can understand their capabilities.

#### Acceptance Criteria

1. WHEN listing agents, THE CLI SHALL display database access status for each agent
2. WHEN displaying agent details, THE CLI SHALL show configured database types and connection information (excluding passwords)
3. WHEN an agent has multiple databases configured, THE CLI SHALL list all of them
4. WHEN an agent has no database access, THE CLI SHALL indicate "No database access"

### Requirement 8: Query Result Formatting

**User Story:** As an agent, I want query results formatted clearly, so that I can understand and communicate the data effectively.

#### Acceptance Criteria

1. WHEN query results are returned, THE Database_Tool SHALL format them as a structured table with column headers
2. WHEN results contain NULL values, THE Database_Tool SHALL represent them as "NULL" in the output
3. WHEN results contain long text fields, THE Database_Tool SHALL truncate them to 200 characters with an ellipsis
4. WHEN results are empty, THE Database_Tool SHALL return a message indicating no rows were found
5. THE Database_Tool SHALL include row count information in the result metadata

### Requirement 9: Error Handling and Recovery

**User Story:** As a user, I want database errors to be handled gracefully, so that my chat sessions remain stable even when database issues occur.

#### Acceptance Criteria

1. WHEN a database connection cannot be established, THE System SHALL log the error and continue the chat session without database tools
2. WHEN a query fails due to syntax errors, THE Database_Tool SHALL return the error message to the agent for correction
3. WHEN a database becomes unavailable during a session, THE System SHALL notify the agent and disable database tools
4. WHEN database operations timeout, THE System SHALL cancel the operation and return a timeout error
5. IF database errors occur repeatedly, THEN THE System SHALL suggest checking the database configuration

### Requirement 10: Database Tool Discovery

**User Story:** As an agent, I want to discover available database tools, so that I know what operations I can perform.

#### Acceptance Criteria

1. WHEN an agent session starts with database access, THE System SHALL register database tools with the tool calling system
2. WHEN an agent requests available tools, THE System SHALL include database tools in the response
3. THE System SHALL provide tool descriptions that explain query execution, schema discovery, and result formatting
4. WHEN multiple databases are configured, THE System SHALL namespace tools by database name to avoid conflicts
5. THE System SHALL include parameter schemas for each database tool to guide proper usage
