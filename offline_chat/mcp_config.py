"""MCP Server configuration data model for Offline Chat application."""

from dataclasses import dataclass, field
from typing import Any

from offline_chat.exceptions import MCPConfigError


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server.

    An MCP server provides external tools that agents can use during
    conversations via the Model Context Protocol.

    Attributes:
        name: Unique identifier for this server configuration.
        command: The command to execute (e.g., "uvx", "npx").
        args: List of arguments to pass to the command.
        env: Optional environment variables for the server process.
        disabled: Whether this server is disabled.
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    disabled: bool = False

    def validate(self) -> None:
        """Validate the MCP server configuration.

        Raises:
            MCPConfigError: If the configuration is invalid.
        """
        if not self.name or not isinstance(self.name, str) or not self.name.strip():
            raise MCPConfigError("MCP server name must be a non-empty string")

        if not self.command or not isinstance(self.command, str) or not self.command.strip():
            raise MCPConfigError("MCP server command must be a non-empty string")

        if not isinstance(self.args, list):
            raise MCPConfigError("MCP server args must be a list")

        if not isinstance(self.env, dict):
            raise MCPConfigError("MCP server env must be a dictionary")

        if not isinstance(self.disabled, bool):
            raise MCPConfigError("MCP server disabled must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary.

        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args.copy(),
            "env": self.env.copy(),
            "disabled": self.disabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPServerConfig":
        """Deserialize configuration from dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            MCPServerConfig instance.
        """
        return cls(
            name=data["name"],
            command=data["command"],
            args=data.get("args", []),
            env=data.get("env", {}),
            disabled=data.get("disabled", False),
        )
