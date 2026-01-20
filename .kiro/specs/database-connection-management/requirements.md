# Requirements Document

## Introduction

This document specifies requirements for a centralized database connection management system for the Offline Chat application. The system will enable users to define database connections once and reuse them across multiple agents, improving maintainability and security.

## Glossary

- **Database_Connection**: A named configuration containing database type and connection parameters (host, port, credentials, etc.)
- **Connection_Manager**: The system component responsible for CRUD operations on database connections
- **Agent**: A customized Ollama model with specific purpose, persona, and optional database access
- **Connection_Reference**: A connection name stored in an agent's configuration
- **Connection_Store**: The centralized JSON file (~/.offline-chat/database_connections.json) storing all connection definitions
- **Agent_Config**: The configuration file for an agent, which may include connection references

## Requirements

### Requirement 1: Centralized Connection Storage

**User Story:** As a system administrator, I want database connections stored in a centralized location, so that I can manage them independently from agent configurations.

#### Acceptance Criteria

1. THE Connection_Store SHALL be located at ~/.offline-chat/database_connections.json
2. WHEN the Connection_Store does not exist, THE System SHALL create it with an empty connections list
3. THE Connection_Store SHALL contain a JSON array of connection objects with fields: name, database_type, and connection parameters
4. WHEN the Connection_Store is accessed, THE System SHALL validate its JSON structure
5. THE Connection_Store SHALL have file permissions restricting access to the owner only (600)

### Requirement 2: Create Database Connection

**User Story:** As a user, I want to create new database connections, so that I can define reusable connection configurations.

#### Acceptance Criteria

1. WHEN a user creates a connection, THE System SHALL require a unique name in kebab-case format
2. WHEN a user creates a connection, THE System SHALL require a database_type from the supported list (oracle, postgresql, mysql, sqlite)
3. WHEN a user creates a connection with duplicate name, THE System SHALL reject the creation and display an error message
4. WHEN a user provides connection parameters, THE System SHALL validate required fields based on database_type
5. WHEN a user creates a connection, THE System SHALL test the connection before saving
6. WHEN connection validation succeeds, THE System SHALL save the connection to the Connection_Store
7. WHEN connection validation fails, THE System SHALL display the error and not save the connection

### Requirement 3: List Database Connections

**User Story:** As a user, I want to view all available database connections, so that I can see what connections exist and their details.

#### Acceptance Criteria

1. WHEN a user lists connections, THE System SHALL display all connections from the Connection_Store
2. WHEN displaying connections, THE System SHALL show name, database_type, and host information
3. WHEN displaying connections, THE System SHALL mask sensitive credentials (passwords, tokens)
4. WHEN displaying connections, THE System SHALL indicate which agents are using each connection
5. WHEN no connections exist, THE System SHALL display a message indicating the list is empty

### Requirement 4: Update Database Connection

**User Story:** As a user, I want to update existing database connections, so that I can modify connection parameters without recreating them.

#### Acceptance Criteria

1. WHEN a user updates a connection, THE System SHALL allow modification of all connection parameters except the name
2. WHEN a user updates a connection, THE System SHALL validate the new parameters
3. WHEN a user updates a connection, THE System SHALL test the connection with new parameters before saving
4. WHEN connection validation succeeds, THE System SHALL save the updated connection
5. WHEN connection validation fails, THE System SHALL display the error and preserve the original connection
6. WHEN a connection is updated, THE System SHALL notify that all agents using this connection will use the new parameters

### Requirement 5: Delete Database Connection

**User Story:** As a user, I want to delete database connections, so that I can remove connections that are no longer needed.

#### Acceptance Criteria

1. WHEN a user deletes a connection, THE System SHALL check if any agents reference this connection
2. WHEN a connection is referenced by agents, THE System SHALL prevent deletion and display which agents are using it
3. WHEN a connection is not referenced by any agents, THE System SHALL remove it from the Connection_Store
4. WHEN a connection is deleted, THE System SHALL confirm the deletion with the user before proceeding
5. WHEN a connection deletion is cancelled, THE System SHALL preserve the connection unchanged

### Requirement 6: Agent Connection Assignment

**User Story:** As a user, I want to assign database connections to agents, so that agents can access databases without inline configuration.

#### Acceptance Criteria

1. WHEN an agent is created or updated, THE System SHALL allow selection of zero or more database connections
2. WHEN a user assigns a connection to an agent, THE System SHALL validate that the connection exists in the Connection_Store
3. WHEN a user assigns connections, THE Agent_Config SHALL store an array of connection names
4. WHEN a user views agent configuration, THE System SHALL display assigned connection names
5. WHEN an agent starts, THE System SHALL resolve connection names to actual connection configurations

### Requirement 7: Update Agent Configuration

**User Story:** As a user, I want to update existing agents, so that I can modify their configuration including database connections.

#### Acceptance Criteria

1. WHEN a user selects update agent, THE System SHALL display a list of existing agents
2. WHEN a user selects an agent to update, THE System SHALL display update options: system prompt, temperature, language, web search, database connections, MCP servers
3. WHEN a user selects database connections option, THE System SHALL display currently assigned connections
4. WHEN updating database connections, THE System SHALL allow adding connections from available list
5. WHEN updating database connections, THE System SHALL allow removing currently assigned connections
6. WHEN agent update is complete, THE System SHALL save the updated Agent_Config

### Requirement 8: Connection Validation

**User Story:** As a developer, I want connections validated before use, so that agents don't fail due to invalid connection configurations.

#### Acceptance Criteria

1. WHEN a connection is created or updated, THE System SHALL test connectivity to the database
2. WHEN testing a connection, THE System SHALL verify required parameters are present
3. WHEN testing an Oracle connection, THE System SHALL verify host, port, service_name, username, and password
4. WHEN testing a PostgreSQL connection, THE System SHALL verify host, port, database, username, and password
5. WHEN testing a MySQL connection, THE System SHALL verify host, port, database, username, and password
6. WHEN testing a SQLite connection, THE System SHALL verify the database file path exists or can be created
7. WHEN connection test fails, THE System SHALL return a descriptive error message

### Requirement 9: Migration from Inline Configuration

**User Story:** As a system administrator, I want existing inline database configurations migrated to the centralized system, so that backward compatibility is maintained.

#### Acceptance Criteria

1. WHEN the System starts, THE System SHALL check for agents with inline database configurations
2. WHEN an agent has inline database configuration, THE System SHALL create a corresponding connection in the Connection_Store
3. WHEN creating a migrated connection, THE System SHALL generate a unique name based on agent name and database type
4. WHEN migration creates a connection, THE System SHALL update the Agent_Config to reference the new connection name
5. WHEN migration is complete, THE System SHALL remove inline configuration from Agent_Config
6. WHEN migration encounters errors, THE System SHALL log the error and preserve the original configuration

### Requirement 10: Connection Security

**User Story:** As a security-conscious user, I want database credentials protected, so that sensitive information is not exposed.

#### Acceptance Criteria

1. THE Connection_Store file SHALL have permissions set to 600 (owner read/write only)
2. WHEN displaying connections in CLI, THE System SHALL mask password fields with asterisks
3. WHEN displaying connections in CLI, THE System SHALL mask sensitive tokens or keys
4. WHEN logging connection operations, THE System SHALL not log sensitive credentials
5. WHEN an error occurs with connection details, THE System SHALL sanitize credentials from error messages

### Requirement 11: Connection Resolution

**User Story:** As a developer, I want connection names resolved to configurations at runtime, so that agents always use current connection parameters.

#### Acceptance Criteria

1. WHEN an agent session starts, THE System SHALL load the agent's connection references
2. WHEN resolving connection references, THE System SHALL look up each connection name in the Connection_Store
3. WHEN a referenced connection does not exist, THE System SHALL display an error and list available connections
4. WHEN a referenced connection exists, THE System SHALL load its full configuration
5. WHEN all connections are resolved, THE System SHALL provide them to the agent session

### Requirement 12: Database Access Levels

**User Story:** As a security administrator, I want to control what database operations each agent can perform, so that I can enforce least-privilege access.

#### Acceptance Criteria

1. WHEN assigning a connection to an agent, THE System SHALL allow specification of an access level
2. THE System SHALL support access levels: read-only, read-write, table-specific-read, table-specific-read-write
3. WHEN access level is "read-only", THE Agent SHALL only execute SELECT queries
4. WHEN access level is "read-write", THE Agent SHALL execute SELECT, INSERT, UPDATE, DELETE queries
5. WHEN access level is "table-specific-read", THE System SHALL allow specification of allowed tables for SELECT
6. WHEN access level is "table-specific-read-write", THE System SHALL allow specification of allowed tables for all operations
7. WHEN an agent attempts a query, THE System SHALL validate the query against the assigned access level
8. WHEN a query violates access level, THE System SHALL reject it with a descriptive error message
9. THE Agent_Config SHALL store access level per connection assignment
10. WHEN displaying agent configuration, THE System SHALL show access level for each connection

### Requirement 13: Agent Guidelines Management

**User Story:** As a user, I want to define and manage agent guidelines as a list of bullet points, so that I can easily add, edit, or remove specific behavioral rules.

#### Acceptance Criteria

1. THE Agent_Config SHALL include a guidelines field storing a list of guideline strings
2. WHEN creating an agent, THE System SHALL allow optional specification of guidelines
3. WHEN updating an agent, THE System SHALL provide options to: add guideline, edit guideline, delete guideline, list guidelines
4. WHEN adding a guideline, THE System SHALL append it to the guidelines list
5. WHEN editing a guideline, THE System SHALL allow selection by index and modification of text
6. WHEN deleting a guideline, THE System SHALL allow selection by index and remove it from the list
7. WHEN listing guidelines, THE System SHALL display all guidelines with index numbers
8. THE System SHALL include guidelines in the agent's system prompt when starting a session
9. WHEN guidelines are empty, THE System SHALL use only the base system prompt
10. WHEN guidelines exist, THE System SHALL format them as bullet points in the system prompt

### Requirement 14: CLI Menu Integration

**User Story:** As a user, I want database connection management integrated into the main menu, so that I can easily access connection operations.

#### Acceptance Criteria

1. THE Main_Menu SHALL include a "Manage database connections" option
2. WHEN "Manage database connections" is selected, THE System SHALL display connection management submenu
3. THE Connection_Management_Submenu SHALL include options: Create, List, Update, Delete, Back
4. THE Main_Menu SHALL include an "Update agent" option
5. WHEN "Update agent" is selected, THE System SHALL display agent selection and update options
6. THE Update_Agent_Menu SHALL include a "Manage guidelines" option
7. WHEN "Manage guidelines" is selected, THE System SHALL display guideline management submenu
