# Implementation Plan: Database Connection Management

## Overview

This implementation plan breaks down the centralized database connection management system into discrete coding tasks. The approach follows an incremental development strategy: core data models → connection manager → validation → agent integration → CLI → migration → testing.

## Tasks

- [ ] 1. Set up core data models and storage structure
  - [x] 1.1 Create DatabaseConnection dataclass in `database/connection.py`
    - Implement dataclass with all fields (name, database_type, host, port, etc.)
    - Add `to_dict()` and `from_dict()` methods for JSON serialization
    - Add `mask_sensitive_fields()` method for secure display
    - _Requirements: 1.3, 10.2, 10.3_
  
  - [x] 1.2 Write property test for DatabaseConnection serialization
    - **Property 6: Connection Store Structure**
    - **Validates: Requirements 1.3**
  
  - [x] 1.3 Create Result type for error handling in `database/result.py`
    - Implement generic Result[T, E] type for success/error returns
    - Add helper methods: `is_ok()`, `is_err()`, `unwrap()`, `unwrap_err()`
    - _Requirements: All error handling_

- [ ] 2. Implement DatabaseConnectionManager core CRUD operations
  - [x] 2.1 Create DatabaseConnectionManager class in `database/manager.py`
    - Initialize with store path (~/.offline-chat/database_connections.json)
    - Implement `_ensure_store_exists()` to create store if missing
    - Implement `_set_secure_permissions()` to set file permissions to 600
    - Implement `_load_store()` and `_save_store()` for JSON I/O
    - _Requirements: 1.1, 1.2, 10.1_
  
  - [x] 2.2 Write property test for store initialization
    - **Property 6: Connection Store Structure**
    - **Validates: Requirements 1.2, 1.3**
  
  - [x] 2.3 Implement `create_connection()` method
    - Validate connection name uniqueness
    - Validate connection name format (kebab-case)
    - Validate database_type is in supported list
    - Call validation before saving
    - Save to store on success
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  
  - [x] 2.4 Write property tests for connection creation
    - **Property 1: Connection Name Uniqueness**
    - **Property 2: Connection Name Format Validation**
    - **Property 3: Database Type Validation**
    - **Property 5: Connection Persistence Based on Validation**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.5, 2.6, 2.7**
  
  - [x] 2.5 Implement `list_connections()` and `get_connection()` methods
    - Load all connections from store
    - Return list of DatabaseConnection objects
    - Handle missing connection in get_connection
    - _Requirements: 3.1_
  
  - [x] 2.6 Write property test for list operations
    - **Property 8: List Returns All Connections**
    - **Validates: Requirements 3.1**
  
  - [x] 2.7 Implement `update_connection()` method
    - Load existing connection
    - Prevent name changes
    - Apply updates to other fields
    - Validate updated connection
    - Save on success, preserve original on failure
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
  
  - [x] 2.8 Write property tests for connection updates
    - **Property 11: Update Name Immutability**
    - **Property 12: Update Persistence Based on Validation**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
  
  - [x] 2.9 Implement `delete_connection()` method
    - Check if connection is referenced by agents
    - Prevent deletion if in use
    - Remove from store if not in use
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 2.10 Write property test for deletion referential integrity
    - **Property 13: Deletion Referential Integrity**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 3. Checkpoint - Ensure core CRUD tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement connection validation
  - [x] 4.1 Create ConnectionValidator class in `database/validator.py`
    - Implement `validate_oracle()` with required fields check
    - Implement `validate_postgresql()` with required fields check
    - Implement `validate_mysql()` with required fields check
    - Implement `validate_sqlite()` with required fields check
    - Implement `test_connection()` to actually test database connectivity
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [x] 4.2 Write property tests for validation
    - **Property 4: Required Fields Validation by Database Type**
    - **Property 27: Error Message Quality**
    - **Validates: Requirements 2.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**
  
  - [x] 4.3 Integrate ConnectionValidator into DatabaseConnectionManager
    - Call appropriate validator in `create_connection()`
    - Call appropriate validator in `update_connection()`
    - Return validation errors to caller
    - _Requirements: 2.5, 4.3_
  
  - [x] 4.4 Write property test for validation integration
    - **Property 5: Connection Persistence Based on Validation**
    - **Validates: Requirements 2.5, 2.6, 2.7, 8.1**

- [ ] 5. Implement agent connection assignment with access control
  - [x] 5.1 Create AccessLevel enum in `database/access_level.py`
    - Define enum with values: READ_ONLY, READ_WRITE, TABLE_SPECIFIC_READ, TABLE_SPECIFIC_READ_WRITE
    - _Requirements: 12.2_
  
  - [x] 5.2 Create AgentConnectionAssignment dataclass in `database/connection_assignment.py`
    - Implement dataclass with connection_name, access_level, allowed_tables fields
    - Add `to_dict()` and `from_dict()` methods for JSON serialization
    - _Requirements: 12.9_
  
  - [x] 5.3 Update AgentConfig dataclass in `agents/agent.py`
    - Replace `connection_references` with `connection_assignments: list[AgentConnectionAssignment]`
    - Add `guidelines: list[str]` field
    - Add `get_full_system_prompt()` method to include guidelines
    - Keep `connection_references` and `database_config` for backward compatibility
    - Update `to_dict()` and `from_dict()` methods
    - _Requirements: 6.3, 12.9, 13.1, 13.8_
  
  - [x] 5.4 Write property tests for AgentConfig with guidelines
    - **Property 34: Guidelines Storage**
    - **Property 38: Guidelines in System Prompt**
    - **Property 39: Empty Guidelines Handling**
    - **Validates: Requirements 13.1, 13.4, 13.8, 13.9, 13.10**
  
  - [x] 5.5 Add connection methods to AgentManager in `agents/manager.py`
    - Inject DatabaseConnectionManager into AgentManager constructor
    - Implement `assign_connection()` method with access_level and allowed_tables parameters
    - Implement `remove_connection()` method
    - Validate all connection names exist before assignment
    - Validate allowed_tables for table-specific access levels
    - Update agent config with connection_assignments
    - _Requirements: 6.1, 6.2, 6.3, 12.1, 12.5, 12.6_
  
  - [x] 5.6 Write property tests for agent connection assignment with access control
    - **Property 14: Agent Connection Assignment Validation**
    - **Property 15: Agent Connection Storage**
    - **Property 16: Connection Assignment Cardinality**
    - **Property 32: Access Level Storage**
    - **Validates: Requirements 6.1, 6.2, 6.3, 12.9**
  
  - [x] 5.7 Implement `update_agent()` method in AgentManager
    - Support updating system_prompt, temperature, language, web_search, connection_assignments, mcp_servers, guidelines
    - Load agent config, apply updates, save config
    - _Requirements: 7.4, 7.5, 7.6_
  
  - [x] 5.8 Write property tests for agent updates
    - **Property 19: Agent Update Persistence**
    - **Property 25: Connection Addition to Agent**
    - **Property 26: Connection Removal from Agent**
    - **Validates: Requirements 7.4, 7.5, 7.6**
  
  - [x] 5.9 Implement `resolve_connections()` in DatabaseConnectionManager
    - Take list of AgentConnectionAssignment objects
    - Look up each connection_name in store
    - Return error if any not found
    - Return list of tuples (DatabaseConnection, AccessLevel, allowed_tables)
    - _Requirements: 6.5, 11.1, 11.2, 11.4, 11.5_
  
  - [x] 5.10 Write property tests for connection resolution
    - **Property 17: Connection Resolution**
    - **Property 18: Connection Resolution Error Handling**
    - **Validates: Requirements 6.5, 11.1, 11.2, 11.3, 11.4, 11.5**
  
  - [x] 5.11 Implement `get_agents_using_connection()` in DatabaseConnectionManager
    - Scan all agent configs in data/agents/
    - Check connection_assignments field for connection_name
    - Return list of agent names
    - _Requirements: 3.4, 5.1_
  
  - [x] 5.12 Write property test for connection usage tracking
    - **Property 10: Connection Usage Tracking**
    - **Property 33: Access Level Display**
    - **Validates: Requirements 3.4, 12.10**

- [x] 6. Checkpoint - Ensure agent integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement access level validation
  - [x] 7.1 Create AccessLevelValidator class in `database/access_validator.py`
    - Implement `validate_query()` method to check query against access level
    - Implement `_parse_query_operation()` to extract operation type (SELECT, INSERT, etc.)
    - Implement `_extract_table_names()` to extract table names from query
    - _Requirements: 12.3, 12.4, 12.5, 12.6, 12.7_
  
  - [x] 7.2 Write property tests for access level validation
    - **Property 28: Access Level Query Validation - Read Only**
    - **Property 29: Access Level Query Validation - Read Write**
    - **Property 30: Access Level Query Validation - Table Specific Read**
    - **Property 31: Access Level Query Validation - Table Specific Read Write**
    - **Validates: Requirements 12.3, 12.4, 12.5, 12.6, 12.7, 12.8**
  
  - [x] 7.3 Integrate AccessLevelValidator into query execution flow
    - Update agent session to validate queries before execution
    - Pass access_level and allowed_tables to validator
    - Return validation errors to user
    - _Requirements: 12.7, 12.8_
  
  - [x] 7.4 Write unit tests for access level integration
    - Test query validation in agent session
    - Test error messages for access violations
    - Test successful queries with appropriate access
    - _Requirements: 12.7, 12.8_

- [ ] 8. Implement guidelines management
  - [x] 8.1 Add guideline methods to AgentManager in `agents/manager.py`
    - Implement `add_guideline()` method
    - Implement `edit_guideline()` method with index validation
    - Implement `delete_guideline()` method with index validation
    - Implement `list_guidelines()` method
    - _Requirements: 13.3, 13.4, 13.5, 13.6, 13.7_
  
  - [x] 8.2 Write property tests for guidelines management
    - **Property 35: Guideline Addition**
    - **Property 36: Guideline Editing**
    - **Property 37: Guideline Deletion**
    - **Property 40: Guideline Listing**
    - **Validates: Requirements 13.4, 13.5, 13.6, 13.7**
  
  - [x] 8.3 Write unit tests for guidelines edge cases
    - Test adding empty guideline (should fail)
    - Test editing with invalid index (should fail)
    - Test deleting with invalid index (should fail)
    - Test listing empty guidelines
    - _Requirements: 13.3, 13.4, 13.5, 13.6, 13.7_

- [x] 9. Checkpoint - Ensure access level and guidelines tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement CLI menu integration
  - [x] 10.1 Create database connection CLI module in `cli/database_menu.py`
    - Implement `show_database_menu()` with options: Create, List, Update, Delete, Back
    - Implement `create_connection_flow()` to prompt for connection details
    - Implement `list_connections_display()` to show connections with masked credentials and access levels
    - Implement `update_connection_flow()` to modify existing connection
    - Implement `delete_connection_flow()` with confirmation and usage check
    - _Requirements: 12.1, 12.2, 12.3, 14.1, 14.2, 14.3_
  
  - [x] 10.2 Create agent update CLI module in `cli/agent_update_menu.py`
    - Implement `show_update_agent_menu()` to select agent and update option
    - Implement `update_database_connections_flow()` to add/remove connections with access level selection
    - Implement `select_access_level()` to prompt for access level
    - Implement `select_allowed_tables()` for table-specific access
    - Display currently assigned connections with access levels
    - Display available connections for assignment
    - _Requirements: 7.1, 7.2, 7.3, 12.1, 12.5, 12.6, 14.4, 14.5_
  
  - [x] 10.3 Create guidelines management CLI module in `cli/guidelines_menu.py`
    - Implement `show_guidelines_menu()` with options: Add, Edit, Delete, List, Back
    - Implement `add_guideline_flow()` to prompt for guideline text
    - Implement `edit_guideline_flow()` to select and modify guideline
    - Implement `delete_guideline_flow()` to select and remove guideline
    - Implement `list_guidelines_display()` to show all guidelines with indices
    - _Requirements: 13.3, 13.4, 13.5, 13.6, 13.7, 14.7_
  
  - [x] 10.4 Integrate new menus into main CLI in `main.py`
    - Add "Manage database connections" option to main menu
    - Add "Update agent" option to main menu
    - Add "Manage guidelines" option to agent update menu
    - Wire up menu handlers
    - _Requirements: 14.1, 14.4, 14.6, 14.7_
  
  - [x] 10.5 Write unit tests for CLI flows
    - Test menu navigation
    - Test input validation
    - Test error display
    - Test confirmation prompts
    - Test access level selection
    - Test guidelines management flows
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7_

- [ ] 11. Implement security features
  - [x] 11.1 Add credential masking to DatabaseConnection
    - Implement `mask_sensitive_fields()` to replace passwords with asterisks
    - Apply masking in CLI display functions
    - _Requirements: 10.2, 10.3_
  
  - [x] 11.2 Write property test for sensitive field masking
    - **Property 9: Sensitive Field Masking**
    - **Validates: Requirements 3.3, 10.2, 10.3**
  
  - [x] 11.3 Add credential sanitization to error messages
    - Create `sanitize_error_message()` utility function
    - Remove passwords/tokens from error strings
    - Apply to all error messages and logs
    - _Requirements: 10.4, 10.5_
  
  - [x] 11.4 Write property test for log credential sanitization
    - **Property 24: Log Credential Sanitization**
    - **Validates: Requirements 10.4, 10.5**
  
  - [x] 11.5 Implement secure file permissions
    - Set connection store to 600 permissions on creation
    - Verify permissions on load
    - Warn if permissions are too permissive
    - _Requirements: 1.5, 10.1_

- [ ] 12. Implement migration from inline configurations
  - [x] 12.1 Create migration module in `database/migration.py`
    - Implement `detect_inline_configs()` to scan agents
    - Implement `migrate_agent()` to convert one agent
    - Generate connection name as "{agent_name}-{database_type}"
    - Create connection in store with read-write access
    - Update agent config with connection_assignment
    - Remove database_config and connection_references fields
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 12.2 Write property tests for migration
    - **Property 20: Migration Connection Creation**
    - **Property 21: Migration Config Update**
    - **Property 22: Migration Detection**
    - **Property 23: Migration Error Handling**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**
  
  - [x] 12.3 Add `migrate_inline_configs()` to AgentManager
    - Call migration for all agents with inline configs
    - Return mapping of agent -> connection name
    - Handle errors gracefully (log and continue)
    - _Requirements: 9.6_
  
  - [x] 12.4 Add migration check to application startup
    - Run migration check on first load
    - Display migration results to user
    - _Requirements: 9.1_

- [ ] 13. Implement JSON structure validation
  - [x] 13.1 Add JSON validation to DatabaseConnectionManager
    - Validate JSON structure in `_load_store()`
    - Check for required top-level fields
    - Check for valid connection objects
    - Return descriptive errors for malformed JSON
    - _Requirements: 1.4_
  
  - [x] 13.2 Write property test for JSON structure validation
    - **Property 7: JSON Structure Validation**
    - **Validates: Requirements 1.4**

- [ ] 14. Integration and end-to-end testing
  - [x] 14.1 Write integration tests for complete workflows
    - Test: Create connection → Assign to agent with access level → Start session → Resolve → Delete
    - Test: Create connection → Assign to multiple agents with different access levels → Update connection
    - Test: Create agents with inline configs → Migrate → Verify
    - Test: Corrupt store → Attempt operations → Verify error handling
    - Test: Add/edit/delete guidelines → Verify system prompt generation
    - Test: Query validation with different access levels
    - _Requirements: All_
  
  - [x] 14.2 Write unit tests for edge cases
    - Empty connection list display
    - Connection deletion cancellation
    - File permission errors
    - Store file missing
    - Invalid connection references
    - Invalid access level specifications
    - Empty guidelines list
    - _Requirements: 3.5, 5.5_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation follows the existing project structure and coding standards
- All database operations use appropriate Python database drivers (cx_Oracle, psycopg2, pymysql, sqlite3)
- File permissions are set using `os.chmod()` with mode 0o600
- JSON serialization uses the standard `json` module
- Error handling uses the Result type pattern for explicit error propagation
