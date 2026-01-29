"""Unit tests for guidelines management CLI module."""

from unittest.mock import Mock, patch

import pytest

from cli.guidelines_menu import (
    add_guideline_flow,
    delete_guideline_flow,
    edit_guideline_flow,
    list_guidelines_display,
    show_guidelines_menu,
)
from offline_chat.database.result import Err, Ok
from offline_chat.manager import AgentManager


@pytest.fixture
def mock_agent_manager():
    """Create a mock AgentManager."""
    manager = Mock(spec=AgentManager)
    return manager


class TestShowGuidelinesMenu:
    """Tests for show_guidelines_menu function."""

    def test_menu_display(self, mock_agent_manager, capsys):
        """Test that menu displays all options correctly."""
        with patch("builtins.input", return_value="5"):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Manage Guidelines: test-agent" in captured.out
        assert "1. Add guideline" in captured.out
        assert "2. Edit guideline" in captured.out
        assert "3. Delete guideline" in captured.out
        assert "4. List guidelines" in captured.out
        assert "5. Back" in captured.out

    def test_select_add_guideline(self, mock_agent_manager):
        """Test selecting add guideline option."""
        mock_agent_manager.add_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["1", "Test guideline", "5"]):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        mock_agent_manager.add_guideline.assert_called_once_with("test-agent", "Test guideline")

    def test_select_edit_guideline(self, mock_agent_manager):
        """Test selecting edit guideline option."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])
        mock_agent_manager.edit_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["2", "1", "Updated guideline", "5"]):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        mock_agent_manager.edit_guideline.assert_called_once_with("test-agent", 0, "Updated guideline")

    def test_select_delete_guideline(self, mock_agent_manager):
        """Test selecting delete guideline option."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])
        mock_agent_manager.delete_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["3", "1", "y", "5"]):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        mock_agent_manager.delete_guideline.assert_called_once_with("test-agent", 0)

    def test_select_list_guidelines(self, mock_agent_manager):
        """Test selecting list guidelines option."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1", "Guideline 2"])

        with patch("builtins.input", side_effect=["4", "5"]):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        mock_agent_manager.list_guidelines.assert_called_once_with("test-agent")

    def test_select_back(self, mock_agent_manager):
        """Test selecting back option."""
        with patch("builtins.input", return_value="5"):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        # Should return without error

    def test_invalid_option(self, mock_agent_manager, capsys):
        """Test invalid menu option."""
        with patch("builtins.input", side_effect=["99", "5"]):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Invalid option" in captured.out

    def test_keyboard_interrupt(self, mock_agent_manager, capsys):
        """Test keyboard interrupt handling."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            show_guidelines_menu(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Returning to previous menu" in captured.out


class TestAddGuidelineFlow:
    """Tests for add_guideline_flow function."""

    def test_add_guideline_success(self, mock_agent_manager, capsys):
        """Test successfully adding a guideline."""
        mock_agent_manager.add_guideline.return_value = Ok(None)

        with patch("builtins.input", return_value="Always explain your queries"):
            add_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Add Guideline" in captured.out
        assert "Guideline added successfully" in captured.out

        mock_agent_manager.add_guideline.assert_called_once_with("test-agent", "Always explain your queries")

    def test_add_guideline_failure(self, mock_agent_manager, capsys):
        """Test handling guideline addition failure."""
        mock_agent_manager.add_guideline.return_value = Err("Agent not found")

        with patch("builtins.input", return_value="Test guideline"):
            add_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Agent not found" in captured.out

    def test_add_guideline_empty_input(self, mock_agent_manager, capsys):
        """Test cancelling with empty input."""
        with patch("builtins.input", return_value=""):
            add_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guideline addition cancelled" in captured.out

        mock_agent_manager.add_guideline.assert_not_called()

    def test_add_guideline_whitespace_only(self, mock_agent_manager, capsys):
        """Test cancelling with whitespace-only input."""
        with patch("builtins.input", return_value="   "):
            add_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guideline addition cancelled" in captured.out

        mock_agent_manager.add_guideline.assert_not_called()

    def test_add_guideline_keyboard_interrupt(self, mock_agent_manager, capsys):
        """Test keyboard interrupt handling."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            add_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guideline addition cancelled" in captured.out


class TestEditGuidelineFlow:
    """Tests for edit_guideline_flow function."""

    def test_edit_guideline_success(self, mock_agent_manager, capsys):
        """Test successfully editing a guideline."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1", "Guideline 2"])
        mock_agent_manager.edit_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["1", "Updated guideline"]):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Edit Guideline" in captured.out
        assert "Current Guidelines:" in captured.out
        assert "1. Guideline 1" in captured.out
        assert "2. Guideline 2" in captured.out
        assert "Current text: Guideline 1" in captured.out
        assert "Guideline updated successfully" in captured.out

        mock_agent_manager.edit_guideline.assert_called_once_with("test-agent", 0, "Updated guideline")

    def test_edit_guideline_failure(self, mock_agent_manager, capsys):
        """Test handling guideline edit failure."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])
        mock_agent_manager.edit_guideline.return_value = Err("Index out of range")

        with patch("builtins.input", side_effect=["1", "Updated guideline"]):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Index out of range" in captured.out

    def test_edit_guideline_no_guidelines(self, mock_agent_manager, capsys):
        """Test editing when no guidelines exist."""
        mock_agent_manager.list_guidelines.return_value = Ok([])

        edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "No guidelines to edit" in captured.out
        assert "Add some first" in captured.out

    def test_edit_guideline_cancel_selection(self, mock_agent_manager, capsys):
        """Test cancelling guideline selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="0"):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Edit cancelled" in captured.out

        mock_agent_manager.edit_guideline.assert_not_called()

    def test_edit_guideline_invalid_selection(self, mock_agent_manager, capsys):
        """Test invalid guideline selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="99"):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out

    def test_edit_guideline_cancel_text_entry(self, mock_agent_manager, capsys):
        """Test cancelling text entry."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", side_effect=["1", ""]):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Edit cancelled" in captured.out

        mock_agent_manager.edit_guideline.assert_not_called()

    def test_edit_guideline_non_numeric_input(self, mock_agent_manager, capsys):
        """Test non-numeric input for selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="abc"):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Invalid input" in captured.out

    def test_edit_guideline_list_error(self, mock_agent_manager, capsys):
        """Test handling error when listing guidelines."""
        mock_agent_manager.list_guidelines.return_value = Err("Agent not found")

        edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Agent not found" in captured.out

    def test_edit_guideline_keyboard_interrupt(self, mock_agent_manager, capsys):
        """Test keyboard interrupt handling."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            edit_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Edit cancelled" in captured.out


class TestDeleteGuidelineFlow:
    """Tests for delete_guideline_flow function."""

    def test_delete_guideline_success(self, mock_agent_manager, capsys):
        """Test successfully deleting a guideline."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1", "Guideline 2"])
        mock_agent_manager.delete_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["1", "y"]):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Delete Guideline" in captured.out
        assert "Current Guidelines:" in captured.out
        assert "1. Guideline 1" in captured.out
        assert "2. Guideline 2" in captured.out
        assert "Guideline deleted successfully" in captured.out

        mock_agent_manager.delete_guideline.assert_called_once_with("test-agent", 0)

    def test_delete_guideline_failure(self, mock_agent_manager, capsys):
        """Test handling guideline deletion failure."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])
        mock_agent_manager.delete_guideline.return_value = Err("Index out of range")

        with patch("builtins.input", side_effect=["1", "y"]):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Index out of range" in captured.out

    def test_delete_guideline_no_guidelines(self, mock_agent_manager, capsys):
        """Test deleting when no guidelines exist."""
        mock_agent_manager.list_guidelines.return_value = Ok([])

        delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "No guidelines to delete" in captured.out

    def test_delete_guideline_cancel_selection(self, mock_agent_manager, capsys):
        """Test cancelling guideline selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="0"):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Deletion cancelled" in captured.out

        mock_agent_manager.delete_guideline.assert_not_called()

    def test_delete_guideline_invalid_selection(self, mock_agent_manager, capsys):
        """Test invalid guideline selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="99"):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out

    def test_delete_guideline_cancel_confirmation(self, mock_agent_manager, capsys):
        """Test cancelling deletion confirmation."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", side_effect=["1", "n"]):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Deletion cancelled" in captured.out

        mock_agent_manager.delete_guideline.assert_not_called()

    def test_delete_guideline_confirmation_case_insensitive(self, mock_agent_manager, capsys):
        """Test that confirmation is case-insensitive."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])
        mock_agent_manager.delete_guideline.return_value = Ok(None)

        with patch("builtins.input", side_effect=["1", "Y"]):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guideline deleted successfully" in captured.out

        mock_agent_manager.delete_guideline.assert_called_once()

    def test_delete_guideline_non_numeric_input(self, mock_agent_manager, capsys):
        """Test non-numeric input for selection."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", return_value="abc"):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Invalid input" in captured.out

    def test_delete_guideline_list_error(self, mock_agent_manager, capsys):
        """Test handling error when listing guidelines."""
        mock_agent_manager.list_guidelines.return_value = Err("Agent not found")

        delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Agent not found" in captured.out

    def test_delete_guideline_keyboard_interrupt(self, mock_agent_manager, capsys):
        """Test keyboard interrupt handling."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Guideline 1"])

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            delete_guideline_flow(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Deletion cancelled" in captured.out


class TestListGuidelinesDisplay:
    """Tests for list_guidelines_display function."""

    def test_list_guidelines_success(self, mock_agent_manager, capsys):
        """Test successfully listing guidelines."""
        mock_agent_manager.list_guidelines.return_value = Ok(
            [
                "Always explain your SQL queries",
                "Never modify production data",
                "Provide data visualizations when appropriate",
            ]
        )

        list_guidelines_display(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guidelines for: test-agent" in captured.out
        assert "1. Always explain your SQL queries" in captured.out
        assert "2. Never modify production data" in captured.out
        assert "3. Provide data visualizations when appropriate" in captured.out
        assert "Total: 3 guideline(s)" in captured.out

    def test_list_guidelines_empty(self, mock_agent_manager, capsys):
        """Test listing when no guidelines exist."""
        mock_agent_manager.list_guidelines.return_value = Ok([])

        list_guidelines_display(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Guidelines for: test-agent" in captured.out
        assert "No guidelines defined for this agent" in captured.out

    def test_list_guidelines_single(self, mock_agent_manager, capsys):
        """Test listing a single guideline."""
        mock_agent_manager.list_guidelines.return_value = Ok(["Always explain your queries"])

        list_guidelines_display(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "1. Always explain your queries" in captured.out
        assert "Total: 1 guideline(s)" in captured.out

    def test_list_guidelines_error(self, mock_agent_manager, capsys):
        """Test handling error when listing guidelines."""
        mock_agent_manager.list_guidelines.return_value = Err("Agent not found")

        list_guidelines_display(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert "Error: Agent not found" in captured.out

    def test_list_guidelines_long_text(self, mock_agent_manager, capsys):
        """Test listing guidelines with long text."""
        long_guideline = "A" * 200  # Very long guideline
        mock_agent_manager.list_guidelines.return_value = Ok([long_guideline])

        list_guidelines_display(mock_agent_manager, "test-agent")

        captured = capsys.readouterr()
        assert long_guideline in captured.out
        assert "Total: 1 guideline(s)" in captured.out
