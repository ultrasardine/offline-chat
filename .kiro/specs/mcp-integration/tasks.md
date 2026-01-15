# Implementation Plan: MCP Server Integration

## Overview

This plan implements MCP (Model Context Protocol) server integration for the Offline Chat application. The implementation follows a bottom-up approach: first creating the data models and configuration, then the MCP client components, and finally integrating with the existing ChatSession and CLI.

## Tasks

- [x] 1. Add MCP Python SDK dependency
  - Add `mcp` package to pyproject.toml dependencies
  - Run `uv sync` to install the package
  - _Requirements: 2.2_

- [x] 2. Implement MCPServerConfig data model
  - [x] 2.1 Create MCPServerConfig dataclass in `offline_chat/mcp_config.py`
    - Define fields: name, command, args, env, disabled
    - Implement `to_dict()` method for serialization
    - Implement `from_dict()` class method for deserialization
    - Implement `validate()` method for config validation
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Write property test for MCPServerConfig round-trip
    - **Property 1: MCP Server Configuration Round Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 2.3 Write property test for MCPServerConfig validation
    - **Property 7: MCP Config Validation**
    - **Validates: Requirements 5.4**

- [x] 3. Extend Agent class with MCP server support
  - [x] 3.1 Update Agent dataclass in `offline_chat/agent.py`
    - Add `mcp_servers: list[MCPServerConfig]` field with default empty list
    - Update `to_dict()` to serialize MCP configs
    - Update `from_dict()` to deserialize MCP configs with backward compatibility
    - _Requirements: 1.1, 1.4, 6.1_

  - [x] 3.2 Write property test for Agent round-trip with MCP configs
    - **Property 2: Agent Configuration Round Trip with MCP Servers**
    - **Validates: Requirements 1.4**

  - [x] 3.3 Write property test for backward compatibility
    - **Property 6: Backward Compatibility - Empty MCP Config**
    - **Validates: Requirements 6.1**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement MCPClient class
  - [x] 5.1 Create MCPClient class in `offline_chat/mcp_client.py`
    - Implement `__init__` with MCPServerConfig
    - Implement async context manager (`__aenter__`, `__aexit__`)
    - Implement `connect()` method using stdio transport
    - Implement `disconnect()` method for cleanup
    - Implement `list_tools()` to get tools from server
    - Implement `call_tool()` to execute tool calls
    - _Requirements: 2.1, 2.2, 2.3, 4.2, 4.3_

  - [x] 5.2 Write property test for schema conversion
    - **Property 4: Schema Conversion Validity**
    - **Validates: Requirements 3.2**

- [x] 6. Implement MCPClientManager class
  - [x] 6.1 Create MCPClientManager class in `offline_chat/mcp_client.py`
    - Implement `__init__` with list of MCPServerConfig
    - Implement async context manager for managing multiple clients
    - Implement `connect_all()` with error handling for individual failures
    - Implement `disconnect_all()` for cleanup
    - Implement `get_all_tools()` to aggregate tools from all servers
    - Implement `call_tool()` with routing to correct server
    - Maintain tool_registry mapping tool names to server names
    - _Requirements: 2.1, 2.4, 2.5, 3.1, 3.3, 3.4, 4.1, 4.4_

  - [x] 6.2 Write property test for tool aggregation
    - **Property 3: Tool Aggregation Completeness**
    - **Validates: Requirements 3.1, 3.3**

  - [x] 6.3 Write property test for tool routing
    - **Property 5: Tool Routing Correctness**
    - **Validates: Requirements 3.4, 4.1**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Integrate MCP with ChatSession
  - [x] 8.1 Update ChatSession in `offline_chat/session.py`
    - Add `_mcp_manager` attribute
    - Create `start_async()` method that connects to MCP servers
    - Create `end_async()` method that disconnects MCP servers
    - Update `_get_tools()` to include MCP tools
    - Create `_execute_tool_async()` for MCP tool execution
    - Update `send_message()` to use async tool execution when MCP tools present
    - _Requirements: 2.1, 2.5, 3.1, 4.1, 4.2, 4.3, 4.4, 6.2_

  - [x] 8.2 Write unit tests for ChatSession MCP integration
    - Test session start with MCP servers
    - Test tool aggregation in session
    - Test session without MCP servers (backward compatibility)
    - _Requirements: 6.2, 6.3_

- [x] 9. Update CLI for MCP server configuration
  - [x] 9.1 Update agent creation flow in `offline_chat/cli.py`
    - Add prompt for MCP server configurations
    - Support adding multiple MCP servers
    - Validate MCP configs before saving
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 9.2 Update chat command to use async session methods
    - Use `start_async()` and `end_async()` when agent has MCP servers
    - Handle async context properly in CLI
    - _Requirements: 2.1, 2.5_

- [x] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property tests are required for comprehensive validation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- The MCP Python SDK (`mcp` package) provides stdio_client and ClientSession for server communication
- Async context managers are used throughout for proper resource management
