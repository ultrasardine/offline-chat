"""Result type for functional error handling.

This module provides a Rust-style Result type for explicit error propagation
throughout the database connection management system. The Result type forces
explicit handling of success and error cases, making error flows visible and
preventing silent failures.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, Callable, Any


T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type


@dataclass
class Ok(Generic[T]):
    """Represents a successful result containing a value.
    
    Attributes:
        value: The success value of type T
    """
    value: T


@dataclass
class Err(Generic[E]):
    """Represents an error result containing an error value.
    
    Attributes:
        error: The error value of type E
    """
    error: E


# Result type is a union of Ok and Err
Result = Ok[T] | Err[E]


def is_ok(result: Result[T, E]) -> bool:
    """Check if result is Ok.
    
    Args:
        result: Result to check
        
    Returns:
        True if result is Ok, False if Err
        
    Example:
        >>> result = Ok(42)
        >>> is_ok(result)
        True
        >>> result = Err("error")
        >>> is_ok(result)
        False
    """
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    """Check if result is Err.
    
    Args:
        result: Result to check
        
    Returns:
        True if result is Err, False if Ok
        
    Example:
        >>> result = Ok(42)
        >>> is_err(result)
        False
        >>> result = Err("error")
        >>> is_err(result)
        True
    """
    return isinstance(result, Err)


def unwrap(result: Result[T, E]) -> T:
    """Extract the value from an Ok result.
    
    Args:
        result: Result to unwrap
        
    Returns:
        The success value if result is Ok
        
    Raises:
        ValueError: If result is Err
        
    Example:
        >>> result = Ok(42)
        >>> unwrap(result)
        42
        >>> result = Err("error")
        >>> unwrap(result)
        Traceback (most recent call last):
        ...
        ValueError: Called unwrap on an Err value: error
    """
    if isinstance(result, Ok):
        return result.value
    else:
        raise ValueError(f"Called unwrap on an Err value: {result.error}")


def unwrap_err(result: Result[T, E]) -> E:
    """Extract the error from an Err result.
    
    Args:
        result: Result to unwrap
        
    Returns:
        The error value if result is Err
        
    Raises:
        ValueError: If result is Ok
        
    Example:
        >>> result = Err("error")
        >>> unwrap_err(result)
        'error'
        >>> result = Ok(42)
        >>> unwrap_err(result)
        Traceback (most recent call last):
        ...
        ValueError: Called unwrap_err on an Ok value: 42
    """
    if isinstance(result, Err):
        return result.error
    else:
        raise ValueError(f"Called unwrap_err on an Ok value: {result.value}")


def unwrap_or(result: Result[T, E], default: T) -> T:
    """Extract the value from result or return default if Err.
    
    Args:
        result: Result to unwrap
        default: Default value to return if result is Err
        
    Returns:
        The success value if Ok, otherwise the default value
        
    Example:
        >>> result = Ok(42)
        >>> unwrap_or(result, 0)
        42
        >>> result = Err("error")
        >>> unwrap_or(result, 0)
        0
    """
    if isinstance(result, Ok):
        return result.value
    else:
        return default


def map_result(result: Result[T, E], func: Callable[[T], Any]) -> Result[Any, E]:
    """Apply a function to the Ok value, leaving Err unchanged.
    
    Args:
        result: Result to map over
        func: Function to apply to Ok value
        
    Returns:
        New Result with function applied to Ok value, or original Err
        
    Example:
        >>> result = Ok(42)
        >>> map_result(result, lambda x: x * 2)
        Ok(value=84)
        >>> result = Err("error")
        >>> map_result(result, lambda x: x * 2)
        Err(error='error')
    """
    if isinstance(result, Ok):
        return Ok(func(result.value))
    else:
        return result


def map_err(result: Result[T, E], func: Callable[[E], Any]) -> Result[T, Any]:
    """Apply a function to the Err value, leaving Ok unchanged.
    
    Args:
        result: Result to map over
        func: Function to apply to Err value
        
    Returns:
        New Result with function applied to Err value, or original Ok
        
    Example:
        >>> result = Err("error")
        >>> map_err(result, lambda e: f"Error: {e}")
        Err(error='Error: error')
        >>> result = Ok(42)
        >>> map_err(result, lambda e: f"Error: {e}")
        Ok(value=42)
    """
    if isinstance(result, Err):
        return Err(func(result.error))
    else:
        return result


def and_then(result: Result[T, E], func: Callable[[T], Result[Any, E]]) -> Result[Any, E]:
    """Chain operations that return Results (flatMap/bind).
    
    Args:
        result: Result to chain from
        func: Function that takes Ok value and returns a new Result
        
    Returns:
        Result of applying func to Ok value, or original Err
        
    Example:
        >>> def divide(x: int) -> Result[int, str]:
        ...     if x == 0:
        ...         return Err("division by zero")
        ...     return Ok(100 // x)
        >>> result = Ok(10)
        >>> and_then(result, divide)
        Ok(value=10)
        >>> result = Ok(0)
        >>> and_then(result, divide)
        Err(error='division by zero')
        >>> result = Err("initial error")
        >>> and_then(result, divide)
        Err(error='initial error')
    """
    if isinstance(result, Ok):
        return func(result.value)
    else:
        return result
