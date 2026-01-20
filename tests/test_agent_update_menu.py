"""Unit tests for agent update menu CLI module."""

import pytest
from unittest.mock import Mock, patch, call
from io import StringIO

from cli.agent_update_menu import (
    show_update_agent_menu,
    update_database_connections_flow,
    select_access_level,
    select_allowed_tables,
)
from offline_chat.agent import Agent
from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.result import Ok, Err
from offline_chat.manager import AgentManager
from offline_chat.database.manager import DatabaseConnectionManager


@pytest.fixture
def mock_agent_manager():
    """Create a mock AgentManager."""
    manager = Mock(spec=AgentManager)
    return manager


@pytest.fixture
def mock_db_manager():
    """Create a mock DatabaseConnectionManager."""
    manager = Mock(spec=DatabaseConnectionManager)
    return manager


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return Agent(
        name="test-agent",
        display_name="Test Agent",
        base_model="llama3:latest",
        system_prompt="You are a test agent.",
        connection_assignments=[
            AgentConnectionAssignment(
                connection_name="prod-db",
                access_level=AccessLevel.READ_ONLY,
                allowed_tables=None
            )
        ]
    )


@pytest.fixture
def sample_connections():
    """Create sample database connections."""
    return [
        DatabaseConnection(
            name="prod-db",
            database_type="postgresql",
            host="localhost",
            port=5432,
            database="prod",
            username="user",
            password="pass"
        ),
        DatabaseConnection(
            name="dev-db",
            database_type="mysql",
            host="localhost",
            port=3306,
            database="dev",
            username="user",
            password="pass"
        ),
    ]


class TestShowUpdateAgentMenu:
    """Tests for show_update_agent_menu function."""
    
    def test_no_agents_available(self, mock_agent_manager, mock_db_manager, capsys):
        """Test menu when no agents are available."""
        mock_agent_manager.list_agents.return_value = []
        
        with patch("builtins.input", return_value="0"):
            show_update_agent_menu(mock_agent_manager, mock_db_manager)
        
        captured = capsys.readouterr()
        assert "No agents available" in captured.out
        assert "Create one first" in captured.out
    
    def test_cancel_agent_selection(self, mock_agent_manager, mock_db_manager, sample_agent):
        """Test cancelling agent selection."""
        mock_agent_manager.list_agents.return_value = [sample_agent]
        
        with patch("builtins.input", return_value="0"):
            show_update_agent_menu(mock_agent_manager, mock_db_manager)
        
        # Should return without error
        mock_agent_manager.list_agents.assert_called_once()
    
    def test_invalid_agent_selection(self, mock_agent_manager, mock_db_manager, sample_agent, capsys):
        """Test invalid agent selection."""
        mock_agent_manager.list_agents.return_value = [sample_agent]
        
        with patch("builtins.input", side_effect=["99", "0"]):
            show_update_agent_menu(mock_agent_manager, mock_db_manager)
        
        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out
    
    def test_keyboard_interrupt(self, mock_agent_manager, mock_db_manager, sample_agent, capsys):
        """Test keyboard interrupt handling."""
        mock_agent_manager.list_agents.return_value = [sample_agent]
        
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            show_update_agent_menu(mock_agent_manager, mock_db_manager)
        
        captured = capsys.readouterr()
        assert "Returning to main menu" in captured.out


class TestUpdateDatabaseConnectionsFlow:
    """Tests for update_database_connections_flow function."""
    
    def test_display_current_connections(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test displaying currently assigned connections."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        
        with patch("builtins.input", return_value="b"):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Currently Assigned Connections:" in captured.out
        assert "prod-db" in captured.out
        assert "read-only" in captured.out
    
    def test_display_available_connections(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test displaying available connections."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        
        with patch("builtins.input", return_value="b"):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Available Connections:" in captured.out
        assert "dev-db" in captured.out
        assert "mysql" in captured.out
    
    def test_no_available_connections_to_add(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        capsys
    ):
        """Test when all connections are already assigned."""
        # Agent has prod-db assigned
        mock_agent_manager.get_agent.return_value = sample_agent
        # Only prod-db exists
        mock_db_manager.list_connections.return_value = [
            DatabaseConnection(
                name="prod-db",
                database_type="postgresql",
                host="localhost",
                port=5432,
                database="prod",
                username="user",
                password="pass"
            )
        ]
        
        with patch("builtins.input", side_effect=["a", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "No available connections to add" in captured.out
    
    def test_agent_not_found(self, mock_agent_manager, mock_db_manager, capsys):
        """Test when agent is not found."""
        mock_agent_manager.get_agent.return_value = None
        
        update_database_connections_flow(
            mock_agent_manager,
            mock_db_manager,
            "nonexistent-agent"
        )
        
        captured = capsys.readouterr()
        assert "Agent 'nonexistent-agent' not found" in captured.out


class TestSelectAccessLevel:
    """Tests for select_access_level function."""
    
    def test_select_read_only(self, capsys):
        """Test selecting read-only access level."""
        with patch("builtins.input", return_value="1"):
            result = select_access_level()
        
        assert result == AccessLevel.READ_ONLY
        captured = capsys.readouterr()
        assert "Select Access Level" in captured.out
        assert "read-only" in captured.out
    
    def test_select_read_write(self):
        """Test selecting read-write access level."""
        with patch("builtins.input", return_value="2"):
            result = select_access_level()
        
        assert result == AccessLevel.READ_WRITE
    
    def test_select_table_specific_read(self):
        """Test selecting table-specific-read access level."""
        with patch("builtins.input", return_value="3"):
            result = select_access_level()
        
        assert result == AccessLevel.TABLE_SPECIFIC_READ
    
    def test_select_table_specific_read_write(self):
        """Test selecting table-specific-read-write access level."""
        with patch("builtins.input", return_value="4"):
            result = select_access_level()
        
        assert result == AccessLevel.TABLE_SPECIFIC_READ_WRITE
    
    def test_cancel_selection(self):
        """Test cancelling access level selection."""
        with patch("builtins.input", return_value="0"):
            result = select_access_level()
        
        assert result is None
    
    def test_invalid_selection(self, capsys):
        """Test invalid access level selection."""
        with patch("builtins.input", return_value="99"):
            result = select_access_level()
        
        assert result is None
        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out


class TestSelectAllowedTables:
    """Tests for select_allowed_tables function."""
    
    def test_select_single_table(self, mock_db_manager, capsys):
        """Test selecting a single table."""
        with patch("builtins.input", return_value="users"):
            result = select_allowed_tables(mock_db_manager, "prod-db")
        
        assert result == ["users"]
        captured = capsys.readouterr()
        assert "Specify Allowed Tables" in captured.out
        assert "Allowed tables: users" in captured.out
    
    def test_select_multiple_tables(self, mock_db_manager, capsys):
        """Test selecting multiple tables."""
        with patch("builtins.input", return_value="users, orders, products"):
            result = select_allowed_tables(mock_db_manager, "prod-db")
        
        assert result == ["users", "orders", "products"]
        captured = capsys.readouterr()
        assert "Allowed tables: users, orders, products" in captured.out
    
    def test_empty_input(self, mock_db_manager, capsys):
        """Test empty table input."""
        with patch("builtins.input", return_value=""):
            result = select_allowed_tables(mock_db_manager, "prod-db")
        
        assert result is None
        captured = capsys.readouterr()
        assert "At least one table name is required" in captured.out
    
    def test_whitespace_handling(self, mock_db_manager):
        """Test that whitespace is properly trimmed."""
        with patch("builtins.input", return_value="  users  ,  orders  ,  products  "):
            result = select_allowed_tables(mock_db_manager, "prod-db")
        
        assert result == ["users", "orders", "products"]
    
    def test_keyboard_interrupt(self, mock_db_manager, capsys):
        """Test keyboard interrupt handling."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = select_allowed_tables(mock_db_manager, "prod-db")
        
        assert result is None
        captured = capsys.readouterr()
        assert "Table selection cancelled" in captured.out


class TestAddConnectionFlow:
    """Tests for adding connections through the flow."""
    
    def test_add_connection_with_read_only_access(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test adding a connection with read-only access."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        mock_agent_manager.assign_connection.return_value = Ok(None)
        
        # Select add (a), choose connection 2 (dev-db), select read-only (1), then back (b)
        with patch("builtins.input", side_effect=["a", "1", "1", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Connection 'dev-db' assigned successfully" in captured.out
        
        # Verify assign_connection was called correctly
        mock_agent_manager.assign_connection.assert_called_once_with(
            "test-agent",
            "dev-db",
            AccessLevel.READ_ONLY,
            None
        )
    
    def test_add_connection_with_table_specific_access(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test adding a connection with table-specific access."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        mock_agent_manager.assign_connection.return_value = Ok(None)
        
        # Select add (a), choose connection 1, select table-specific-read (3),
        # enter tables, then back (b)
        with patch("builtins.input", side_effect=["a", "1", "3", "users, orders", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Connection 'dev-db' assigned successfully" in captured.out
        assert "Allowed tables: users, orders" in captured.out
        
        # Verify assign_connection was called with allowed_tables
        mock_agent_manager.assign_connection.assert_called_once_with(
            "test-agent",
            "dev-db",
            AccessLevel.TABLE_SPECIFIC_READ,
            ["users", "orders"]
        )
    
    def test_add_connection_failure(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test handling connection assignment failure."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        mock_agent_manager.assign_connection.return_value = Err("Connection validation failed")
        
        with patch("builtins.input", side_effect=["a", "1", "1", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Error: Connection validation failed" in captured.out


class TestRemoveConnectionFlow:
    """Tests for removing connections through the flow."""
    
    def test_remove_connection_success(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test successfully removing a connection."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        mock_agent_manager.remove_connection.return_value = Ok(None)
        
        # Select remove (r), choose connection 1, confirm (y), then back (b)
        with patch("builtins.input", side_effect=["r", "1", "y", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Connection 'prod-db' removed successfully" in captured.out
        
        mock_agent_manager.remove_connection.assert_called_once_with(
            "test-agent",
            "prod-db"
        )
    
    def test_remove_connection_cancelled(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_agent,
        sample_connections,
        capsys
    ):
        """Test cancelling connection removal."""
        mock_agent_manager.get_agent.return_value = sample_agent
        mock_db_manager.list_connections.return_value = sample_connections
        
        # Select remove (r), choose connection 1, cancel (n), then back (b)
        with patch("builtins.input", side_effect=["r", "1", "n", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "Removal cancelled" in captured.out
        
        # Verify remove_connection was not called
        mock_agent_manager.remove_connection.assert_not_called()
    
    def test_no_connections_to_remove(
        self,
        mock_agent_manager,
        mock_db_manager,
        sample_connections,
        capsys
    ):
        """Test when agent has no connections to remove."""
        agent_no_connections = Agent(
            name="test-agent",
            display_name="Test Agent",
            base_model="llama3:latest",
            system_prompt="You are a test agent.",
            connection_assignments=[]
        )
        mock_agent_manager.get_agent.return_value = agent_no_connections
        mock_db_manager.list_connections.return_value = sample_connections
        
        # Try to remove (r), then back (b)
        with patch("builtins.input", side_effect=["r", "b"]):
            update_database_connections_flow(
                mock_agent_manager,
                mock_db_manager,
                "test-agent"
            )
        
        captured = capsys.readouterr()
        assert "No connections to remove" in captured.out
