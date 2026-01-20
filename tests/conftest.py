"""Shared pytest fixtures for Offline Chat tests."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_agents_dir(temp_data_dir: Path):
    """Create a temporary agents directory."""
    agents_dir = temp_data_dir / "agents"
    agents_dir.mkdir(parents=True)
    return agents_dir


@pytest.fixture
def temp_history_dir(temp_data_dir: Path):
    """Create a temporary history directory."""
    history_dir = temp_data_dir / "history"
    history_dir.mkdir(parents=True)
    return history_dir


@pytest.fixture(autouse=True)
def mock_getpass_globally():
    """Automatically mock getpass for all tests to prevent password prompts.
    
    This fixture patches getpass at the module level where it's imported.
    Tests with explicit @patch decorators will override this default.
    """
    with patch('offline_chat.database_menu.getpass', return_value='test_password'), \
         patch('offline_chat.database_config_cli.getpass', return_value='test_password'):
        yield
