"""Query result formatting for database operations.

This module provides the QueryResult dataclass for formatting database query
results in various formats (markdown tables, JSON) with proper handling of
NULL values, text truncation, and empty results.

The QueryResult class is designed to be used by database MCP servers to format
query results in a way that's easy for agents to understand and present to users.

Features:
    - Markdown table formatting with aligned columns
    - JSON serialization for structured data
    - NULL value representation as "NULL" string
    - Automatic truncation of long text fields (>200 chars)
    - Row count and execution time metadata
    - Truncation indicators for large result sets

Usage Example:
    >>> from offline_chat.query_result import QueryResult
    >>>
    >>> # Create a query result
    >>> result = QueryResult(
    ...     columns=["id", "name", "email", "created_at"],
    ...     rows=[
    ...         [1, "Alice", "alice@example.com", "2024-01-15"],
    ...         [2, "Bob", None, "2024-01-16"],
    ...         [3, "Charlie", "charlie@example.com", "2024-01-17"]
    ...     ],
    ...     row_count=3,
    ...     truncated=False,
    ...     execution_time_ms=45.2
    ... )
    >>>
    >>> # Format as markdown table
    >>> print(result.to_markdown_table())
    | id | name    | email               | created_at |
    |----|---------|---------------------|------------|
    | 1  | Alice   | alice@example.com   | 2024-01-15 |
    | 2  | Bob     | NULL                | 2024-01-16 |
    | 3  | Charlie | charlie@example.com | 2024-01-17 |

    Row count: 3
    Execution time: 45.2ms
    >>>
    >>> # Format as JSON
    >>> import json
    >>> print(json.dumps(json.loads(result.to_json()), indent=2))
    {
      "columns": ["id", "name", "email", "created_at"],
      "rows": [
        [1, "Alice", "alice@example.com", "2024-01-15"],
        [2, "Bob", null, "2024-01-16"],
        [3, "Charlie", "charlie@example.com", "2024-01-17"]
      ],
      "row_count": 3,
      "truncated": false,
      "execution_time_ms": 45.2
    }

Handling Large Results:
    >>> # Result with truncation
    >>> large_result = QueryResult(
    ...     columns=["id", "data"],
    ...     rows=[[i, f"Row {i}"] for i in range(100)],
    ...     row_count=1000,  # Total rows in database
    ...     truncated=True,  # Only first 100 returned
    ...     execution_time_ms=250.5
    ... )
    >>>
    >>> table = large_result.to_markdown_table()
    >>> # Output includes: "(Results truncated)"

Handling Long Text:
    >>> # Result with long text field
    >>> long_text = "A" * 300  # 300 character string
    >>> text_result = QueryResult(
    ...     columns=["id", "description"],
    ...     rows=[[1, long_text]],
    ...     row_count=1,
    ...     truncated=False,
    ...     execution_time_ms=10.0
    ... )
    >>>
    >>> # Long text is automatically truncated to 200 chars + "..."
    >>> table = text_result.to_markdown_table()
    >>> # Description column shows: "AAAA...AAA..." (200 chars + "...")
"""

import json
from dataclasses import dataclass
from typing import Any, List


@dataclass
class QueryResult:
    """Formatted database query result.

    Attributes:
        columns: List of column names from the query result
        rows: List of rows, where each row is a list of values
        row_count: Total number of rows in the result
        truncated: Whether the result was truncated (e.g., limited to 100 rows)
        execution_time_ms: Query execution time in milliseconds
    """

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: float

    def to_markdown_table(self) -> str:
        """Format result as a markdown table.

        Returns:
            Markdown-formatted table string with headers and rows.
            Returns "No rows found" message if result is empty.

        Examples:
            >>> result = QueryResult(
            ...     columns=["id", "name"],
            ...     rows=[[1, "Alice"], [2, "Bob"]],
            ...     row_count=2,
            ...     truncated=False,
            ...     execution_time_ms=45.2
            ... )
            >>> print(result.to_markdown_table())
            | id | name |
            |----|------|
            | 1  | Alice |
            | 2  | Bob |

            Row count: 2
            Execution time: 45.2ms
        """
        if self.row_count == 0:
            return "No rows found"

        # Format NULL values and truncate long text
        formatted_rows = []
        for row in self.rows:
            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append("NULL")
                elif isinstance(value, str) and len(value) > 200:
                    formatted_row.append(value[:200] + "...")
                else:
                    formatted_row.append(str(value))
            formatted_rows.append(formatted_row)

        # Calculate column widths
        col_widths = [len(col) for col in self.columns]
        for row in formatted_rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # Build header
        header_parts = []
        separator_parts = []
        for i, col in enumerate(self.columns):
            header_parts.append(col.ljust(col_widths[i]))
            separator_parts.append("-" * col_widths[i])

        lines = []
        lines.append("| " + " | ".join(header_parts) + " |")
        lines.append("| " + " | ".join(separator_parts) + " |")

        # Build rows
        for row in formatted_rows:
            row_parts = []
            for i, cell in enumerate(row):
                row_parts.append(cell.ljust(col_widths[i]))
            lines.append("| " + " | ".join(row_parts) + " |")

        # Add metadata
        lines.append("")
        lines.append(f"Row count: {self.row_count}")
        if self.truncated:
            lines.append("(Results truncated)")
        lines.append(f"Execution time: {self.execution_time_ms:.1f}ms")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Format result as JSON.

        Returns:
            JSON string representation of the query result.
            NULL values are represented as null in JSON.
            Long text fields are truncated to 200 characters.

        Examples:
            >>> result = QueryResult(
            ...     columns=["id", "name"],
            ...     rows=[[1, "Alice"], [2, None]],
            ...     row_count=2,
            ...     truncated=False,
            ...     execution_time_ms=45.2
            ... )
            >>> print(result.to_json())
            {
              "columns": ["id", "name"],
              "rows": [[1, "Alice"], [2, null]],
              "row_count": 2,
              "truncated": false,
              "execution_time_ms": 45.2
            }
        """
        # Format rows with NULL handling and text truncation
        formatted_rows = []
        for row in self.rows:
            formatted_row = []
            for value in row:
                if value is None:
                    formatted_row.append(None)
                elif isinstance(value, str) and len(value) > 200:
                    formatted_row.append(value[:200] + "...")
                else:
                    formatted_row.append(value)
            formatted_rows.append(formatted_row)

        result_dict = {
            "columns": self.columns,
            "rows": formatted_rows,
            "row_count": self.row_count,
            "truncated": self.truncated,
            "execution_time_ms": self.execution_time_ms,
        }

        return json.dumps(result_dict, indent=2)
