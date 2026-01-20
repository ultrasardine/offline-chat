"""Agent data model for Offline Chat application."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from offline_chat.database.connection_assignment import AgentConnectionAssignment
    from offline_chat.mcp_config import MCPServerConfig


@dataclass
class Agent:
    """Represents an AI agent configuration.

    An agent is a customized Ollama model with a unique name, persona,
    system prompt, and persistent conversation history.

    Attributes:
        name: Unique identifier in kebab-case format.
        display_name: Human-readable name for display.
        base_model: Ollama base model (e.g., "llama3:latest").
        system_prompt: Persona and purpose definition.
        temperature: Response creativity (0.0-1.0).
        language: Language for agent responses (e.g., "English", "German").
        web_search_enabled: Whether the agent can search the web for information.
        mcp_servers: List of MCP server configurations for external tools.
        connection_assignments: List of database connection assignments with access control.
        guidelines: List of behavioral guidelines for the agent.
        created_at: Timestamp when the agent was created.
        connection_references: (Deprecated) Legacy field for backward compatibility.
        database_config: (Deprecated) Legacy field for backward compatibility.
    """

    name: str
    display_name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7
    language: str = "English"
    web_search_enabled: bool = False
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
    connection_assignments: list[AgentConnectionAssignment] = field(default_factory=list)
    guidelines: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Legacy fields for backward compatibility (deprecated)
    connection_references: list[str] = field(default_factory=list)
    database_config: dict[str, Any] | None = None

    # Regex pattern for valid agent names: kebab-case
    # Lowercase letters, numbers, and hyphens, not starting or ending with hyphen
    _NAME_PATTERN: str = field(default=r"^[a-z0-9]+(-[a-z0-9]+)*$", init=False, repr=False)

    def validate_name(self) -> bool:
        """Validate agent name follows kebab-case pattern.

        Returns:
            True if the name is valid, False otherwise.
        """
        if not self.name:
            return False
        return bool(re.match(self._NAME_PATTERN, self.name))

    def get_full_system_prompt(self) -> str:
        """Generate system prompt with guidelines included.
        
        If guidelines are present, they are appended to the base system prompt
        as a formatted bullet list. If no guidelines exist, returns just the
        base system prompt.
        
        Returns:
            The complete system prompt including guidelines if present.
            
        Example:
            >>> agent = Agent(
            ...     name="test",
            ...     display_name="Test",
            ...     base_model="llama3:latest",
            ...     system_prompt="You are a helpful assistant.",
            ...     guidelines=["Be concise", "Always verify facts"]
            ... )
            >>> prompt = agent.get_full_system_prompt()
            >>> "Guidelines:" in prompt
            True
            >>> "- Be concise" in prompt
            True
        """
        if not self.guidelines:
            return self.system_prompt
        
        guidelines_text = "\n\nGuidelines:\n" + "\n".join(f"- {g}" for g in self.guidelines)
        return self.system_prompt + guidelines_text

    def to_modelfile(self) -> str:
        """Generate Ollama Modelfile content.

        Returns:
            String content for the Modelfile.
        """
        # Build full system prompt with language instruction
        full_prompt = self.system_prompt
        if self.language and self.language.lower() != "english":
            full_prompt = f"{self.system_prompt} Always respond in {self.language}."

        # Escape double quotes in system prompt for Modelfile format
        escaped_prompt = full_prompt.replace("\\", "\\\\").replace('"', '\\"')
        return f'''FROM {self.base_model}

SYSTEM "{escaped_prompt}"

PARAMETER temperature {self.temperature}
'''

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent to dictionary.

        Returns:
            Dictionary representation of the agent.
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "base_model": self.base_model,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "language": self.language,
            "web_search_enabled": self.web_search_enabled,
            "mcp_servers": [s.to_dict() for s in self.mcp_servers],
            "connection_assignments": [ca.to_dict() for ca in self.connection_assignments],
            "guidelines": self.guidelines,
            "created_at": self.created_at.isoformat(),
            # Include legacy fields if present for backward compatibility
            "connection_references": self.connection_references,
            "database_config": self.database_config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Agent":
        """Deserialize agent from dictionary.

        Args:
            data: Dictionary containing agent data.

        Returns:
            Agent instance.
        """
        # Import here to avoid circular imports at module level
        from offline_chat.database.access_level import AccessLevel
        from offline_chat.database.connection_assignment import AgentConnectionAssignment
        from offline_chat.mcp_config import MCPServerConfig

        # Deserialize MCP server configs with backward compatibility
        mcp_servers = [MCPServerConfig.from_dict(s) for s in data.get("mcp_servers", [])]
        
        # Deserialize connection assignments with backward compatibility
        connection_assignments = []
        if "connection_assignments" in data:
            connection_assignments = [
                AgentConnectionAssignment.from_dict(ca) 
                for ca in data["connection_assignments"]
            ]
        elif "connection_references" in data and data["connection_references"]:
            # Migration: convert old connection_references to connection_assignments
            # Default to read-write access for backward compatibility
            connection_assignments = [
                AgentConnectionAssignment(
                    connection_name=ref,
                    access_level=AccessLevel.READ_WRITE,
                    allowed_tables=None
                )
                for ref in data["connection_references"]
            ]
        
        # Get guidelines with backward compatibility
        guidelines = data.get("guidelines", [])
        
        # Get legacy fields for backward compatibility
        connection_references = data.get("connection_references", [])
        database_config = data.get("database_config")

        return cls(
            name=data["name"],
            display_name=data["display_name"],
            base_model=data["base_model"],
            system_prompt=data["system_prompt"],
            temperature=data.get("temperature", 0.7),
            language=data.get("language", "English"),
            web_search_enabled=data.get("web_search_enabled", False),
            mcp_servers=mcp_servers,
            connection_assignments=connection_assignments,
            guidelines=guidelines,
            created_at=datetime.fromisoformat(data["created_at"]),
            connection_references=connection_references,
            database_config=database_config,
        )
