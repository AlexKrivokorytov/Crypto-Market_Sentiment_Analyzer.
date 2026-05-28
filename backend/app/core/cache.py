"""
In-memory TTL cache for the Market Sentiment Analyzer backend.

Designed for single-instance Render Free Tier deployments where Redis is not
available. Uses lazy eviction — expired entries are removed on read, not on a
background schedule.
"""

import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """
    A simple in-memory key-value cache with per-entry time-to-live (TTL).

    Thread safety: Not thread-safe. Safe for single-threaded asyncio usage
    because Python's GIL protects dict operations.

    Eviction strategy: Lazy — expired entries are evicted on `get()` only,
    not proactively. Suitable for low-volume caches without unbounded growth.
    """

    def __init__(self) -> None:
        """Initialises an empty cache store."""
        self._store: Dict[str, Tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Stores a value under the given key with a TTL.

        Args:
            key: Cache key string.
            value: Arbitrary value to cache (must be JSON-serialisable for safety).
            ttl_seconds: Number of seconds before the entry expires.
        """
        expiry = time.monotonic() + ttl_seconds
        self._store[key] = (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a cached value by key.

        Lazily evicts the entry if it has expired.

        Args:
            key: Cache key string.

        Returns:
            The cached value, or None if the key is missing or expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def invalidate(self, key: str) -> None:
        """
        Removes a cached entry immediately regardless of its TTL.

        Args:
            key: Cache key string. No-op if the key does not exist.
        """
        self._store.pop(key, None)


# Module-level singleton shared across all service modules
cache = TTLCache()
