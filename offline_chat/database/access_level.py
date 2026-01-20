"""Database access level enumeration for agent-connection assignments.

This module defines the access levels that can be assigned to agents when they
are connected to databases, enabling fine-grained access control.
"""

from enum import Enum


class AccessLevel(str, Enum):
    """Database access levels for agent-connection assignments.
    
    This enum defines the different levels of database access that can be granted
    to agents when they are assigned to database connections. Access levels control
    what types of queries an agent can execute.
    
    Attributes:
        READ_ONLY: Agent can only execute SELECT queries. No data modification allowed.
        READ_WRITE: Agent can execute SELECT, INSERT, UPDATE, and DELETE queries.
                   DDL operations (CREATE, DROP, ALTER) are not allowed.
        TABLE_SPECIFIC_READ: Agent can only execute SELECT queries on specific tables
                            defined in the allowed_tables list.
        TABLE_SPECIFIC_READ_WRITE: Agent can execute SELECT, INSERT, UPDATE, and DELETE
                                   queries, but only on specific tables defined in the
                                   allowed_tables list.
    """
    
    READ_ONLY = "read-only"
    READ_WRITE = "read-write"
    TABLE_SPECIFIC_READ = "table-specific-read"
    TABLE_SPECIFIC_READ_WRITE = "table-specific-read-write"
