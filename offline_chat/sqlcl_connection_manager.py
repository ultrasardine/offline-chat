"""SQLcl named connection management.

This module provides utilities for creating and managing named connections
in Oracle SQLcl, which are required for the SQLcl MCP server to function.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_sqlcl_named_connection(
    connection_name: str,
    username: str,
    password: str,
    host: str,
    port: int,
    service_name: str,
) -> bool:
    """Create a named connection in SQLcl.

    Oracle SQLcl MCP server requires named connections to be pre-configured
    before they can be used. This function creates a named connection by
    running SQLcl commands programmatically.

    Args:
        connection_name: Name for the connection (used in 'connect' tool calls)
        username: Database username
        password: Database password
        host: Database host
        port: Database port
        service_name: Oracle service name

    Returns:
        True if connection was created successfully, False otherwise

    Example:
        >>> success = create_sqlcl_named_connection(
        ...     connection_name="prod_db",
        ...     username="app_user",
        ...     password="secret",
        ...     host="db.example.com",
        ...     port=1521,
        ...     service_name="PRODDB"
        ... )
        >>> if success:
        ...     print("Connection created successfully")
    """
    try:
        # Build connection string
        # Format: username/password@host:port/service_name
        conn_string = f"{username}/{password}@{host}:{port}/{service_name}"

        # Create SQLcl commands to save the connection
        # We use /nolog to start without connecting, then connect and save
        sqlcl_commands = f"""conn {conn_string}
save {connection_name}
exit
"""

        logger.debug(f"Creating SQLcl named connection '{connection_name}'")

        # Run SQLcl with the commands
        result = subprocess.run(
            ["sql", "/nolog"],
            input=sqlcl_commands,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check if the connection was saved successfully
        if result.returncode == 0:
            # Verify the connection was saved by checking if it appears in list
            if _verify_connection_exists(connection_name):
                logger.info(f"SQLcl named connection '{connection_name}' created successfully")
                return True
            else:
                logger.warning(
                    f"SQLcl commands executed but connection '{connection_name}' not found in saved connections"
                )
                return False
        else:
            logger.error(
                f"Failed to create SQLcl named connection '{connection_name}': "
                f"Exit code {result.returncode}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout while creating SQLcl named connection '{connection_name}'")
        return False
    except FileNotFoundError:
        logger.error("SQLcl (sql command) not found. Please install SQLcl first.")
        return False
    except Exception as e:
        logger.error(f"Error creating SQLcl named connection '{connection_name}': {e}")
        return False


def _verify_connection_exists(connection_name: str) -> bool:
    """Verify that a named connection exists in SQLcl.

    Checks if the connection file exists in the SQLcl connections directory.

    Args:
        connection_name: Name of the connection to verify

    Returns:
        True if connection exists, False otherwise
    """
    try:
        # SQLcl stores connections in ~/.dbtools/connections/
        connections_dir = Path.home() / ".dbtools" / "connections"

        if not connections_dir.exists():
            return False

        # Connection files are stored as <name>.json
        connection_file = connections_dir / f"{connection_name}.json"

        return connection_file.exists()

    except Exception as e:
        logger.debug(f"Error verifying connection existence: {e}")
        return False


def delete_sqlcl_named_connection(connection_name: str) -> bool:
    """Delete a named connection from SQLcl.

    Removes the connection file from SQLcl's connections directory.

    Args:
        connection_name: Name of the connection to delete

    Returns:
        True if connection was deleted successfully, False otherwise

    Example:
        >>> success = delete_sqlcl_named_connection("prod_db")
        >>> if success:
        ...     print("Connection deleted")
    """
    try:
        connections_dir = Path.home() / ".dbtools" / "connections"
        connection_file = connections_dir / f"{connection_name}.json"

        if connection_file.exists():
            connection_file.unlink()
            logger.info(f"SQLcl named connection '{connection_name}' deleted")
            return True
        else:
            logger.warning(f"SQLcl named connection '{connection_name}' not found")
            return False

    except Exception as e:
        logger.error(f"Error deleting SQLcl named connection '{connection_name}': {e}")
        return False


def list_sqlcl_named_connections() -> list[str]:
    """List all named connections in SQLcl.

    Returns:
        List of connection names

    Example:
        >>> connections = list_sqlcl_named_connections()
        >>> print(f"Found {len(connections)} connections")
    """
    try:
        connections_dir = Path.home() / ".dbtools" / "connections"

        if not connections_dir.exists():
            return []

        # List all .json files in the connections directory
        connection_files = connections_dir.glob("*.json")
        return [f.stem for f in connection_files]

    except Exception as e:
        logger.error(f"Error listing SQLcl named connections: {e}")
        return []
