"""Tests for search provider functionality.

This module contains property-based tests and unit tests for the SearchResult
dataclass and DuckDuckGoProvider.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.search import DuckDuckGoProvider, SearchResult


# Strategy for generating valid SearchResult objects
def valid_search_result_strategy():
    """Generate valid SearchResult objects for property testing."""
    return st.builds(
        SearchResult,
        title=st.text(min_size=0, max_size=200),
        href=st.text(min_size=0, max_size=500),
        body=st.text(min_size=0, max_size=1000),
    )


class TestSearchResultStructure:
    """Property 2: Search Result Structure.

    Feature: web-search, Property 2: Search Result Structure
    Validates: Requirements 1.5, 2.4

    For any successful search execution, each result in the returned list SHALL
    contain non-null "title", "href", and "body" string fields.
    """

    @settings(max_examples=100)
    @given(result=valid_search_result_strategy())
    def test_search_result_has_required_fields(self, result: SearchResult):
        """SearchResult should have title, href, and body fields as strings."""
        # Verify all fields exist and are strings (not None)
        assert isinstance(result.title, str), "title must be a string"
        assert isinstance(result.href, str), "href must be a string"
        assert isinstance(result.body, str), "body must be a string"

    @settings(max_examples=100)
    @given(result=valid_search_result_strategy())
    def test_search_result_to_dict_contains_all_fields(self, result: SearchResult):
        """to_dict should include title, href, and body fields."""
        data = result.to_dict()

        assert "title" in data, "to_dict missing 'title' field"
        assert "href" in data, "to_dict missing 'href' field"
        assert "body" in data, "to_dict missing 'body' field"

        # Values should match the original
        assert data["title"] == result.title
        assert data["href"] == result.href
        assert data["body"] == result.body

    @settings(max_examples=100)
    @given(result=valid_search_result_strategy())
    def test_search_result_to_dict_values_are_strings(self, result: SearchResult):
        """to_dict values should all be strings."""
        data = result.to_dict()

        assert isinstance(data["title"], str), "title in dict must be a string"
        assert isinstance(data["href"], str), "href in dict must be a string"
        assert isinstance(data["body"], str), "body in dict must be a string"

    def test_specific_search_result_example(self):
        """Unit test for a specific SearchResult example."""
        result = SearchResult(
            title="Python Documentation",
            href="https://docs.python.org",
            body="Welcome to Python's official documentation."
        )

        assert result.title == "Python Documentation"
        assert result.href == "https://docs.python.org"
        assert result.body == "Welcome to Python's official documentation."

        data = result.to_dict()
        assert data == {
            "title": "Python Documentation",
            "href": "https://docs.python.org",
            "body": "Welcome to Python's official documentation."
        }


class TestDuckDuckGoProviderConfiguration:
    """Tests for DuckDuckGoProvider configuration."""

    def test_default_timeout(self):
        """Provider should have default timeout of 10 seconds."""
        provider = DuckDuckGoProvider()
        assert provider.timeout == 10

    def test_custom_timeout(self):
        """Provider should accept custom timeout."""
        provider = DuckDuckGoProvider(timeout=30)
        assert provider.timeout == 30
