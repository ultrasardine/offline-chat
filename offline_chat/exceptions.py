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
        super().__init__(
            f"Invalid agent name '{name}'. Use lowercase letters, numbers, and hyphens only."
        )


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
