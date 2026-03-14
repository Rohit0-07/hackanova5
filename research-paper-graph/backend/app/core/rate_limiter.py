"""Async rate limiter — per-domain token bucket to prevent 429 errors.

Usage:
    limiter = RateLimiter()
    await limiter.acquire("semantic_scholar")  # waits before allowing the call
"""

import asyncio
import time
import random
from typing import Dict
from loguru import logger


# Default delays (seconds) per domain
DEFAULT_DELAYS: Dict[str, float] = {
    "semantic_scholar": 1.2,
    "arxiv": 3.0,
    "google_scholar": 5.0,
}


class RateLimiter:
    """Per-domain async rate limiter using token-bucket timing."""

    def __init__(self, custom_delays: Dict[str, float] = None):
        self._delays = {**DEFAULT_DELAYS, **(custom_delays or {})}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_call: Dict[str, float] = {}

    def _get_lock(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def acquire(self, domain: str, add_jitter: bool = False):
        """Wait until a call to `domain` is safe.

        Args:
            domain: The API domain key (e.g. "semantic_scholar").
            add_jitter: If True, adds random 0-2s extra delay (good for Google Scholar).
        """
        lock = self._get_lock(domain)
        async with lock:
            delay = self._delays.get(domain, 1.0)
            if add_jitter:
                delay += random.uniform(0.5, 2.0)

            last = self._last_call.get(domain, 0)
            elapsed = time.monotonic() - last
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"Rate limiter: waiting {wait_time:.1f}s for {domain}")
                await asyncio.sleep(wait_time)

            self._last_call[domain] = time.monotonic()


# Singleton instance
rate_limiter = RateLimiter()
