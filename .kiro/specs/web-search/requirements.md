# Requirements Document

## Introduction

This feature extends the Offline Chat application to enable AI agents to search the web for current information. Using Ollama's tool calling capabilities, agents can autonomously decide when to search the web to answer user questions that require up-to-date information. The feature integrates seamlessly with the existing agent and chat session architecture while maintaining the local-first, privacy-focused design philosophy.

## Glossary

- **Tool_Calling**: Ollama's capability that allows models to invoke external functions and incorporate their results into responses
- **Web_Search_Tool**: A function that performs web searches and returns results to the agent
- **Search_Provider**: An external service that executes web searches (e.g., DuckDuckGo, SearXNG)
- **Tool_Result**: The response from a tool execution that is passed back to the model
- **Agent_Loop**: A conversation pattern where the model can make multiple tool calls before generating a final response
- **Search_Enabled_Agent**: An agent configured to use web search capabilities
- **Web_Fetch_Tool**: A function that fetches and parses web page content from a URL
- **Page_Content**: The extracted text content from a web page after HTML parsing
- **Chat_Session**: An interactive conversation between a user and an agent (existing)
- **Agent_Manager**: The component responsible for creating, listing, and deleting agents (existing)

## Requirements

### Requirement 1: Web Search Tool Definition

**User Story:** As a developer, I want a web search tool that can be passed to Ollama's tool calling API, so that agents can search the web for information.

#### Acceptance Criteria

1. THE Web_Search_Tool SHALL define a function schema compatible with Ollama's tool calling format
2. THE Web_Search_Tool SHALL accept a search query string as input
3. THE Web_Search_Tool SHALL accept an optional max_results parameter with a default value of 5
4. WHEN the Web_Search_Tool is invoked, THE Search_Provider SHALL execute the search and return results
5. THE Web_Search_Tool SHALL return results containing title, href, and body for each result (matching duckduckgo-search output)
6. IF the search fails, THEN THE Web_Search_Tool SHALL return an error message describing the failure

### Requirement 2: Search Provider Integration

**User Story:** As a user, I want web searches to use a privacy-respecting search provider, so that my queries remain private.

#### Acceptance Criteria

1. THE Search_Provider SHALL use the `duckduckgo-search` Python library as the search backend
2. THE Search_Provider SHALL use the DDGS class from duckduckgo_search to execute text searches
3. THE Search_Provider SHALL support configurable timeout for search requests with a default of 10 seconds
4. WHEN a search is executed, THE Search_Provider SHALL return results containing title, href, and body fields
5. IF the Search_Provider times out, THEN THE system SHALL return a timeout error message
6. IF the Search_Provider is unavailable, THEN THE system SHALL return a connection error message

### Requirement 3: Tool-Enabled Chat Session

**User Story:** As a user, I want to chat with agents that can search the web when needed, so that I can get current information in my conversations.

#### Acceptance Criteria

1. WHEN a Chat_Session is started with a Search_Enabled_Agent, THE session SHALL register the Web_Search_Tool with Ollama
2. WHEN the model requests a tool call, THE Chat_Session SHALL execute the Web_Search_Tool and return results to the model
3. WHEN the model makes multiple tool calls, THE Chat_Session SHALL execute them in sequence and accumulate results
4. WHEN tool results are returned, THE Chat_Session SHALL continue the conversation with the model until a final response is generated
5. THE Chat_Session SHALL stream the final response character by character as in the existing implementation
6. WHEN a tool call is executed, THE Chat_Session SHALL NOT add tool call messages to the persistent conversation history
7. THE Chat_Session SHALL only persist user messages and final assistant responses to history

### Requirement 4: Agent Web Search Configuration

**User Story:** As a user, I want to enable or disable web search for each agent, so that I can control which agents have internet access.

#### Acceptance Criteria

1. THE Agent configuration SHALL include a web_search_enabled boolean field with a default value of False
2. WHEN creating an agent, THE CLI SHALL prompt whether to enable web search
3. WHEN web_search_enabled is True, THE Agent SHALL be treated as a Search_Enabled_Agent
4. WHEN web_search_enabled is False, THE Chat_Session SHALL NOT register any tools with Ollama
5. THE Agent serialization (to_dict/from_dict) SHALL include the web_search_enabled field

### Requirement 5: Search Result Formatting

**User Story:** As a user, I want search results to be formatted clearly for the agent, so that it can provide accurate and well-sourced responses.

#### Acceptance Criteria

1. WHEN formatting search results for the model, THE system SHALL include numbered results with title, URL, and snippet
2. WHEN no results are found, THE system SHALL return a message indicating no results were found
3. THE formatted results SHALL be concise to fit within model context limits
4. WHEN the agent uses search results, THE agent SHOULD cite sources in its response

### Requirement 6: CLI Web Search Indicator

**User Story:** As a user, I want to see when an agent is searching the web, so that I understand why there might be a delay in response.

#### Acceptance Criteria

1. WHEN a tool call is being executed, THE CLI SHALL display a "Searching..." indicator
2. WHEN the search completes, THE CLI SHALL clear the indicator and begin streaming the response
3. THE indicator SHALL be displayed on a separate line from the response

### Requirement 7: Error Handling for Web Search

**User Story:** As a user, I want clear error messages when web search fails, so that I understand what went wrong.

#### Acceptance Criteria

1. IF the search times out, THEN THE system SHALL inform the agent that the search timed out
2. IF the search provider is unavailable, THEN THE system SHALL inform the agent that web search is currently unavailable
3. IF an unexpected error occurs, THEN THE system SHALL log the error and inform the agent that the search failed
4. WHEN a search error occurs, THE agent SHALL still attempt to answer using its existing knowledge

### Requirement 8: Library API for Web Search

**User Story:** As a developer, I want to use web search capabilities programmatically, so that I can build applications with web-enabled agents.

#### Acceptance Criteria

1. THE package SHALL expose a WebSearchTool class for programmatic use
2. THE package SHALL expose a WebFetchTool class for programmatic use
3. THE package SHALL expose a SearchProvider class for custom search implementations
4. THE ChatSession class SHALL accept an optional tools parameter for custom tool configurations
5. WHEN using the library, THE developer SHALL be able to enable/disable web search per session
6. THE package SHALL export all web search related classes in __init__.py

### Requirement 9: Web Page Fetching

**User Story:** As a user, I want agents to fetch and read full web page content, so that they can provide more detailed answers based on complete articles.

#### Acceptance Criteria

1. THE Web_Fetch_Tool SHALL define a function schema compatible with Ollama's tool calling format
2. THE Web_Fetch_Tool SHALL accept a URL string as input
3. THE Web_Fetch_Tool SHALL accept an optional max_length parameter with a default value of 5000 characters
4. WHEN the Web_Fetch_Tool is invoked, THE system SHALL fetch the web page using HTTP GET
5. WHEN a page is fetched, THE system SHALL parse the HTML using beautifulsoup4 to extract text content
6. THE Web_Fetch_Tool SHALL remove script, style, and navigation elements before extracting text
7. THE Web_Fetch_Tool SHALL return clean, readable text content truncated to max_length
8. IF the fetch fails, THEN THE Web_Fetch_Tool SHALL return an error message describing the failure
9. IF the URL is invalid, THEN THE Web_Fetch_Tool SHALL return an error message indicating invalid URL

### Requirement 10: Web Fetch Error Handling

**User Story:** As a user, I want clear error messages when web page fetching fails, so that I understand what went wrong.

#### Acceptance Criteria

1. IF the page fetch times out, THEN THE system SHALL inform the agent that the page could not be loaded
2. IF the page returns a non-200 status code, THEN THE system SHALL inform the agent of the HTTP error
3. IF the page content cannot be parsed, THEN THE system SHALL inform the agent that the content could not be extracted
4. WHEN a fetch error occurs, THE agent SHALL still attempt to answer using search snippets or existing knowledge
