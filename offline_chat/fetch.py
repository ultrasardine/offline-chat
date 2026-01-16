"""Web page fetching tool for Ollama tool calling.

This module provides the WebFetchTool class that integrates with Ollama's
tool calling capabilities to enable agents to fetch and read web page content.
"""

from typing import Any

import requests
from bs4 import BeautifulSoup


class WebFetchTool:
    """Web page fetching tool for Ollama tool calling.

    This tool provides a schema compatible with Ollama's tool calling format
    and fetches web page content, parsing HTML to extract readable text.

    Attributes:
        timeout: Request timeout in seconds.
    """

    def __init__(self, timeout: int = 10):
        """Initialize the web fetch tool.

        Args:
            timeout: Request timeout in seconds. Defaults to 10.
        """
        self.timeout = timeout

    def get_tool_schema(self) -> dict[str, Any]:
        """Get the Ollama-compatible tool schema.

        Returns:
            Tool schema dictionary with type, function name, description,
            and parameters specification.
        """
        return {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": (
                    "Fetch and read the full content of a web page. Use this when "
                    "you need more detail from a specific URL found in search results."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the web page to fetch",
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum characters to return (default: 5000)",
                            "default": 5000,
                        },
                    },
                },
            },
        }

    def execute(self, url: str, max_length: int = 5000) -> str:
        """Fetch a web page and return its text content.

        Args:
            url: The URL to fetch.
            max_length: Maximum characters to return. Defaults to 5000.

        Returns:
            Extracted text content from the page, or an error message
            if the fetch fails.
        """
        try:
            # Validate URL
            if not url.startswith(("http://", "https://")):
                return f"Invalid URL: {url}. URL must start with http:// or https://"

            # Fetch the page
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OfflineChat/1.0)"},
            )
            response.raise_for_status()

            # Parse and extract text
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "\n\n[Content truncated...]"

            return text if text else "No readable content found on this page."

        except requests.Timeout:
            return f"Page fetch timed out after {self.timeout} seconds."
        except requests.HTTPError as e:
            return f"HTTP error {e.response.status_code} when fetching {url}"
        except requests.RequestException as e:
            return f"Failed to fetch page: {str(e)}"
        except Exception as e:
            return f"Error parsing page content: {str(e)}"
