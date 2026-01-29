"""Search provider implementations for web search functionality."""

from dataclasses import dataclass
from typing import Protocol

from ddgs import DDGS
from ddgs.exceptions import DDGSException, TimeoutException

from offline_chat.exceptions import SearchConnectionError, SearchTimeoutError


@dataclass
class SearchResult:
    """Represents a single search result.

    Attributes:
        title: The title of the search result.
        href: The URL of the search result.
        body: A snippet/description of the search result.
    """

    title: str
    href: str
    body: str

    def to_dict(self) -> dict[str, str]:
        """Serialize to dictionary.

        Returns:
            Dictionary with title, href, and body fields.
        """
        return {"title": self.title, "href": self.href, "body": self.body}


class SearchProviderProtocol(Protocol):
    """Protocol for search provider implementations."""

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Execute a search and return results.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects.

        Raises:
            SearchTimeoutError: If the search times out.
            SearchConnectionError: If the provider is unavailable.
        """
        ...


class DuckDuckGoProvider:
    """Search provider using DuckDuckGo.

    This provider uses the duckduckgo-search library to execute
    privacy-respecting web searches.

    Attributes:
        timeout: Request timeout in seconds.
    """

    def __init__(self, timeout: int = 10):
        """Initialize the provider.

        Args:
            timeout: Request timeout in seconds. Defaults to 10.
        """
        self.timeout = timeout

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Execute a DuckDuckGo search.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return. Defaults to 5.

        Returns:
            List of SearchResult objects.

        Raises:
            SearchTimeoutError: If the search times out.
            SearchConnectionError: If the provider is unavailable.
        """
        try:
            with DDGS(timeout=self.timeout) as ddgs:
                results = ddgs.text(query, max_results=max_results)
                return [
                    SearchResult(title=r.get("title", ""), href=r.get("href", ""), body=r.get("body", ""))
                    for r in results
                ]
        except TimeoutException as e:
            raise SearchTimeoutError(self.timeout) from e
        except DDGSException as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                raise SearchTimeoutError(self.timeout) from e
            raise SearchConnectionError() from e
        except TimeoutError as e:
            raise SearchTimeoutError(self.timeout) from e
        except (ConnectionError, OSError) as e:
            raise SearchConnectionError() from e
