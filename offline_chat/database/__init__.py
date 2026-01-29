"""Database connection management module."""

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.connection import DatabaseConnection
from offline_chat.database.connection_assignment import AgentConnectionAssignment
from offline_chat.database.manager import DatabaseConnectionManager
from offline_chat.database.result import (
    Err,
    Ok,
    Result,
    and_then,
    is_err,
    is_ok,
    map_err,
    map_result,
    unwrap,
    unwrap_err,
    unwrap_or,
)
from offline_chat.database.validator import ConnectionValidator

__all__ = [
    "AccessLevel",
    "AgentConnectionAssignment",
    "DatabaseConnection",
    "DatabaseConnectionManager",
    "Ok",
    "Err",
    "Result",
    "is_ok",
    "is_err",
    "unwrap",
    "unwrap_err",
    "unwrap_or",
    "map_result",
    "map_err",
    "and_then",
    "ConnectionValidator",
]
