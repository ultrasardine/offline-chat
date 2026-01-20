"""Tests for AgentManager guideline management methods.

This module contains unit tests for the guideline management functionality
in the AgentManager class.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from offline_chat import Agent, AgentManager
from offline_chat.database.result import is_ok, is_err, unwrap, unwrap_err


class TestAddGuideline:
    """Tests for add_guideline method."""

    def test_add_guideline_to_agent_with_no_guidelines(self):
        """Adding a guideline to an agent with no guidelines should succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Add guideline
            result = manager.add_guideline(
                "test-agent",
                "Always explain your reasoning"
            )

            assert is_ok(result)

            # Verify guideline was added
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 1
            assert updated_agent.guidelines[0] == "Always explain your reasoning"

    def test_add_multiple_guidelines(self):
        """Adding multiple guidelines should append them in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Add multiple guidelines
            guidelines = [
                "Always explain your reasoning",
                "Be concise and clear",
                "Provide examples when helpful"
            ]

            for guideline in guidelines:
                result = manager.add_guideline("test-agent", guideline)
                assert is_ok(result)

            # Verify all guidelines were added in order
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 3
            assert updated_agent.guidelines == guidelines

    def test_add_empty_guideline_fails(self):
        """Adding an empty guideline should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to add empty guideline
            result = manager.add_guideline("test-agent", "")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Try to add whitespace-only guideline
            result = manager.add_guideline("test-agent", "   ")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

    def test_add_guideline_to_nonexistent_agent_fails(self):
        """Adding a guideline to a non-existent agent should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            result = manager.add_guideline("nonexistent-agent", "Some guideline")
            assert is_err(result)
            assert "not found" in unwrap_err(result).lower()

    def test_add_non_string_guideline_fails(self):
        """Adding a non-string guideline should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to add non-string guideline
            result = manager.add_guideline("test-agent", 123)  # type: ignore
            assert is_err(result)
            assert "must be a string" in unwrap_err(result).lower()


class TestEditGuideline:
    """Tests for edit_guideline method."""

    def test_edit_guideline_updates_text(self):
        """Editing a guideline should update its text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Original guideline 1", "Original guideline 2"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Edit the first guideline
            result = manager.edit_guideline("test-agent", 0, "Updated guideline 1")
            assert is_ok(result)

            # Verify guideline was updated
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 2
            assert updated_agent.guidelines[0] == "Updated guideline 1"
            assert updated_agent.guidelines[1] == "Original guideline 2"

    def test_edit_guideline_preserves_other_guidelines(self):
        """Editing a guideline should not affect other guidelines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with multiple guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2", "Guideline 3"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Edit the middle guideline
            result = manager.edit_guideline("test-agent", 1, "Updated Guideline 2")
            assert is_ok(result)

            # Verify only the target guideline was updated
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 3
            assert updated_agent.guidelines[0] == "Guideline 1"
            assert updated_agent.guidelines[1] == "Updated Guideline 2"
            assert updated_agent.guidelines[2] == "Guideline 3"

    def test_edit_guideline_with_invalid_index_fails(self):
        """Editing with an invalid index should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to edit with index out of range
            result = manager.edit_guideline("test-agent", 5, "New text")
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "2" in error_msg  # Should mention the agent has 2 guidelines

            # Try to edit with negative index
            result = manager.edit_guideline("test-agent", -1, "New text")
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

    def test_edit_guideline_with_empty_text_fails(self):
        """Editing a guideline with empty text should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to edit with empty text
            result = manager.edit_guideline("test-agent", 0, "")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

    def test_edit_guideline_on_nonexistent_agent_fails(self):
        """Editing a guideline on a non-existent agent should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            result = manager.edit_guideline("nonexistent-agent", 0, "New text")
            assert is_err(result)
            assert "not found" in unwrap_err(result).lower()


class TestDeleteGuideline:
    """Tests for delete_guideline method."""

    def test_delete_guideline_removes_it(self):
        """Deleting a guideline should remove it from the list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2", "Guideline 3"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Delete the middle guideline
            result = manager.delete_guideline("test-agent", 1)
            assert is_ok(result)

            # Verify guideline was removed
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 2
            assert updated_agent.guidelines[0] == "Guideline 1"
            assert updated_agent.guidelines[1] == "Guideline 3"

    def test_delete_guideline_preserves_order(self):
        """Deleting a guideline should preserve the order of remaining guidelines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["First", "Second", "Third", "Fourth"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Delete the first guideline
            result = manager.delete_guideline("test-agent", 0)
            assert is_ok(result)

            # Verify order is preserved
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert updated_agent.guidelines == ["Second", "Third", "Fourth"]

    def test_delete_last_guideline(self):
        """Deleting the last guideline should result in an empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with one guideline
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Only guideline"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Delete the only guideline
            result = manager.delete_guideline("test-agent", 0)
            assert is_ok(result)

            # Verify guidelines list is empty
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 0
            assert updated_agent.guidelines == []

    def test_delete_guideline_with_invalid_index_fails(self):
        """Deleting with an invalid index should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to delete with index out of range
            result = manager.delete_guideline("test-agent", 10)
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "2" in error_msg  # Should mention the agent has 2 guidelines

            # Try to delete with negative index
            result = manager.delete_guideline("test-agent", -1)
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

    def test_delete_guideline_on_nonexistent_agent_fails(self):
        """Deleting a guideline on a non-existent agent should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            result = manager.delete_guideline("nonexistent-agent", 0)
            assert is_err(result)
            assert "not found" in unwrap_err(result).lower()


class TestListGuidelines:
    """Tests for list_guidelines method."""

    def test_list_guidelines_returns_all_guidelines(self):
        """Listing guidelines should return all guidelines in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            guidelines = ["First guideline", "Second guideline", "Third guideline"]
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=guidelines
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # List guidelines
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            listed_guidelines = unwrap(result)
            assert listed_guidelines == guidelines

    def test_list_guidelines_returns_empty_list_when_no_guidelines(self):
        """Listing guidelines should return empty list when agent has no guidelines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent without guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # List guidelines
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            listed_guidelines = unwrap(result)
            assert listed_guidelines == []

    def test_list_guidelines_on_nonexistent_agent_fails(self):
        """Listing guidelines on a non-existent agent should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            result = manager.list_guidelines("nonexistent-agent")
            assert is_err(result)
            assert "not found" in unwrap_err(result).lower()


class TestGuidelinesEdgeCases:
    """Additional edge case tests for guidelines management.
    
    This test class specifically addresses the edge cases mentioned in task 8.3:
    - Adding empty guideline (should fail)
    - Editing with invalid index (should fail)
    - Deleting with invalid index (should fail)
    - Listing empty guidelines
    
    Validates Requirements: 13.3, 13.4, 13.5, 13.6, 13.7
    """

    def test_add_empty_guideline_edge_cases(self):
        """Test various forms of empty guidelines - all should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Test empty string
            result = manager.add_guideline("test-agent", "")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Test whitespace only (spaces)
            result = manager.add_guideline("test-agent", "   ")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Test whitespace only (tabs)
            result = manager.add_guideline("test-agent", "\t\t")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Test whitespace only (newlines)
            result = manager.add_guideline("test-agent", "\n\n")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Test mixed whitespace
            result = manager.add_guideline("test-agent", " \t\n ")
            assert is_err(result)
            assert "cannot be empty" in unwrap_err(result).lower()

            # Verify no guidelines were added
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert len(updated_agent.guidelines) == 0

    def test_edit_with_invalid_index_edge_cases(self):
        """Test editing with various invalid indices - all should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with 2 guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Test index equal to length (out of bounds)
            result = manager.edit_guideline("test-agent", 2, "New text")
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "2" in error_msg  # Should mention count

            # Test index greater than length
            result = manager.edit_guideline("test-agent", 10, "New text")
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Test negative index
            result = manager.edit_guideline("test-agent", -1, "New text")
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Test large negative index
            result = manager.edit_guideline("test-agent", -100, "New text")
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Verify guidelines remain unchanged
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert updated_agent.guidelines == ["Guideline 1", "Guideline 2"]

    def test_edit_with_invalid_index_on_empty_guidelines(self):
        """Test editing when agent has no guidelines - should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with no guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to edit index 0 when no guidelines exist
            result = manager.edit_guideline("test-agent", 0, "New text")
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "0" in error_msg  # Should mention count is 0

    def test_delete_with_invalid_index_edge_cases(self):
        """Test deleting with various invalid indices - all should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with 3 guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["First", "Second", "Third"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Test index equal to length (out of bounds)
            result = manager.delete_guideline("test-agent", 3)
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "3" in error_msg  # Should mention count

            # Test index greater than length
            result = manager.delete_guideline("test-agent", 100)
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Test negative index
            result = manager.delete_guideline("test-agent", -1)
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Test large negative index
            result = manager.delete_guideline("test-agent", -50)
            assert is_err(result)
            assert "out of range" in unwrap_err(result).lower()

            # Verify guidelines remain unchanged
            updated_agent = manager.get_agent("test-agent")
            assert updated_agent is not None
            assert updated_agent.guidelines == ["First", "Second", "Third"]

    def test_delete_with_invalid_index_on_empty_guidelines(self):
        """Test deleting when agent has no guidelines - should fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with no guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Try to delete index 0 when no guidelines exist
            result = manager.delete_guideline("test-agent", 0)
            assert is_err(result)
            error_msg = unwrap_err(result)
            assert "out of range" in error_msg.lower()
            assert "0" in error_msg  # Should mention count is 0

    def test_list_empty_guidelines_comprehensive(self):
        """Test listing guidelines when agent has no guidelines - should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with no guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # List guidelines - should return empty list
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            guidelines = unwrap(result)
            assert isinstance(guidelines, list)
            assert len(guidelines) == 0
            assert guidelines == []

    def test_list_empty_guidelines_after_deleting_all(self):
        """Test listing guidelines after deleting all guidelines - should return empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
                guidelines=["Guideline 1", "Guideline 2"]
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # Delete all guidelines
            result = manager.delete_guideline("test-agent", 0)
            assert is_ok(result)
            result = manager.delete_guideline("test-agent", 0)
            assert is_ok(result)

            # List guidelines - should return empty list
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            guidelines = unwrap(result)
            assert isinstance(guidelines, list)
            assert len(guidelines) == 0
            assert guidelines == []

    def test_operations_on_empty_guidelines_list(self):
        """Test that operations correctly handle empty guidelines list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            history_dir = Path(tmpdir) / "history"
            manager = AgentManager(agents_dir=agents_dir, history_dir=history_dir)

            # Create agent with no guidelines
            agent = Agent(
                name="test-agent",
                display_name="Test Agent",
                base_model="llama3:latest",
                system_prompt="You are a test agent.",
                temperature=0.7,
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                mock_run.return_value.stdout = ""
                manager.create_agent(agent)

            # List should return empty
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            assert unwrap(result) == []

            # Edit should fail
            result = manager.edit_guideline("test-agent", 0, "Text")
            assert is_err(result)

            # Delete should fail
            result = manager.delete_guideline("test-agent", 0)
            assert is_err(result)

            # Add should succeed
            result = manager.add_guideline("test-agent", "First guideline")
            assert is_ok(result)

            # Now list should return one item
            result = manager.list_guidelines("test-agent")
            assert is_ok(result)
            assert unwrap(result) == ["First guideline"]
