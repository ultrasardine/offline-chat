"""Integration tests for secure file permissions.

This module tests the complete workflow of secure file permissions
for the database connection store.
"""

import os
import tempfile
from pathlib import Path

import pytest

from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.manager import DatabaseConnectionManager


class TestSecurePermissionsIntegration:
    """Integration tests for secure file permissions."""

    def test_complete_workflow_with_secure_permissions(self, capsys):
        """Test complete workflow: create store, verify permissions, warn on insecure."""
        if os.name == "nt":  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            # Step 1: Create manager - should set secure permissions
            manager = DatabaseConnectionManager(store_path)

            # Verify permissions are 600
            stat_info = os.stat(store_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600

            # Step 2: Create a connection - should preserve permissions
            conn = DatabaseConnection(name="test-conn", database_type="sqlite", file_path="/tmp/test.db")
            result = manager.create_connection(conn)
            from offline_chat.database.result import is_ok

            assert is_ok(result)

            # Verify permissions are still 600
            stat_info = os.stat(store_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600

            # Step 3: Manually set insecure permissions
            os.chmod(store_path, 0o644)

            # Step 4: Load store - should warn about insecure permissions
            capsys.readouterr()  # Clear previous output
            manager._load_store()

            captured = capsys.readouterr()
            assert "WARNING" in captured.out
            assert "insecure permissions" in captured.out

            # Step 5: Save store - should restore secure permissions
            data = manager._load_store()
            manager._save_store(data)

            # Verify permissions are back to 600
            stat_info = os.stat(store_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600

    def test_permissions_maintained_across_operations(self):
        """Test that permissions remain secure across multiple operations."""
        if os.name == "nt":  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)

            # Create multiple connections
            connections = [
                DatabaseConnection(name=f"conn-{i}", database_type="sqlite", file_path=f"/tmp/test{i}.db")
                for i in range(5)
            ]

            for conn in connections:
                manager.create_connection(conn)

                # Verify permissions after each operation
                stat_info = os.stat(store_path)
                permissions = stat_info.st_mode & 0o777
                assert permissions == 0o600, f"Permissions changed after creating {conn.name}"

            # Update a connection
            manager.update_connection("conn-0", {"file_path": "/tmp/updated.db"})
            stat_info = os.stat(store_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600, "Permissions changed after update"

            # Delete a connection
            manager.delete_connection("conn-1")
            stat_info = os.stat(store_path)
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600, "Permissions changed after delete"

    def test_warning_message_content(self, capsys):
        """Test that warning message contains helpful information."""
        if os.name == "nt":  # Skip on Windows
            pytest.skip("Permission checks not applicable on Windows")

        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "connections.json"

            manager = DatabaseConnectionManager(store_path)

            # Set various insecure permissions and verify warnings
            insecure_perms = [0o644, 0o666, 0o777, 0o755]

            for perms in insecure_perms:
                os.chmod(store_path, perms)
                capsys.readouterr()  # Clear previous output

                manager._verify_permissions()

                captured = capsys.readouterr()
                assert "WARNING" in captured.out
                assert "insecure permissions" in captured.out
                assert oct(perms) in captured.out
                assert "chmod 600" in captured.out
                assert str(store_path) in captured.out
