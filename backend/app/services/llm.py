"""
Service layer for OpenRouter LLM sentiment analysis.

Rate-limiting strategy
----------------------
OpenRouter's free tier allows 20 requests per minute across all models.
The background RSS crawler and user manual clicks share this budget.

To guarantee that manual user clicks always succeed:
  - A global TokenBucket enforces a conservative cap of 10 req/min for
    background (non-priority) callers.
  - User clicks (bypass_breaker=True) bypass the bucket entirely and
    attempt the API call immediately with priority.
  - On a 429 response, the caller retries once after a short backoff;
    on a second 429 it falls back to the local VADER engine.
"""

import asyncio
import json
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict, cast

import httpx

from backend.app.core.circuit_breaker import CircuitBreaker
from backend.app.services.sentiment_engine import analyze_sentiment_local


class SentimentResult(TypedDict, total=False):
    sentimentScore: float
    sentimentLabel: str
    confidence: float
    keywords: List[str]
    reasoning: str
    is_fallback: bool


logger = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# Simulated fallback templates (used when no LLM is configured or as the last
# resort when both the API and VADER fail).
# ──────────────────────────────────────────────────────────────────────────────

SIMULATED_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "BULLISH": [
        {
            "reasoning": "Positive macro developments and rising buying momentum suggest strong upward pressure. Institutional interest continues to bid up the asset.",
            "keywords": ["momentum", "growth", "institution", "adoption"],
        },
        {
            "reasoning": "A key macro level was cleared on above-average volume, confirming a bullish market structure.",
            "keywords": ["technical", "breakout", "volume", "momentum"],
        },
    ],
    "BEARISH": [
        {
            "reasoning": "Macro headwinds and tightening regulations are fuelling concern. Retail panic could drive near-term selling.",
            "keywords": ["regulation", "risk", "outflow", "derisking"],
        },
        {
            "reasoning": "Negative technical divergence signals that key support zones are under pressure and may break.",
            "keywords": ["security", "bearish", "divergence", "support"],
        },
    ],
    "NEUTRAL": [
        {
            "reasoning": "The asset is consolidating in a tight range with no immediate macro catalyst driving price in either direction.",
            "keywords": ["consolidation", "neutral", "range", "expiry"],
        },
        {
            "reasoning": "Conference-level discussions provide long-term branding value but carry no immediate price impact.",
            "keywords": ["discussion", "conference", "branding", "panel"],
        },
    ],
}


def _get_mock_sentiment(title: str, summary: str) -> Dict[str, Any]:
    """
    Heuristic template-based fallback when no LLM is available.

    Args:
        title:   Article headline.
        summary: Article body or excerpt.

    Returns:
        Dict with sentimentScore, sentimentLabel, confidence, keywords, reasoning.
    """
    text = (title + " " + summary).lower()
    bullish_kw = [
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
    bearish_kw = [
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
    bull_hits = sum(1 for kw in bullish_kw if kw in text)
    bear_hits = sum(1 for kw in bearish_kw if kw in text)

    if bull_hits > bear_hits:
        label = "Bullish"
        score = round(0.3 + random.random() * 0.6, 2)
    elif bear_hits > bull_hits:
        label = "Bearish"
        score = round(-0.3 - random.random() * 0.6, 2)
    else:
        label = "Neutral"
        score = round((random.random() - 0.5) * 0.3, 2)

    templates = SIMULATED_TEMPLATES[label.upper()]
    tpl = random.choice(templates)
    reasoning = str(tpl["reasoning"]) + "\n\n(Simulated Analysis — No LLM Configured)"
    return {
        "sentimentScore": score,
        "sentimentLabel": label,
        "confidence": round(0.7 + random.random() * 0.25, 2),
        "keywords": list(tpl["keywords"]),
        "reasoning": reasoning,
    }


# ──────────────────────────────────────────────────────────────────────────────
# In-memory LLM result cache
# ──────────────────────────────────────────────────────────────────────────────


class LLMAnalysisCache:
    """
    Async-safe in-memory LRU+TTL cache for LLM analysis results.

    Prevents redundant API calls for identical article content within
    a 1-hour window. The cache is bypassed for user-triggered manual
    analysis requests (bypass_breaker=True).
    """

    def __init__(self, maxsize: int = 200, ttl_seconds: int = 3600) -> None:
        """
        Args:
            maxsize:     Maximum entries before FIFO eviction kicks in.
            ttl_seconds: Seconds before a cached entry expires.
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[float, SentimentResult]] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[SentimentResult]:
        """
        Returns the cached value if present and not expired, else None.

        Args:
            key: Cache key string.
        """
        async with self.lock:
            if key not in self.cache:
                return None
            ts, data = self.cache[key]
            if time.time() - ts >= self.ttl_seconds:
                self.cache.pop(key, None)
                return None
            return data

    async def set(self, key: str, value: SentimentResult) -> None:
        """
        Stores a result in cache with FIFO eviction when full.

        Args:
            key:   Cache key string.
            value: Result dict to cache.
        """
        async with self.lock:
            if len(self.cache) >= self.maxsize:
                oldest = next(iter(self.cache))
                self.cache.pop(oldest, None)
            self.cache[key] = (time.time(), value)


# Module-level singleton cache
llm_cache = LLMAnalysisCache()


# ──────────────────────────────────────────────────────────────────────────────
# Token-bucket rate limiter
#
# Caps background crawler calls to MAX_BACKGROUND_RPM requests/min.
# User manual clicks (bypass_breaker=True) bypass the bucket entirely.
# ──────────────────────────────────────────────────────────────────────────────

# Background callers may use at most this many OpenRouter requests per minute.
# Leaves the remainder of the free-tier 20 RPM budget for user clicks.
_MAX_BACKGROUND_RPM: int = 8
_WINDOW_SECONDS: float = 60.0

# Sliding window of timestamps for background calls issued in the last minute
_bg_call_timestamps: List[float] = []
_bg_rate_lock = asyncio.Lock()


async def _background_rate_limit_ok() -> bool:
    """
    Returns True if a background LLM call may proceed under the rate limit.

    Implements a sliding-window counter over the last 60 seconds.
    Does NOT block — returns immediately so the caller can fall back to VADER.
    """
    async with _bg_rate_lock:
        now = time.monotonic()
        cutoff = now - _WINDOW_SECONDS
        # Evict expired timestamps
        while _bg_call_timestamps and _bg_call_timestamps[0] < cutoff:
            _bg_call_timestamps.pop(0)
        if len(_bg_call_timestamps) >= _MAX_BACKGROUND_RPM:
            return False
        _bg_call_timestamps.append(now)
        return True


# ──────────────────────────────────────────────────────────────────────────────
# Circuit Breaker for the background crawler path only
# ──────────────────────────────────────────────────────────────────────────────

_sentiment_breaker = CircuitBreaker(
    name="sentiment_engine",
    failure_threshold=3,
    recovery_timeout=60.0,
)


def clean_text(text: str) -> str:
    """
    Strips HTML tags, URLs, and common boilerplate from article text.

    Args:
        text: Raw source text.

    Returns:
        Cleaned, whitespace-normalised text.
    """
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    for bp in [
        "click here to read more",
        "read more on",
        "all rights reserved",
        "copyright",
    ]:
        text = re.compile(re.escape(bp), re.IGNORECASE).sub("", text)
    return " ".join(text.split())


# Shared singleton httpx client for all OpenRouter calls
_llm_client: Optional[httpx.AsyncClient] = None


def get_llm_client() -> httpx.AsyncClient:
    """
    Returns the shared AsyncClient, creating it on first call.

    Returns:
        A reusable httpx.AsyncClient with a 30-second timeout.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = httpx.AsyncClient(timeout=15.0)
    return _llm_client


def _parse_llm_json(content: str) -> SentimentResult:
    """
    Extracts and normalises the JSON object from an LLM response string.

    Handles both clean JSON and JSON wrapped in markdown code fences.
    Uses case-insensitive key lookup to tolerate camelCase/snake_case drift.

    Args:
        content: Raw string returned by the LLM.

    Returns:
        Normalised dict with sentimentScore, sentimentLabel, confidence,
        keywords, and reasoning keys.

    Raises:
        ValueError: If no valid JSON object can be extracted or parsed.
    """
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {content[:200]!r}")

    parsed: Dict[str, Any] = json.loads(match.group(0))

    def _get(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in parsed:
                return parsed[k]
            norm = k.lower().replace("_", "")
            for dk, dv in parsed.items():
                if dk.lower().replace("_", "") == norm:
                    return dv
        return default

    raw_score = _get("sentimentScore", "sentiment_score", default=0.0)
    score = float(raw_score) if raw_score is not None else 0.0
    score = max(-1.0, min(1.0, score))

    raw_label = _get("sentimentLabel", "sentiment_label", default="Neutral")
    label = str(raw_label).strip().capitalize() if raw_label is not None else "Neutral"
    if label not in ("Bullish", "Bearish", "Neutral"):
        label = "Neutral"

    raw_conf = _get("confidence", default=0.8)
    conf = float(raw_conf) if raw_conf is not None else 0.8
    conf = max(0.0, min(1.0, conf))

    raw_kw = _get("keywords", default=[])
    keywords: List[str] = list(raw_kw) if isinstance(raw_kw, list) else []

    raw_reason = _get("reasoning", default="Analyzed by AI model.")
    reasoning = str(raw_reason) if raw_reason is not None else "Analyzed by AI model."

    return {
        "sentimentScore": score,
        "sentimentLabel": label,
        "confidence": conf,
        "keywords": keywords,
        "reasoning": reasoning,
    }


async def _call_openrouter(
    title: str,
    summary: str,
    asset_symbol: str,
    priority: bool = False,
) -> SentimentResult:
    """
    Makes a single POST request to OpenRouter's chat completions endpoint.

    Background calls (priority=False) do NOT retry on 429 — they raise
    immediately so the circuit breaker can route to VADER without wasting
    a second API slot.

    Priority calls (priority=True, i.e. user manual clicks) retry once with
    a 10-second backoff before raising, since the user is waiting for a result.

    Args:
        title:        Article headline.
        summary:      Article summary text.
        asset_symbol: Ticker symbol used in the prompt (e.g. 'BTC').
        priority:     True for user-triggered clicks; False for background crawler.

    Returns:
        Normalised sentiment dict (sentimentScore, sentimentLabel,
        confidence, keywords, reasoning).

    Raises:
        httpx.HTTPStatusError: On persistent API errors.
        ValueError:            If the LLM response cannot be parsed as JSON.
    """
    from backend.app.core.config import settings

    prompt = (
        f"Analyze the financial market sentiment for asset '{asset_symbol}'.\n"
        f"Article title: {title}\n"
        f"Article summary: {summary}\n\n"
        f"Return ONLY a JSON object with these exact keys:\n"
        f'{{"sentimentScore": <float -1.0 to 1.0>, '
        f'"sentimentLabel": <"Bullish"|"Bearish"|"Neutral">, '
        f'"confidence": <float 0.0 to 1.0>, '
        f'"keywords": <list of 3-5 strings>, '
        f'"reasoning": <one concise professional sentence>}}'
    )

    payload: Dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional financial sentiment analyst. "
                    "Respond ONLY with a valid JSON object. No markdown, no preamble."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    headers: Dict[str, str] = {}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    api_url = str(settings.LLM_API_URL).rstrip("/")
    client = get_llm_client()

    # Define the fallback chain
    model_chain = [
        settings.LLM_MODEL,
        "google/gemini-2.5-flash:free",
        "meta-llama/llama-3-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    
    # Deduplicate in case LLM_MODEL is already one of the fallbacks
    models = []
    for m in model_chain:
        if m not in models:
            models.append(m)

    last_error: Optional[Exception] = None
    resp = None
    
    for i, current_model in enumerate(models):
        payload["model"] = current_model
        try:
            resp = await client.post(
                f"{api_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            
            # Retry once on 429 with backoff for priority calls on the first model
            if resp.status_code == 429 and priority and i == 0:
                logger.warning(
                    "openrouter_429_retry: asset=%s model=%s sleeping=10s",
                    asset_symbol, current_model
                )
                await asyncio.sleep(10.0)
                resp = await client.post(
                    f"{api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            
            resp.raise_for_status()
            
            # Ensure we actually got a response, sometimes free models return empty or error objects
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                content = str(data["choices"][0]["message"]["content"])
                result = _parse_llm_json(content)
                logger.info(
                    "openrouter_success: asset=%s model=%s label=%s score=%.2f",
                    asset_symbol,
                    current_model,
                    result["sentimentLabel"],
                    result["sentimentScore"],
                )
                return result
            else:
                raise ValueError("No choices in LLM response")
                
        except (httpx.HTTPStatusError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "openrouter_model_failed: asset=%s model=%s error=%s",
                asset_symbol,
                current_model,
                str(exc),
            )
            # Try next model in the fallback chain

    # If all models in the chain failed, raise the last error
    if last_error:
        raise last_error
    raise ValueError("Fallback chain exhausted with no result.")


async def analyze_article_sentiment(
    title: str,
    summary: str,
    asset_symbol: str,
    bypass_breaker: bool = False,
) -> SentimentResult:
    """
    Main entry point for article sentiment evaluation.

    Routing logic:
      1. Cache hit (and not a manual user click) → return cached result immediately.
      2. No LLM configured → local VADER fallback.
      3. bypass_breaker=True (user manual click) → call OpenRouter directly,
         bypassing both the cache check and the background rate limiter.
      4. Background call → check token-bucket rate limiter first:
           - Quota available → call OpenRouter via Circuit Breaker.
           - Quota exhausted → VADER fallback immediately (preserve budget for clicks).

    On 429 from OpenRouter:
      - `_call_openrouter` retries once with 10s backoff.
      - If the retry also 429s, httpx.HTTPStatusError is raised, caught by the
        Circuit Breaker (background) or propagated to the endpoint (user click).

    Args:
        title:          Article headline.
        summary:        Article summary or body excerpt.
        asset_symbol:   Ticker symbol (e.g. 'BTC') for logging and prompt context.
        bypass_breaker: True for user-triggered manual clicks (highest priority).

    Returns:
        Dict with keys: sentimentScore, sentimentLabel, confidence,
        keywords, reasoning, is_fallback.
    """
    from backend.app.core.config import settings

    cleaned_title = clean_text(title)
    cleaned_summary = clean_text(summary)
    cache_key = f"{asset_symbol}:{cleaned_title}:{cleaned_summary}"

    # ── 1. Cache hit (background callers only) ────────────────────────────────
    if not bypass_breaker:
        cached = await llm_cache.get(cache_key)
        if cached is not None:
            logger.info("sentiment_cache_hit: asset=%s", asset_symbol)
            return cached

    # ── 2. No remote LLM configured → local VADER ─────────────────────────────
    api_url = settings.LLM_API_URL
    if not api_url:
        local_res = analyze_sentiment_local(cleaned_title, cleaned_summary)
        local_res["is_fallback"] = True
        res = cast(SentimentResult, local_res)
        await llm_cache.set(cache_key, res)
        return res

    # ── 3. User manual click (bypass_breaker=True) → priority direct call ─────
    if bypass_breaker:
        result = await _call_openrouter(title, summary, asset_symbol, priority=True)
        result["is_fallback"] = False
        await llm_cache.set(cache_key, result)
        return result

    # ── 4. Background call → check rate-limit bucket first ────────────────────
    bucket_ok = await _background_rate_limit_ok()
    if not bucket_ok:
        logger.info(
            "sentiment_rate_limit_fallback: asset=%s bucket_full=True",
            asset_symbol,
        )
        local_res = analyze_sentiment_local(cleaned_title, cleaned_summary)
        local_res["is_fallback"] = True
        res = cast(SentimentResult, local_res)
        await llm_cache.set(cache_key, res)
        return res

    # ── 5. Background call with circuit breaker protection ────────────────────
    async def _primary() -> SentimentResult:
        """Attempt remote LLM call for background crawler."""
        res = await _call_openrouter(title, summary, asset_symbol)
        res["is_fallback"] = False
        return res

    async def _fallback() -> SentimentResult:
        """Local VADER fallback when circuit breaker is open or primary fails."""
        logger.warning(
            "sentiment_llm_fallback_triggered: asset=%s breaker_state=%s",
            asset_symbol,
            _sentiment_breaker.state.name,
        )
        local_res = analyze_sentiment_local(cleaned_title, cleaned_summary)
        local_res["is_fallback"] = True
        return cast(SentimentResult, local_res)

    result = await _sentiment_breaker.call(primary=_primary, fallback=_fallback)
    await llm_cache.set(cache_key, result)
    return result


async def analyze_articles_batch(
    articles: List[Dict[str, str]]
) -> Dict[str, SentimentResult]:
    from backend.app.core.config import settings

    if not articles:
        return {}

    final_results: Dict[str, SentimentResult] = {}
    to_fetch: List[Dict[str, str]] = []

    for art in articles:
        asset = art.get('asset_symbol', 'Crypto')
        c_title = clean_text(art['title'])
        c_summary = clean_text(art['summary'])
        cache_key = f"{asset}:{c_title}:{c_summary}"
        art["_cache_key"] = cache_key
        
        cached = await llm_cache.get(cache_key)
        if cached is not None:
            final_results[art["id"]] = cached
        else:
            to_fetch.append(art)

    if not to_fetch:
        return final_results

    def _fallback_for_remaining():
        for art in to_fetch:
            local_res = analyze_sentiment_local(clean_text(art["title"]), clean_text(art["summary"]))
            local_res["is_fallback"] = True
            final_results[art["id"]] = cast(SentimentResult, local_res)

    api_url = settings.LLM_API_URL
    if not api_url:
        _fallback_for_remaining()
        return final_results

    bucket_ok = await _background_rate_limit_ok()
    if not bucket_ok:
        logger.info("sentiment_batch_rate_limit_fallback: bucket_full=True")
        _fallback_for_remaining()
        return final_results

    prompt = (
        "You are a senior financial analyst specializing in crypto markets.\n"
        "Analyze the market sentiment of each article below and return ONLY a valid JSON object.\n"
        "Each key is the article ID. Each value has these exact fields:\n"
        '{"sentimentScore": <float -1.0 to 1.0>, '
        '"sentimentLabel": <"Bullish"|"Bearish"|"Neutral">, '
        '"confidence": <float 0.0 to 1.0>, '
        '"keywords": <list of 3-5 relevant financial terms>, '
        '"reasoning": <one precise sentence citing specific article facts>}\n\n'
        "Articles:\n"
    )
    for art in to_fetch:
        body = art.get("full_text") or art.get("summary", "")
        source = art.get("source", "Unknown")
        prompt += f"--- ID: {art['id']} ---\n"
        prompt += f"Asset: {art.get('asset_symbol', 'Crypto')} | Source: {source}\n"
        prompt += f"Title: {art['title']}\n"
        prompt += f"Content: {body[:1500]}\n\n"

    payload: Dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional financial sentiment analyst. Respond ONLY with a valid JSON object mapping IDs to results. No markdown, no preamble.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 8192,
    }

    headers: Dict[str, str] = {}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    client = get_llm_client()

    async def _primary() -> Dict[str, SentimentResult]:
        resp = await client.post(
            f"{str(api_url).rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = str(data["choices"][0]["message"]["content"])
        
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError(f"No JSON object found in batch response")
        
        parsed = json.loads(match.group(0))
        for art in to_fetch:
            art_id = art["id"]
            if art_id in parsed:
                item_data = parsed[art_id]
                res = _parse_llm_json(json.dumps(item_data))
                res["is_fallback"] = False
                final_results[art_id] = res
                await llm_cache.set(art["_cache_key"], res)
            else:
                local_res = analyze_sentiment_local(clean_text(art["title"]), clean_text(art["summary"]))
                local_res["is_fallback"] = True
                final_results[art_id] = cast(SentimentResult, local_res)
        return final_results

    async def _fallback() -> Dict[str, SentimentResult]:
        logger.warning(
            "sentiment_batch_llm_fallback_triggered: breaker_state=%s",
            _sentiment_breaker.state.name,
        )
        _fallback_for_remaining()
        return final_results

    await _sentiment_breaker.call(primary=_primary, fallback=_fallback)
    return final_results
