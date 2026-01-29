"""Access level validation for database queries.

This module provides validation of SQL queries against assigned access levels,
ensuring agents can only execute queries permitted by their access level.
"""

import re
from typing import List

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.result import Err, Ok, Result


class AccessLevelValidator:
    """Validates queries against assigned access levels.

    This class provides static methods to validate SQL queries against the access
    level assigned to an agent for a specific database connection. It parses queries
    to identify operation types and table names, then checks if the operation is
    permitted by the access level.
    """

    # SQL operation keywords
    READ_OPERATIONS = {"SELECT"}
    WRITE_OPERATIONS = {"INSERT", "UPDATE", "DELETE"}
    DDL_OPERATIONS = {"CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME"}

    @staticmethod
    def validate_query(
        query: str,
        access_level: AccessLevel,
        allowed_tables: List[str]
    ) -> Result[None, str]:
        """Validate a query against the assigned access level.

        This method parses the query to identify the operation type and table names,
        then checks if the operation is allowed by the access level. For table-specific
        access levels, it also verifies that all referenced tables are in the allowed list.

        Steps:
        1. Parse query to identify operation type (SELECT, INSERT, UPDATE, DELETE, etc.)
        2. Extract table names from query
        3. Check if operation is allowed by access level
        4. For table-specific access, check if tables are in allowed list
        5. Return success or error with details

        Args:
            query: SQL query to validate
            access_level: Access level to enforce
            allowed_tables: List of allowed tables (for table-specific access)

        Returns:
            Result with None on success or error message on failure

        Examples:
            >>> validator = AccessLevelValidator()
            >>> result = validator.validate_query(
            ...     "SELECT * FROM users",
            ...     AccessLevel.READ_ONLY,
            ...     []
            ... )
            >>> is_ok(result)
            True

            >>> result = validator.validate_query(
            ...     "DELETE FROM users",
            ...     AccessLevel.READ_ONLY,
            ...     []
            ... )
            >>> is_err(result)
            True
        """
        # Normalize query (strip whitespace, convert to uppercase for parsing)
        normalized_query = query.strip()
        if not normalized_query:
            return Err("Query cannot be empty")

        # Parse operation type
        operation = AccessLevelValidator._parse_query_operation(normalized_query)
        if not operation:
            return Err("Unable to parse query operation")

        # Extract table names
        table_names = AccessLevelValidator._extract_table_names(normalized_query)

        # Validate based on access level
        if access_level == AccessLevel.READ_ONLY:
            # Only SELECT queries allowed
            if operation not in AccessLevelValidator.READ_OPERATIONS:
                return Err(
                    f"Query not allowed with read-only access: {operation} operation is not permitted"
                )

        elif access_level == AccessLevel.READ_WRITE:
            # SELECT, INSERT, UPDATE, DELETE allowed; DDL not allowed
            if operation in AccessLevelValidator.DDL_OPERATIONS:
                return Err(
                    f"Query not allowed with read-write access: {operation} operation is not permitted (DDL operations not allowed)"
                )
            if operation not in (AccessLevelValidator.READ_OPERATIONS | AccessLevelValidator.WRITE_OPERATIONS):
                return Err(
                    f"Query not allowed with read-write access: {operation} operation is not permitted"
                )

        elif access_level == AccessLevel.TABLE_SPECIFIC_READ:
            # Only SELECT queries on allowed tables
            if operation not in AccessLevelValidator.READ_OPERATIONS:
                return Err(
                    f"Query not allowed with table-specific-read access: {operation} operation is not permitted"
                )
            # Check if all tables are in allowed list
            if not allowed_tables:
                return Err("Table-specific access requires allowed_tables to be specified")

            disallowed_tables = [t for t in table_names if t not in allowed_tables]
            if disallowed_tables:
                return Err(
                    f"Query not allowed with table-specific-read access: tables {disallowed_tables} are not in allowed list"
                )

        elif access_level == AccessLevel.TABLE_SPECIFIC_READ_WRITE:
            # SELECT, INSERT, UPDATE, DELETE on allowed tables; DDL not allowed
            if operation in AccessLevelValidator.DDL_OPERATIONS:
                return Err(
                    f"Query not allowed with table-specific-read-write access: {operation} operation is not permitted (DDL operations not allowed)"
                )
            if operation not in (AccessLevelValidator.READ_OPERATIONS | AccessLevelValidator.WRITE_OPERATIONS):
                return Err(
                    f"Query not allowed with table-specific-read-write access: {operation} operation is not permitted"
                )
            # Check if all tables are in allowed list
            if not allowed_tables:
                return Err("Table-specific access requires allowed_tables to be specified")

            disallowed_tables = [t for t in table_names if t not in allowed_tables]
            if disallowed_tables:
                return Err(
                    f"Query not allowed with table-specific-read-write access: tables {disallowed_tables} are not in allowed list"
                )

        return Ok(None)

    @staticmethod
    def _parse_query_operation(query: str) -> str:
        """Extract operation type from query (SELECT, INSERT, UPDATE, DELETE, etc.).

        This method identifies the primary SQL operation by looking for operation
        keywords at the beginning of the query (after stripping comments and whitespace).

        Args:
            query: SQL query to parse

        Returns:
            Operation type as uppercase string (e.g., "SELECT", "INSERT"), or empty string if not found

        Examples:
            >>> AccessLevelValidator._parse_query_operation("SELECT * FROM users")
            'SELECT'
            >>> AccessLevelValidator._parse_query_operation("  select * from users")
            'SELECT'
            >>> AccessLevelValidator._parse_query_operation("INSERT INTO users VALUES (1, 'John')")
            'INSERT'
            >>> AccessLevelValidator._parse_query_operation("-- comment\\nSELECT * FROM users")
            'SELECT'
        """
        # Remove leading/trailing whitespace
        query = query.strip()

        # Remove SQL comments (-- style and /* */ style)
        # Remove single-line comments
        query = re.sub(r'--[^\n]*', '', query)
        # Remove multi-line comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

        # Strip whitespace again after removing comments
        query = query.strip()

        if not query:
            return ""

        # Extract first word (the operation)
        match = re.match(r'^\s*(\w+)', query, re.IGNORECASE)
        if match:
            operation = match.group(1).upper()
            return operation

        return ""

    @staticmethod
    def _extract_table_names(query: str) -> List[str]:
        """Extract table names referenced in query.

        This method attempts to identify table names in SQL queries by looking for
        common patterns (FROM, JOIN, INTO, UPDATE). It handles basic SQL syntax but
        may not cover all edge cases (subqueries, CTEs, etc.).

        Args:
            query: SQL query to parse

        Returns:
            List of table names found in the query (may be empty)

        Examples:
            >>> AccessLevelValidator._extract_table_names("SELECT * FROM users")
            ['users']
            >>> AccessLevelValidator._extract_table_names("SELECT * FROM users u JOIN orders o ON u.id = o.user_id")
            ['users', 'orders']
            >>> AccessLevelValidator._extract_table_names("INSERT INTO users (name) VALUES ('John')")
            ['users']
            >>> AccessLevelValidator._extract_table_names("UPDATE users SET name = 'Jane' WHERE id = 1")
            ['users']
        """
        # Remove SQL comments
        query = re.sub(r'--[^\n]*', '', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

        # Convert to uppercase for pattern matching
        query_upper = query.upper()

        table_names = []

        # Pattern 1: FROM clause - matches "FROM table_name" or "FROM schema.table_name"
        # Handles optional alias: "FROM table_name alias" or "FROM table_name AS alias"
        from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        from_matches = re.finditer(from_pattern, query_upper)
        for match in from_matches:
            table_name = match.group(1)
            # If schema.table format, extract just the table name
            if '.' in table_name:
                table_name = table_name.split('.')[-1]
            # Get the actual case from original query
            start, end = match.span(1)
            actual_table = query[start:end]
            if '.' in actual_table:
                actual_table = actual_table.split('.')[-1]
            table_names.append(actual_table.lower())

        # Pattern 2: JOIN clause - matches "JOIN table_name" or "JOIN schema.table_name"
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        join_matches = re.finditer(join_pattern, query_upper)
        for match in join_matches:
            table_name = match.group(1)
            if '.' in table_name:
                table_name = table_name.split('.')[-1]
            start, end = match.span(1)
            actual_table = query[start:end]
            if '.' in actual_table:
                actual_table = actual_table.split('.')[-1]
            table_names.append(actual_table.lower())

        # Pattern 3: INTO clause (for INSERT) - matches "INTO table_name"
        into_pattern = r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        into_matches = re.finditer(into_pattern, query_upper)
        for match in into_matches:
            table_name = match.group(1)
            if '.' in table_name:
                table_name = table_name.split('.')[-1]
            start, end = match.span(1)
            actual_table = query[start:end]
            if '.' in actual_table:
                actual_table = actual_table.split('.')[-1]
            table_names.append(actual_table.lower())

        # Pattern 4: UPDATE clause - matches "UPDATE table_name"
        update_pattern = r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
        update_matches = re.finditer(update_pattern, query_upper)
        for match in update_matches:
            table_name = match.group(1)
            if '.' in table_name:
                table_name = table_name.split('.')[-1]
            start, end = match.span(1)
            actual_table = query[start:end]
            if '.' in actual_table:
                actual_table = actual_table.split('.')[-1]
            table_names.append(actual_table.lower())

        # Remove duplicates while preserving order
        seen = set()
        unique_tables = []
        for table in table_names:
            if table not in seen:
                seen.add(table)
                unique_tables.append(table)

        return unique_tables
