"""Tests for QueryResult dataclass and formatting methods.

This module contains both unit tests and property-based tests for the
QueryResult class, validating requirements 8.1, 8.2, 8.3, 8.4, and 8.5.
"""

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from offline_chat.query_result import QueryResult

# ============================================================================
# Unit Tests
# ============================================================================


class TestQueryResultBasic:
    """Basic unit tests for QueryResult functionality."""

    def test_create_query_result(self):
        """Test creating a basic QueryResult instance."""
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            truncated=False,
            execution_time_ms=45.2,
        )

        assert result.columns == ["id", "name"]
        assert result.rows == [[1, "Alice"], [2, "Bob"]]
        assert result.row_count == 2
        assert result.truncated is False
        assert result.execution_time_ms == 45.2

    def test_empty_result_markdown(self):
        """Test that empty results return 'No rows found' message.

        Validates: Requirement 8.4
        """
        result = QueryResult(
            columns=["id", "name"], rows=[], row_count=0, truncated=False, execution_time_ms=10.0
        )

        markdown = result.to_markdown_table()
        assert markdown == "No rows found"

    def test_null_values_in_markdown(self):
        """Test that NULL values are represented as 'NULL' in markdown.

        Validates: Requirement 8.2
        """
        result = QueryResult(
            columns=["id", "name", "email"],
            rows=[[1, "Alice", None], [2, None, "bob@example.com"]],
            row_count=2,
            truncated=False,
            execution_time_ms=20.0,
        )

        markdown = result.to_markdown_table()
        assert "NULL" in markdown
        assert markdown.count("NULL") == 2

    def test_null_values_in_json(self):
        """Test that NULL values are represented as null in JSON.

        Validates: Requirement 8.2
        """
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, None], [2, "Bob"]],
            row_count=2,
            truncated=False,
            execution_time_ms=20.0,
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["rows"][0][1] is None
        assert parsed["rows"][1][1] == "Bob"

    def test_long_text_truncation_markdown(self):
        """Test that long text fields are truncated to 200 characters in markdown.

        Validates: Requirement 8.3
        """
        long_text = "A" * 250
        result = QueryResult(
            columns=["id", "description"],
            rows=[[1, long_text]],
            row_count=1,
            truncated=False,
            execution_time_ms=15.0,
        )

        markdown = result.to_markdown_table()
        # Should contain truncated text with ellipsis
        assert "A" * 200 + "..." in markdown
        assert "A" * 250 not in markdown

    def test_long_text_truncation_json(self):
        """Test that long text fields are truncated to 200 characters in JSON.

        Validates: Requirement 8.3
        """
        long_text = "B" * 300
        result = QueryResult(
            columns=["id", "content"],
            rows=[[1, long_text]],
            row_count=1,
            truncated=False,
            execution_time_ms=15.0,
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)

        assert parsed["rows"][0][1] == "B" * 200 + "..."
        assert len(parsed["rows"][0][1]) == 203  # 200 + "..."

    def test_markdown_table_structure(self):
        """Test that markdown table has proper structure with headers.

        Validates: Requirement 8.1
        """
        result = QueryResult(
            columns=["id", "name", "amount"],
            rows=[[1, "Product A", 99.99], [2, "Product B", 149.99]],
            row_count=2,
            truncated=False,
            execution_time_ms=45.2,
        )

        markdown = result.to_markdown_table()
        lines = markdown.split("\n")

        # Check header row
        assert "id" in lines[0]
        assert "name" in lines[0]
        assert "amount" in lines[0]

        # Check separator row
        assert "---" in lines[1]

        # Check data rows
        assert "Product A" in markdown
        assert "Product B" in markdown
        assert "99.99" in markdown
        assert "149.99" in markdown

    def test_row_count_in_metadata(self):
        """Test that row count is included in result metadata.

        Validates: Requirement 8.5
        """
        result = QueryResult(
            columns=["id"],
            rows=[[1], [2], [3]],
            row_count=3,
            truncated=False,
            execution_time_ms=30.0,
        )

        markdown = result.to_markdown_table()
        assert "Row count: 3" in markdown

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["row_count"] == 3

    def test_truncated_flag_in_markdown(self):
        """Test that truncated flag is shown in markdown output."""
        result = QueryResult(
            columns=["id"],
            rows=[[i] for i in range(100)],
            row_count=150,  # More rows exist but truncated to 100
            truncated=True,
            execution_time_ms=100.0,
        )

        markdown = result.to_markdown_table()
        assert "(Results truncated)" in markdown

    def test_execution_time_in_output(self):
        """Test that execution time is included in output."""
        result = QueryResult(
            columns=["id"], rows=[[1]], row_count=1, truncated=False, execution_time_ms=123.456
        )

        markdown = result.to_markdown_table()
        assert "123.5ms" in markdown

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["execution_time_ms"] == 123.456


# ============================================================================
# Property-Based Tests
# ============================================================================


@pytest.mark.property_test
class TestQueryResultProperties:
    """Property-based tests for QueryResult."""

    @given(
        columns=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10),
        row_count=st.integers(min_value=0, max_value=1000),
        truncated=st.booleans(),
        execution_time_ms=st.floats(
            min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    def test_property_29_table_formatting_with_headers(
        self, columns, row_count, truncated, execution_time_ms
    ):
        """Property 29: Table formatting with headers.

        For any query result with columns and rows, formatting should produce
        a structured table that includes all column headers.

        **Validates: Requirements 8.1**
        """
        # Generate rows matching the columns
        rows = [[f"val_{i}_{j}" for j in range(len(columns))] for i in range(min(row_count, 10))]

        result = QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            truncated=truncated,
            execution_time_ms=execution_time_ms,
        )

        if row_count > 0:
            markdown = result.to_markdown_table()

            # All column headers should be present in the output
            for column in columns:
                assert column in markdown

            # Should have table structure (pipes and separators)
            assert "|" in markdown
            assert "---" in markdown

    @given(
        columns=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda s: s.upper() != "NULL"),
            min_size=1,
            max_size=5,
        ),
        null_positions=st.lists(
            st.integers(min_value=0, max_value=4), min_size=0, max_size=5, unique=True
        ),
    )
    def test_property_30_null_value_representation(self, columns, null_positions):
        """Property 30: NULL value representation.

        For any query result containing NULL values, the formatted output
        should represent each NULL as the string "NULL".

        **Validates: Requirements 8.2**
        """
        # Filter null_positions to only include valid indices for the columns
        valid_null_positions = [pos for pos in null_positions if pos < len(columns)]

        # Create a row with NULLs at specified positions
        row = []
        for i in range(len(columns)):
            if i in valid_null_positions:
                row.append(None)
            else:
                row.append(f"value_{i}")

        result = QueryResult(
            columns=columns, rows=[row], row_count=1, truncated=False, execution_time_ms=10.0
        )

        markdown = result.to_markdown_table()
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # Count NULLs in markdown (excluding column headers)
        # Split by lines and only count in data rows (after the separator line)
        lines = markdown.split("\n")
        data_lines = [line for line in lines if line and not line.startswith("|---")]
        # Skip header line (first line)
        if len(data_lines) > 1:
            data_content = "\n".join(data_lines[1:])
            null_count_markdown = data_content.count("NULL")
        else:
            null_count_markdown = 0
        assert null_count_markdown == len(valid_null_positions)

        # Count nulls in JSON
        null_count_json = sum(1 for val in parsed["rows"][0] if val is None)
        assert null_count_json == len(valid_null_positions)

    @given(
        text_length=st.integers(min_value=201, max_value=1000),
        num_long_fields=st.integers(min_value=1, max_value=3),
    )
    def test_property_31_text_field_truncation(self, text_length, num_long_fields):
        """Property 31: Text field truncation.

        For any query result containing text fields longer than 200 characters,
        the formatted output should truncate them to 200 characters with an ellipsis.

        **Validates: Requirements 8.3**
        """
        columns = [f"col_{i}" for i in range(num_long_fields)]
        long_texts = ["X" * text_length for _ in range(num_long_fields)]

        result = QueryResult(
            columns=columns, rows=[long_texts], row_count=1, truncated=False, execution_time_ms=10.0
        )

        markdown = result.to_markdown_table()
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # Check markdown truncation
        for i in range(num_long_fields):
            expected_truncated = "X" * 200 + "..."
            assert expected_truncated in markdown

        # Check JSON truncation
        for value in parsed["rows"][0]:
            assert len(value) == 203  # 200 + "..."
            assert value.endswith("...")

    @given(
        row_count=st.integers(min_value=0, max_value=1000),
        actual_rows=st.integers(min_value=0, max_value=100),
    )
    def test_property_32_row_count_metadata(self, row_count, actual_rows):
        """Property 32: Row count metadata.

        For any query result, the result object should include a row_count
        field that equals the actual number of rows returned.

        **Validates: Requirements 8.5**
        """
        columns = ["id", "name"]
        rows = [[i, f"name_{i}"] for i in range(actual_rows)]

        result = QueryResult(
            columns=columns,
            rows=rows,
            row_count=row_count,
            truncated=(row_count > actual_rows),
            execution_time_ms=10.0,
        )

        # row_count field should be accessible
        assert result.row_count == row_count

        # row_count should be in JSON output
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["row_count"] == row_count

        # row_count should be in markdown output (if not empty)
        if row_count > 0:
            markdown = result.to_markdown_table()
            assert f"Row count: {row_count}" in markdown


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestQueryResultEdgeCases:
    """Edge case tests for QueryResult."""

    def test_single_column_single_row(self):
        """Test minimal result with one column and one row."""
        result = QueryResult(
            columns=["value"], rows=[[42]], row_count=1, truncated=False, execution_time_ms=5.0
        )

        markdown = result.to_markdown_table()
        assert "value" in markdown
        assert "42" in markdown

    def test_many_columns(self):
        """Test result with many columns."""
        columns = [f"col_{i}" for i in range(20)]
        rows = [[i for i in range(20)]]

        result = QueryResult(
            columns=columns, rows=rows, row_count=1, truncated=False, execution_time_ms=50.0
        )

        markdown = result.to_markdown_table()
        for col in columns:
            assert col in markdown

    def test_mixed_data_types(self):
        """Test result with mixed data types."""
        result = QueryResult(
            columns=["int_col", "float_col", "str_col", "bool_col", "null_col"],
            rows=[[42, 3.14, "hello", True, None]],
            row_count=1,
            truncated=False,
            execution_time_ms=15.0,
        )

        markdown = result.to_markdown_table()
        assert "42" in markdown
        assert "3.14" in markdown
        assert "hello" in markdown
        assert "True" in markdown
        assert "NULL" in markdown

    def test_exactly_200_chars_no_truncation(self):
        """Test that text with exactly 200 characters is not truncated."""
        text_200 = "A" * 200
        result = QueryResult(
            columns=["text"],
            rows=[[text_200]],
            row_count=1,
            truncated=False,
            execution_time_ms=10.0,
        )

        markdown = result.to_markdown_table()
        # Should not have ellipsis since it's exactly 200 chars
        assert "..." not in markdown
        assert text_200 in markdown

    def test_201_chars_gets_truncated(self):
        """Test that text with 201 characters gets truncated."""
        text_201 = "B" * 201
        result = QueryResult(
            columns=["text"],
            rows=[[text_201]],
            row_count=1,
            truncated=False,
            execution_time_ms=10.0,
        )

        markdown = result.to_markdown_table()
        assert "B" * 200 + "..." in markdown
        assert text_201 not in markdown

    def test_special_characters_in_data(self):
        """Test handling of special characters in data."""
        result = QueryResult(
            columns=["data"],
            rows=[["Line 1\nLine 2"], ["Tab\there"], ['Quote"test']],
            row_count=3,
            truncated=False,
            execution_time_ms=20.0,
        )

        markdown = result.to_markdown_table()
        json_str = result.to_json()

        # Should handle special characters without crashing
        assert markdown is not None
        assert json_str is not None
        parsed = json.loads(json_str)
        assert len(parsed["rows"]) == 3
