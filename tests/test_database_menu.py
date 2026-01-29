"""Unit tests for database connection CLI menu.

This module tests the interactive CLI functions for database connection
management, including menu navigation, input validation, and error handling.
"""

from unittest.mock import patch

import pytest

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import is_err, is_ok, unwrap
from offline_chat.database_menu import (
    _configure_mysql_connection,
    _configure_oracle_connection,
    _configure_postgresql_connection,
    _configure_sqlite_connection,
    _select_connection,
    _select_database_type,
    create_connection_flow,
    delete_connection_flow,
    list_connections_display,
    show_database_menu,
    update_connection_flow,
)


def _get_printed_text(mock_print):
    """Helper to extract printed text from mock_print.call_args_list.

    Handles both print(text) and print() calls (empty print for newlines).
    """
    return "".join(str(call[0][0]) if call[0] else "" for call in mock_print.call_args_list)


@pytest.fixture
def mock_manager(tmp_path):
    """Create a mock DatabaseConnectionManager for testing."""
    store_path = tmp_path / "connections.json"
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    return DatabaseConnectionManager(store_path=store_path, agents_dir=agents_dir)


@pytest.fixture
def sample_oracle_connection():
    """Create a sample Oracle connection for testing."""
    return DatabaseConnection(
        name="test-oracle",
        database_type="oracle",
        host="localhost",
        port=1521,
        service_name="TESTDB",
        username="testuser",
        password="testpass",
    )


@pytest.fixture
def sample_postgres_connection():
    """Create a sample PostgreSQL connection for testing."""
    return DatabaseConnection(
        name="test-postgres",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )


class TestShowDatabaseMenu:
    """Tests for show_database_menu function."""

    @patch("builtins.input", side_effect=["5"])
    @patch("builtins.print")
    def test_menu_displays_options(self, mock_print, mock_input, mock_manager):
        """Test that menu displays all options correctly."""
        show_database_menu(mock_manager)

        # Check that menu options were printed
        # Handle both print(text) and print() calls
        printed_text = "".join(str(call[0][0]) if call[0] else "" for call in mock_print.call_args_list)
        assert "Database Connection Management" in printed_text
        assert "Create connection" in printed_text
        assert "List connections" in printed_text
        assert "Update connection" in printed_text
        assert "Delete connection" in printed_text
        assert "Back to main menu" in printed_text

    @patch("builtins.input", side_effect=["1", "5"])
    @patch("offline_chat.database_menu.create_connection_flow")
    def test_menu_calls_create_flow(self, mock_create, mock_input, mock_manager):
        """Test that selecting option 1 calls create_connection_flow."""
        show_database_menu(mock_manager)
        mock_create.assert_called_once_with(mock_manager)

    @patch("builtins.input", side_effect=["2", "5"])
    @patch("offline_chat.database_menu.list_connections_display")
    def test_menu_calls_list_display(self, mock_list, mock_input, mock_manager):
        """Test that selecting option 2 calls list_connections_display."""
        show_database_menu(mock_manager)
        mock_list.assert_called_once_with(mock_manager)

    @patch("builtins.input", side_effect=["3", "5"])
    @patch("offline_chat.database_menu.update_connection_flow")
    def test_menu_calls_update_flow(self, mock_update, mock_input, mock_manager):
        """Test that selecting option 3 calls update_connection_flow."""
        show_database_menu(mock_manager)
        mock_update.assert_called_once_with(mock_manager)

    @patch("builtins.input", side_effect=["4", "5"])
    @patch("offline_chat.database_menu.delete_connection_flow")
    def test_menu_calls_delete_flow(self, mock_delete, mock_input, mock_manager):
        """Test that selecting option 4 calls delete_connection_flow."""
        show_database_menu(mock_manager)
        mock_delete.assert_called_once_with(mock_manager)

    @patch("builtins.input", side_effect=["99", "5"])
    @patch("builtins.print")
    def test_menu_handles_invalid_option(self, mock_print, mock_input, mock_manager):
        """Test that invalid menu option shows error message."""
        show_database_menu(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "Invalid option" in printed_text

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("builtins.print")
    def test_menu_handles_keyboard_interrupt(self, mock_print, mock_input, mock_manager):
        """Test that Ctrl+C exits gracefully."""
        show_database_menu(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "Returning to main menu" in printed_text


class TestCreateConnectionFlow:
    """Tests for create_connection_flow function."""

    @patch("builtins.input", side_effect=[""])
    @patch("builtins.print")
    def test_create_requires_name(self, mock_print, mock_input, mock_manager):
        """Test that empty connection name shows error."""
        create_connection_flow(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "Connection name is required" in printed_text

    @patch("builtins.input", side_effect=["test-conn", "1", "localhost", "1521", "TESTDB", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    @patch("builtins.print")
    def test_create_oracle_connection_success(self, mock_print, mock_getpass, mock_input, mock_manager):
        """Test successful Oracle connection creation."""
        create_connection_flow(mock_manager)

        # Verify connection was created
        result = mock_manager.get_connection("test-conn")
        assert is_ok(result)
        conn = unwrap(result)
        assert conn.name == "test-conn"
        assert conn.database_type == "oracle"
        assert conn.host == "localhost"
        assert conn.port == 1521

        printed_text = _get_printed_text(mock_print)
        assert "created successfully" in printed_text

    @patch("builtins.input", side_effect=["test-conn", "0"])
    @patch("builtins.print")
    def test_create_cancelled(self, mock_print, mock_input, mock_manager):
        """Test that selecting cancel stops creation."""
        create_connection_flow(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "cancelled" in printed_text

    @patch("builtins.input", side_effect=["test-conn", "1", "localhost", "1521", "TESTDB", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    def test_create_duplicate_name_fails(self, mock_getpass, mock_input, mock_manager):
        """Test that duplicate connection name shows error."""
        # Create first connection
        create_connection_flow(mock_manager)

        # Try to create duplicate
        with patch("builtins.input", side_effect=["test-conn", "1", "localhost", "1521", "TESTDB", "user"]):
            with patch("offline_chat.database_menu.getpass", return_value="pass"):
                with patch("builtins.print") as mock_print:
                    create_connection_flow(mock_manager)

                    printed_text = _get_printed_text(mock_print)
                    assert "already exists" in printed_text

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("builtins.print")
    def test_create_handles_keyboard_interrupt(self, mock_print, mock_input, mock_manager):
        """Test that Ctrl+C during creation shows cancellation message."""
        create_connection_flow(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "cancelled" in printed_text


class TestListConnectionsDisplay:
    """Tests for list_connections_display function."""

    @patch("builtins.print")
    def test_list_empty_connections(self, mock_print, mock_manager):
        """Test listing when no connections exist."""
        list_connections_display(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "No connections available" in printed_text

    @patch("builtins.print")
    def test_list_displays_oracle_connection(self, mock_print, mock_manager, sample_oracle_connection):
        """Test that Oracle connection details are displayed correctly."""
        mock_manager.create_connection(sample_oracle_connection)

        list_connections_display(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "test-oracle" in printed_text
        assert "oracle" in printed_text
        assert "localhost:1521" in printed_text
        assert "TESTDB" in printed_text
        assert "testuser" in printed_text
        assert "****" in printed_text  # Password masked
        assert "testpass" not in printed_text  # Password not shown

    @patch("builtins.print")
    def test_list_displays_postgres_connection(self, mock_print, mock_manager, sample_postgres_connection):
        """Test that PostgreSQL connection details are displayed correctly."""
        mock_manager.create_connection(sample_postgres_connection)

        list_connections_display(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "test-postgres" in printed_text
        assert "postgresql" in printed_text
        assert "localhost:5432" in printed_text
        assert "testdb" in printed_text
        assert "testuser" in printed_text
        assert "****" in printed_text

    @patch("builtins.print")
    def test_list_shows_agents_using_connection(self, mock_print, mock_manager, sample_oracle_connection, tmp_path):
        """Test that agents using connection are displayed."""
        # Create connection
        mock_manager.create_connection(sample_oracle_connection)

        # Create agent that uses this connection
        agent_dir = mock_manager.agents_dir / "test-agent"
        agent_dir.mkdir()
        config_path = agent_dir / "config.json"

        import json

        config = {
            "name": "test-agent",
            "connection_assignments": [{"connection_name": "test-oracle", "access_level": "read-only"}],
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        list_connections_display(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "test-agent" in printed_text

    @patch("builtins.print")
    def test_list_masks_additional_params_sensitive_fields(self, mock_print, mock_manager):
        """Test that sensitive fields in additional_params are masked."""
        # Create connection with sensitive additional_params
        conn = DatabaseConnection(
            name="test-conn",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            additional_params={
                "api_key": "secret123",
                "db_token": "token456",
                "connection_timeout": "30",
                "ssl_password": "sslpass789",
            },
        )
        mock_manager.create_connection(conn)

        list_connections_display(mock_manager)

        printed_text = _get_printed_text(mock_print)

        # Check that connection is displayed
        assert "test-conn" in printed_text
        assert "postgresql" in printed_text

        # Check that additional params section is shown
        assert "Additional parameters" in printed_text

        # Check that sensitive fields are masked
        assert "api_key: ********" in printed_text
        assert "db_token: ********" in printed_text
        assert "ssl_password: ********" in printed_text

        # Check that non-sensitive fields are shown
        assert "connection_timeout: 30" in printed_text

        # Check that actual sensitive values are NOT shown
        assert "secret123" not in printed_text
        assert "token456" not in printed_text
        assert "sslpass789" not in printed_text


class TestUpdateConnectionFlow:
    """Tests for update_connection_flow function."""

    @patch("builtins.input", side_effect=["0"])
    @patch("builtins.print")
    def test_update_cancelled(self, mock_print, mock_input, mock_manager):
        """Test that selecting cancel stops update."""
        update_connection_flow(mock_manager)

        # Should not crash, just return
        assert True

    @patch("builtins.input", side_effect=["1", "newhost", "", "", "", "n"])
    @patch("builtins.print")
    def test_update_oracle_host(self, mock_print, mock_input, mock_manager, sample_oracle_connection):
        """Test updating Oracle connection host."""
        # Create connection first
        mock_manager.create_connection(sample_oracle_connection)

        update_connection_flow(mock_manager)

        # Verify update
        result = mock_manager.get_connection("test-oracle")
        assert is_ok(result)
        conn = unwrap(result)
        assert conn.host == "newhost"

        printed_text = _get_printed_text(mock_print)
        assert "updated successfully" in printed_text

    @patch("builtins.input", side_effect=["1", "", "", "", "", "y"])
    @patch("offline_chat.database_menu.getpass", return_value="newpass")
    @patch("builtins.print")
    def test_update_password(self, mock_print, mock_getpass, mock_input, mock_manager, sample_oracle_connection):
        """Test updating connection password."""
        mock_manager.create_connection(sample_oracle_connection)

        update_connection_flow(mock_manager)

        result = mock_manager.get_connection("test-oracle")
        assert is_ok(result)
        conn = unwrap(result)
        assert conn.password == "newpass"

    @patch("builtins.input", side_effect=["1", "", "", "", "", "n"])
    @patch("builtins.print")
    def test_update_no_changes(self, mock_print, mock_input, mock_manager, sample_oracle_connection):
        """Test update with no changes shows message."""
        mock_manager.create_connection(sample_oracle_connection)

        update_connection_flow(mock_manager)

        printed_text = _get_printed_text(mock_print)
        assert "No changes made" in printed_text


class TestDeleteConnectionFlow:
    """Tests for delete_connection_flow function."""

    @patch("builtins.input", side_effect=["0"])
    @patch("builtins.print")
    def test_delete_cancelled(self, mock_print, mock_input, mock_manager):
        """Test that selecting cancel stops deletion."""
        delete_connection_flow(mock_manager)
        assert True

    @patch("builtins.input", side_effect=["1", "y"])
    @patch("builtins.print")
    def test_delete_connection_success(self, mock_print, mock_input, mock_manager, sample_oracle_connection):
        """Test successful connection deletion."""
        mock_manager.create_connection(sample_oracle_connection)

        delete_connection_flow(mock_manager)

        # Verify deletion
        result = mock_manager.get_connection("test-oracle")
        assert is_err(result)

        printed_text = _get_printed_text(mock_print)
        assert "deleted successfully" in printed_text

    @patch("builtins.input", side_effect=["1", "n"])
    @patch("builtins.print")
    def test_delete_confirmation_declined(self, mock_print, mock_input, mock_manager, sample_oracle_connection):
        """Test that declining confirmation preserves connection."""
        mock_manager.create_connection(sample_oracle_connection)

        delete_connection_flow(mock_manager)

        # Verify connection still exists
        result = mock_manager.get_connection("test-oracle")
        assert is_ok(result)

        printed_text = _get_printed_text(mock_print)
        assert "cancelled" in printed_text

    @patch("builtins.input", side_effect=["1"])
    @patch("builtins.print")
    def test_delete_connection_in_use(self, mock_print, mock_input, mock_manager, sample_oracle_connection):
        """Test that connection in use cannot be deleted."""
        mock_manager.create_connection(sample_oracle_connection)

        # Create agent that uses this connection
        agent_dir = mock_manager.agents_dir / "test-agent"
        agent_dir.mkdir()
        config_path = agent_dir / "config.json"

        import json

        config = {
            "name": "test-agent",
            "connection_assignments": [{"connection_name": "test-oracle", "access_level": "read-only"}],
        }
        with open(config_path, "w") as f:
            json.dump(config, f)

        delete_connection_flow(mock_manager)

        # Verify connection still exists
        result = mock_manager.get_connection("test-oracle")
        assert is_ok(result)

        printed_text = _get_printed_text(mock_print)
        assert "Cannot delete" in printed_text
        assert "test-agent" in printed_text


class TestSelectDatabaseType:
    """Tests for _select_database_type helper function."""

    @patch("builtins.input", return_value="1")
    def test_select_oracle(self, mock_input):
        """Test selecting Oracle database type."""
        result = _select_database_type()
        assert result == "oracle"

    @patch("builtins.input", return_value="2")
    def test_select_postgresql(self, mock_input):
        """Test selecting PostgreSQL database type."""
        result = _select_database_type()
        assert result == "postgresql"

    @patch("builtins.input", return_value="3")
    def test_select_mysql(self, mock_input):
        """Test selecting MySQL database type."""
        result = _select_database_type()
        assert result == "mysql"

    @patch("builtins.input", return_value="4")
    def test_select_sqlite(self, mock_input):
        """Test selecting SQLite database type."""
        result = _select_database_type()
        assert result == "sqlite"

    @patch("builtins.input", return_value="0")
    def test_select_cancel(self, mock_input):
        """Test cancelling database type selection."""
        result = _select_database_type()
        assert result is None

    @patch("builtins.input", return_value="99")
    @patch("builtins.print")
    def test_select_invalid_option(self, mock_print, mock_input):
        """Test invalid option returns None."""
        result = _select_database_type()
        assert result is None


class TestSelectConnection:
    """Tests for _select_connection helper function."""

    @patch("builtins.input", return_value="0")
    @patch("builtins.print")
    def test_select_cancel(self, mock_print, mock_input, mock_manager):
        """Test cancelling connection selection."""
        result = _select_connection(mock_manager)
        assert result is None

    @patch("builtins.input", return_value="1")
    def test_select_first_connection(self, mock_input, mock_manager, sample_oracle_connection):
        """Test selecting first connection from list."""
        mock_manager.create_connection(sample_oracle_connection)

        result = _select_connection(mock_manager)
        assert result is not None
        assert result.name == "test-oracle"

    @patch("builtins.print")
    def test_select_no_connections(self, mock_print, mock_manager):
        """Test selecting when no connections exist."""
        result = _select_connection(mock_manager)
        assert result is None

        printed_text = _get_printed_text(mock_print)
        assert "No connections available" in printed_text


class TestConfigureConnections:
    """Tests for connection configuration helper functions."""

    @patch("builtins.input", side_effect=["localhost", "1521", "TESTDB", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    def test_configure_oracle_connection(self, mock_getpass, mock_input):
        """Test Oracle connection configuration."""
        conn = _configure_oracle_connection("test-oracle")

        assert conn is not None
        assert conn.name == "test-oracle"
        assert conn.database_type == "oracle"
        assert conn.host == "localhost"
        assert conn.port == 1521
        assert conn.service_name == "TESTDB"
        assert conn.username == "user"
        assert conn.password == "pass"

    @patch("builtins.input", side_effect=["localhost", "5432", "testdb", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    def test_configure_postgresql_connection(self, mock_getpass, mock_input):
        """Test PostgreSQL connection configuration."""
        conn = _configure_postgresql_connection("test-postgres")

        assert conn is not None
        assert conn.name == "test-postgres"
        assert conn.database_type == "postgresql"
        assert conn.host == "localhost"
        assert conn.port == 5432
        assert conn.database == "testdb"
        assert conn.username == "user"
        assert conn.password == "pass"

    @patch("builtins.input", side_effect=["localhost", "3306", "testdb", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    def test_configure_mysql_connection(self, mock_getpass, mock_input):
        """Test MySQL connection configuration."""
        conn = _configure_mysql_connection("test-mysql")

        assert conn is not None
        assert conn.name == "test-mysql"
        assert conn.database_type == "mysql"
        assert conn.host == "localhost"
        assert conn.port == 3306
        assert conn.database == "testdb"
        assert conn.username == "user"
        assert conn.password == "pass"

    @patch("builtins.input", return_value="/path/to/db.sqlite")
    def test_configure_sqlite_connection(self, mock_input):
        """Test SQLite connection configuration."""
        conn = _configure_sqlite_connection("test-sqlite")

        assert conn is not None
        assert conn.name == "test-sqlite"
        assert conn.database_type == "sqlite"
        assert conn.file_path == "/path/to/db.sqlite"

    @patch("builtins.input", side_effect=["", "", "", ""])
    @patch("offline_chat.database_menu.getpass", return_value="")
    @patch("builtins.print")
    def test_configure_oracle_missing_required_fields(self, mock_print, mock_getpass, mock_input):
        """Test that missing required fields returns None."""
        conn = _configure_oracle_connection("test-oracle")
        assert conn is None

    @patch("builtins.input", side_effect=["localhost", "invalid", "TESTDB", "user"])
    @patch("offline_chat.database_menu.getpass", return_value="pass")
    @patch("builtins.print")
    def test_configure_oracle_invalid_port(self, mock_print, mock_getpass, mock_input):
        """Test that invalid port number returns None."""
        conn = _configure_oracle_connection("test-oracle")
        assert conn is None
