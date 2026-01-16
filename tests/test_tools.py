"""Tests for web search tool functionality.

This module contains property-based tests and unit tests for the WebSearchTool
class and format_search_results function.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.search import SearchResult
from offline_chat.tools import WebSearchTool, format_search_results


class TestToolSchemaValidity:
    """Property 1: Tool Schema Validity.

    Feature: web-search, Property 1: Tool Schema Validity
    Validates: Requirements 1.1, 1.2, 1.3

    For any WebSearchTool instance, the generated tool schema SHALL be a valid
    dictionary containing "type" set to "function", a "function" object with
    "name", "description", and "parameters" fields, where parameters includes
    "query" as a required string property.
    """

    @settings(max_examples=100)
    @given(timeout=st.integers(min_value=1, max_value=120))
    def test_tool_schema_has_required_structure(self, timeout: int):
        """Tool schema should have type, function with name, description, parameters."""
        from offline_chat.search import DuckDuckGoProvider

        provider = DuckDuckGoProvider(timeout=timeout)
        tool = WebSearchTool(provider=provider)
        schema = tool.get_tool_schema()

        # Verify top-level structure
        assert isinstance(schema, dict), "Schema must be a dictionary"
        assert "type" in schema, "Schema must have 'type' field"
        assert schema["type"] == "function", "Schema type must be 'function'"
        assert "function" in schema, "Schema must have 'function' field"

        # Verify function structure
        func = schema["function"]
        assert isinstance(func, dict), "Function must be a dictionary"
        assert "name" in func, "Function must have 'name' field"
        assert "description" in func, "Function must have 'description' field"
        assert "parameters" in func, "Function must have 'parameters' field"

        # Verify name is web_search
        assert func["name"] == "web_search", "Function name must be 'web_search'"

        # Verify parameters structure
        params = func["parameters"]
        assert isinstance(params, dict), "Parameters must be a dictionary"
        assert "type" in params, "Parameters must have 'type' field"
        assert params["type"] == "object", "Parameters type must be 'object'"
        assert "required" in params, "Parameters must have 'required' field"
        assert "properties" in params, "Parameters must have 'properties' field"

        # Verify query is required
        assert "query" in params["required"], "'query' must be in required list"

        # Verify query property
        props = params["properties"]
        assert "query" in props, "Properties must include 'query'"
        assert props["query"]["type"] == "string", "Query type must be 'string'"

    def test_default_provider_schema(self):
        """Tool with default provider should produce valid schema."""
        tool = WebSearchTool()
        schema = tool.get_tool_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_search"
        assert "query" in schema["function"]["parameters"]["required"]

    def test_schema_includes_max_results_parameter(self):
        """Schema should include optional max_results parameter."""
        tool = WebSearchTool()
        schema = tool.get_tool_schema()

        props = schema["function"]["parameters"]["properties"]
        assert "max_results" in props, "Properties should include 'max_results'"
        assert props["max_results"]["type"] == "integer"


class TestSearchResultFormatting:
    """Property 6: Search Result Formatting.

    Feature: web-search, Property 6: Search Result Formatting
    Validates: Requirements 5.1, 5.3

    For any non-empty list of SearchResult objects, the formatted output SHALL
    contain numbered entries (1., 2., etc.), and each entry SHALL include the
    result's title and href.
    """

    @settings(max_examples=100)
    @given(
        results=st.lists(
            st.builds(
                SearchResult,
                title=st.text(min_size=1, max_size=100),
                href=st.text(min_size=1, max_size=200),
                body=st.text(min_size=0, max_size=500),
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_formatted_results_contain_numbered_entries(self, results: list[SearchResult]):
        """Formatted results should contain numbered entries with title and URL."""
        formatted = format_search_results(results)

        for i, result in enumerate(results, 1):
            # Check numbered entry exists
            assert f"{i}." in formatted, f"Missing numbered entry {i}."
            # Check title is present
            assert result.title in formatted, f"Missing title: {result.title}"
            # Check URL is present
            assert result.href in formatted, f"Missing URL: {result.href}"

    def test_empty_results_returns_no_results_message(self):
        """Empty results list should return appropriate message."""
        formatted = format_search_results([])
        assert "No search results found" in formatted

    def test_body_truncation(self):
        """Long body text should be truncated to 200 characters."""
        long_body = "x" * 300
        result = SearchResult(
            title="Test Title",
            href="https://example.com",
            body=long_body,
        )
        formatted = format_search_results([result])

        # Should contain truncated body with ellipsis
        assert "..." in formatted
        # Should not contain full body
        assert long_body not in formatted
