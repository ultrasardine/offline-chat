"""Shared pytest fixtures for Offline Chat tests."""

import tempfile
from pathlib import Path

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
