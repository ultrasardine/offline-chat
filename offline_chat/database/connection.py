"""Database connection data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DatabaseConnection:
    """Represents a database connection configuration.

    This dataclass stores all necessary information to connect to various
    database types (Oracle, PostgreSQL, MySQL, SQLite). It includes methods
    for JSON serialization and secure display of sensitive information.

    Attributes:
        name: Unique identifier in kebab-case format
        database_type: Type of database (oracle, postgresql, mysql, sqlite)
        host: Database host (not used for sqlite)
        port: Database port (not used for sqlite)
        database: Database name (for postgresql/mysql)
        service_name: Oracle service name (for oracle only)
        username: Database username
        password: Database password (should be encrypted in storage)
        file_path: SQLite file path (for sqlite only)
        additional_params: Extra connection parameters
        created_at: Timestamp when connection was created
        updated_at: Timestamp when connection was last updated
    """

    name: str
    database_type: str
    host: str | None = None
    port: int | None = None
    database: str | None = None
    service_name: str | None = None
    username: str | None = None
    password: str | None = None
    file_path: str | None = None
    additional_params: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation with all fields, including datetime
            objects converted to ISO format strings.
        """
        return {
            "name": self.name,
            "database_type": self.database_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "service_name": self.service_name,
            "username": self.username,
            "password": self.password,
            "file_path": self.file_path,
            "additional_params": self.additional_params,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatabaseConnection":
        """Create instance from dictionary.

        Args:
            data: Dictionary containing connection data, typically from JSON.

        Returns:
            DatabaseConnection instance with data populated from dictionary.
        """
        # Parse datetime strings back to datetime objects
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            name=data["name"],
            database_type=data["database_type"],
            host=data.get("host"),
            port=data.get("port"),
            database=data.get("database"),
            service_name=data.get("service_name"),
            username=data.get("username"),
            password=data.get("password"),
            file_path=data.get("file_path"),
            additional_params=data.get("additional_params", {}),
            created_at=created_at,
            updated_at=updated_at,
        )

    def mask_sensitive_fields(self) -> dict[str, Any]:
        """Return dict with masked passwords/credentials for secure display.

        This method creates a dictionary representation suitable for displaying
        to users or logging, with sensitive fields (password, tokens, keys)
        replaced with asterisks.

        Returns:
            Dictionary with sensitive fields masked with '********'.
        """
        masked = self.to_dict()

        # Mask password field
        if masked.get("password"):
            masked["password"] = "********"

        # Mask any sensitive keys in additional_params
        if masked.get("additional_params"):
            sensitive_keys = ["password", "token", "key", "secret", "credential"]
            for key in masked["additional_params"]:
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    masked["additional_params"][key] = "********"

        return masked
