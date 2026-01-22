"""
Web scraper for fetching content from approved URLs using MCP tools.
"""

import asyncio
import logging
import time
from typing import Any

from offline_chat.mcp_client import MCPClient
from offline_chat.rag.models import ScrapedContent

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Fetch content from approved URLs using MCP tools.
    
    This class provides methods for scraping web content with retry logic
    and rate limiting. Uses the MCP fetch tool to retrieve web content.
    """
    
    def __init__(self, mcp_client: MCPClient):
        """
        Initialize with MCP client for web fetching.
        
        Args:
            mcp_client: MCP client instance for calling fetch tool
        """
        self.mcp_client = mcp_client
        self._rate_limit_delay = 1.0  # Delay between requests in seconds
    
    async def scrape_url(
        self,
        url: str,
        max_retries: int = 3,
        max_length: int = 50000
    ) -> ScrapedContent:
        """
        Scrape content from a URL with exponential backoff retry logic.
        
        Implements retry logic with exponential backoff (1s, 2s, 4s) for
        handling transient network failures. Extracts text content from
        HTML and markdown formats.
        
        Args:
            url: URL to scrape
            max_retries: Maximum retry attempts (default: 3)
            max_length: Maximum content length in characters (default: 50000)
            
        Returns:
            ScrapedContent with text and metadata
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Calculate backoff delay: 1s, 2s, 4s
                if attempt > 0:
                    backoff_delay = 2 ** (attempt - 1)
                    logger.info(
                        f"Retry attempt {attempt + 1}/{max_retries} for {url} "
                        f"after {backoff_delay}s delay"
                    )
                    await asyncio.sleep(backoff_delay)
                
                # Call MCP fetch tool
                # The fetch tool returns markdown-formatted content
                result = await self.mcp_client.call_tool(
                    "fetch",
                    {
                        "url": url,
                        "max_length": max_length,
                        "raw": False  # Get simplified markdown, not raw HTML
                    }
                )
                
                # Check if result indicates an error
                if result.startswith("Error:"):
                    raise RuntimeError(result)
                
                # Extract metadata from the result
                metadata = {
                    "fetch_timestamp": time.time(),
                    "attempt": attempt + 1,
                    "content_length": len(result)
                }
                
                logger.info(
                    f"Successfully scraped {url} "
                    f"({len(result)} chars, attempt {attempt + 1})"
                )
                
                return ScrapedContent(
                    url=url,
                    text=result,
                    metadata=metadata,
                    success=True,
                    error_message=None
                )
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Failed to scrape {url} on attempt {attempt + 1}/{max_retries}: {e}"
                )
        
        # All retries exhausted
        error_msg = f"Failed to scrape after {max_retries} attempts: {last_error}"
        logger.error(f"Scraping failed for {url}: {error_msg}")
        
        return ScrapedContent(
            url=url,
            text="",
            metadata={"attempts": max_retries},
            success=False,
            error_message=error_msg
        )
    
    async def scrape_urls_batch(
        self,
        urls: list[str],
        max_retries: int = 3,
        rate_limit_delay: float | None = None
    ) -> list[ScrapedContent]:
        """
        Scrape multiple URLs with rate limiting.
        
        Implements rate limiting to avoid overwhelming servers. Processes
        URLs sequentially with a configurable delay between requests.
        
        Args:
            urls: List of URLs to scrape
            max_retries: Maximum retry attempts per URL (default: 3)
            rate_limit_delay: Delay between requests in seconds
                            (default: 1.0 second)
            
        Returns:
            List of ScrapedContent objects (one per URL)
        """
        if rate_limit_delay is not None:
            self._rate_limit_delay = rate_limit_delay
        
        results: list[ScrapedContent] = []
        
        for i, url in enumerate(urls):
            # Apply rate limiting (skip delay for first URL)
            if i > 0:
                logger.debug(f"Rate limiting: waiting {self._rate_limit_delay}s")
                await asyncio.sleep(self._rate_limit_delay)
            
            # Scrape the URL
            result = await self.scrape_url(url, max_retries=max_retries)
            results.append(result)
            
            # Log progress
            logger.info(
                f"Batch progress: {i + 1}/{len(urls)} URLs processed "
                f"({'success' if result.success else 'failed'})"
            )
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Batch scraping complete: {successful}/{len(urls)} URLs successful"
        )
        
        return results
