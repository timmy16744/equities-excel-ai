"""Anthropic API client wrapper with rate limiting and retries."""
import asyncio
import time
from typing import Optional, Any
from datetime import datetime, timedelta

import anthropic
from anthropic import AsyncAnthropic, Anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 50) -> None:
        self.rpm = requests_per_minute
        self.requests: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until we can make another request."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            # Remove requests older than 1 minute
            self.requests = [t for t in self.requests if t > minute_ago]

            if len(self.requests) >= self.rpm:
                # Wait until oldest request expires
                wait_time = self.requests[0] - minute_ago
                if wait_time > 0:
                    logger.debug("Rate limit reached, waiting", wait_time=wait_time)
                    await asyncio.sleep(wait_time)

            self.requests.append(now)


class TokenTracker:
    """Track token usage for cost monitoring."""

    def __init__(self) -> None:
        self.daily_usage: dict[str, int] = {}
        self.monthly_usage: dict[str, int] = {}
        self._today: str = ""
        self._month: str = ""

    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Track token usage."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        # Reset daily counter if new day
        if today != self._today:
            self.daily_usage = {}
            self._today = today

        # Reset monthly counter if new month
        if month != self._month:
            self.monthly_usage = {}
            self._month = month

        total = input_tokens + output_tokens
        self.daily_usage[today] = self.daily_usage.get(today, 0) + total
        self.monthly_usage[month] = self.monthly_usage.get(month, 0) + total

    def get_daily_usage(self) -> int:
        """Get today's token usage."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.daily_usage.get(today, 0)

    def get_monthly_usage(self) -> int:
        """Get this month's token usage."""
        month = datetime.utcnow().strftime("%Y-%m")
        return self.monthly_usage.get(month, 0)


class AnthropicClient:
    """
    Wrapper for Anthropic API with rate limiting, retries, and token tracking.

    Usage:
        client = AnthropicClient(api_key="sk-ant-...")
        response = await client.complete(
            model="claude-sonnet-4-5-20250929",
            system="You are an expert analyst.",
            messages=[{"role": "user", "content": "Analyze this data..."}],
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        requests_per_minute: int = 50,
        max_retries: int = 3,
        timeout: int = 30,
    ) -> None:
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            requests_per_minute: Rate limit for API calls
            max_retries: Maximum retry attempts for failed calls
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout

        self._async_client: Optional[AsyncAnthropic] = None
        self._sync_client: Optional[Anthropic] = None
        self._rate_limiter = RateLimiter(requests_per_minute)
        self._token_tracker = TokenTracker()

    @property
    def async_client(self) -> AsyncAnthropic:
        """Get or create async client."""
        if self._async_client is None:
            self._async_client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._async_client

    @property
    def sync_client(self) -> Anthropic:
        """Get or create sync client."""
        if self._sync_client is None:
            self._sync_client = Anthropic(
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._sync_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    )
    async def complete(
        self,
        model: str,
        messages: list[dict],
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        """
        Send a completion request to Claude.

        Args:
            model: Model ID (e.g., "claude-sonnet-4-5-20250929")
            messages: List of message dicts with "role" and "content"
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            **kwargs: Additional API parameters

        Returns:
            Dict with response content and metadata
        """
        # Check for API key
        if not self.api_key and not self.async_client.api_key:
            logger.warning("No Anthropic API key configured, returning mock response")
            return self._mock_response(model, messages)

        # Wait for rate limit
        await self._rate_limiter.acquire()

        logger.debug(
            "Sending completion request",
            model=model,
            message_count=len(messages),
            max_tokens=max_tokens,
        )

        try:
            response = await self.async_client.messages.create(
                model=model,
                messages=messages,
                system=system or "",
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

            # Track token usage
            self._token_tracker.track(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            logger.info(
                "Completion successful",
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return {
                "content": response.content[0].text if response.content else "",
                "model": response.model,
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

        except anthropic.AuthenticationError as e:
            logger.error("Authentication failed", error=str(e))
            raise
        except anthropic.RateLimitError as e:
            logger.warning("Rate limited by API", error=str(e))
            raise
        except anthropic.APIError as e:
            logger.error("API error", error=str(e))
            raise

    def _mock_response(self, model: str, messages: list[dict]) -> dict:
        """Generate a mock response when API key is not available."""
        return {
            "content": (
                "MOCK RESPONSE: API key not configured. "
                "This is a placeholder response for development/testing. "
                "Configure the anthropic_api_key setting to enable real responses."
            ),
            "model": model,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            },
            "is_mock": True,
        }

    def get_token_usage(self) -> dict:
        """Get current token usage statistics."""
        return {
            "daily": self._token_tracker.get_daily_usage(),
            "monthly": self._token_tracker.get_monthly_usage(),
        }

    async def close(self) -> None:
        """Close the client connections."""
        if self._async_client:
            await self._async_client.close()


# Global client instance (initialized on first use)
_client: Optional[AnthropicClient] = None


def get_anthropic_client(
    api_key: Optional[str] = None,
    requests_per_minute: int = 50,
) -> AnthropicClient:
    """
    Get or create the global Anthropic client.

    Args:
        api_key: Optional API key (uses env var if not provided)
        requests_per_minute: Rate limit

    Returns:
        AnthropicClient instance
    """
    global _client
    if _client is None:
        _client = AnthropicClient(
            api_key=api_key,
            requests_per_minute=requests_per_minute,
        )
    return _client
