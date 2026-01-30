"""Tests for SQLcl installation validator."""

import platform
from unittest.mock import patch

import pytest

from offline_chat.sqlcl_validator import (
    get_installation_instructions,
    get_sqlcl_status,
    get_sqlcl_version,
    is_sqlcl_installed,
    validate_sqlcl_or_raise,
)


class TestSQLclValidator:
    """Test SQLcl installation validation."""

    @patch("offline_chat.sqlcl_validator.shutil.which")
    def test_is_sqlcl_installed_true(self, mock_which):
        """Test detection when SQLcl is installed."""
        mock_which.return_value = "/usr/local/bin/sql"
        assert is_sqlcl_installed() is True
        mock_which.assert_called_once_with("sql")

    @patch("offline_chat.sqlcl_validator.shutil.which")
    def test_is_sqlcl_installed_false(self, mock_which):
        """Test detection when SQLcl is not installed."""
        mock_which.return_value = None
        assert is_sqlcl_installed() is False
        mock_which.assert_called_once_with("sql")

    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_version_not_installed(self, mock_installed):
        """Test version check when SQLcl is not installed."""
        mock_installed.return_value = False
        assert get_sqlcl_version() is None

    @patch("offline_chat.sqlcl_validator.subprocess.run")
    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_version_success(self, mock_installed, mock_run):
        """Test version extraction from SQLcl output."""
        mock_installed.return_value = True
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "SQLcl: Release 25.2 Production"

        version = get_sqlcl_version()
        assert version == "25.2"

    @patch("offline_chat.sqlcl_validator.subprocess.run")
    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_version_timeout(self, mock_installed, mock_run):
        """Test version check with timeout."""
        mock_installed.return_value = True
        mock_run.side_effect = Exception("Timeout")

        version = get_sqlcl_version()
        assert version is None

    @patch("offline_chat.sqlcl_validator.platform.system")
    def test_get_installation_instructions_macos(self, mock_system):
        """Test installation instructions for macOS."""
        mock_system.return_value = "Darwin"

        platform_name, instructions = get_installation_instructions()

        assert platform_name == "macOS"
        assert "brew install sqlcl" in instructions
        assert "Homebrew" in instructions

    @patch("offline_chat.sqlcl_validator.platform.system")
    def test_get_installation_instructions_linux(self, mock_system):
        """Test installation instructions for Linux."""
        mock_system.return_value = "Linux"

        platform_name, instructions = get_installation_instructions()

        assert platform_name == "Linux"
        assert "brew install sqlcl" in instructions or "apt-get" in instructions

    @patch("offline_chat.sqlcl_validator.platform.system")
    def test_get_installation_instructions_windows(self, mock_system):
        """Test installation instructions for Windows."""
        mock_system.return_value = "Windows"

        platform_name, instructions = get_installation_instructions()

        assert platform_name == "Windows"
        assert "PATH" in instructions
        assert "oracle.com" in instructions

    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_validate_sqlcl_or_raise_success(self, mock_installed):
        """Test validation passes when SQLcl is installed."""
        mock_installed.return_value = True

        # Should not raise
        validate_sqlcl_or_raise()

    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_validate_sqlcl_or_raise_failure(self, mock_installed):
        """Test validation raises when SQLcl is not installed."""
        mock_installed.return_value = False

        with pytest.raises(RuntimeError) as exc_info:
            validate_sqlcl_or_raise()

        error_msg = str(exc_info.value)
        assert "SQLcl is not installed" in error_msg
        assert "Oracle database connections require SQLcl" in error_msg

    @patch("offline_chat.sqlcl_validator.get_sqlcl_version")
    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_status_installed_with_version(self, mock_installed, mock_version):
        """Test status message when SQLcl is installed with version."""
        mock_installed.return_value = True
        mock_version.return_value = "25.2"

        status = get_sqlcl_status()
        assert "✓ SQLcl is installed" in status
        assert "25.2" in status

    @patch("offline_chat.sqlcl_validator.get_sqlcl_version")
    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_status_installed_no_version(self, mock_installed, mock_version):
        """Test status message when SQLcl is installed but version unknown."""
        mock_installed.return_value = True
        mock_version.return_value = None

        status = get_sqlcl_status()
        assert "✓ SQLcl is installed" in status

    @patch("offline_chat.sqlcl_validator.is_sqlcl_installed")
    def test_get_sqlcl_status_not_installed(self, mock_installed):
        """Test status message when SQLcl is not installed."""
        mock_installed.return_value = False

        status = get_sqlcl_status()
        assert "✗ SQLcl is not installed" in status
