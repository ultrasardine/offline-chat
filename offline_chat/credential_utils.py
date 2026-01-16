"""Utilities for masking and sanitizing credentials in database configurations."""

from typing import Any

from offline_chat.mcp_config import MCPServerConfig


def mask_password(password: str | None) -> str:
    """Mask a password for display purposes.

    Args:
        password: The password to mask, or None.

    Returns:
        Masked password string ("****") if password is not None, otherwise "None".
    """
    if password is None:
        return "None"
    return "****"


def sanitize_config_for_display(config: MCPServerConfig) -> dict[str, Any]:
    """Sanitize an MCP server configuration for display by masking sensitive fields.

    This function creates a dictionary representation of the configuration with
    password fields masked to prevent credential exposure in logs or UI.

    Args:
        config: The MCP server configuration to sanitize.

    Returns:
        Dictionary with sensitive fields masked.

    Examples:
        >>> from offline_chat.mcp_config import MCPServerConfig
        >>>
        >>> # Oracle configuration with password
        >>> config = MCPServerConfig(
        ...     name="prod_db",
        ...     command="sql",
        ...     args=["-mcp", "user/secret@host:1521/PRODDB"],
        ...     database_type="oracle",
        ...     database_user="user",
        ...     database_password="secret"
        ... )
        >>>
        >>> # Sanitize for display
        >>> safe_config = sanitize_config_for_display(config)
        >>> print(safe_config["database_password"])
        ****
        >>>
        >>> # PostgreSQL with password in environment
        >>> pg_config = MCPServerConfig(
        ...     name="analytics",
        ...     command="uvx",
        ...     args=["postgres-mcp-server"],
        ...     env={"PGPASSWORD": "secret123"},
        ...     database_type="postgresql"
        ... )
        >>>
        >>> safe_pg = sanitize_config_for_display(pg_config)
        >>> print(safe_pg["env"]["PGPASSWORD"])
        ****
    """
    result = config.to_dict()

    # Mask the database password if present
    if "database_password" in result and result["database_password"] is not None:
        result["database_password"] = mask_password(result["database_password"])

    # Also check for passwords in environment variables
    if "env" in result and isinstance(result["env"], dict):
        masked_env = {}
        for key, value in result["env"].items():
            # Mask common password environment variable names
            if any(
                pwd_key in key.upper()
                for pwd_key in ["PASSWORD", "PASSWD", "PWD", "SECRET", "TOKEN"]
            ):
                masked_env[key] = mask_password(value)
            else:
                masked_env[key] = value
        result["env"] = masked_env

    return result


def sanitize_error_message(error_message: str, config: MCPServerConfig | None = None) -> str:
    """Remove credentials from error messages.

    This function scans error messages for potential credential exposure and
    replaces any found credentials with masked values.

    Args:
        error_message: The error message to sanitize.
        config: Optional configuration to extract credentials from for replacement.

    Returns:
        Sanitized error message with credentials removed.
    """
    sanitized = error_message

    if config is not None:
        # Replace database password if present
        if config.database_password is not None and config.database_password in sanitized:
            sanitized = sanitized.replace(config.database_password, "****")

        # Replace passwords from environment variables
        if config.env:
            for key, value in config.env.items():
                if any(
                    pwd_key in key.upper()
                    for pwd_key in ["PASSWORD", "PASSWD", "PWD", "SECRET", "TOKEN"]
                ):
                    if value and value in sanitized:
                        sanitized = sanitized.replace(value, "****")

    return sanitized
