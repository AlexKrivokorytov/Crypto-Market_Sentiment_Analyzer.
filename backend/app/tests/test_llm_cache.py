"""
Unit tests for the LLM caching, input pre-cleaning, and parser time-window deduplication.
"""

import pytest
from backend.app.services.llm import LLMAnalysisCache, clean_text
from backend.app.services.parser import _is_duplicate_in_window


def test_clean_text_strips_html_urls_and_boilerplates() -> None:
    """
    Verifies that clean_text successfully strips HTML tags, absolute URLs,
    common RSS newsletter boilerplates, and standardizes whitespaces.
    """
    raw_text = (
        "<p>Breaking: Major news on Bitcoin! "
        "Read more on https://example.com/bitcoin-news "
        "Click here to read more. Copyright 2026. All rights reserved.</p>"
    )
    cleaned = clean_text(raw_text)

    # Assert HTML tags, URLs, and boilerplates are fully purged
    assert "<p>" not in cleaned
    assert "https://" not in cleaned
    assert "Click here to read more" not in cleaned
    assert "All rights reserved" not in cleaned
    assert cleaned == "Breaking: Major news on Bitcoin! . 2026. ."


@pytest.mark.anyio
async def test_llm_cache_set_get_and_eviction() -> None:
    """
    Verifies that LLMAnalysisCache successfully saves, retrieves,
    and evicts oldest entries using FIFO/LRU properties when size limits are reached.
    """
    # Max size = 3, TTL = 10s
    cache = LLMAnalysisCache(maxsize=3, ttl_seconds=10)

    # Test set and get
    await cache.set("key1", {"sentimentScore": 0.8})
    await cache.set("key2", {"sentimentScore": -0.5})
    await cache.set("key3", {"sentimentScore": 0.0})

    res1 = await cache.get("key1")
    assert res1 is not None
    assert res1["sentimentScore"] == 0.8

    # Test Eviction: Adding key4 should evict the oldest key (key1)
    await cache.set("key4", {"sentimentScore": 0.95})

    evicted = await cache.get("key1")
    assert evicted is None  # Evicted!

    # Key2, 3, 4 should still be cached
    assert await cache.get("key2") is not None
    assert await cache.get("key3") is not None
    assert await cache.get("key4") is not None


@pytest.mark.anyio
async def test_llm_cache_ttl_expiration() -> None:
    """
    Verifies that cached elements are successfully invalidated when their TTL expires.
    """
    # TTL = 0 seconds (instantly expires)
    cache = LLMAnalysisCache(maxsize=5, ttl_seconds=0)

    await cache.set("key1", {"sentimentScore": 0.5})
    expired = await cache.get("key1")
    assert expired is None  # Instantly expired!


def test_time_window_deduplication_filter() -> None:
    """
    Verifies that _is_duplicate_in_window correctly flags duplicate titles
    within a sliding time window and cleanly accepts new unique ones.
    """
    title_1 = "Bitcoin Price Surges Past $100K!"
    title_2 = "Solana developers launch new update"

    # First insertion should not be marked as duplicate
    assert _is_duplicate_in_window(title_1) is False

    # Second identical title insertion must be flagged as duplicate immediately
    assert _is_duplicate_in_window(title_1) is True

    # Same title with minor spacing and capitalization mismatches should still match
    variant_title_1 = "  bitcoin price surges past $100k!  "
    assert _is_duplicate_in_window(variant_title_1) is True

    # A different unique title must not be marked as duplicate
    assert _is_duplicate_in_window(title_2) is False
