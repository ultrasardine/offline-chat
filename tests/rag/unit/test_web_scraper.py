"""
Unit tests for WebScraper.

Tests cover:
- Scraping with mock MCP responses
- Retry logic with failing requests
- Rate limiting behavior
- Error handling for network failures

Requirements: 2.6, 9.4, 9.5
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from offline_chat.mcp_client import MCPClient
from offline_chat.rag.models import ScrapedContent
from offline_chat.rag.web_scraper import WebScraper


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client for testing."""
    client = MagicMock(spec=MCPClient)
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def web_scraper(mock_mcp_client):
    """Create a WebScraper instance with mock MCP client."""
    return WebScraper(mock_mcp_client)


class TestWebScraperInitialization:
    """Test WebScraper initialization."""
    
    def test_initialization(self, mock_mcp_client):
        """Test that WebScraper initializes with MCP client."""
        scraper = WebScraper(mock_mcp_client)
        
        assert scraper.mcp_client is mock_mcp_client
        assert scraper._rate_limit_delay == 1.0


class TestWebScraperScrapeUrl:
    """Test scraping a single URL."""
    
    @pytest.mark.anyio
    async def test_scrape_url_success(self, web_scraper, mock_mcp_client):
        """Test successful URL scraping on first attempt."""
        test_url = "https://example.com"
        test_content = "This is the scraped content from the webpage."
        
        # Mock successful response
        mock_mcp_client.call_tool.return_value = test_content
        
        result = await web_scraper.scrape_url(test_url)
        
        # Verify result
        assert isinstance(result, ScrapedContent)
        assert result.url == test_url
        assert result.text == test_content
        assert result.success is True
        assert result.error_message is None
        assert "fetch_timestamp" in result.metadata
        assert result.metadata["attempt"] == 1
        assert result.metadata["content_length"] == len(test_content)
        
        # Verify MCP client was called correctly
        mock_mcp_client.call_tool.assert_called_once_with(
            "fetch",
            {
                "url": test_url,
                "max_length": 50000,
                "raw": False
            }
        )
    
    @pytest.mark.anyio
    async def test_scrape_url_with_custom_max_length(self, web_scraper, mock_mcp_client):
        """Test scraping with custom max_length parameter."""
        test_url = "https://example.com"
        test_content = "Content"
        custom_max_length = 10000
        
        mock_mcp_client.call_tool.return_value = test_content
        
        result = await web_scraper.scrape_url(test_url, max_length=custom_max_length)
        
        assert result.success is True
        mock_mcp_client.call_tool.assert_called_once_with(
            "fetch",
            {
                "url": test_url,
                "max_length": custom_max_length,
                "raw": False
            }
        )
    
    @pytest.mark.anyio
    async def test_scrape_url_with_error_response(self, web_scraper, mock_mcp_client):
        """Test handling of error response from MCP tool."""
        test_url = "https://example.com"
        error_message = "Error: Failed to fetch URL"
        
        # Mock error response
        mock_mcp_client.call_tool.return_value = error_message
        
        result = await web_scraper.scrape_url(test_url, max_retries=3)
        
        # Should fail after all retries
        assert result.success is False
        assert result.url == test_url
        assert result.text == ""
        assert result.error_message is not None
        assert "Failed to scrape after 3 attempts" in result.error_message
        assert result.metadata["attempts"] == 3
        
        # Should have tried 3 times
        assert mock_mcp_client.call_tool.call_count == 3
    
    @pytest.mark.anyio
    async def test_scrape_url_retry_logic_with_exception(self, web_scraper, mock_mcp_client):
        """Test retry logic when MCP client raises exceptions."""
        test_url = "https://example.com"
        
        # Mock to raise exception on first two calls, succeed on third
        mock_mcp_client.call_tool.side_effect = [
            RuntimeError("Network error"),
            RuntimeError("Timeout"),
            "Success content"
        ]
        
        result = await web_scraper.scrape_url(test_url, max_retries=3)
        
        # Should succeed on third attempt
        assert result.success is True
        assert result.text == "Success content"
        assert result.metadata["attempt"] == 3
        
        # Should have tried 3 times
        assert mock_mcp_client.call_tool.call_count == 3
    
    @pytest.mark.anyio
    async def test_scrape_url_exponential_backoff(self, web_scraper, mock_mcp_client):
        """Test that retry logic uses exponential backoff (1s, 2s, 4s)."""
        test_url = "https://example.com"
        
        # Mock to fail all attempts
        mock_mcp_client.call_tool.side_effect = RuntimeError("Network error")
        
        # Track sleep calls
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await web_scraper.scrape_url(test_url, max_retries=3)
        
        # Should fail after all retries
        assert result.success is False
        
        # Verify exponential backoff: 1s, 2s (no sleep before first attempt)
        assert len(sleep_times) == 2
        assert sleep_times[0] == 1  # 2^0 = 1
        assert sleep_times[1] == 2  # 2^1 = 2
    
    @pytest.mark.anyio
    async def test_scrape_url_all_retries_exhausted(self, web_scraper, mock_mcp_client):
        """Test behavior when all retry attempts are exhausted."""
        test_url = "https://example.com"
        
        # Mock to always fail
        mock_mcp_client.call_tool.side_effect = RuntimeError("Persistent error")
        
        result = await web_scraper.scrape_url(test_url, max_retries=3)
        
        # Should return failed result
        assert result.success is False
        assert result.url == test_url
        assert result.text == ""
        assert "Failed to scrape after 3 attempts" in result.error_message
        assert "Persistent error" in result.error_message
        assert result.metadata["attempts"] == 3
        
        # Should have tried exactly 3 times
        assert mock_mcp_client.call_tool.call_count == 3
    
    @pytest.mark.anyio
    async def test_scrape_url_with_single_retry(self, web_scraper, mock_mcp_client):
        """Test scraping with max_retries=1."""
        test_url = "https://example.com"
        
        # Mock to always fail
        mock_mcp_client.call_tool.side_effect = RuntimeError("Error")
        
        result = await web_scraper.scrape_url(test_url, max_retries=1)
        
        assert result.success is False
        assert result.metadata["attempts"] == 1
        assert mock_mcp_client.call_tool.call_count == 1
    
    @pytest.mark.anyio
    async def test_scrape_url_empty_content(self, web_scraper, mock_mcp_client):
        """Test scraping that returns empty content."""
        test_url = "https://example.com"
        
        # Mock empty response
        mock_mcp_client.call_tool.return_value = ""
        
        result = await web_scraper.scrape_url(test_url)
        
        # Should succeed but with empty text
        assert result.success is True
        assert result.text == ""
        assert result.metadata["content_length"] == 0


class TestWebScraperBatchScraping:
    """Test scraping multiple URLs with rate limiting."""
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_success(self, web_scraper, mock_mcp_client):
        """Test successful batch scraping of multiple URLs."""
        test_urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        
        # Mock responses for each URL
        mock_mcp_client.call_tool.side_effect = [
            "Content from page 1",
            "Content from page 2",
            "Content from page 3"
        ]
        
        results = await web_scraper.scrape_urls_batch(test_urls)
        
        # Verify results
        assert len(results) == 3
        assert all(isinstance(r, ScrapedContent) for r in results)
        assert all(r.success for r in results)
        assert results[0].url == test_urls[0]
        assert results[1].url == test_urls[1]
        assert results[2].url == test_urls[2]
        assert results[0].text == "Content from page 1"
        assert results[1].text == "Content from page 2"
        assert results[2].text == "Content from page 3"
        
        # Verify all URLs were scraped
        assert mock_mcp_client.call_tool.call_count == 3
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_with_rate_limiting(self, web_scraper, mock_mcp_client):
        """Test that rate limiting is applied between requests."""
        test_urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        
        mock_mcp_client.call_tool.return_value = "Content"
        
        # Track sleep calls
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            results = await web_scraper.scrape_urls_batch(
                test_urls,
                rate_limit_delay=0.5
            )
        
        # Should have successful results
        assert len(results) == 3
        assert all(r.success for r in results)
        
        # Should have slept between requests (not before first request)
        # Total sleeps = (num_urls - 1) for rate limiting + retries if any
        rate_limit_sleeps = [s for s in sleep_times if s == 0.5]
        assert len(rate_limit_sleeps) == 2  # Between 3 URLs
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_with_custom_rate_limit(self, web_scraper, mock_mcp_client):
        """Test batch scraping with custom rate limit delay."""
        test_urls = ["https://example.com/page1", "https://example.com/page2"]
        
        mock_mcp_client.call_tool.return_value = "Content"
        
        # Track sleep calls
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        custom_delay = 2.0
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await web_scraper.scrape_urls_batch(
                test_urls,
                rate_limit_delay=custom_delay
            )
        
        # Should have used custom delay
        rate_limit_sleeps = [s for s in sleep_times if s == custom_delay]
        assert len(rate_limit_sleeps) == 1  # Between 2 URLs
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_mixed_success_failure(self, web_scraper, mock_mcp_client):
        """Test batch scraping with some successes and some failures."""
        test_urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        
        # Mock mixed responses: success, failure, success
        mock_mcp_client.call_tool.side_effect = [
            "Content from page 1",
            RuntimeError("Network error"),
            RuntimeError("Network error"),
            RuntimeError("Network error"),  # All retries for page 2 fail
            "Content from page 3"
        ]
        
        results = await web_scraper.scrape_urls_batch(test_urls, max_retries=3)
        
        # Verify results
        assert len(results) == 3
        assert results[0].success is True
        assert results[0].text == "Content from page 1"
        assert results[1].success is False
        assert results[1].text == ""
        assert results[2].success is True
        assert results[2].text == "Content from page 3"
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_empty_list(self, web_scraper, mock_mcp_client):
        """Test batch scraping with empty URL list."""
        results = await web_scraper.scrape_urls_batch([])
        
        assert results == []
        mock_mcp_client.call_tool.assert_not_called()
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_single_url(self, web_scraper, mock_mcp_client):
        """Test batch scraping with single URL (no rate limiting needed)."""
        test_urls = ["https://example.com/page1"]
        
        mock_mcp_client.call_tool.return_value = "Content"
        
        # Track sleep calls
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            results = await web_scraper.scrape_urls_batch(test_urls)
        
        # Should succeed
        assert len(results) == 1
        assert results[0].success is True
        
        # Should not have any rate limiting sleeps (only 1 URL)
        rate_limit_sleeps = [s for s in sleep_times if s == 1.0]
        assert len(rate_limit_sleeps) == 0
    
    @pytest.mark.anyio
    async def test_scrape_urls_batch_preserves_order(self, web_scraper, mock_mcp_client):
        """Test that batch scraping preserves URL order in results."""
        test_urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4"
        ]
        
        # Mock responses with identifiable content
        mock_mcp_client.call_tool.side_effect = [
            "Content 1",
            "Content 2",
            "Content 3",
            "Content 4"
        ]
        
        results = await web_scraper.scrape_urls_batch(test_urls)
        
        # Verify order is preserved
        assert len(results) == 4
        for i, result in enumerate(results):
            assert result.url == test_urls[i]
            assert result.text == f"Content {i + 1}"


class TestWebScraperErrorHandling:
    """Test error handling for various failure scenarios."""
    
    @pytest.mark.anyio
    async def test_network_failure_handling(self, web_scraper, mock_mcp_client):
        """Test handling of network failures."""
        test_url = "https://example.com"
        
        # Mock network error
        mock_mcp_client.call_tool.side_effect = RuntimeError("Connection refused")
        
        result = await web_scraper.scrape_url(test_url, max_retries=2)
        
        assert result.success is False
        assert "Connection refused" in result.error_message
        assert mock_mcp_client.call_tool.call_count == 2
    
    @pytest.mark.anyio
    async def test_timeout_handling(self, web_scraper, mock_mcp_client):
        """Test handling of timeout errors."""
        test_url = "https://example.com"
        
        # Mock timeout error
        mock_mcp_client.call_tool.side_effect = asyncio.TimeoutError("Request timed out")
        
        result = await web_scraper.scrape_url(test_url, max_retries=2)
        
        assert result.success is False
        assert "Request timed out" in result.error_message
        assert mock_mcp_client.call_tool.call_count == 2
    
    @pytest.mark.anyio
    async def test_invalid_url_handling(self, web_scraper, mock_mcp_client):
        """Test handling of invalid URL errors."""
        test_url = "not-a-valid-url"
        
        # Mock invalid URL error
        mock_mcp_client.call_tool.side_effect = ValueError("Invalid URL format")
        
        result = await web_scraper.scrape_url(test_url, max_retries=1)
        
        assert result.success is False
        assert "Invalid URL format" in result.error_message
    
    @pytest.mark.anyio
    async def test_mcp_tool_not_available(self, web_scraper, mock_mcp_client):
        """Test handling when MCP fetch tool is not available."""
        test_url = "https://example.com"
        
        # Mock tool not available error
        mock_mcp_client.call_tool.side_effect = RuntimeError("Tool 'fetch' not found")
        
        result = await web_scraper.scrape_url(test_url, max_retries=1)
        
        assert result.success is False
        assert "Tool 'fetch' not found" in result.error_message
    
    @pytest.mark.anyio
    async def test_partial_content_error(self, web_scraper, mock_mcp_client):
        """Test handling of partial content errors."""
        test_url = "https://example.com"
        
        # Mock partial content error
        mock_mcp_client.call_tool.return_value = "Error: Content truncated"
        
        result = await web_scraper.scrape_url(test_url, max_retries=2)
        
        assert result.success is False
        assert mock_mcp_client.call_tool.call_count == 2


class TestWebScraperRateLimiting:
    """Test rate limiting behavior in detail."""
    
    @pytest.mark.anyio
    async def test_rate_limit_delay_configuration(self, web_scraper, mock_mcp_client):
        """Test that rate limit delay can be configured."""
        # Default delay
        assert web_scraper._rate_limit_delay == 1.0
        
        # Change delay
        test_urls = ["https://example.com/page1", "https://example.com/page2"]
        mock_mcp_client.call_tool.return_value = "Content"
        
        await web_scraper.scrape_urls_batch(test_urls, rate_limit_delay=3.0)
        
        # Delay should be updated
        assert web_scraper._rate_limit_delay == 3.0
    
    @pytest.mark.anyio
    async def test_no_rate_limit_on_first_request(self, web_scraper, mock_mcp_client):
        """Test that no rate limiting is applied before the first request."""
        test_urls = ["https://example.com/page1", "https://example.com/page2"]
        mock_mcp_client.call_tool.return_value = "Content"
        
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await web_scraper.scrape_urls_batch(test_urls, rate_limit_delay=1.5)
        
        # Should have exactly 1 rate limit sleep (between requests)
        rate_limit_sleeps = [s for s in sleep_times if s == 1.5]
        assert len(rate_limit_sleeps) == 1
    
    @pytest.mark.anyio
    async def test_rate_limiting_with_retries(self, web_scraper, mock_mcp_client):
        """Test that rate limiting and retry backoff work together."""
        test_urls = ["https://example.com/page1", "https://example.com/page2"]
        
        # First URL fails once then succeeds, second URL succeeds immediately
        mock_mcp_client.call_tool.side_effect = [
            RuntimeError("Temporary error"),
            "Content 1",
            "Content 2"
        ]
        
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            results = await web_scraper.scrape_urls_batch(
                test_urls,
                max_retries=2,
                rate_limit_delay=0.5
            )
        
        # Both should succeed
        assert all(r.success for r in results)
        
        # Should have both retry backoff and rate limiting sleeps
        assert len(sleep_times) >= 2  # At least retry backoff + rate limit
