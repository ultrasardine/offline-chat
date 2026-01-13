# Implementation Plan: Offline Chat

## Overview

This implementation plan breaks down the Offline Chat application into incremental coding tasks. Each task builds on previous work, ensuring no orphaned code. The plan follows a bottom-up approach: data models → storage → business logic → CLI → integration.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create package directory structure (offline_chat/)
  - Update pyproject.toml with dependencies (ollama, hypothesis, pytest)
  - Create __init__.py with package exports
  - Create exceptions.py with custom exception classes
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 2. Implement Agent data model
  - [x] 2.1 Create Agent dataclass with all fields
    - Implement name, display_name, base_model, system_prompt, temperature, created_at
    - Implement validate_name() method with kebab-case regex
    - Implement to_modelfile() method for Modelfile generation
    - Implement to_dict() and from_dict() for serialization
    - _Requirements: 1.2, 1.4_

  - [x] 2.2 Write property test for Agent name validation
    - **Property 1: Agent Name Validation**
    - **Validates: Requirements 1.2**

  - [x] 2.3 Write property test for Agent serialization round-trip
    - **Property 3: Agent Serialization Round-Trip**
    - **Validates: Requirements 1.4, 2.1**

  - [x] 2.4 Write property test for Modelfile generation
    - **Property 4: Modelfile Generation Correctness**
    - **Validates: Requirements 1.4**

- [x] 3. Implement HistoryStore for conversation persistence
  - [x] 3.1 Create Message and ConversationHistory dataclasses
    - Implement Message with role, content, timestamp
    - Implement ConversationHistory with agent_name, messages, last_updated
    - Implement serialization methods (to_dict, from_dict)
    - _Requirements: 5.2_

  - [x] 3.2 Implement HistoryStore class
    - Implement load() to read history from JSON file
    - Implement save() to write history to JSON file
    - Implement delete() to remove history file
    - Handle missing file case (return empty history)
    - _Requirements: 5.1, 5.3, 5.4_

  - [x] 3.3 Write property test for History serialization round-trip
    - **Property 8: History Serialization Round-Trip**
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 4. Checkpoint - Verify data models
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement AgentManager for agent CRUD operations
  - [x] 5.1 Create AgentManager class with storage paths
    - Initialize data directories (data/agents/, data/history/)
    - Implement agent_exists() method
    - Implement get_agent() to load agent config
    - _Requirements: 2.1_

  - [x] 5.2 Implement agent creation
    - Validate agent name format
    - Check for existing agent
    - Save config.json and Modelfile
    - Execute ollama create command
    - Handle errors and cleanup on failure
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 5.3 Implement agent listing
    - Read all agent directories
    - Load and return agent configs
    - Handle empty state
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 5.4 Implement agent deletion
    - Execute ollama rm command
    - Delete agent directory
    - Delete history file
    - Handle non-existent agent
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 5.5 Write property test for Agent uniqueness
    - **Property 2: Agent Uniqueness Constraint**
    - **Validates: Requirements 1.3**

  - [x] 5.6 Write property test for Agent deletion completeness
    - **Property 7: Agent Deletion Completeness**
    - **Validates: Requirements 4.3, 4.4**

- [x] 6. Implement ChatSession for conversations
  - [x] 6.1 Create ChatSession class
    - Initialize with AgentManager and HistoryStore
    - Implement start() to load agent and history
    - Implement end() to save history
    - _Requirements: 3.1, 3.5_

  - [x] 6.2 Implement message handling
    - Implement send_message() with streaming response
    - Append user message to history
    - Append assistant response to history
    - Handle Ollama connection errors
    - _Requirements: 3.2, 3.3, 3.4, 3.7_

  - [x] 6.3 Implement clear_history()
    - Reset messages list
    - Update last_updated timestamp
    - _Requirements: 3.6_

  - [x] 6.4 Write property test for Message persistence
    - **Property 5: Message Persistence**
    - **Validates: Requirements 3.2, 3.4, 5.1, 5.2**

  - [x] 6.5 Write property test for History clear
    - **Property 6: History Clear Resets State**
    - **Validates: Requirements 3.6**

- [x] 7. Checkpoint - Verify core functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement CLI interface
  - [x] 8.1 Create CLI class with menu system
    - Implement run() main loop
    - Implement display_menu() with options
    - Handle Ctrl+C gracefully
    - _Requirements: 6.1, 6.6_

  - [x] 8.2 Implement create_agent_flow()
    - Prompt for all agent fields
    - Validate input
    - Call AgentManager.create_agent()
    - Display success/error messages
    - _Requirements: 1.1, 6.5_

  - [x] 8.3 Implement list_agents_flow()
    - Call AgentManager.list_agents()
    - Format and display agent list
    - Handle empty state
    - _Requirements: 2.2, 2.3_

  - [x] 8.4 Implement chat_flow()
    - Select agent from list
    - Start ChatSession
    - Handle user input loop (exit, clear, messages)
    - Display formatted messages
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 8.5 Implement delete_agent_flow()
    - Select agent from list
    - Confirm deletion
    - Call AgentManager.delete_agent()
    - Display success/error messages
    - _Requirements: 4.1, 4.5_

  - [x] 8.6 Write property test for Message display formatting
    - **Property 9: Message Display Formatting**
    - **Validates: Requirements 6.3, 6.4**

- [x] 9. Create Makefile with all targets
  - [x] 9.1 Create Makefile with grouped targets
    - Add help target with descriptions
    - Add install target (uv sync)
    - Add run target (uv run python main.py)
    - Add test target (uv run pytest)
    - Add lint target (uv run ruff check)
    - Add format target (uv run ruff format)
    - Add clean target (remove caches, data)
    - Group targets with comments
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 10. Update main.py entry point
  - Import CLI from package
  - Call CLI.run() in main()
  - _Requirements: 6.1_

- [x] 11. Update package exports
  - Export Agent, AgentManager, ChatSession in __init__.py
  - Ensure library usage doesn't trigger CLI
  - _Requirements: 7.2, 7.3, 7.4, 7.5_

- [x] 12. Final checkpoint - Full integration test
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property-based tests are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Use `uv` for all package management (not pip)
- Ollama must be running for integration tests
