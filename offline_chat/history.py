"""History storage for Offline Chat application.

This module provides data models and storage for conversation history persistence.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Import SourceCitation for type hints
from offline_chat.rag.models import SourceCitation


@dataclass
class Message:
    """Represents a single message in conversation history.

    Attributes:
        role: The role of the message sender ("user" or "assistant").
        content: The message content.
        timestamp: When the message was sent.
        sources: Optional list of source citations for RAG-enhanced responses.
    """

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: list[SourceCitation] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize message to dictionary.

        Returns:
            Dictionary representation of the message.
        """
        result = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        
        # Only include sources if they exist (RAG-enhanced messages)
        if self.sources is not None:
            result["sources"] = [
                {
                    "source_type": source.source_type,
                    "identifier": source.identifier,
                    "relevance_score": source.relevance_score,
                }
                for source in self.sources
            ]
        
        return result
    
    def format_for_display(self, agent_display_name: str = "Agent") -> str:
        """Format message for display in conversation history.
        
        For RAG-enhanced messages (those with sources), includes source citations
        in the formatted output to show which knowledge sources were consulted.
        
        Args:
            agent_display_name: The display name of the agent (for assistant messages).
        
        Returns:
            Formatted string ready for display in terminal.
        """
        timestamp_str = self.timestamp.strftime("%H:%M")
        
        # Format the main message
        if self.role == "user":
            formatted = f"[{timestamp_str}] You: {self.content}"
        else:
            formatted = f"[{timestamp_str}] {agent_display_name}: {self.content}"
        
        # Add source citations if this is a RAG-enhanced message
        if self.sources is not None and len(self.sources) > 0:
            formatted += "\n  Sources:"
            for source in self.sources:
                formatted += f"\n    - {source.format_for_display()}"
        
        return formatted

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Deserialize message from dictionary.

        Maintains backward compatibility with non-RAG conversation histories
        by treating missing 'sources' field as None.

        Args:
            data: Dictionary containing message data.

        Returns:
            Message instance.
        """
        # Parse sources if present (RAG-enhanced messages)
        sources = None
        if "sources" in data and data["sources"] is not None:
            sources = [
                SourceCitation(
                    source_type=source["source_type"],
                    identifier=source["identifier"],
                    relevance_score=source["relevance_score"],
                )
                for source in data["sources"]
            ]
        
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sources=sources,
        )


@dataclass
class ConversationHistory:
    """Represents the full conversation history for an agent.

    Attributes:
        agent_name: The name of the agent this history belongs to.
        messages: List of messages in the conversation.
        last_updated: Timestamp of the last update.
    """

    agent_name: str
    messages: list[Message] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize conversation history to dictionary.

        Returns:
            Dictionary representation of the conversation history.
        """
        return {
            "agent_name": self.agent_name,
            "messages": [msg.to_dict() for msg in self.messages],
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationHistory":
        """Deserialize conversation history from dictionary.

        Args:
            data: Dictionary containing conversation history data.

        Returns:
            ConversationHistory instance.
        """
        return cls(
            agent_name=data["agent_name"],
            messages=[Message.from_dict(msg) for msg in data.get("messages", [])],
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )


class HistoryStore:
    """Manages persistence of conversation history.

    This class handles loading, saving, and deleting conversation history
    files from the file system.

    Attributes:
        history_dir: Path to the directory where history files are stored.
    """

    def __init__(self, history_dir: Path | str = "data/history"):
        """Initialize the HistoryStore.

        Args:
            history_dir: Path to the directory for storing history files.
        """
        self.history_dir = Path(history_dir)

    def _get_history_path(self, agent_name: str) -> Path:
        """Get the file path for an agent's history.

        Args:
            agent_name: The name of the agent.

        Returns:
            Path to the history JSON file.
        """
        return self.history_dir / f"{agent_name}.json"

    def load(self, agent_name: str) -> ConversationHistory:
        """Load conversation history for an agent.

        If no history file exists, returns an empty history.

        Args:
            agent_name: The name of the agent.

        Returns:
            ConversationHistory for the agent.
        """
        history_path = self._get_history_path(agent_name)

        if not history_path.exists():
            # Return empty history if file doesn't exist
            return ConversationHistory(agent_name=agent_name)

        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ConversationHistory.from_dict(data)

    def save(self, history: ConversationHistory) -> None:
        """Save conversation history to file.

        Creates the history directory if it doesn't exist.

        Args:
            history: The conversation history to save.
        """
        # Ensure directory exists
        self.history_dir.mkdir(parents=True, exist_ok=True)

        history_path = self._get_history_path(history.agent_name)

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history.to_dict(), f, indent=2)

    def delete(self, agent_name: str) -> None:
        """Delete conversation history for an agent.

        Does nothing if the history file doesn't exist.

        Args:
            agent_name: The name of the agent.
        """
        history_path = self._get_history_path(agent_name)

        if history_path.exists():
            history_path.unlink()
