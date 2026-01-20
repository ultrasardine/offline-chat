# SQLite MCP Server Test Consistency

## Overview
Update the SQLite MCP server configuration to use the correct command format that matches the actual mcp-server-sqlite-npx package interface.

## Background
The implementation in `offline_chat/database_config.py` was using:
- Command: `npx`
- Args: `["-y", "mcp-server-sqlite-npx", "--db-path", path]`

However, the actual mcp-server-sqlite-npx package expects the database path as a positional argument, not as a `--db-path` flag:
- Args: `["-y", "mcp-server-sqlite-npx", path]`

This change simplifies the command and aligns with the package's actual interface.

## User Stories

### 1. Correct Command Format
**As a** developer  
**I want** the SQLite MCP server configuration to use the correct command format  
**So that** the MCP server can be invoked successfully with the database path

**Acceptance Criteria:**
- 1.1 SQLite `MCPServerConfig` uses `command="npx"`
- 1.2 SQLite `MCPServerConfig` uses `mcp-server-sqlite-npx` package name in args
- 1.3 Database path is passed as a positional argument (not `--db-path` flag)
- 1.4 All existing tests pass after the update

### 2. Test Consistency
**As a** developer  
**I want** all test files to verify the correct SQLite MCP server configuration  
**So that** tests accurately reflect the actual implementation behavior

**Acceptance Criteria:**
- 2.1 All test files that create SQLite `MCPServerConfig` objects expect the correct args format
- 2.2 Test assertions verify the path is in args as a positional argument
- 2.3 No test assertions check for `--db-path` flag
- 2.4 All existing tests continue to pass after updates

## Changes Made

### Implementation
- Updated `offline_chat/database_config.py` line 184 to remove `--db-path` flag
- Database path is now passed as a positional argument: `["-y", "mcp-server-sqlite-npx", path]`

### Tests
- Updated `tests/test_database_config_factory.py` line 415 to expect new args format
- Updated `tests/test_database_config_factory.py` line 201-204 to remove `--db-path` assertion
- Updated `tests/test_sqlite_integration.py` line 140 to remove `--db-path` check

## Out of Scope
- Changes to non-SQLite database configurations (Oracle, PostgreSQL, MySQL remain unchanged)
- Changes to README.md (already documents the correct usage)
- Changes to other spec files in `.kiro/specs/`

## Technical Notes
- The correct configuration is defined in `offline_chat/database_config.py` line 183-186
- `test_database_config_factory.py` was already updated and serves as the reference
- `test_sqlite_integration.py` already uses the correct configuration
