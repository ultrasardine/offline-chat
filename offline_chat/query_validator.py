"""Query validation utilities for database access.

This module provides functions to validate SQL queries for safety,
particularly ensuring that only read-only queries are executed.

The primary purpose is to prevent accidental or malicious write operations
(INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE) from being
executed through agent database access. This is a critical security feature
that ensures agents can only read data, not modify it.

Security Model:
    - Only SELECT queries are allowed
    - All write operation keywords are blocked
    - Case-insensitive detection
    - Whitespace normalization
    - Simple keyword matching (not full SQL parsing)

Limitations:
    This is a simple keyword-based validator, not a full SQL parser. It may:
    - Block legitimate queries with write keywords in comments or strings
    - Not catch all possible write operations in complex SQL dialects
    - Not validate SQL syntax (only checks for write operations)
    
    For production use with untrusted input, consider using database-level
    read-only users or more sophisticated SQL parsing libraries.

Usage Example:
    >>> from offline_chat.query_validator import is_read_only_query
    >>> 
    >>> # Valid read-only queries
    >>> is_read_only_query("SELECT * FROM users")
    True
    >>> is_read_only_query("  select id, name from products where price > 100  ")
    True
    >>> is_read_only_query("SELECT COUNT(*) FROM orders")
    True
    >>> 
    >>> # Invalid write operations
    >>> is_read_only_query("INSERT INTO users VALUES (1, 'John')")
    False
    >>> is_read_only_query("UPDATE users SET name = 'Jane' WHERE id = 1")
    False
    >>> is_read_only_query("DELETE FROM users WHERE id = 1")
    False
    >>> is_read_only_query("DROP TABLE users")
    False
    >>> is_read_only_query("ALTER TABLE users ADD COLUMN age INT")
    False
    >>> is_read_only_query("CREATE TABLE new_table (id INT)")
    False
    >>> is_read_only_query("TRUNCATE TABLE users")
    False

Integration with Database Tools:
    >>> from offline_chat.query_validator import is_read_only_query
    >>> 
    >>> def execute_query(query: str):
    ...     '''Execute a database query with safety validation.'''
    ...     if not is_read_only_query(query):
    ...         return "Error: Only SELECT queries are allowed (read-only mode)"
    ...     
    ...     # Execute the query...
    ...     return execute_sql(query)
    >>> 
    >>> # Agent attempts to query
    >>> result = execute_query("SELECT * FROM customers LIMIT 10")
    >>> # Success - query executed
    >>> 
    >>> # Agent attempts to modify data
    >>> result = execute_query("DELETE FROM customers WHERE id = 1")
    >>> # Returns: "Error: Only SELECT queries are allowed (read-only mode)"

Edge Cases:
    >>> # Query with comment containing write keyword (blocked)
    >>> is_read_only_query("SELECT * FROM users -- INSERT comment")
    False
    >>> 
    >>> # Query with string containing write keyword (blocked)
    >>> is_read_only_query("SELECT 'DELETE' as action FROM users")
    False
    >>> 
    >>> # Multiple statements (blocked if any contains write keyword)
    >>> is_read_only_query("SELECT * FROM users; DELETE FROM logs;")
    False
    >>> 
    >>> # Case variations (all detected)
    >>> is_read_only_query("insert into users values (1)")
    False
    >>> is_read_only_query("InSeRt InTo users values (1)")
    False
"""


def is_read_only_query(query: str) -> bool:
    """Check if a SQL query is read-only.
    
    This function validates that a query contains only SELECT statements
    and does not contain any write operations (INSERT, UPDATE, DELETE, etc.).
    
    Args:
        query: SQL query string to validate
        
    Returns:
        True if query is read-only (SELECT only), False otherwise
        
    Examples:
        >>> is_read_only_query("SELECT * FROM users")
        True
        >>> is_read_only_query("INSERT INTO users VALUES (1, 'John')")
        False
        >>> is_read_only_query("  select id from products  ")
        True
        >>> is_read_only_query("DELETE FROM users WHERE id = 1")
        False
    """
    # Normalize query: strip whitespace and convert to uppercase
    normalized = query.strip().upper()
    
    # Check for write operation keywords
    write_keywords = [
        "INSERT",
        "UPDATE", 
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE"
    ]
    
    # Check if any write keyword is present in the query
    for keyword in write_keywords:
        if keyword in normalized:
            return False
    
    # Query must start with SELECT (after normalization)
    return normalized.startswith("SELECT")
