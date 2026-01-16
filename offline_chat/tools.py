"""Web search tool for Ollama tool calling.

This module provides the WebSearchTool class that integrates with Ollama's
tool calling capabilities to enable agents to search the web.
"""

from typing import Any

from offline_chat.exceptions import SearchConnectionError, SearchTimeoutError
from offline_chat.search import DuckDuckGoProvider, SearchProviderProtocol, SearchResult


def format_search_results(results: list[SearchResult]) -> str:
    """Format search results for model consumption.

    Args:
        results: List of SearchResult objects.

    Returns:
        Formatted string with numbered results.
    """
    if not results:
        return "No search results found for this query."

    formatted = []
    for i, result in enumerate(results, 1):
        # Truncate body to keep results concise
        body = result.body[:200] + "..." if len(result.body) > 200 else result.body
        formatted.append(f"{i}. {result.title}\n   URL: {result.href}\n   {body}")

    return "\n\n".join(formatted)


class WebSearchTool:
    """Web search tool for Ollama tool calling.

    This tool provides a schema compatible with Ollama's tool calling format
    and executes web searches using a configurable search provider.

    Attributes:
        provider: The search provider instance used to execute searches.
    """

    def __init__(self, provider: SearchProviderProtocol | None = None):
        """Initialize the web search tool.

        Args:
            provider: Search provider instance. Defaults to DuckDuckGoProvider.
        """
        self.provider = provider or DuckDuckGoProvider()

    def get_tool_schema(self) -> dict[str, Any]:
        """Get the Ollama-compatible tool schema.

        Returns:
            Tool schema dictionary with type, function name, description,
            and parameters specification.
        """
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the web for current information. Use this when you need "
                    "up-to-date information or facts you're not certain about."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 5)",
                            "default": 5,
                        },
                    },
                },
            },
        }

    def execute(self, query: str, max_results: int = 5) -> str:
        """Execute a web search and return formatted results.

        Args:
            query: The search query.
            max_results: Maximum number of results. Defaults to 5.

        Returns:
            Formatted search results string, or an error message if the
            search fails.
        """
        try:
            results = self.provider.search(query, max_results)
            return format_search_results(results)
        except SearchTimeoutError:
            return "Search timed out. Please try again or rephrase your query."
        except SearchConnectionError:
            return (
                "Web search is currently unavailable. "
                "Please answer based on your existing knowledge."
            )
        except Exception as e:
            return f"Search failed: {str(e)}. Please answer based on your existing knowledge."
