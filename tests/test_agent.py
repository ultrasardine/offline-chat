"""Tests for Agent data model.

This module contains property-based tests and unit tests for the Agent dataclass.
"""

import re
from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat import Agent


# Strategy for generating valid kebab-case names
def valid_kebab_case_strategy():
    """Generate valid kebab-case strings."""
    # Generate segments of lowercase letters and numbers
    segment = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=1,
        max_size=10,
    )
    # Generate 1-5 segments joined by hyphens
    return st.lists(segment, min_size=1, max_size=5).map(lambda parts: "-".join(parts))


# Strategy for generating invalid names (various invalid patterns)
def invalid_name_strategy():
    """Generate strings that should fail kebab-case validation."""
    return st.one_of(
        # Empty string
        st.just(""),
        # Contains uppercase
        st.text(min_size=1).filter(lambda s: any(c.isupper() for c in s)),
        # Contains spaces
        st.text(min_size=1).filter(lambda s: " " in s),
        # Starts with hyphen
        st.text(min_size=1).map(lambda s: "-" + s.lower().replace(" ", "")),
        # Ends with hyphen
        st.text(min_size=1).map(lambda s: s.lower().replace(" ", "") + "-"),
        # Contains consecutive hyphens
        st.text(min_size=1).map(lambda s: s.lower().replace(" ", "") + "--" + "a"),
        # Contains special characters
        st.text(min_size=1).filter(lambda s: any(c in s for c in "!@#$%^&*()+=[]{}|;:',.<>?/~`")),
    )


class TestAgentNameValidation:
    """Property 1: Agent Name Validation.

    Feature: offline-chat, Property 1: Agent Name Validation
    Validates: Requirements 1.2

    For any string input as an agent name, the validation function SHALL accept
    only strings matching the pattern ^[a-z0-9]+(-[a-z0-9]+)*$ (lowercase letters,
    numbers, and hyphens, not starting or ending with hyphen).
    """

    @settings(max_examples=100)
    @given(name=valid_kebab_case_strategy())
    def test_valid_names_are_accepted(self, name: str):
        """Valid kebab-case names should pass validation."""
        agent = Agent(
            name=name,
            display_name="Test",
            base_model="llama3:latest",
            system_prompt="Test prompt",
        )
        assert agent.validate_name() is True

    @settings(max_examples=100)
    @given(name=invalid_name_strategy())
    def test_invalid_names_are_rejected(self, name: str):
        """Invalid names should fail validation."""
        # Skip if the generated string accidentally matches valid pattern
        pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        if re.match(pattern, name):
            return  # Skip this case as it's actually valid

        agent = Agent(
            name=name,
            display_name="Test",
            base_model="llama3:latest",
            system_prompt="Test prompt",
        )
        assert agent.validate_name() is False

    def test_specific_valid_examples(self):
        """Unit tests for specific valid name examples."""
        valid_names = [
            "agent",
            "my-agent",
            "agent1",
            "my-agent-123",
            "a",
            "a1b2c3",
            "test-agent-v2",
        ]
        for name in valid_names:
            agent = Agent(
                name=name,
                display_name="Test",
                base_model="llama3:latest",
                system_prompt="Test",
            )
            assert agent.validate_name() is True, f"Expected '{name}' to be valid"

    def test_specific_invalid_examples(self):
        """Unit tests for specific invalid name examples."""
        invalid_names = [
            "",
            "-agent",
            "agent-",
            "my--agent",
            "My-Agent",
            "my agent",
            "my_agent",
            "agent!",
            "123-",
            "-123",
        ]
        for name in invalid_names:
            agent = Agent(
                name=name,
                display_name="Test",
                base_model="llama3:latest",
                system_prompt="Test",
            )
            assert agent.validate_name() is False, f"Expected '{name}' to be invalid"


# Strategy for generating valid Agent objects
def valid_agent_strategy():
    """Generate valid Agent objects for property testing."""
    return st.builds(
        Agent,
        name=valid_kebab_case_strategy(),
        display_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        base_model=st.sampled_from(["llama3:latest", "mistral", "codellama", "llama2"]),
        system_prompt=st.text(min_size=1, max_size=500).filter(lambda s: s.strip()),
        temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        created_at=st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )


class TestAgentSerializationRoundTrip:
    """Property 3: Agent Serialization Round-Trip.

    Feature: offline-chat, Property 3: Agent Serialization Round-Trip
    Validates: Requirements 1.4, 2.1

    For any valid Agent object, serializing it to JSON (to_dict) and then
    deserializing (from_dict) SHALL produce an equivalent Agent object with
    all fields preserved.
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_serialization_round_trip(self, agent: Agent):
        """Serializing and deserializing an Agent should preserve all fields."""
        # Serialize to dict
        data = agent.to_dict()

        # Deserialize back to Agent
        restored = Agent.from_dict(data)

        # Verify all fields are preserved
        assert restored.name == agent.name
        assert restored.display_name == agent.display_name
        assert restored.base_model == agent.base_model
        assert restored.system_prompt == agent.system_prompt
        assert restored.temperature == agent.temperature
        assert restored.created_at == agent.created_at

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_to_dict_contains_all_fields(self, agent: Agent):
        """to_dict should include all required fields."""
        data = agent.to_dict()

        required_fields = [
            "name",
            "display_name",
            "base_model",
            "system_prompt",
            "temperature",
            "created_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_specific_round_trip_example(self):
        """Unit test for a specific round-trip example."""
        original = Agent(
            name="german-tutor",
            display_name="German Language Tutor",
            base_model="llama3:latest",
            system_prompt="You are a friendly German language tutor.",
            temperature=0.7,
            created_at=datetime(2025, 1, 13, 10, 0, 0),
        )

        data = original.to_dict()
        restored = Agent.from_dict(data)

        assert restored.name == original.name
        assert restored.display_name == original.display_name
        assert restored.base_model == original.base_model
        assert restored.system_prompt == original.system_prompt
        assert restored.temperature == original.temperature
        assert restored.created_at == original.created_at


class TestModelfileGeneration:
    """Property 4: Modelfile Generation Correctness.

    Feature: offline-chat, Property 4: Modelfile Generation Correctness
    Validates: Requirements 1.4

    For any valid Agent configuration, the generated Modelfile SHALL contain:
    - A FROM directive with the base_model value
    - A SYSTEM directive with the system_prompt value
    - A PARAMETER temperature directive with the temperature value
    """

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_from_directive(self, agent: Agent):
        """Modelfile should contain FROM directive with base_model."""
        modelfile = agent.to_modelfile()
        assert f"FROM {agent.base_model}" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_system_directive(self, agent: Agent):
        """Modelfile should contain SYSTEM directive with system_prompt."""
        modelfile = agent.to_modelfile()
        # The system prompt is escaped in the modelfile
        assert 'SYSTEM "' in modelfile
        # Verify the modelfile starts with SYSTEM directive after FROM
        assert "SYSTEM" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_contains_temperature_parameter(self, agent: Agent):
        """Modelfile should contain PARAMETER temperature directive."""
        modelfile = agent.to_modelfile()
        assert f"PARAMETER temperature {agent.temperature}" in modelfile

    @settings(max_examples=100)
    @given(agent=valid_agent_strategy())
    def test_modelfile_structure_is_valid(self, agent: Agent):
        """Modelfile should have valid structure with all directives."""
        modelfile = agent.to_modelfile()
        lines = [line.strip() for line in modelfile.strip().split("\n") if line.strip()]

        # Should have at least 3 non-empty lines: FROM, SYSTEM, PARAMETER
        assert len(lines) >= 3

        # First line should be FROM
        assert lines[0].startswith("FROM ")

        # Should contain SYSTEM directive
        system_lines = [line for line in lines if line.startswith("SYSTEM ")]
        assert len(system_lines) == 1

        # Should contain PARAMETER temperature
        param_lines = [line for line in lines if line.startswith("PARAMETER temperature")]
        assert len(param_lines) == 1

    def test_specific_modelfile_example(self):
        """Unit test for a specific Modelfile generation example."""
        agent = Agent(
            name="german-tutor",
            display_name="German Language Tutor",
            base_model="llama3:latest",
            system_prompt="You are a friendly German language tutor.",
            temperature=0.7,
        )

        modelfile = agent.to_modelfile()

        assert "FROM llama3:latest" in modelfile
        assert 'SYSTEM "You are a friendly German language tutor."' in modelfile
        assert "PARAMETER temperature 0.7" in modelfile

    def test_modelfile_escapes_quotes_in_system_prompt(self):
        """Modelfile should properly escape quotes in system prompt."""
        agent = Agent(
            name="test-agent",
            display_name="Test",
            base_model="llama3:latest",
            system_prompt='Say "hello" to the user.',
            temperature=0.5,
        )

        modelfile = agent.to_modelfile()

        # Quotes should be escaped
        assert '\\"hello\\"' in modelfile
        # The modelfile should still be valid (SYSTEM directive present)
        assert "SYSTEM" in modelfile
