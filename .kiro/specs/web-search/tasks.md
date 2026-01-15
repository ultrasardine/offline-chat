# Implementation Plan: Web Search Feature

## Overview

This implementation plan adds web search capabilities to Offline Chat using Ollama's tool calling. The plan follows a bottom-up approach: search provider → tool definition → session integration → CLI updates → package exports.

## Tasks

- [x] 1. Add dependencies and search exceptions
  - [x] 1.1 Update pyproject.toml with dependencies
    - Add `duckduckgo-search` to project dependencies
    - Add `requests` to project dependencies
    - Add `beautifulsoup4` to project dependencies
    - _Requirements: 2.1, 9.4, 9.5_

  - [x] 1.2 Add search-related exceptions to exceptions.py
    - Add SearchError base exception
    - Add SearchTimeoutError with timeout parameter
    - Add SearchConnectionError
    - Add FetchError base exception
    - Add FetchTimeoutError
    - Add FetchHTTPError
    - _Requirements: 2.5, 2.6, 7.1, 7.2, 7.3, 10.1, 10.2, 10.3_

- [x] 2. Implement SearchProvider
  - [x] 2.1 Create search.py with SearchResult dataclass and DuckDuckGoProvider
    - Create SearchResult dataclass with title, href, body fields
    - Implement DuckDuckGoProvider with configurable timeout
    - Implement search() method using DDGS.text()
    - Handle timeout and connection errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Write property test for search result structure
    - **Property 2: Search Result Structure**
    - **Validates: Requirements 1.5, 2.4**

- [x] 3. Implement WebSearchTool
  - [x] 3.1 Create tools.py with WebSearchTool class
    - Implement get_tool_schema() returning Ollama-compatible schema
    - Implement execute() method that calls provider and formats results
    - Handle search errors and return appropriate messages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 3.2 Write property test for tool schema validity
    - **Property 1: Tool Schema Validity**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [x] 3.3 Implement format_search_results function
    - Format results with numbered entries
    - Include title, URL, and truncated body
    - Handle empty results case
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 3.4 Write property test for search result formatting
    - **Property 6: Search Result Formatting**
    - **Validates: Requirements 5.1, 5.3**

- [x] 4. Implement WebFetchTool
  - [x] 4.1 Create fetch.py with WebFetchTool class
    - Implement get_tool_schema() returning Ollama-compatible schema
    - Implement execute() method that fetches URL and parses HTML
    - Use requests for HTTP GET with configurable timeout
    - Use BeautifulSoup to parse HTML and extract text
    - Remove script, style, nav, header, footer, aside elements
    - Truncate content to max_length
    - Handle fetch errors and return appropriate messages
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [x] 4.2 Write property test for fetch tool schema validity
    - **Property 8: Web Fetch Tool Schema Validity**
    - **Validates: Requirements 9.1, 9.2, 9.3**

  - [x] 4.3 Write property test for content extraction
    - **Property 9: Web Fetch Content Extraction**
    - **Validates: Requirements 9.5, 9.6, 9.7**

- [x] 5. Checkpoint - Verify search and fetch components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Extend Agent dataclass
  - [x] 6.1 Add web_search_enabled field to Agent
    - Add web_search_enabled: bool = False field
    - Update to_dict() to include web_search_enabled
    - Update from_dict() to read web_search_enabled with default False
    - _Requirements: 4.1, 4.5_

  - [x] 6.2 Write property test for extended agent serialization
    - **Property 3: Agent Serialization Round-Trip (Extended)**
    - **Validates: Requirements 4.5**

- [x] 7. Extend ChatSession with agent loop
  - [x] 7.1 Add tool support to ChatSession.__init__
    - Add optional tools parameter
    - Add _web_search_tool instance variable
    - Add _web_fetch_tool instance variable
    - Add _on_tool_call callback for UI notifications
    - _Requirements: 8.3, 8.4_

  - [x] 7.2 Implement _get_tools() method
    - Return custom tools if provided
    - Return web search and web fetch tools if agent.web_search_enabled is True
    - Return empty list otherwise
    - _Requirements: 3.1, 4.3, 4.4_

  - [x] 7.3 Implement _execute_tool() method
    - Execute web_search tool by name
    - Execute web_fetch tool by name
    - Call _on_tool_call callback if set
    - Return tool result string
    - _Requirements: 3.2_

  - [x] 7.4 Implement agent loop in send_message()
    - Use non-streaming for tool detection
    - Execute tool calls and accumulate results
    - Continue loop until no more tool calls
    - Stream final response
    - Only persist user and final assistant messages to history
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 7.5 Write property test for tool registration
    - **Property 4: Tool Registration Based on Configuration**
    - **Validates: Requirements 3.1, 4.3, 4.4**

  - [x] 7.6 Write property test for history persistence
    - **Property 5: History Persistence Excludes Tool Messages**
    - **Validates: Requirements 3.6, 3.7**

  - [x] 7.7 Write property test for agent loop termination
    - **Property 7: Agent Loop Termination**
    - **Validates: Requirements 3.4, 3.5**

- [x] 8. Checkpoint - Verify core functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update CLI for web search
  - [x] 9.1 Update create_agent_flow() to prompt for web search
    - Add prompt for web_search_enabled (y/N)
    - Pass value to Agent constructor
    - _Requirements: 4.2_

  - [x] 9.2 Update chat_flow() to show search/fetch indicator
    - Set tool callback on ChatSession
    - Display "Searching..." when web_search tool is called
    - Display "Fetching page..." when web_fetch tool is called
    - Clear indicator before streaming response
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 9.3 Update list_agents_flow() to show web search status
    - Display indicator for web-search-enabled agents
    - _Requirements: 2.2_

- [x] 10. Update package exports
  - [x] 10.1 Export web search and fetch classes in __init__.py
    - Export SearchResult, DuckDuckGoProvider
    - Export WebSearchTool, WebFetchTool
    - Export SearchError, SearchTimeoutError, SearchConnectionError
    - Export FetchError, FetchTimeoutError, FetchHTTPError
    - _Requirements: 8.1, 8.2, 8.6_

- [x] 11. Update documentation
  - [x] 11.1 Update README.md with web search documentation
    - Add web search section to features
    - Document agent creation with web search
    - Add library usage examples for web search and fetch
    - _Requirements: 8.1, 8.2_

- [x] 12. Final checkpoint - Full integration test
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property-based tests are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Use `uv` for all package management (not pip)
- Ollama must be running with a tool-capable model (e.g., llama3.1, qwen3) for integration tests
- DuckDuckGo searches require internet connectivity
- Web page fetching requires internet connectivity and respects robots.txt via User-Agent
