"""
Service layer for LLM (LM Studio / Ollama) sentiment analysis integration.
"""

import asyncio
import json
import logging
import random
import re
import time
from typing import Any, Dict, Optional, Tuple
import httpx

from backend.app.core.config import settings

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
            if time.time() - ts > self.ttl_seconds:
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


# Global reusable HTTP client for LLM API calls with a high timeout (60.0s) for model cold starts
_llm_client: Optional[httpx.AsyncClient] = None


def get_llm_client() -> httpx.AsyncClient:
    """
    Returns a shared singleton instance of AsyncClient for LLM queries.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = httpx.AsyncClient(timeout=60.0)
    return _llm_client


async def analyze_article_sentiment(
    title: str, summary: str, asset_symbol: str
) -> Dict[str, Any]:
    """
    Queries local LLM endpoint (Ollama / LM Studio) to evaluate article sentiment.
    Uses in-memory semantic cache and pre-cleans text inputs to protect token costs.

    Args:
        title: The headline title of the article.
        summary: The short summary text of the article.
        asset_symbol: The asset symbol context.

    Returns:
        A dictionary containing sentimentScore, sentimentLabel, confidence, keywords, and reasoning.
    """
    # Clean text to minimize prompt footprint
    cleaned_title = clean_text(title)
    cleaned_summary = clean_text(summary)

    # Check the in-memory cache first to avoid identical API requests
    cache_key = f"{asset_symbol}:{cleaned_title}:{cleaned_summary}"
    cached_result = await llm_cache.get(cache_key)
    if cached_result is not None:
        logger.info("llm_sentiment_cache_hit: asset=%s", asset_symbol)
        return cached_result

    if not settings.LLM_API_URL:
        result = _get_mock_sentiment(cleaned_title, cleaned_summary)
        await llm_cache.set(cache_key, result)
        return result

    url = f"{settings.LLM_API_URL.rstrip('/')}/chat/completions"

    system_instruction = (
        "You are an expert financial analyst. Analyze the sentiment of the provided news article "
        f"headline and summary with respect to the asset {asset_symbol}.\n"
        "You must respond with a raw JSON object containing exactly the following fields:\n"
        '- "sentimentScore": a float between -1.0 (extremely bearish) and 1.0 (extremely bullish)\n'
        '- "sentimentLabel": either "Bullish", "Bearish", or "Neutral"\n'
        '- "confidence": a float between 0.0 and 1.0 indicating your confidence in the score\n'
        '- "keywords": a JSON array of up to 4 string keywords/tags relevant to the article\n'
        '- "reasoning": a brief 1-3 sentence explanation of your reasoning\n'
        "Do not include any markdown formatting like ```json or trailing text. Return ONLY valid JSON."
    )

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": f"Title: {cleaned_title}\nSummary: {cleaned_summary}",
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        client = get_llm_client()
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            result_body = response.json()
            content = result_body["choices"][0]["message"]["content"].strip()

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            data = json.loads(content)
            score = max(-1.0, min(1.0, float(data.get("sentimentScore", 0.0))))

            label = str(data.get("sentimentLabel", "Neutral"))
            if label not in ("Bullish", "Bearish", "Neutral"):
                label = "Neutral"

            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.8))))
            keywords = list(data.get("keywords", []))
            reasoning = str(data.get("reasoning", "No explanation provided."))

            sentiment_data = {
                "sentimentScore": score,
                "sentimentLabel": label,
                "confidence": confidence,
                "keywords": keywords,
                "reasoning": reasoning,
            }

            await llm_cache.set(cache_key, sentiment_data)
            return sentiment_data

        logger.warning(
            "llm_api_non_200",
            extra={"status_code": response.status_code},
        )
    except Exception as exc:
        logger.warning(
            "llm_api_request_failed",
            extra={"error": str(exc)},
        )

    fallback_result = _get_mock_sentiment(cleaned_title, cleaned_summary)
    await llm_cache.set(cache_key, fallback_result)
    return fallback_result
