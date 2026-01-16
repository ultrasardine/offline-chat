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
        command: The command to execute (e.g., "uvx", "npx", "sql").
        args: List of arguments to pass to the command.
        env: Optional environment variables for the server process.
        disabled: Whether this server is disabled.

        database_type: Optional database type ("oracle", "postgresql", "mysql", "sqlite").
            Used to identify database MCP servers and enable database-specific features.

        oracle_connection_name: Optional SQLcl connection name for Oracle databases.
            When provided, uses an existing SQLcl connection instead of creating a new one.
            This is the recommended approach for Oracle as it reuses saved credentials.
            Example: "PROD_ANALYTICS" (refers to a connection in ~/.sqlcl/connections.json)

        oracle_tns_name: Optional TNS alias for Oracle databases.
            When provided, uses a TNS name from tnsnames.ora for connection.
            Requires database_user and database_password to be set.
            Example: "PROD_TNS" (refers to an entry in tnsnames.ora)

        database_path: Optional file path for SQLite databases.
            The absolute or relative path to the SQLite database file.
            Example: "/data/app.db" or "./local.db"

        database_host: Optional host for Oracle/PostgreSQL/MySQL databases.
            The hostname or IP address of the database server.
            Example: "db.example.com" or "192.168.1.100"

        database_port: Optional port for Oracle/PostgreSQL/MySQL databases.
            The port number the database server listens on.
            Defaults: Oracle=1521, PostgreSQL=5432, MySQL=3306

        database_name: Optional database/service name.
            For Oracle: The service name (e.g., "PRODDB", "ORCL")
            For PostgreSQL/MySQL: The database name (e.g., "analytics", "sales")

        database_user: Optional database username.
            The username for database authentication.
            Example: "analyst", "app_user"

        database_password: Optional database password.
            The password for database authentication.
            Note: Stored in configuration files - ensure proper file permissions.
            Masked in displays and logs for security.

    Examples:
        Oracle with existing SQLcl connection (recommended):
            >>> config = MCPServerConfig(
            ...     name="prod_db",
            ...     command="sql",
            ...     args=["-mcp", "-connection", "PROD_ANALYTICS"],
            ...     database_type="oracle",
            ...     oracle_connection_name="PROD_ANALYTICS"
            ... )

        Oracle with TNS alias:
            >>> config = MCPServerConfig(
            ...     name="prod_db",
            ...     command="sql",
            ...     args=["-mcp", "analyst/password@PROD_TNS"],
            ...     database_type="oracle",
            ...     oracle_tns_name="PROD_TNS",
            ...     database_user="analyst",
            ...     database_password="password"
            ... )

        Oracle with full connection details:
            >>> config = MCPServerConfig(
            ...     name="prod_db",
            ...     command="sql",
            ...     args=["-mcp", "analyst/password@db.example.com:1521/PRODDB"],
            ...     database_type="oracle",
            ...     database_host="db.example.com",
            ...     database_port=1521,
            ...     database_name="PRODDB",
            ...     database_user="analyst",
            ...     database_password="password"
            ... )

        PostgreSQL:
            >>> config = MCPServerConfig(
            ...     name="analytics_db",
            ...     command="uvx",
            ...     args=["postgres-mcp-server", "--host", "localhost",
            ...           "--port", "5432", "--database", "analytics", "--user", "analyst"],
            ...     env={"PGPASSWORD": "password"},
            ...     database_type="postgresql",
            ...     database_host="localhost",
            ...     database_port=5432,
            ...     database_name="analytics",
            ...     database_user="analyst",
            ...     database_password="password"
            ... )

        SQLite:
            >>> config = MCPServerConfig(
            ...     name="local_db",
            ...     command="uvx",
            ...     args=["sqlite-mcp-server", "--db-path", "/data/app.db"],
            ...     database_type="sqlite",
            ...     database_path="/data/app.db"
            ... )
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    disabled: bool = False

    # Database-specific fields (optional, used when server is a database)
    database_type: str | None = None
    oracle_connection_name: str | None = None
    oracle_tns_name: str | None = None
    database_path: str | None = None
    database_host: str | None = None
    database_port: int | None = None
    database_name: str | None = None
    database_user: str | None = None
    database_password: str | None = None

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
        result = {
            "name": self.name,
            "command": self.command,
            "args": self.args.copy(),
            "env": self.env.copy(),
            "disabled": self.disabled,
        }

        # Add database-specific fields if present
        if self.database_type is not None:
            result["database_type"] = self.database_type
        if self.oracle_connection_name is not None:
            result["oracle_connection_name"] = self.oracle_connection_name
        if self.oracle_tns_name is not None:
            result["oracle_tns_name"] = self.oracle_tns_name
        if self.database_path is not None:
            result["database_path"] = self.database_path
        if self.database_host is not None:
            result["database_host"] = self.database_host
        if self.database_port is not None:
            result["database_port"] = self.database_port
        if self.database_name is not None:
            result["database_name"] = self.database_name
        if self.database_user is not None:
            result["database_user"] = self.database_user
        if self.database_password is not None:
            result["database_password"] = self.database_password

        return result

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
            database_type=data.get("database_type"),
            oracle_connection_name=data.get("oracle_connection_name"),
            oracle_tns_name=data.get("oracle_tns_name"),
            database_path=data.get("database_path"),
            database_host=data.get("database_host"),
            database_port=data.get("database_port"),
            database_name=data.get("database_name"),
            database_user=data.get("database_user"),
            database_password=data.get("database_password"),
        )
