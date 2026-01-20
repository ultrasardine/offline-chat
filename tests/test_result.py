"""Tests for Result type error handling.

This module contains both unit tests and property-based tests for the Result
type implementation. The tests verify that the Result type correctly handles
success and error cases, and that all helper functions work as expected.
"""

import pytest
from hypothesis import given, strategies as st

from offline_chat.database.result import (
    Ok,
    Err,
    Result,
    is_ok,
    is_err,
    unwrap,
    unwrap_err,
    unwrap_or,
    map_result,
    map_err,
    and_then,
)


# Unit Tests


class TestResultConstruction:
    """Test Result type construction."""
    
    def test_ok_construction(self):
        """Test creating Ok result."""
        result = Ok(42)
        assert result.value == 42
    
    def test_err_construction(self):
        """Test creating Err result."""
        result = Err("error message")
        assert result.error == "error message"
    
    def test_ok_with_none(self):
        """Test Ok can contain None."""
        result = Ok(None)
        assert result.value is None
    
    def test_ok_with_complex_type(self):
        """Test Ok can contain complex types."""
        data = {"key": "value", "nested": [1, 2, 3]}
        result = Ok(data)
        assert result.value == data


class TestIsOk:
    """Test is_ok function."""
    
    def test_is_ok_with_ok(self):
        """Test is_ok returns True for Ok."""
        result = Ok(42)
        assert is_ok(result) is True
    
    def test_is_ok_with_err(self):
        """Test is_ok returns False for Err."""
        result = Err("error")
        assert is_ok(result) is False


class TestIsErr:
    """Test is_err function."""
    
    def test_is_err_with_err(self):
        """Test is_err returns True for Err."""
        result = Err("error")
        assert is_err(result) is True
    
    def test_is_err_with_ok(self):
        """Test is_err returns False for Ok."""
        result = Ok(42)
        assert is_err(result) is False


class TestUnwrap:
    """Test unwrap function."""
    
    def test_unwrap_ok(self):
        """Test unwrap extracts value from Ok."""
        result = Ok(42)
        assert unwrap(result) == 42
    
    def test_unwrap_err_raises(self):
        """Test unwrap raises ValueError for Err."""
        result = Err("error message")
        with pytest.raises(ValueError, match="Called unwrap on an Err value: error message"):
            unwrap(result)
    
    def test_unwrap_ok_with_none(self):
        """Test unwrap can extract None from Ok."""
        result = Ok(None)
        assert unwrap(result) is None


class TestUnwrapErr:
    """Test unwrap_err function."""
    
    def test_unwrap_err_extracts_error(self):
        """Test unwrap_err extracts error from Err."""
        result = Err("error message")
        assert unwrap_err(result) == "error message"
    
    def test_unwrap_err_ok_raises(self):
        """Test unwrap_err raises ValueError for Ok."""
        result = Ok(42)
        with pytest.raises(ValueError, match="Called unwrap_err on an Ok value: 42"):
            unwrap_err(result)


class TestUnwrapOr:
    """Test unwrap_or function."""
    
    def test_unwrap_or_with_ok(self):
        """Test unwrap_or returns Ok value."""
        result = Ok(42)
        assert unwrap_or(result, 0) == 42
    
    def test_unwrap_or_with_err(self):
        """Test unwrap_or returns default for Err."""
        result = Err("error")
        assert unwrap_or(result, 0) == 0
    
    def test_unwrap_or_with_none_default(self):
        """Test unwrap_or with None as default."""
        result = Err("error")
        assert unwrap_or(result, None) is None


class TestMapResult:
    """Test map_result function."""
    
    def test_map_result_ok(self):
        """Test map_result applies function to Ok value."""
        result = Ok(42)
        mapped = map_result(result, lambda x: x * 2)
        assert is_ok(mapped)
        assert unwrap(mapped) == 84
    
    def test_map_result_err(self):
        """Test map_result leaves Err unchanged."""
        result = Err("error")
        mapped = map_result(result, lambda x: x * 2)
        assert is_err(mapped)
        assert unwrap_err(mapped) == "error"
    
    def test_map_result_type_change(self):
        """Test map_result can change value type."""
        result = Ok(42)
        mapped = map_result(result, lambda x: str(x))
        assert unwrap(mapped) == "42"


class TestMapErr:
    """Test map_err function."""
    
    def test_map_err_transforms_error(self):
        """Test map_err applies function to Err value."""
        result = Err("error")
        mapped = map_err(result, lambda e: f"Error: {e}")
        assert is_err(mapped)
        assert unwrap_err(mapped) == "Error: error"
    
    def test_map_err_leaves_ok_unchanged(self):
        """Test map_err leaves Ok unchanged."""
        result = Ok(42)
        mapped = map_err(result, lambda e: f"Error: {e}")
        assert is_ok(mapped)
        assert unwrap(mapped) == 42


class TestAndThen:
    """Test and_then function for chaining operations."""
    
    def test_and_then_ok_to_ok(self):
        """Test and_then chains Ok to Ok."""
        def double(x: int) -> Result[int, str]:
            return Ok(x * 2)
        
        result = Ok(21)
        chained = and_then(result, double)
        assert is_ok(chained)
        assert unwrap(chained) == 42
    
    def test_and_then_ok_to_err(self):
        """Test and_then chains Ok to Err."""
        def divide_by_zero(x: int) -> Result[int, str]:
            return Err("division by zero")
        
        result = Ok(42)
        chained = and_then(result, divide_by_zero)
        assert is_err(chained)
        assert unwrap_err(chained) == "division by zero"
    
    def test_and_then_err_short_circuits(self):
        """Test and_then doesn't call function for Err."""
        called = False
        
        def should_not_be_called(x: int) -> Result[int, str]:
            nonlocal called
            called = True
            return Ok(x * 2)
        
        result = Err("initial error")
        chained = and_then(result, should_not_be_called)
        
        assert not called
        assert is_err(chained)
        assert unwrap_err(chained) == "initial error"
    
    def test_and_then_multiple_chains(self):
        """Test chaining multiple operations."""
        def add_one(x: int) -> Result[int, str]:
            return Ok(x + 1)
        
        def multiply_by_two(x: int) -> Result[int, str]:
            return Ok(x * 2)
        
        result = Ok(10)
        chained = and_then(and_then(result, add_one), multiply_by_two)
        assert unwrap(chained) == 22  # (10 + 1) * 2


# Property-Based Tests


@given(st.integers())
def test_ok_preserves_value(value: int):
    """Property: Ok preserves the value it wraps."""
    result = Ok(value)
    assert unwrap(result) == value


@given(st.text())
def test_err_preserves_error(error: str):
    """Property: Err preserves the error it wraps."""
    result = Err(error)
    assert unwrap_err(result) == error


@given(st.integers())
def test_is_ok_and_is_err_are_opposites(value: int):
    """Property: is_ok and is_err are mutually exclusive."""
    ok_result = Ok(value)
    err_result = Err(value)
    
    assert is_ok(ok_result) and not is_err(ok_result)
    assert is_err(err_result) and not is_ok(err_result)


@given(st.integers(), st.integers())
def test_unwrap_or_returns_value_for_ok(value: int, default: int):
    """Property: unwrap_or returns the Ok value, ignoring default."""
    result = Ok(value)
    assert unwrap_or(result, default) == value


@given(st.text(), st.integers())
def test_unwrap_or_returns_default_for_err(error: str, default: int):
    """Property: unwrap_or returns default for Err."""
    result = Err(error)
    assert unwrap_or(result, default) == default


@given(st.integers())
def test_map_result_identity(value: int):
    """Property: Mapping identity function preserves value."""
    result = Ok(value)
    mapped = map_result(result, lambda x: x)
    assert unwrap(mapped) == value


@given(st.integers())
def test_map_result_composition(value: int):
    """Property: map(f, map(g, x)) == map(f ∘ g, x)."""
    result = Ok(value)
    
    # Map twice
    mapped_twice = map_result(map_result(result, lambda x: x + 1), lambda x: x * 2)
    
    # Map with composed function
    mapped_composed = map_result(result, lambda x: (x + 1) * 2)
    
    assert unwrap(mapped_twice) == unwrap(mapped_composed)


@given(st.text())
def test_map_result_preserves_err(error: str):
    """Property: map_result doesn't change Err."""
    result = Err(error)
    mapped = map_result(result, lambda x: x * 2)
    assert is_err(mapped)
    assert unwrap_err(mapped) == error


@given(st.text())
def test_map_err_identity(error: str):
    """Property: Mapping identity function over error preserves it."""
    result = Err(error)
    mapped = map_err(result, lambda e: e)
    assert unwrap_err(mapped) == error


@given(st.integers())
def test_map_err_preserves_ok(value: int):
    """Property: map_err doesn't change Ok."""
    result = Ok(value)
    mapped = map_err(result, lambda e: f"Error: {e}")
    assert is_ok(mapped)
    assert unwrap(mapped) == value


@given(st.integers())
def test_and_then_left_identity(value: int):
    """Property: and_then(Ok(x), f) == f(x) (left identity)."""
    def f(x: int) -> Result[int, str]:
        return Ok(x * 2)
    
    result1 = and_then(Ok(value), f)
    result2 = f(value)
    
    assert unwrap(result1) == unwrap(result2)


@given(st.integers())
def test_and_then_right_identity(value: int):
    """Property: and_then(m, Ok) == m (right identity)."""
    result = Ok(value)
    chained = and_then(result, lambda x: Ok(x))
    
    assert unwrap(chained) == unwrap(result)


@given(st.integers())
def test_and_then_associativity(value: int):
    """Property: and_then is associative."""
    def f(x: int) -> Result[int, str]:
        return Ok(x + 1)
    
    def g(x: int) -> Result[int, str]:
        return Ok(x * 2)
    
    result = Ok(value)
    
    # (m >>= f) >>= g
    left = and_then(and_then(result, f), g)
    
    # m >>= (\x -> f(x) >>= g)
    right = and_then(result, lambda x: and_then(f(x), g))
    
    assert unwrap(left) == unwrap(right)


@given(st.text())
def test_and_then_err_short_circuit(error: str):
    """Property: and_then with Err doesn't execute the function."""
    result = Err(error)
    
    # This function should never be called
    def should_not_run(x: int) -> Result[int, str]:
        raise AssertionError("Function should not be called for Err")
    
    chained = and_then(result, should_not_run)
    assert is_err(chained)
    assert unwrap_err(chained) == error


@given(st.integers(), st.integers())
def test_result_type_safety(ok_value: int, err_value: int):
    """Property: Result maintains type safety between Ok and Err."""
    ok_result = Ok(ok_value)
    err_result = Err(err_value)
    
    # Ok and Err are distinct types
    assert type(ok_result) != type(err_result)
    
    # Can't unwrap Err as Ok
    with pytest.raises(ValueError):
        unwrap(err_result)
    
    # Can't unwrap Ok as Err
    with pytest.raises(ValueError):
        unwrap_err(ok_result)


# Integration Tests


class TestResultIntegration:
    """Integration tests for Result type in realistic scenarios."""
    
    def test_database_connection_simulation(self):
        """Test Result type in simulated database connection scenario."""
        def connect_to_db(host: str) -> Result[str, str]:
            if not host:
                return Err("Host cannot be empty")
            if host == "invalid":
                return Err("Connection failed: invalid host")
            return Ok(f"Connected to {host}")
        
        def query_db(connection: str) -> Result[list[dict], str]:
            if "Connected" not in connection:
                return Err("Not connected")
            return Ok([{"id": 1, "name": "test"}])
        
        # Success path
        result = and_then(connect_to_db("localhost"), query_db)
        assert is_ok(result)
        assert len(unwrap(result)) == 1
        
        # Error path - empty host
        result = and_then(connect_to_db(""), query_db)
        assert is_err(result)
        assert unwrap_err(result) == "Host cannot be empty"
        
        # Error path - invalid host
        result = and_then(connect_to_db("invalid"), query_db)
        assert is_err(result)
        assert "Connection failed" in unwrap_err(result)
    
    def test_validation_chain(self):
        """Test Result type in validation chain scenario."""
        def validate_name(name: str) -> Result[str, str]:
            if not name:
                return Err("Name cannot be empty")
            if not name.islower():
                return Err("Name must be lowercase")
            return Ok(name)
        
        def validate_format(name: str) -> Result[str, str]:
            if " " in name:
                return Err("Name cannot contain spaces")
            return Ok(name)
        
        def validate_length(name: str) -> Result[str, str]:
            if len(name) > 50:
                return Err("Name too long")
            return Ok(name)
        
        # Valid name
        result = and_then(and_then(validate_name("test"), validate_format), validate_length)
        assert is_ok(result)
        assert unwrap(result) == "test"
        
        # Empty name
        result = and_then(and_then(validate_name(""), validate_format), validate_length)
        assert is_err(result)
        assert unwrap_err(result) == "Name cannot be empty"
        
        # Uppercase name
        result = and_then(and_then(validate_name("Test"), validate_format), validate_length)
        assert is_err(result)
        assert unwrap_err(result) == "Name must be lowercase"
        
        # Name with spaces
        result = and_then(and_then(validate_name("test name"), validate_format), validate_length)
        assert is_err(result)
        assert unwrap_err(result) == "Name cannot contain spaces"
