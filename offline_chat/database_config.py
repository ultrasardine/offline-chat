"""Database MCP configuration factory for Offline Chat application.

This module provides factory functions to create MCP server configurations
for different database types (Oracle, PostgreSQL, MySQL, SQLite).
"""

from offline_chat.mcp_config import MCPServerConfig


def create_database_mcp_config(db_type: str, name: str, **kwargs) -> MCPServerConfig:
    """Create an MCP server configuration for a database.

    This factory function creates properly configured MCPServerConfig instances
    for different database types. Each database type has specific connection
    parameters and command structures.

    Args:
        db_type: Database type ("oracle", "postgresql", "mysql", "sqlite")
        name: Unique name for this database connection
        **kwargs: Database-specific connection parameters:

            For Oracle:
                - connection_name: Existing SQLcl connection name (highest priority)
                - tns_name: TNS alias (second priority)
                - host: Database host (for full connection details)
                - port: Database port (default: 1521)
                - service_name: Oracle service name
                - username: Database username
                - password: Database password

            For SQLite:
                - path: File path to the SQLite database file

            For PostgreSQL:
                - host: Database host
                - port: Database port (default: 5432)
                - database: Database name
                - username: Database username
                - password: Database password

            For MySQL:
                - host: Database host
                - port: Database port (default: 3306)
                - database: Database name
                - username: Database username
                - password: Database password

    Returns:
        MCPServerConfig configured for the specified database

    Raises:
        ValueError: If db_type is unsupported or required params missing

    Examples:
        >>> # Oracle with existing SQLcl connection
        >>> config = create_database_mcp_config(
        ...     "oracle", "prod_db", connection_name="PROD_CONN"
        ... )

        >>> # SQLite with file path
        >>> config = create_database_mcp_config(
        ...     "sqlite", "local_db", path="/data/app.db"
        ... )

        >>> # PostgreSQL with full connection details
        >>> config = create_database_mcp_config(
        ...     "postgresql", "analytics_db",
        ...     host="localhost", port=5432, database="analytics",
        ...     username="analyst", password="secret"
        ... )
    """
    if db_type == "oracle":
        return _create_oracle_config(name, **kwargs)
    elif db_type == "sqlite":
        return _create_sqlite_config(name, **kwargs)
    elif db_type == "postgresql":
        return _create_postgresql_config(name, **kwargs)
    elif db_type == "mysql":
        return _create_mysql_config(name, **kwargs)
    else:
        raise ValueError(
            f"Unsupported database type: {db_type}. "
            f"Supported types: oracle, postgresql, mysql, sqlite"
        )


def _create_oracle_config(
    name: str,
    connection_name: str | None = None,
    host: str | None = None,
    port: int = 1521,
    service_name: str | None = None,
    username: str | None = None,
    password: str | None = None,
    tns_name: str | None = None,
    **kwargs,
) -> MCPServerConfig:
    """Create Oracle Database MCP server config using SQLcl.

    Priority order for connection methods:
    1. Use existing SQLcl connection_name if provided
    2. Use TNS alias if provided
    3. Use full connection details (host, port, service_name, username, password)

    Args:
        name: Unique name for this database connection
        connection_name: Existing SQLcl connection name (highest priority)
        host: Database host (for full connection details)
        port: Database port (default: 1521)
        service_name: Oracle service name
        username: Database username
        password: Database password
        tns_name: TNS alias (second priority)
        **kwargs: Additional arguments (ignored)

    Returns:
        MCPServerConfig configured for Oracle Database

    Raises:
        ValueError: If required parameters are missing
    """
    if connection_name:
        # Use existing SQLcl connection (highest priority)
        return MCPServerConfig(
            name=name,
            command="sql",  # SQLcl command
            args=["-mcp", "-connection", connection_name],
            database_type="oracle",
            oracle_connection_name=connection_name,
        )
    elif tns_name:
        # Use TNS alias (second priority)
        if not username or password is None:
            raise ValueError("Oracle TNS connection requires 'username' and 'password'")
        return MCPServerConfig(
            name=name,
            command="sql",
            args=["-mcp", f"{username}/{password}@{tns_name}"],
            database_type="oracle",
            oracle_tns_name=tns_name,
            database_user=username,
            database_password=password,
        )
    else:
        # Use full connection details (third priority)
        if not all([host, service_name, username]) or password is None:
            raise ValueError(
                "Oracle full connection requires 'host', 'service_name', 'username', and 'password'"
            )
        conn_string = f"{username}/{password}@{host}:{port}/{service_name}"
        return MCPServerConfig(
            name=name,
            command="sql",
            args=["-mcp", conn_string],
            database_type="oracle",
            database_host=host,
            database_port=port,
            database_name=service_name,
            database_user=username,
            database_password=password,
        )


def _create_sqlite_config(name: str, path: str | None = None, **kwargs) -> MCPServerConfig:
    """Create SQLite database MCP server config.

    Args:
        name: Unique name for this database connection
        path: File path to the SQLite database file
        **kwargs: Additional arguments (ignored)

    Returns:
        MCPServerConfig configured for SQLite

    Raises:
        ValueError: If path is not provided
    """
    if not path:
        raise ValueError("SQLite configuration requires 'path' parameter")

    return MCPServerConfig(
        name=name,
        command="uvx",
        args=["sqlite-mcp-server", "--db-path", path],
        database_type="sqlite",
        database_path=path,
    )


def _create_postgresql_config(
    name: str,
    host: str | None = None,
    port: int = 5432,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
    **kwargs,
) -> MCPServerConfig:
    """Create PostgreSQL database MCP server config.

    Args:
        name: Unique name for this database connection
        host: Database host
        port: Database port (default: 5432)
        database: Database name
        username: Database username
        password: Database password
        **kwargs: Additional arguments (ignored)

    Returns:
        MCPServerConfig configured for PostgreSQL

    Raises:
        ValueError: If required parameters are missing
    """
    if not all([host, database, username]) or password is None:
        raise ValueError(
            "PostgreSQL configuration requires 'host', 'database', 'username', and 'password'"
        )

    return MCPServerConfig(
        name=name,
        command="uvx",
        args=[
            "postgres-mcp-server",
            "--host",
            host,
            "--port",
            str(port),
            "--database",
            database,
            "--user",
            username,
        ],
        env={"PGPASSWORD": password},
        database_type="postgresql",
        database_host=host,
        database_port=port,
        database_name=database,
        database_user=username,
        database_password=password,
    )


def _create_mysql_config(
    name: str,
    host: str | None = None,
    port: int = 3306,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
    **kwargs,
) -> MCPServerConfig:
    """Create MySQL database MCP server config.

    Args:
        name: Unique name for this database connection
        host: Database host
        port: Database port (default: 3306)
        database: Database name
        username: Database username
        password: Database password
        **kwargs: Additional arguments (ignored)

    Returns:
        MCPServerConfig configured for MySQL

    Raises:
        ValueError: If required parameters are missing
    """
    if not all([host, database, username]) or password is None:
        raise ValueError(
            "MySQL configuration requires 'host', 'database', 'username', and 'password'"
        )

    return MCPServerConfig(
        name=name,
        command="uvx",
        args=[
            "mysql-mcp-server",
            "--host",
            host,
            "--port",
            str(port),
            "--database",
            database,
            "--user",
            username,
            "--password",
            password,
        ],
        database_type="mysql",
        database_host=host,
        database_port=port,
        database_name=database,
        database_user=username,
        database_password=password,
    )
