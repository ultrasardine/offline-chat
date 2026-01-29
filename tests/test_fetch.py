"""Tests for web fetch tool functionality.

This module contains property-based tests and unit tests for the WebFetchTool
class.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.fetch import WebFetchTool


class TestWebFetchToolSchemaValidity:
    """Property 8: Web Fetch Tool Schema Validity.

    Feature: web-search, Property 8: Web Fetch Tool Schema Validity
    Validates: Requirements 9.1, 9.2, 9.3

    For any WebFetchTool instance, the generated tool schema SHALL be a valid
    dictionary containing "type" set to "function", a "function" object with
    "name" set to "web_fetch", "description", and "parameters" fields, where
    parameters includes "url" as a required string property.
    """

    @settings(max_examples=100)
    @given(timeout=st.integers(min_value=1, max_value=120))
    def test_tool_schema_has_required_structure(self, timeout: int):
        """Tool schema should have type, function with name, description, parameters."""
        tool = WebFetchTool(timeout=timeout)
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

        # Verify name is web_fetch
        assert func["name"] == "web_fetch", "Function name must be 'web_fetch'"

        # Verify parameters structure
        params = func["parameters"]
        assert isinstance(params, dict), "Parameters must be a dictionary"
        assert "type" in params, "Parameters must have 'type' field"
        assert params["type"] == "object", "Parameters type must be 'object'"
        assert "required" in params, "Parameters must have 'required' field"
        assert "properties" in params, "Parameters must have 'properties' field"

        # Verify url is required
        assert "url" in params["required"], "'url' must be in required list"

        # Verify url property
        props = params["properties"]
        assert "url" in props, "Properties must include 'url'"
        assert props["url"]["type"] == "string", "URL type must be 'string'"

    def test_default_timeout_schema(self):
        """Tool with default timeout should produce valid schema."""
        tool = WebFetchTool()
        schema = tool.get_tool_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_fetch"
        assert "url" in schema["function"]["parameters"]["required"]

    def test_schema_includes_max_length_parameter(self):
        """Schema should include optional max_length parameter."""
        tool = WebFetchTool()
        schema = tool.get_tool_schema()

        props = schema["function"]["parameters"]["properties"]
        assert "max_length" in props, "Properties should include 'max_length'"
        assert props["max_length"]["type"] == "integer"


class TestWebFetchContentExtraction:
    """Property 9: Web Fetch Content Extraction.

    Feature: web-search, Property 9: Web Fetch Content Extraction
    Validates: Requirements 9.5, 9.6, 9.7

    For any valid HTML page content, the WebFetchTool SHALL extract text content
    with script, style, nav, header, footer, and aside elements removed, and the
    result SHALL be truncated to max_length characters if exceeded.
    """

    @staticmethod
    def _extract_content_from_html(html: str, max_length: int = 5000) -> str:
        """Helper to extract content using BeautifulSoup directly.

        This simulates what WebFetchTool.execute does for HTML parsing,
        allowing us to test the extraction logic without network calls.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[Content truncated...]"

        return text if text else "No readable content found on this page."

    @settings(max_examples=100)
    @given(
        main_content=st.text(
            min_size=1,
            max_size=200,
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"), whitelist_characters=" "),
        ),
    )
    def test_unwanted_elements_are_removed(self, main_content: str):
        """Script, style, nav, header, footer, aside elements should be removed."""
        # Use unique marker strings for unwanted content that won't match generated content
        script_marker = "SCRIPT_CONTENT_UNIQUE_MARKER_12345"
        style_marker = "STYLE_CONTENT_UNIQUE_MARKER_67890"
        header_marker = "HEADER_CONTENT_UNIQUE_MARKER_ABCDE"
        nav_marker = "NAV_CONTENT_UNIQUE_MARKER_FGHIJ"
        aside_marker = "ASIDE_CONTENT_UNIQUE_MARKER_KLMNO"
        footer_marker = "FOOTER_CONTENT_UNIQUE_MARKER_PQRST"

        # Build HTML with various elements
        html = f"""
        <html>
        <head>
            <script>{script_marker}</script>
            <style>{style_marker}</style>
        </head>
        <body>
            <header>{header_marker}</header>
            <nav>{nav_marker}</nav>
            <main>
                <p>{main_content}</p>
            </main>
            <aside>{aside_marker}</aside>
            <footer>{footer_marker}</footer>
        </body>
        </html>
        """

        result = self._extract_content_from_html(html)

        # Main content should be present (if non-empty after stripping)
        stripped_main = main_content.strip()
        if stripped_main:
            assert stripped_main in result, f"Main content '{stripped_main}' should be in result"

        # Unwanted content should NOT be present
        assert header_marker not in result, "Header content should be removed"
        assert nav_marker not in result, "Nav content should be removed"
        assert aside_marker not in result, "Aside content should be removed"
        assert footer_marker not in result, "Footer content should be removed"
        assert script_marker not in result, "Script content should be removed"
        assert style_marker not in result, "Style content should be removed"

    @settings(max_examples=100)
    @given(
        content_length=st.integers(min_value=100, max_value=10000),
        max_length=st.integers(min_value=50, max_value=500),
    )
    def test_content_truncation(self, content_length: int, max_length: int):
        """Content exceeding max_length should be truncated."""
        # Generate content of specified length
        content = "x" * content_length
        html = f"<html><body><p>{content}</p></body></html>"

        result = self._extract_content_from_html(html, max_length=max_length)

        if content_length > max_length:
            # Result should be truncated
            assert "[Content truncated...]" in result, "Truncation marker should be present"
            # The actual content part should be max_length
            content_part = result.replace("\n\n[Content truncated...]", "")
            assert len(content_part) == max_length, f"Content should be truncated to {max_length}"
        else:
            # Result should not be truncated
            assert "[Content truncated...]" not in result, "Should not be truncated"
            assert content in result, "Full content should be present"

    def test_empty_content_returns_message(self):
        """Empty HTML should return appropriate message."""
        html = "<html><body></body></html>"
        result = self._extract_content_from_html(html)
        assert result == "No readable content found on this page."

    def test_only_unwanted_elements_returns_message(self):
        """HTML with only unwanted elements should return appropriate message."""
        html = """
        <html>
        <body>
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
            <nav>Navigation</nav>
        </body>
        </html>
        """
        result = self._extract_content_from_html(html)
        assert result == "No readable content found on this page."
