"""Custom exceptions for Offline Chat application."""


class OfflineChatError(Exception):
    """Base exception for Offline Chat errors."""

    pass


class AgentNotFoundError(OfflineChatError):
    """Raised when an agent does not exist."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Agent '{name}' not found. Use 'list' to see available agents.")


class AgentExistsError(OfflineChatError):
    """Raised when attempting to create an agent that already exists."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Agent '{name}' already exists.")


class InvalidAgentNameError(OfflineChatError):
    """Raised when agent name is invalid."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Invalid agent name '{name}'. Use lowercase letters, numbers, and hyphens only.")


class OllamaConnectionError(OfflineChatError):
    """Raised when Ollama is not reachable."""

    def __init__(self):
        super().__init__("Cannot connect to Ollama. Is it running?")


class OllamaCommandError(OfflineChatError):
    """Raised when an Ollama command fails."""

    def __init__(self, command: str, error: str):
        self.command = command
        self.error = error
        super().__init__(f"Ollama command failed: {error}")


class SearchError(OfflineChatError):
    """Base exception for search errors."""

    pass


class SearchTimeoutError(SearchError):
    """Raised when a search times out."""

    def __init__(self, timeout: int):
        self.timeout = timeout
        super().__init__(f"Search timed out after {timeout} seconds.")


class SearchConnectionError(SearchError):
    """Raised when the search provider is unavailable."""

    def __init__(self):
        super().__init__("Cannot connect to search provider.")


class FetchError(OfflineChatError):
    """Base exception for web fetch errors."""

    pass


class FetchTimeoutError(FetchError):
    """Raised when a page fetch times out."""

    def __init__(self, timeout: int):
        self.timeout = timeout
        super().__init__(f"Page fetch timed out after {timeout} seconds.")


class FetchHTTPError(FetchError):
    """Raised when a page returns an HTTP error."""

    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP error {status_code} when fetching {url}")


class MCPConfigError(OfflineChatError):
    """Raised when MCP server configuration is invalid."""

    pass
