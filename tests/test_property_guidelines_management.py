"""Property-based tests for guidelines management.

This module contains property-based tests using Hypothesis to verify universal
properties of guideline management functionality.

Properties tested:
- Property 35: Guideline Addition
- Property 36: Guideline Editing
- Property 37: Guideline Deletion
- Property 40: Guideline Listing

**Validates: Requirements 13.4, 13.5, 13.6, 13.7**
"""

import json
import tempfile
import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
from unittest.mock import patch

from offline_chat.agent import Agent
from offline_chat.database.result import is_ok, is_err, unwrap, unwrap_err
from offline_chat.manager import AgentManager


# ============================================================================
# Hypothesis Strategies
# ============================================================================

# Valid agent names (kebab-case)
valid_agent_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=1,
    max_size=30
).filter(lambda s: s[0] != '-' and s[-1] != '-' and '--' not in s and s[0] not in '0123456789')

# Valid guideline text (non-empty strings with reasonable content)
valid_guideline_text = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=" .,!?-"),
    min_size=5,
    max_size=100
).filter(lambda s: s.strip() != '')

# Lists of guidelines
guideline_lists = st.lists(
    valid_guideline_text,
    min_size=0,
    max_size=10,
    unique=True
)

# Valid indices (will be constrained based on list size)
valid_indices = st.integers(min_value=0, max_value=20)


# ============================================================================
# Helper Functions
# ============================================================================

def setup_test_environment():
    """Set up test environment with temporary directories and managers."""
    tmp_dir = Path(tempfile.mkdtemp())
    
    agents_dir = tmp_dir / "agents"
    history_dir = tmp_dir / "history"
    
    agents_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    
    agent_manager = AgentManager(
        agents_dir=agents_dir,
        history_dir=history_dir,
    )
    
    return {
        "tmp_dir": tmp_dir,
        "agents_dir": agents_dir,
        "history_dir": history_dir,
        "agent_manager": agent_manager,
    }


def create_test_agent(agent_manager, name: str, guidelines=None) -> bool:
    """Create a test agent without Ollama registration."""
    agent = Agent(
        name=name,
        display_name=f"Test Agent {name}",
        base_model="llama3:latest",
        system_prompt="You are a test agent.",
        temperature=0.7,
        guidelines=guidelines if guidelines is not None else [],
    )
    
    # Save agent config manually (skip Ollama registration for tests)
    agent_dir = agent_manager._get_agent_dir(agent.name)
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = agent_manager._get_config_path(agent.name)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(agent.to_dict(), f, indent=2)
    
    return True


# ============================================================================
# Property 35: Guideline Addition
# ============================================================================

@given(
    agent_name=valid_agent_names,
    initial_guidelines=guideline_lists,
    new_guideline=valid_guideline_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_35_guideline_addition(
    agent_name, initial_guidelines, new_guideline
):
    """Property 35: Guideline Addition
    
    **Validates: Requirements 13.4**
    
    For any agent and guideline text, adding a guideline should append it to
    the end of the guidelines list.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Get initial count
    initial_count = len(initial_guidelines)
    
    # Add the new guideline
    result = agent_manager.add_guideline(agent_name, new_guideline)
    
    # Verify addition succeeded
    assert is_ok(result), f"Guideline addition should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline addition"
    
    # Verify the guideline was added to the end
    assert len(reloaded_agent.guidelines) == initial_count + 1, \
        f"Should have {initial_count + 1} guidelines after addition, got {len(reloaded_agent.guidelines)}"
    
    # Verify the new guideline is at the end
    assert reloaded_agent.guidelines[-1] == new_guideline, \
        f"Last guideline should be '{new_guideline}', got '{reloaded_agent.guidelines[-1]}'"
    
    # Verify all previous guidelines are preserved in order
    assert reloaded_agent.guidelines[:-1] == initial_guidelines, \
        f"Previous guidelines should be preserved: expected {initial_guidelines}, got {reloaded_agent.guidelines[:-1]}"


@given(
    agent_name=valid_agent_names,
    guidelines_to_add=st.lists(valid_guideline_text, min_size=1, max_size=5, unique=True),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_35_guideline_addition_multiple(
    agent_name, guidelines_to_add
):
    """Property 35: Guideline Addition (Multiple)
    
    **Validates: Requirements 13.4**
    
    For any agent and multiple guideline texts, adding each guideline should
    append them to the end of the guidelines list in order.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with no guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=[])
    
    # Add each guideline
    for guideline in guidelines_to_add:
        result = agent_manager.add_guideline(agent_name, guideline)
        assert is_ok(result), f"Guideline addition should succeed for '{guideline}'"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline additions"
    
    # Verify all guidelines were added in order
    assert len(reloaded_agent.guidelines) == len(guidelines_to_add), \
        f"Should have {len(guidelines_to_add)} guidelines, got {len(reloaded_agent.guidelines)}"
    
    assert reloaded_agent.guidelines == guidelines_to_add, \
        f"Guidelines should match in order: expected {guidelines_to_add}, got {reloaded_agent.guidelines}"


# ============================================================================
# Property 36: Guideline Editing
# ============================================================================

@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
    new_text=valid_guideline_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_36_guideline_editing(
    agent_name, initial_guidelines, new_text
):
    """Property 36: Guideline Editing
    
    **Validates: Requirements 13.5**
    
    For any agent, guideline index, and new text, editing a guideline should
    replace the text at that index while preserving all other guidelines.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Choose a valid index to edit
    index_to_edit = len(initial_guidelines) // 2  # Edit middle guideline
    
    # Edit the guideline
    result = agent_manager.edit_guideline(agent_name, index_to_edit, new_text)
    
    # Verify edit succeeded
    assert is_ok(result), f"Guideline edit should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline edit"
    
    # Verify the guideline count is unchanged
    assert len(reloaded_agent.guidelines) == len(initial_guidelines), \
        f"Should have {len(initial_guidelines)} guidelines after edit, got {len(reloaded_agent.guidelines)}"
    
    # Verify the edited guideline has the new text
    assert reloaded_agent.guidelines[index_to_edit] == new_text, \
        f"Guideline at index {index_to_edit} should be '{new_text}', got '{reloaded_agent.guidelines[index_to_edit]}'"
    
    # Verify all other guidelines are unchanged
    for i, guideline in enumerate(initial_guidelines):
        if i != index_to_edit:
            assert reloaded_agent.guidelines[i] == guideline, \
                f"Guideline at index {i} should be unchanged: expected '{guideline}', got '{reloaded_agent.guidelines[i]}'"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
    new_text=valid_guideline_text,
    index=valid_indices,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_36_guideline_editing_all_indices(
    agent_name, initial_guidelines, new_text, index
):
    """Property 36: Guideline Editing (All Indices)
    
    **Validates: Requirements 13.5**
    
    For any agent and any valid index, editing a guideline should replace
    the text at that index while preserving all other guidelines.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Constrain index to valid range
    assume(0 <= index < len(initial_guidelines))
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Edit the guideline at the specified index
    result = agent_manager.edit_guideline(agent_name, index, new_text)
    
    # Verify edit succeeded
    assert is_ok(result), f"Guideline edit should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline edit"
    
    # Verify the guideline count is unchanged
    assert len(reloaded_agent.guidelines) == len(initial_guidelines), \
        f"Should have {len(initial_guidelines)} guidelines after edit, got {len(reloaded_agent.guidelines)}"
    
    # Verify the edited guideline has the new text
    assert reloaded_agent.guidelines[index] == new_text, \
        f"Guideline at index {index} should be '{new_text}', got '{reloaded_agent.guidelines[index]}'"
    
    # Verify all other guidelines are unchanged
    for i, guideline in enumerate(initial_guidelines):
        if i != index:
            assert reloaded_agent.guidelines[i] == guideline, \
                f"Guideline at index {i} should be unchanged: expected '{guideline}', got '{reloaded_agent.guidelines[i]}'"


# ============================================================================
# Property 37: Guideline Deletion
# ============================================================================

@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_37_guideline_deletion(
    agent_name, initial_guidelines
):
    """Property 37: Guideline Deletion
    
    **Validates: Requirements 13.6**
    
    For any agent and guideline index, deleting a guideline should remove it
    from the list while preserving the order of remaining guidelines.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Choose a valid index to delete
    index_to_delete = len(initial_guidelines) // 2  # Delete middle guideline
    
    # Remember the guideline being deleted
    deleted_guideline = initial_guidelines[index_to_delete]
    
    # Delete the guideline
    result = agent_manager.delete_guideline(agent_name, index_to_delete)
    
    # Verify deletion succeeded
    assert is_ok(result), f"Guideline deletion should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline deletion"
    
    # Verify the guideline count decreased by 1
    assert len(reloaded_agent.guidelines) == len(initial_guidelines) - 1, \
        f"Should have {len(initial_guidelines) - 1} guidelines after deletion, got {len(reloaded_agent.guidelines)}"
    
    # Verify the deleted guideline is not in the list
    assert deleted_guideline not in reloaded_agent.guidelines, \
        f"Deleted guideline '{deleted_guideline}' should not be in the list"
    
    # Verify the order of remaining guidelines is preserved
    expected_remaining = initial_guidelines[:index_to_delete] + initial_guidelines[index_to_delete + 1:]
    assert reloaded_agent.guidelines == expected_remaining, \
        f"Remaining guidelines should match expected order: expected {expected_remaining}, got {reloaded_agent.guidelines}"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
    index=valid_indices,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_37_guideline_deletion_all_indices(
    agent_name, initial_guidelines, index
):
    """Property 37: Guideline Deletion (All Indices)
    
    **Validates: Requirements 13.6**
    
    For any agent and any valid index, deleting a guideline should remove it
    from the list while preserving the order of remaining guidelines.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Constrain index to valid range
    assume(0 <= index < len(initial_guidelines))
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Remember the guideline being deleted
    deleted_guideline = initial_guidelines[index]
    
    # Delete the guideline at the specified index
    result = agent_manager.delete_guideline(agent_name, index)
    
    # Verify deletion succeeded
    assert is_ok(result), f"Guideline deletion should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after guideline deletion"
    
    # Verify the guideline count decreased by 1
    assert len(reloaded_agent.guidelines) == len(initial_guidelines) - 1, \
        f"Should have {len(initial_guidelines) - 1} guidelines after deletion, got {len(reloaded_agent.guidelines)}"
    
    # Verify the deleted guideline is not in the list
    assert deleted_guideline not in reloaded_agent.guidelines, \
        f"Deleted guideline '{deleted_guideline}' should not be in the list"
    
    # Verify the order of remaining guidelines is preserved
    expected_remaining = initial_guidelines[:index] + initial_guidelines[index + 1:]
    assert reloaded_agent.guidelines == expected_remaining, \
        f"Remaining guidelines should match expected order: expected {expected_remaining}, got {reloaded_agent.guidelines}"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_37_guideline_deletion_all_guidelines(
    agent_name, initial_guidelines
):
    """Property 37: Guideline Deletion (Delete All)
    
    **Validates: Requirements 13.6**
    
    For any agent with guidelines, deleting all guidelines one by one should
    result in an empty guidelines list.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Delete all guidelines one by one (always delete index 0)
    for i in range(len(initial_guidelines)):
        result = agent_manager.delete_guideline(agent_name, 0)
        assert is_ok(result), f"Guideline deletion {i+1} should succeed"
    
    # Load the agent from storage
    reloaded_agent = agent_manager.get_agent(agent_name)
    assert reloaded_agent is not None, "Agent should exist after deleting all guidelines"
    
    # Verify all guidelines were deleted
    assert len(reloaded_agent.guidelines) == 0, \
        f"Should have 0 guidelines after deleting all, got {len(reloaded_agent.guidelines)}"
    
    assert reloaded_agent.guidelines == [], \
        "Guidelines list should be empty"


# ============================================================================
# Property 40: Guideline Listing
# ============================================================================

@given(
    agent_name=valid_agent_names,
    guidelines=guideline_lists,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_40_guideline_listing(
    agent_name, guidelines
):
    """Property 40: Guideline Listing
    
    **Validates: Requirements 13.7**
    
    For any agent, listing guidelines should return all guidelines in the
    correct order with their indices.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=guidelines)
    
    # List the guidelines
    result = agent_manager.list_guidelines(agent_name)
    
    # Verify listing succeeded
    assert is_ok(result), f"Guideline listing should succeed: {unwrap_err(result) if is_err(result) else ''}"
    
    # Get the listed guidelines
    listed_guidelines = unwrap(result)
    
    # Verify the count matches
    assert len(listed_guidelines) == len(guidelines), \
        f"Should list {len(guidelines)} guidelines, got {len(listed_guidelines)}"
    
    # Verify the guidelines match in order
    assert listed_guidelines == guidelines, \
        f"Listed guidelines should match in order: expected {guidelines}, got {listed_guidelines}"
    
    # Verify each guideline is at the correct index
    for i, guideline in enumerate(guidelines):
        assert listed_guidelines[i] == guideline, \
            f"Guideline at index {i} should be '{guideline}', got '{listed_guidelines[i]}'"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
    new_guideline=valid_guideline_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_40_guideline_listing_after_addition(
    agent_name, initial_guidelines, new_guideline
):
    """Property 40: Guideline Listing (After Addition)
    
    **Validates: Requirements 13.7**
    
    For any agent, after adding a guideline, listing guidelines should return
    all guidelines including the new one in the correct order.
    """
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Add a new guideline
    result = agent_manager.add_guideline(agent_name, new_guideline)
    assert is_ok(result), "Guideline addition should succeed"
    
    # List the guidelines
    result = agent_manager.list_guidelines(agent_name)
    assert is_ok(result), "Guideline listing should succeed"
    
    # Get the listed guidelines
    listed_guidelines = unwrap(result)
    
    # Verify the count includes the new guideline
    expected_count = len(initial_guidelines) + 1
    assert len(listed_guidelines) == expected_count, \
        f"Should list {expected_count} guidelines, got {len(listed_guidelines)}"
    
    # Verify the guidelines match in order (including the new one at the end)
    expected_guidelines = initial_guidelines + [new_guideline]
    assert listed_guidelines == expected_guidelines, \
        f"Listed guidelines should match expected: expected {expected_guidelines}, got {listed_guidelines}"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=2, max_size=10, unique=True),
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_40_guideline_listing_after_deletion(
    agent_name, initial_guidelines
):
    """Property 40: Guideline Listing (After Deletion)
    
    **Validates: Requirements 13.7**
    
    For any agent, after deleting a guideline, listing guidelines should return
    the remaining guidelines in the correct order.
    """
    # Ensure we have at least 2 guidelines
    assume(len(initial_guidelines) >= 2)
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Delete the first guideline
    result = agent_manager.delete_guideline(agent_name, 0)
    assert is_ok(result), "Guideline deletion should succeed"
    
    # List the guidelines
    result = agent_manager.list_guidelines(agent_name)
    assert is_ok(result), "Guideline listing should succeed"
    
    # Get the listed guidelines
    listed_guidelines = unwrap(result)
    
    # Verify the count decreased by 1
    expected_count = len(initial_guidelines) - 1
    assert len(listed_guidelines) == expected_count, \
        f"Should list {expected_count} guidelines, got {len(listed_guidelines)}"
    
    # Verify the guidelines match in order (without the deleted one)
    expected_guidelines = initial_guidelines[1:]
    assert listed_guidelines == expected_guidelines, \
        f"Listed guidelines should match expected: expected {expected_guidelines}, got {listed_guidelines}"


@given(
    agent_name=valid_agent_names,
    initial_guidelines=st.lists(valid_guideline_text, min_size=1, max_size=10, unique=True),
    new_text=valid_guideline_text,
)
@settings(deadline=1000, max_examples=100)
@pytest.mark.property_test
def test_property_40_guideline_listing_after_edit(
    agent_name, initial_guidelines, new_text
):
    """Property 40: Guideline Listing (After Edit)
    
    **Validates: Requirements 13.7**
    
    For any agent, after editing a guideline, listing guidelines should return
    all guidelines with the edited one updated in the correct order.
    """
    # Ensure we have at least one guideline
    assume(len(initial_guidelines) >= 1)
    
    # Set up test environment
    env = setup_test_environment()
    agent_manager = env["agent_manager"]
    
    # Create the agent with initial guidelines
    assert create_test_agent(agent_manager, agent_name, guidelines=initial_guidelines)
    
    # Edit the first guideline
    result = agent_manager.edit_guideline(agent_name, 0, new_text)
    assert is_ok(result), "Guideline edit should succeed"
    
    # List the guidelines
    result = agent_manager.list_guidelines(agent_name)
    assert is_ok(result), "Guideline listing should succeed"
    
    # Get the listed guidelines
    listed_guidelines = unwrap(result)
    
    # Verify the count is unchanged
    assert len(listed_guidelines) == len(initial_guidelines), \
        f"Should list {len(initial_guidelines)} guidelines, got {len(listed_guidelines)}"
    
    # Verify the guidelines match in order (with the edited one)
    expected_guidelines = [new_text] + initial_guidelines[1:]
    assert listed_guidelines == expected_guidelines, \
        f"Listed guidelines should match expected: expected {expected_guidelines}, got {listed_guidelines}"
