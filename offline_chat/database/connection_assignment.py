"""Agent connection assignment with access control.

This module defines the AgentConnectionAssignment dataclass which represents
an agent's assignment to a database connection with specific access control
settings.
"""

from dataclasses import dataclass, field
from typing import Any

from offline_chat.database.access_level import AccessLevel


@dataclass
class AgentConnectionAssignment:
    """Represents an agent's assignment to a database connection with access control.
    
    This dataclass encapsulates the relationship between an agent and a database
    connection, including the access level granted and any table-specific restrictions.
    
    Attributes:
        connection_name: The name of the database connection this assignment refers to.
                        Must match a connection name in the connection store.
        access_level: The level of database access granted to the agent for this
                     connection. Controls what types of queries can be executed.
        allowed_tables: Optional list of table names that the agent can access.
                       Only used when access_level is TABLE_SPECIFIC_READ or
                       TABLE_SPECIFIC_READ_WRITE. None means no table restrictions.
    
    Example:
        >>> # Read-only access to a connection
        >>> assignment = AgentConnectionAssignment(
        ...     connection_name="prod-db",
        ...     access_level=AccessLevel.READ_ONLY
        ... )
        
        >>> # Table-specific read-write access
        >>> assignment = AgentConnectionAssignment(
        ...     connection_name="analytics-db",
        ...     access_level=AccessLevel.TABLE_SPECIFIC_READ_WRITE,
        ...     allowed_tables=["users", "orders", "products"]
        ... )
    """
    
    connection_name: str
    access_level: AccessLevel
    allowed_tables: list[str] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the assignment to a dictionary for JSON serialization.
        
        Returns:
            A dictionary representation of the assignment with:
            - connection_name: str
            - access_level: str (the enum value)
            - allowed_tables: list[str] | None
        
        Example:
            >>> assignment = AgentConnectionAssignment(
            ...     connection_name="prod-db",
            ...     access_level=AccessLevel.READ_ONLY
            ... )
            >>> assignment.to_dict()
            {'connection_name': 'prod-db', 'access_level': 'read-only', 'allowed_tables': None}
        """
        return {
            "connection_name": self.connection_name,
            "access_level": self.access_level.value,
            "allowed_tables": self.allowed_tables,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConnectionAssignment":
        """Create an AgentConnectionAssignment instance from a dictionary.
        
        This method is used for deserializing assignments from JSON storage.
        
        Args:
            data: A dictionary containing the assignment data with keys:
                 - connection_name: str (required)
                 - access_level: str (required, must be a valid AccessLevel value)
                 - allowed_tables: list[str] | None (optional, defaults to None)
        
        Returns:
            A new AgentConnectionAssignment instance.
        
        Raises:
            KeyError: If required keys are missing from the dictionary.
            ValueError: If access_level is not a valid AccessLevel value.
        
        Example:
            >>> data = {
            ...     "connection_name": "prod-db",
            ...     "access_level": "read-only",
            ...     "allowed_tables": None
            ... }
            >>> assignment = AgentConnectionAssignment.from_dict(data)
            >>> assignment.connection_name
            'prod-db'
        """
        return cls(
            connection_name=data["connection_name"],
            access_level=AccessLevel(data["access_level"]),
            allowed_tables=data.get("allowed_tables"),
        )
