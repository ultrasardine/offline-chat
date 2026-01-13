"""Agent data model for Offline Chat application."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
        created_at: Timestamp when the agent was created.
    """

    name: str
    display_name: str
    base_model: str
    system_prompt: str
    temperature: float = 0.7
    created_at: datetime = field(default_factory=datetime.now)

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

    def to_modelfile(self) -> str:
        """Generate Ollama Modelfile content.

        Returns:
            String content for the Modelfile.
        """
        # Escape double quotes in system prompt for Modelfile format
        escaped_prompt = self.system_prompt.replace("\\", "\\\\").replace('"', '\\"')
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
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Agent":
        """Deserialize agent from dictionary.

        Args:
            data: Dictionary containing agent data.

        Returns:
            Agent instance.
        """
        return cls(
            name=data["name"],
            display_name=data["display_name"],
            base_model=data["base_model"],
            system_prompt=data["system_prompt"],
            temperature=data.get("temperature", 0.7),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
