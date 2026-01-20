"""Tests for CLI module.

This module contains property-based tests and unit tests for the CLI class
and message formatting functions.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.cli import format_agent_message, format_user_message


# Strategy for generating non-empty message content
def message_content_strategy():
    """Generate non-empty message content strings."""
    return st.text(min_size=1, max_size=500).filter(lambda s: s.strip())


# Strategy for generating agent display names
def display_name_strategy():
    """Generate valid agent display names."""
    return st.text(min_size=1, max_size=50).filter(lambda s: s.strip())


class TestMessageDisplayFormatting:
    """Property 9: Message Display Formatting.

    Feature: offline-chat, Property 9: Message Display Formatting
    Validates: Requirements 6.3, 6.4

    For any message to be displayed, user messages SHALL be prefixed with "You:"
    and assistant messages SHALL be prefixed with the agent's display name
    followed by ":".
    """

    @settings(max_examples=100)
    @given(content=message_content_strategy())
    def test_user_message_prefixed_with_you(self, content: str):
        """User messages should be prefixed with 'You:'."""
        formatted = format_user_message(content)
        assert formatted.startswith("You: ")
        assert content in formatted

    @settings(max_examples=100)
    @given(display_name=display_name_strategy(), content=message_content_strategy())
    def test_agent_message_prefixed_with_display_name(self, display_name: str, content: str):
        """Agent messages should be prefixed with the agent's display name and ':'."""
        formatted = format_agent_message(display_name, content)
        assert formatted.startswith(f"{display_name}: ")
        assert content in formatted

    @settings(max_examples=100)
    @given(content=message_content_strategy())
    def test_user_message_contains_original_content(self, content: str):
        """Formatted user message should contain the original content."""
        formatted = format_user_message(content)
        # Extract content after "You: "
        extracted = formatted[5:]  # len("You: ") == 5
        assert extracted == content

    @settings(max_examples=100)
    @given(display_name=display_name_strategy(), content=message_content_strategy())
    def test_agent_message_contains_original_content(self, display_name: str, content: str):
        """Formatted agent message should contain the original content."""
        formatted = format_agent_message(display_name, content)
        # Extract content after "{display_name}: "
        prefix_len = len(display_name) + 2  # +2 for ": "
        extracted = formatted[prefix_len:]
        assert extracted == content

    def test_specific_user_message_example(self):
        """Unit test for specific user message formatting."""
        content = "How do I say hello in German?"
        formatted = format_user_message(content)
        assert formatted == "You: How do I say hello in German?"

    def test_specific_agent_message_example(self):
        """Unit test for specific agent message formatting."""
        display_name = "German Language Tutor"
        content = "In German, you say 'Hallo' for a casual greeting."
        formatted = format_agent_message(display_name, content)
        expected = "German Language Tutor: In German, you say 'Hallo' for a casual greeting."
        assert formatted == expected

    def test_empty_content_user_message(self):
        """User message with empty content should still have prefix."""
        formatted = format_user_message("")
        assert formatted == "You: "

    def test_empty_content_agent_message(self):
        """Agent message with empty content should still have prefix."""
        formatted = format_agent_message("Test Agent", "")
        assert formatted == "Test Agent: "


class TestCLIMigrationCheck:
    """Tests for CLI migration check on startup.
    
    Validates: Requirements 9.1
    """
    
    def test_migration_check_called_on_startup(self, tmp_path, monkeypatch):
        """Test that migration check is called when CLI starts."""
        from unittest.mock import Mock, patch, MagicMock
        from offline_chat.cli import CLI
        from offline_chat.manager import AgentManager
        from offline_chat.database.manager import DatabaseConnectionManager
        
        # Create a mock manager with migrate_inline_configs method
        mock_manager = MagicMock(spec=AgentManager)
        mock_manager.migrate_inline_configs.return_value = {}
        mock_manager.history_store = MagicMock()
        
        # Create CLI with mock manager
        cli = CLI(manager=mock_manager)
        
        # Mock the display_menu to exit immediately
        with patch.object(cli, 'display_menu', side_effect=KeyboardInterrupt):
            try:
                cli.run()
            except KeyboardInterrupt:
                pass
        
        # Verify migration check was called
        mock_manager.migrate_inline_configs.assert_called_once()
    
    def test_migration_check_displays_results(self, tmp_path, monkeypatch, capsys):
        """Test that migration results are displayed to user."""
        from unittest.mock import MagicMock, patch
        from offline_chat.cli import CLI
        from offline_chat.manager import AgentManager
        
        # Create a mock manager that returns migration results
        mock_manager = MagicMock(spec=AgentManager)
        mock_manager.migrate_inline_configs.return_value = {
            'test-agent': 'test-agent-oracle',
            'another-agent': 'another-agent-postgresql'
        }
        mock_manager.history_store = MagicMock()
        
        # Create CLI with mock manager
        cli = CLI(manager=mock_manager)
        
        # Mock the display_menu to exit immediately
        with patch.object(cli, 'display_menu', side_effect=KeyboardInterrupt):
            try:
                cli.run()
            except KeyboardInterrupt:
                pass
        
        # Capture output
        captured = capsys.readouterr()
        
        # Verify migration results are displayed
        assert "Database Configuration Migration" in captured.out
        assert "Migrated 2 agent(s)" in captured.out
        assert "test-agent -> test-agent-oracle" in captured.out
        assert "another-agent -> another-agent-postgresql" in captured.out
        assert "centralized connection management system" in captured.out
    
    def test_migration_check_no_results(self, tmp_path, monkeypatch, capsys):
        """Test that no output is shown when no agents need migration."""
        from unittest.mock import MagicMock, patch
        from offline_chat.cli import CLI
        from offline_chat.manager import AgentManager
        
        # Create a mock manager that returns empty results
        mock_manager = MagicMock(spec=AgentManager)
        mock_manager.migrate_inline_configs.return_value = {}
        mock_manager.history_store = MagicMock()
        
        # Create CLI with mock manager
        cli = CLI(manager=mock_manager)
        
        # Mock the display_menu to exit immediately
        with patch.object(cli, 'display_menu', side_effect=KeyboardInterrupt):
            try:
                cli.run()
            except KeyboardInterrupt:
                pass
        
        # Capture output
        captured = capsys.readouterr()
        
        # Verify no migration message is displayed
        assert "Database Configuration Migration" not in captured.out
        assert "Migrated" not in captured.out or "Migrated 0" not in captured.out
    
    def test_migration_check_handles_errors_gracefully(self, tmp_path, monkeypatch, capsys):
        """Test that migration errors don't prevent app startup."""
        from unittest.mock import MagicMock, patch
        from offline_chat.cli import CLI
        from offline_chat.manager import AgentManager
        
        # Create a mock manager that raises an error
        mock_manager = MagicMock(spec=AgentManager)
        mock_manager.migrate_inline_configs.side_effect = Exception("Test migration error")
        mock_manager.history_store = MagicMock()
        
        # Create CLI with mock manager
        cli = CLI(manager=mock_manager)
        
        # Mock the display_menu to exit immediately
        with patch.object(cli, 'display_menu', side_effect=KeyboardInterrupt):
            try:
                cli.run()
            except KeyboardInterrupt:
                pass
        
        # Capture output
        captured = capsys.readouterr()
        
        # Verify error is displayed but app continues
        assert "Warning: Error during database configuration migration" in captured.out
        assert "Test migration error" in captured.out
        assert "application will continue normally" in captured.out
