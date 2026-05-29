"""
Service layer for LLM (LM Studio / Ollama) sentiment analysis integration.
"""

import asyncio
import logging
import random
import re
import time
from typing import Any, Dict, Optional, Tuple
import httpx

from backend.app.core.circuit_breaker import CircuitBreaker
from backend.app.services.sentiment_engine import analyze_sentiment_local

logger = logging.getLogger("app")

# Local pre-packaged templates for instant simulation
SIMULATED_TEMPLATES = {
    "BULLISH": [
        {
            "reasoning": "The recent positive developments and rising buying momentum suggest strong upward pressure. General institutional interest continues to bid up the asset.",
            "keywords": ["momentum", "growth", "institution", "adoption"],
        },
        {
            "reasoning": "Technical parameters indicate that a key macro level has been cleared on above-average volume, confirming a bullish structure.",
            "keywords": ["technical", "breakout", "volume", "momentum"],
        },
    ],
    "BEARISH": [
        {
            "reasoning": "Short-term macro headwinds and tightening regulations are causing concerns. Retail panic could drive near-term selling.",
            "keywords": ["regulation", "risk", "outflow", "derisking"],
        },
        {
            "reasoning": "Security risks or negative technical divergence indicates that key support zones are being tested and might break.",
            "keywords": ["security", "bearish", "divergence", "support"],
        },
    ],
    "NEUTRAL": [
        {
            "reasoning": "The asset is currently consolidating in a tight trading range. No immediate macro catalyst is driving price in either direction.",
            "keywords": ["consolidation", "neutral", "range", "expiry"],
        },
        {
            "reasoning": "General discussions and conference panels offer long-term branding value but present no immediate impact on price actions.",
            "keywords": ["discussion", "conference", "branding", "panel"],
        },
    ],
}


def _get_mock_sentiment(title: str, summary: str) -> Dict[str, Any]:
    """
    Analyzes content heuristically and matches templates for simulated scenarios.
    """
    text = (title + " " + summary).lower()

    bullish_keywords = [
        "surge",
        "breakout",
        "growth",
        "high",
        "adopt",
        "gain",
        "rise",
        "partnership",
        "success",
        "institutional",
        "launch",
        "all-time",
    ]
    bearish_keywords = [
        "drop",
        "fall",
        "down",
        "bear",
        "scam",
        "regulation",
        "lawsuit",
        "warning",
        "phishing",
        "hack",
        "exploit",
        "crash",
        "sell",
    ]

    bull_hits = sum(1 for kw in bullish_keywords if kw in text)
    bear_hits = sum(1 for kw in bearish_keywords if kw in text)

    if bull_hits > bear_hits:
        sentiment_label = "Bullish"
        sentiment_score = round(0.3 + (random.random() * 0.6), 2)
    elif bear_hits > bull_hits:
        sentiment_label = "Bearish"
        sentiment_score = round(-0.3 - (random.random() * 0.6), 2)
    else:
        sentiment_label = "Neutral"
        sentiment_score = round((random.random() - 0.5) * 0.3, 2)

    templates = SIMULATED_TEMPLATES[sentiment_label.upper()]
    template = random.choice(templates)
    reasoning = (
        str(template["reasoning"]) + "\n\n(Simulated Analysis - No LLM Configured)"
    )

    return {
        "sentimentScore": sentiment_score,
        "sentimentLabel": sentiment_label,
        "confidence": round(0.7 + (random.random() * 0.25), 2),
        "keywords": template["keywords"],
        "reasoning": reasoning,
    }


class LLMAnalysisCache:
    """
    In-memory async-safe cache for LLM analysis results.
    Prevents redundant API calls to external or local ИИ models.
    """

    def __init__(self, maxsize: int = 200, ttl_seconds: int = 3600) -> None:
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves analysis result from cache if present and not expired.
        """
        async with self.lock:
            if key not in self.cache:
                return None
            ts, data = self.cache[key]
            if time.time() - ts >= self.ttl_seconds:
                self.cache.pop(key, None)
                return None
            return data

    async def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Stores the analysis result in cache, evicting the oldest element if maxsize exceeded.
        """
        async with self.lock:
            if len(self.cache) >= self.maxsize:
                # FIFO eviction
                oldest = next(iter(self.cache))
                self.cache.pop(oldest, None)
            self.cache[key] = (time.time(), value)


# Module-level singleton instance for the LLM cache
llm_cache = LLMAnalysisCache()

# ──────────────────────────────────────────────────────────────────────────────
# Circuit Breaker for the sentiment analysis path
#
# Primary:  analyze_sentiment_local() — deterministic local VADER engine
# Fallback: _get_mock_sentiment()     — heuristic keyword template matcher
#
# State transitions are logged at WARNING level for observability.
# failure_threshold=3 means 3 consecutive VADER errors trip the breaker.
# recovery_timeout=60s means the breaker probes again after 1 minute.
# ──────────────────────────────────────────────────────────────────────────────
_sentiment_breaker = CircuitBreaker(
    name="sentiment_engine",
    failure_threshold=3,
    recovery_timeout=60.0,
)


def clean_text(text: str) -> str:
    """
    Cleans raw input text to minimize prompt size and optimize token usage.
    Removes HTML markup, URLs, extra whitespaces, and standard boilerplates.

    Args:
        text: The raw source text string.

    Returns:
        The cleaned, standardized text string.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    # Remove absolute URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # Remove common newsletter RSS boilerplates
    boilerplates = [
        "click here to read more",
        "read more on",
        "all rights reserved",
        "copyright",
    ]
    for bp in boilerplates:
        text = re.compile(re.escape(bp), re.IGNORECASE).sub("", text)

    return " ".join(text.split())


# RESERVED: Retained for future Ollama / LM Studio integration.
# When LLM_API_URL is configured, this client replaces the local VADER engine
# with a remote model call. Currently unused — analyze_sentiment_local is the
# sole analysis path.
_llm_client: Optional[httpx.AsyncClient] = None


def get_llm_client() -> httpx.AsyncClient:
    """
    Returns a shared singleton instance of AsyncClient for LLM queries.

    Reserved for future Ollama / LM Studio integration via LLM_API_URL.
    Currently not called by any active code path.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = httpx.AsyncClient(timeout=60.0)
    return _llm_client


async def analyze_article_sentiment(
    title: str, summary: str, asset_symbol: str
) -> Dict[str, Any]:
    """
    Evaluates article sentiment with Circuit Breaker protection.

    The Circuit Breaker wraps the local VADER engine (primary path) with
    a template-based mock fallback. On 3 consecutive VADER failures the
    breaker trips to OPEN and routes all calls to the fallback until
    a 60-second recovery probe succeeds.

    Results are cached in-memory (TTL 1h) so cache hits bypass the
    circuit breaker entirely — no state changes from cached responses.

    Args:
        title:        The headline title of the article.
        summary:      The short summary text of the article.
        asset_symbol: The asset ticker symbol for cache keying and logging.

    Returns:
        Dict containing sentimentScore, sentimentLabel, confidence,
        keywords, and reasoning.
    """
    # Pre-clean text to minimise prompt footprint and normalise cache keys
    cleaned_title = clean_text(title)
    cleaned_summary = clean_text(summary)

    # Cache hit → bypass breaker entirely (no state change from cached data)
    cache_key = f"{asset_symbol}:{cleaned_title}:{cleaned_summary}"
    cached_result = await llm_cache.get(cache_key)
    if cached_result is not None:
        logger.info("sentiment_local_cache_hit: asset=%s", asset_symbol)
        return cached_result

    async def _primary() -> Dict[str, Any]:
        """Calls the local VADER engine synchronously (CPU-bound, no I/O)."""
        return analyze_sentiment_local(cleaned_title, cleaned_summary)

    async def _fallback() -> Dict[str, Any]:
        """Template-based heuristic fallback when VADER is unavailable."""
        logger.warning(
            "sentiment_fallback_used: asset=%s breaker_state=%s",
            asset_symbol,
            _sentiment_breaker.state.name,
        )
        return _get_mock_sentiment(cleaned_title, cleaned_summary)

    result = await _sentiment_breaker.call(
        primary=_primary,
        fallback=_fallback,
    )

    await llm_cache.set(cache_key, result)
    return result
