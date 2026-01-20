# Design Document: Database Connection Management

## Overview

The centralized database connection management system provides a reusable, secure way to manage database connections across multiple agents. Instead of configuring database connections inline for each agent, users define connections once in a centralized store and reference them by name. This design improves maintainability, security, and consistency.

The system consists of:
- A centralized connection store (~/.offline-chat/database_connections.json)
- A DatabaseConnectionManager class for CRUD operations
- Connection validation and testing capabilities
- Integration with agent configuration and CLI menus
- Migration support for existing inline configurations

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Main Menu       │  │  Update Agent    │                │
│  │  - Manage DB     │  │  - Assign Conns  │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         DatabaseConnectionManager                     │  │
│  │  - create_connection()                                │  │
│  │  - list_connections()                                 │  │
│  │  - update_connection()                                │  │
│  │  - delete_connection()                                │  │
│  │  - validate_connection()                              │  │
│  │  - resolve_connections()                              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         AgentManager (Enhanced)                       │  │
│  │  - update_agent()                                     │  │
│  │  - assign_connections()                               │  │
│  │  - migrate_inline_configs()                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Connection Store │  │  Agent Configs   │                │
│  │  connections.json│  │  config.json     │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

**Creating a Connection:**
1. User selects "Manage database connections" → "Create"
2. CLI prompts for connection details (name, type, parameters)
3. DatabaseConnectionManager validates parameters
4. DatabaseConnectionManager tests connection
5. If valid, save to connection store
6. Display success message

**Assigning Connection to Agent:**
1. User selects "Update agent" → Select agent → "Database connections"
2. CLI displays available connections and currently assigned
3. User adds/removes connections
4. AgentManager validates connection names exist
5. AgentManager updates agent config with connection references
6. Display success message

**Agent Session Start:**
1. Agent session loads agent config
2. Reads connection_references array
3. DatabaseConnectionManager resolves each reference to full config
4. If any reference invalid, display error
5. Pass resolved connections to agent session

## Components and Interfaces

### DatabaseConnection Data Model

```python
@dataclass
class DatabaseConnection:
    """Represents a database connection configuration."""
    name: str                          # Unique identifier (kebab-case)
    database_type: str                 # oracle, postgresql, mysql, sqlite
    host: str | None = None           # Database host (not for sqlite)
    port: int | None = None           # Database port (not for sqlite)
    database: str | None = None       # Database name (postgres/mysql)
    service_name: str | None = None   # Oracle service name
    username: str | None = None       # Database username
    password: str | None = None       # Database password (encrypted)
    file_path: str | None = None      # SQLite file path
    additional_params: dict = field(default_factory=dict)  # Extra params
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConnection':
        """Create instance from dictionary."""
        pass
    
    def mask_sensitive_fields(self) -> dict:
        """Return dict with masked passwords/credentials."""
        pass
```

### DatabaseConnectionManager

```python
class DatabaseConnectionManager:
    """Manages CRUD operations for database connections."""
    
    def __init__(self, store_path: Path = Path.home() / '.offline-chat' / 'database_connections.json'):
        """Initialize manager with connection store path."""
        self.store_path = store_path
        self._ensure_store_exists()
        self._set_secure_permissions()
    
    def create_connection(self, connection: DatabaseConnection) -> Result[DatabaseConnection, str]:
        """
        Create a new database connection.
        
        Steps:
        1. Validate connection name is unique
        2. Validate required parameters for database type
        3. Test connection
        4. Save to store
        5. Return success or error
        
        Returns:
            Result with connection or error message
        """
        pass
    
    def list_connections(self) -> list[DatabaseConnection]:
        """
        List all database connections.
        
        Returns:
            List of all connections from store
        """
        pass
    
    def get_connection(self, name: str) -> Result[DatabaseConnection, str]:
        """
        Get a specific connection by name.
        
        Args:
            name: Connection name
            
        Returns:
            Result with connection or error if not found
        """
        pass
    
    def update_connection(self, name: str, updates: dict) -> Result[DatabaseConnection, str]:
        """
        Update an existing connection.
        
        Steps:
        1. Load existing connection
        2. Apply updates (except name)
        3. Validate updated parameters
        4. Test connection
        5. Save to store
        6. Return success or error
        
        Args:
            name: Connection name to update
            updates: Dictionary of fields to update
            
        Returns:
            Result with updated connection or error message
        """
        pass
    
    def delete_connection(self, name: str) -> Result[None, str]:
        """
        Delete a connection if not in use.
        
        Steps:
        1. Check if any agents reference this connection
        2. If in use, return error with agent list
        3. If not in use, remove from store
        4. Return success or error
        
        Args:
            name: Connection name to delete
            
        Returns:
            Result with None or error message
        """
        pass
    
    def validate_connection(self, connection: DatabaseConnection) -> Result[None, str]:
        """
        Validate connection parameters and test connectivity.
        
        Steps:
        1. Validate required fields for database type
        2. Attempt database connection
        3. Execute simple query (SELECT 1)
        4. Close connection
        5. Return success or error
        
        Args:
            connection: Connection to validate
            
        Returns:
            Result with None or error message
        """
        pass
    
    def resolve_connections(self, connection_names: list[str]) -> Result[list[DatabaseConnection], str]:
        """
        Resolve connection names to full configurations.
        
        Steps:
        1. For each name, look up in store
        2. If any not found, return error
        3. Return list of resolved connections
        
        Args:
            connection_names: List of connection names to resolve
            
        Returns:
            Result with list of connections or error message
        """
        pass
    
    def get_agents_using_connection(self, connection_name: str) -> list[str]:
        """
        Find all agents that reference a connection.
        
        Steps:
        1. Scan all agent configs
        2. Check connection_references field
        3. Return list of agent names
        
        Args:
            connection_name: Connection name to search for
            
        Returns:
            List of agent names using this connection
        """
        pass
    
    def _ensure_store_exists(self) -> None:
        """Create store file if it doesn't exist."""
        pass
    
    def _set_secure_permissions(self) -> None:
        """Set file permissions to 600 (owner only)."""
        pass
    
    def _load_store(self) -> dict:
        """Load connections from JSON file."""
        pass
    
    def _save_store(self, data: dict) -> None:
        """Save connections to JSON file."""
        pass
```

### AccessLevel Data Model

```python
from enum import Enum

class AccessLevel(str, Enum):
    """Database access levels for agent-connection assignments."""
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"
    TABLE_SPECIFIC_READ = "table-specific-read"
    TABLE_SPECIFIC_READ_WRITE = "table-specific-read-write"
```

### AgentConnectionAssignment Data Model

```python
@dataclass
class AgentConnectionAssignment:
    """Represents an agent's assignment to a database connection with access control."""
    connection_name: str
    access_level: AccessLevel
    allowed_tables: list[str] = field(default_factory=list)  # For table-specific access
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "connection_name": self.connection_name,
            "access_level": self.access_level.value,
            "allowed_tables": self.allowed_tables
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConnectionAssignment':
        """Create instance from dictionary."""
        return cls(
            connection_name=data["connection_name"],
            access_level=AccessLevel(data["access_level"]),
            allowed_tables=data.get("allowed_tables", [])
        )
```

### Enhanced AgentConfig

```python
@dataclass
class AgentConfig:
    """Enhanced agent configuration with connection references and guidelines."""
    name: str
    display_name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7
    language: str | None = None
    web_search_enabled: bool = False
    mcp_servers: list[str] = field(default_factory=list)
    connection_assignments: list[AgentConnectionAssignment] = field(default_factory=list)  # NEW
    guidelines: list[str] = field(default_factory=list)  # NEW
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Legacy fields for migration
    connection_references: list[str] = field(default_factory=list)  # Deprecated
    database_config: dict | None = None  # Deprecated, for backward compatibility
    
    def get_full_system_prompt(self) -> str:
        """Generate system prompt with guidelines included."""
        if not self.guidelines:
            return self.system_prompt
        
        guidelines_text = "\n\nGuidelines:\n" + "\n".join(f"- {g}" for g in self.guidelines)
        return self.system_prompt + guidelines_text
```

### AccessLevelValidator

```python
class AccessLevelValidator:
    """Validates queries against assigned access levels."""
    
    @staticmethod
    def validate_query(
        query: str,
        access_level: AccessLevel,
        allowed_tables: list[str]
    ) -> Result[None, str]:
        """
        Validate a query against the assigned access level.
        
        Steps:
        1. Parse query to identify operation type (SELECT, INSERT, UPDATE, DELETE, etc.)
        2. Extract table names from query
        3. Check if operation is allowed by access level
        4. For table-specific access, check if tables are in allowed list
        5. Return success or error with details
        
        Args:
            query: SQL query to validate
            access_level: Access level to enforce
            allowed_tables: List of allowed tables (for table-specific access)
            
        Returns:
            Result with None or error message
        """
        pass
    
    @staticmethod
    def _parse_query_operation(query: str) -> str:
        """Extract operation type from query (SELECT, INSERT, UPDATE, DELETE, etc.)."""
        pass
    
    @staticmethod
    def _extract_table_names(query: str) -> list[str]:
        """Extract table names referenced in query."""
        pass
```

### Enhanced AgentManager

```python
class AgentManager:
    """Enhanced agent manager with connection assignment and guidelines."""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        """Initialize with database connection manager."""
        self.db_manager = db_manager
    
    def update_agent(self, agent_name: str, updates: dict) -> Result[AgentConfig, str]:
        """
        Update an existing agent configuration.
        
        Supports updating:
        - system_prompt
        - temperature
        - language
        - web_search_enabled
        - connection_assignments
        - mcp_servers
        - guidelines
        
        Args:
            agent_name: Name of agent to update
            updates: Dictionary of fields to update
            
        Returns:
            Result with updated config or error message
        """
        pass
    
    def assign_connection(
        self,
        agent_name: str,
        connection_name: str,
        access_level: AccessLevel,
        allowed_tables: list[str] = None
    ) -> Result[None, str]:
        """
        Assign a database connection to an agent with access control.
        
        Steps:
        1. Validate connection name exists
        2. Validate allowed_tables if table-specific access
        3. Load agent config
        4. Create AgentConnectionAssignment
        5. Add to connection_assignments
        6. Save agent config
        
        Args:
            agent_name: Agent to update
            connection_name: Connection name to assign
            access_level: Access level for this connection
            allowed_tables: List of allowed tables (for table-specific access)
            
        Returns:
            Result with None or error message
        """
        pass
    
    def remove_connection(self, agent_name: str, connection_name: str) -> Result[None, str]:
        """
        Remove a connection assignment from an agent.
        
        Args:
            agent_name: Agent to update
            connection_name: Connection name to remove
            
        Returns:
            Result with None or error message
        """
        pass
    
    def add_guideline(self, agent_name: str, guideline: str) -> Result[None, str]:
        """
        Add a guideline to an agent.
        
        Args:
            agent_name: Agent to update
            guideline: Guideline text to add
            
        Returns:
            Result with None or error message
        """
        pass
    
    def edit_guideline(self, agent_name: str, index: int, new_text: str) -> Result[None, str]:
        """
        Edit an existing guideline.
        
        Args:
            agent_name: Agent to update
            index: Index of guideline to edit (0-based)
            new_text: New guideline text
            
        Returns:
            Result with None or error message
        """
        pass
    
    def delete_guideline(self, agent_name: str, index: int) -> Result[None, str]:
        """
        Delete a guideline from an agent.
        
        Args:
            agent_name: Agent to update
            index: Index of guideline to delete (0-based)
            
        Returns:
            Result with None or error message
        """
        pass
    
    def list_guidelines(self, agent_name: str) -> Result[list[str], str]:
        """
        List all guidelines for an agent.
        
        Args:
            agent_name: Agent to query
            
        Returns:
            Result with list of guidelines or error message
        """
        pass
    
    def migrate_inline_configs(self) -> dict[str, str]:
        """
        Migrate agents with inline database configs to centralized system.
        
        Steps:
        1. Scan all agent configs
        2. For each with database_config field:
           a. Create connection in store (name: {agent}-{db_type})
           b. Update agent config with connection_assignment (read-write access)
           c. Remove database_config field
        3. For each with connection_references field:
           a. Convert to connection_assignments with read-write access
           b. Remove connection_references field
        4. Return mapping of agent -> connection name
        
        Returns:
            Dictionary mapping agent names to created connection names
        """
        pass
```

### Connection Validation

```python
class ConnectionValidator:
    """Validates and tests database connections."""
    
    @staticmethod
    def validate_oracle(connection: DatabaseConnection) -> Result[None, str]:
        """
        Validate Oracle connection parameters and test connectivity.
        
        Required fields: host, port, service_name, username, password
        """
        pass
    
    @staticmethod
    def validate_postgresql(connection: DatabaseConnection) -> Result[None, str]:
        """
        Validate PostgreSQL connection parameters and test connectivity.
        
        Required fields: host, port, database, username, password
        """
        pass
    
    @staticmethod
    def validate_mysql(connection: DatabaseConnection) -> Result[None, str]:
        """
        Validate MySQL connection parameters and test connectivity.
        
        Required fields: host, port, database, username, password
        """
        pass
    
    @staticmethod
    def validate_sqlite(connection: DatabaseConnection) -> Result[None, str]:
        """
        Validate SQLite connection parameters and test connectivity.
        
        Required fields: file_path
        """
        pass
    
    @staticmethod
    def test_connection(connection: DatabaseConnection) -> Result[None, str]:
        """
        Test database connectivity by executing a simple query.
        
        Steps:
        1. Establish connection using appropriate driver
        2. Execute SELECT 1 (or equivalent)
        3. Close connection
        4. Return success or error with details
        """
        pass
```

## Data Models

### Connection Store Format

```json
{
  "version": "1.0",
  "connections": [
    {
      "name": "prod-oracle",
      "database_type": "oracle",
      "host": "prod-db.example.com",
      "port": 1521,
      "service_name": "PRODDB",
      "username": "app_user",
      "password": "encrypted_password_here",
      "additional_params": {},
      "created_at": "2025-01-13T10:00:00Z",
      "updated_at": "2025-01-13T10:00:00Z"
    },
    {
      "name": "dev-postgres",
      "database_type": "postgresql",
      "host": "localhost",
      "port": 5432,
      "database": "devdb",
      "username": "dev_user",
      "password": "encrypted_password_here",
      "additional_params": {},
      "created_at": "2025-01-13T10:05:00Z",
      "updated_at": "2025-01-13T10:05:00Z"
    },
    {
      "name": "local-sqlite",
      "database_type": "sqlite",
      "file_path": "/home/user/.offline-chat/data/local.db",
      "additional_params": {},
      "created_at": "2025-01-13T10:10:00Z",
      "updated_at": "2025-01-13T10:10:00Z"
    }
  ]
}
```

### Enhanced Agent Config Format

```json
{
  "name": "data-analyst",
  "display_name": "Data Analyst Agent",
  "base_model": "llama3:latest",
  "system_prompt": "You are a data analyst...",
  "temperature": 0.7,
  "language": "english",
  "web_search_enabled": false,
  "mcp_servers": ["mcp-server-1"],
  "connection_assignments": [
    {
      "connection_name": "prod-oracle",
      "access_level": "read-only",
      "allowed_tables": []
    },
    {
      "connection_name": "dev-postgres",
      "access_level": "table-specific-read-write",
      "allowed_tables": ["users", "orders", "products"]
    }
  ],
  "guidelines": [
    "Always explain your SQL queries before executing them",
    "Never modify production data without explicit user confirmation",
    "Provide data visualizations when appropriate"
  ],
  "created_at": "2025-01-13T09:00:00Z",
  "updated_at": "2025-01-13T11:00:00Z"
}
```

### Migration Example

**Before (inline config):**
```json
{
  "name": "sales-agent",
  "database_config": {
    "type": "oracle",
    "host": "prod-db.example.com",
    "port": 1521,
    "service_name": "PRODDB",
    "username": "sales_user",
    "password": "password123"
  }
}
```

**After (centralized with access control):**

Connection created in store:
```json
{
  "name": "sales-agent-oracle",
  "database_type": "oracle",
  "host": "prod-db.example.com",
  "port": 1521,
  "service_name": "PRODDB",
  "username": "sales_user",
  "password": "encrypted_password"
}
```

Agent config updated:
```json
{
  "name": "sales-agent",
  "connection_assignments": [
    {
      "connection_name": "sales-agent-oracle",
      "access_level": "read-write",
      "allowed_tables": []
    }
  ]
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Connection Name Uniqueness

*For any* connection store and any connection name, attempting to create a second connection with the same name should fail with an error indicating the name already exists.

**Validates: Requirements 2.3**

### Property 2: Connection Name Format Validation

*For any* connection name, the system should accept names in kebab-case format (lowercase letters, numbers, hyphens) and reject names with invalid characters (uppercase, spaces, special characters).

**Validates: Requirements 2.1**

### Property 3: Database Type Validation

*For any* connection, the system should accept database_type values from the supported list (oracle, postgresql, mysql, sqlite) and reject any other values.

**Validates: Requirements 2.2**

### Property 4: Required Fields Validation by Database Type

*For any* connection, the required fields should vary based on database_type: Oracle requires (host, port, service_name, username, password), PostgreSQL and MySQL require (host, port, database, username, password), and SQLite requires (file_path).

**Validates: Requirements 2.4, 8.2, 8.3, 8.4, 8.5, 8.6**

### Property 5: Connection Persistence Based on Validation

*For any* connection, if validation succeeds, the connection should be saved to the store and retrievable; if validation fails, the connection should not appear in the store.

**Validates: Requirements 2.5, 2.6, 2.7, 8.1**

### Property 6: Connection Store Structure

*For any* connection store after saving connections, the JSON file should contain a "connections" array where each element has the required fields (name, database_type, and type-specific parameters).

**Validates: Requirements 1.3**

### Property 7: JSON Structure Validation

*For any* malformed JSON in the connection store file, the system should detect the invalid structure and return an error when attempting to load.

**Validates: Requirements 1.4**

### Property 8: List Returns All Connections

*For any* set of connections in the store, listing connections should return all of them with no connections missing or duplicated.

**Validates: Requirements 3.1**

### Property 9: Sensitive Field Masking

*For any* connection with sensitive fields (password, tokens, keys), displaying the connection should mask these fields with asterisks, and the actual values should not appear in the display output.

**Validates: Requirements 3.3, 10.2, 10.3**

### Property 10: Connection Usage Tracking

*For any* connection, the system should correctly identify all agents that reference it in their connection_references array.

**Validates: Requirements 3.4**

### Property 11: Update Name Immutability

*For any* existing connection, attempting to update its name field should be rejected, while updates to other fields should be allowed.

**Validates: Requirements 4.1**

### Property 12: Update Persistence Based on Validation

*For any* connection update, if validation succeeds, the updated values should be persisted to the store; if validation fails, the original connection should remain unchanged in the store.

**Validates: Requirements 4.2, 4.3, 4.4, 4.5**

### Property 13: Deletion Referential Integrity

*For any* connection, if it is referenced by one or more agents, deletion should fail with an error listing the agents; if it is not referenced by any agents, deletion should succeed and remove it from the store.

**Validates: Requirements 5.1, 5.2, 5.3**

### Property 14: Agent Connection Assignment Validation

*For any* agent and any list of connection names, assigning connections should succeed only if all connection names exist in the store; if any name doesn't exist, the assignment should fail.

**Validates: Requirements 6.2**

### Property 15: Agent Connection Storage

*For any* agent and any list of valid connection names, after successful assignment, the agent's config file should contain a connection_references array with exactly those connection names.

**Validates: Requirements 6.3**

### Property 16: Connection Assignment Cardinality

*For any* agent, the system should allow assignment of zero or more connections (0 to N), including empty lists and lists with multiple connections.

**Validates: Requirements 6.1**

### Property 17: Connection Resolution

*For any* agent with connection references, resolving the references should look up each name in the store and return the full connection configurations for all valid references.

**Validates: Requirements 6.5, 11.1, 11.2, 11.4, 11.5**

### Property 18: Connection Resolution Error Handling

*For any* agent with connection references, if any referenced connection does not exist in the store, resolution should fail with an error indicating which connection is missing.

**Validates: Requirements 11.3**

### Property 19: Agent Update Persistence

*For any* agent and any valid updates (system_prompt, temperature, language, web_search, connection_references, mcp_servers), after successful update, loading the agent config should reflect all the changes.

**Validates: Requirements 7.4, 7.5, 7.6**

### Property 20: Migration Connection Creation

*For any* agent with inline database_config, running migration should create a new connection in the store with a name following the pattern "{agent_name}-{database_type}".

**Validates: Requirements 9.2, 9.3**

### Property 21: Migration Config Update

*For any* agent with inline database_config, after successful migration, the agent config should have the new connection name in connection_references and the database_config field should be removed.

**Validates: Requirements 9.4, 9.5**

### Property 22: Migration Detection

*For any* set of agents, the system should correctly identify which agents have inline database_config fields that need migration.

**Validates: Requirements 9.1**

### Property 23: Migration Error Handling

*For any* agent migration that encounters an error, the original agent configuration should remain unchanged (no partial migration).

**Validates: Requirements 9.6**

### Property 24: Log Credential Sanitization

*For any* log message or error message involving connection details, sensitive credentials (passwords, tokens) should not appear in the message text.

**Validates: Requirements 10.4, 10.5**

### Property 25: Connection Addition to Agent

*For any* agent and any valid connection name, adding the connection should result in the connection name appearing in the agent's connection_references array.

**Validates: Requirements 7.4**

### Property 26: Connection Removal from Agent

*For any* agent and any connection name currently in its connection_references, removing the connection should result in the connection name no longer appearing in the array.

**Validates: Requirements 7.5**

### Property 27: Error Message Quality

*For any* failed connection validation, the error message should be non-empty and contain descriptive information about what failed.

**Validates: Requirements 8.7**

### Property 28: Access Level Query Validation - Read Only

*For any* agent with read-only access to a connection, attempting to execute INSERT, UPDATE, DELETE, or DDL queries should fail with an access denied error, while SELECT queries should be allowed.

**Validates: Requirements 12.3, 12.7, 12.8**

### Property 29: Access Level Query Validation - Read Write

*For any* agent with read-write access to a connection, SELECT, INSERT, UPDATE, and DELETE queries should be allowed, while DDL queries (CREATE, DROP, ALTER) should be rejected.

**Validates: Requirements 12.4, 12.7, 12.8**

### Property 30: Access Level Query Validation - Table Specific Read

*For any* agent with table-specific-read access, SELECT queries on allowed tables should succeed, while SELECT queries on non-allowed tables or any write operations should fail.

**Validates: Requirements 12.5, 12.7, 12.8**

### Property 31: Access Level Query Validation - Table Specific Read Write

*For any* agent with table-specific-read-write access, all operations (SELECT, INSERT, UPDATE, DELETE) on allowed tables should succeed, while operations on non-allowed tables should fail.

**Validates: Requirements 12.6, 12.7, 12.8**

### Property 32: Access Level Storage

*For any* agent and connection assignment, the access level should be stored in the agent config and retrievable when loading the config.

**Validates: Requirements 12.9**

### Property 33: Access Level Display

*For any* agent with connection assignments, displaying the agent configuration should show the access level for each connection.

**Validates: Requirements 12.10**

### Property 34: Guidelines Storage

*For any* agent and list of guidelines, after adding guidelines, the agent config should contain exactly those guidelines in the same order.

**Validates: Requirements 13.1, 13.4**

### Property 35: Guideline Addition

*For any* agent and guideline text, adding a guideline should append it to the end of the guidelines list.

**Validates: Requirements 13.4**

### Property 36: Guideline Editing

*For any* agent, guideline index, and new text, editing a guideline should replace the text at that index while preserving all other guidelines.

**Validates: Requirements 13.5**

### Property 37: Guideline Deletion

*For any* agent and guideline index, deleting a guideline should remove it from the list while preserving the order of remaining guidelines.

**Validates: Requirements 13.6**

### Property 38: Guidelines in System Prompt

*For any* agent with guidelines, the full system prompt should include the base system prompt followed by the guidelines formatted as bullet points.

**Validates: Requirements 13.8, 13.10**

### Property 39: Empty Guidelines Handling

*For any* agent with no guidelines, the full system prompt should be identical to the base system prompt.

**Validates: Requirements 13.9**

### Property 40: Guideline Listing

*For any* agent, listing guidelines should return all guidelines in the correct order with their indices.

**Validates: Requirements 13.7**

## Error Handling

### Connection Validation Errors

**Invalid Parameters:**
- Missing required fields → "Missing required field '{field}' for {database_type} connection"
- Invalid database type → "Invalid database type '{type}'. Supported types: oracle, postgresql, mysql, sqlite"
- Invalid name format → "Connection name must be in kebab-case format (lowercase, numbers, hyphens only)"

**Connection Test Failures:**
- Cannot connect → "Failed to connect to {database_type} database: {error_details}"
- Authentication failure → "Authentication failed for user '{username}'"
- Database not found → "Database '{database}' not found on server"
- Network timeout → "Connection timeout after {seconds} seconds"

### CRUD Operation Errors

**Create:**
- Duplicate name → "Connection '{name}' already exists"
- Validation failure → "Connection validation failed: {error}"

**Update:**
- Connection not found → "Connection '{name}' not found"
- Name change attempted → "Cannot change connection name. Create a new connection instead."
- Validation failure → "Updated connection validation failed: {error}"

**Delete:**
- Connection in use → "Cannot delete connection '{name}'. Used by agents: {agent_list}"
- Connection not found → "Connection '{name}' not found"

**Get/List:**
- Store file corrupted → "Connection store is corrupted. Invalid JSON structure."
- Permission denied → "Cannot access connection store. Check file permissions."

### Agent Assignment Errors

**Invalid References:**
- Connection not found → "Connection '{name}' not found. Available connections: {list}"
- Agent not found → "Agent '{name}' not found"

**Access Level Errors:**
- Invalid access level → "Invalid access level '{level}'. Valid levels: read-only, read-write, table-specific-read, table-specific-read-write"
- Missing allowed tables → "Table-specific access requires allowed_tables to be specified"
- Query access denied → "Query not allowed with {access_level} access: {operation} on {tables}"

**Guidelines Errors:**
- Invalid guideline index → "Guideline index {index} out of range. Agent has {count} guidelines."
- Empty guideline text → "Guideline text cannot be empty"

**Resolution Errors:**
- Missing connection → "Agent references connection '{name}' which no longer exists"
- Multiple missing → "Agent references {count} connections that don't exist: {list}"

### Migration Errors

**Migration Failures:**
- Invalid inline config → "Cannot migrate agent '{name}': invalid database configuration"
- Connection creation failed → "Failed to create connection during migration: {error}"
- Config update failed → "Failed to update agent config during migration: {error}"

### Security Errors

**Permission Issues:**
- Cannot set permissions → "Warning: Could not set secure permissions on connection store"
- Cannot read store → "Permission denied reading connection store"
- Cannot write store → "Permission denied writing connection store"

### Error Recovery Strategies

1. **Validation Failures**: Preserve original state, display error, allow retry
2. **Connection Test Failures**: Don't save connection, provide diagnostic information
3. **File System Errors**: Attempt to create missing directories, check permissions
4. **Migration Errors**: Log error, skip problematic agent, continue with others
5. **Resolution Errors**: Display helpful message with available connections

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific examples of valid and invalid connections
- Edge cases (empty lists, missing files, permission errors)
- Integration between components
- CLI menu navigation and display
- Migration scenarios with specific configurations

**Property-Based Tests** focus on:
- Universal properties that hold for all inputs
- Validation rules across many generated connections
- CRUD operations with randomized data
- Referential integrity with random agent/connection combinations
- Comprehensive input coverage through randomization

### Property-Based Testing Configuration

**Framework**: Hypothesis (Python)

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: database-connection-management, Property {N}: {property_text}**
- Custom generators for:
  - Valid/invalid connection names
  - Connection configurations by database type
  - Agent configurations with connection references
  - Malformed JSON structures

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import pytest

@given(
    name=st.text(min_size=1, max_size=50),
    db_type=st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])
)
@pytest.mark.property_test
def test_connection_name_uniqueness(name, db_type):
    """
    Feature: database-connection-management
    Property 1: Connection Name Uniqueness
    
    For any connection store and any connection name, attempting to create
    a second connection with the same name should fail with an error.
    """
    # Test implementation
    pass
```

### Unit Test Coverage

**Connection Manager Tests**:
- Create connection with valid parameters
- Create connection with invalid parameters
- List connections (empty, single, multiple)
- Update connection successfully
- Update connection with validation failure
- Delete connection (in use, not in use)
- Get connection (exists, doesn't exist)

**Validation Tests**:
- Oracle connection validation (valid, missing fields)
- PostgreSQL connection validation (valid, missing fields)
- MySQL connection validation (valid, missing fields)
- SQLite connection validation (valid, invalid path)
- Connection test success/failure scenarios

**Agent Integration Tests**:
- Assign connections to agent
- Remove connections from agent
- Resolve connection references
- Handle missing connection references
- Update agent with connection changes

**Migration Tests**:
- Migrate agent with Oracle inline config
- Migrate agent with PostgreSQL inline config
- Migrate multiple agents
- Handle migration errors
- Skip agents without inline config

**Security Tests**:
- File permissions set correctly
- Passwords masked in display
- Credentials not in logs
- Credentials not in error messages

**CLI Tests**:
- Menu navigation
- Connection creation flow
- Agent update flow
- Error message display
- Confirmation prompts

### Test Data Generators

**Hypothesis Strategies**:
```python
# Valid connection names (kebab-case)
valid_names = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
    min_size=1,
    max_size=50
).filter(lambda s: s[0] != '-' and s[-1] != '-')

# Invalid connection names
invalid_names = st.one_of(
    st.text(min_size=1).filter(lambda s: not is_kebab_case(s)),
    st.just(''),
    st.text(alphabet=st.characters(whitelist_categories=('Lu',)))
)

# Database types
db_types = st.sampled_from(['oracle', 'postgresql', 'mysql', 'sqlite'])

# Oracle connections
oracle_connections = st.builds(
    DatabaseConnection,
    name=valid_names,
    database_type=st.just('oracle'),
    host=st.text(min_size=1),
    port=st.integers(min_value=1, max_value=65535),
    service_name=st.text(min_size=1),
    username=st.text(min_size=1),
    password=st.text(min_size=1)
)

# Similar strategies for postgresql, mysql, sqlite...
```

### Integration Test Scenarios

1. **End-to-End Connection Lifecycle**:
   - Create connection → Assign to agent → Start agent session → Resolve connections → Delete connection (should fail) → Remove from agent → Delete connection (should succeed)

2. **Multi-Agent Sharing**:
   - Create connection → Assign to multiple agents → Update connection → Verify all agents use new parameters

3. **Migration Flow**:
   - Create agents with inline configs → Run migration → Verify connections created → Verify agent configs updated → Verify inline configs removed

4. **Error Recovery**:
   - Corrupt connection store → Attempt operations → Verify graceful error handling → Restore store → Verify operations work

### Test Execution

**Run all tests**:
```bash
pytest tests/
```

**Run only property tests**:
```bash
pytest -m property_test tests/
```

**Run with coverage**:
```bash
pytest --cov=offline_chat --cov-report=html tests/
```

**Run specific test file**:
```bash
pytest tests/test_connection_manager.py
```
