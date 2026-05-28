"""
Real market data price feeds for CoinGecko (BTC/ETH/SOL) and yfinance (AAPL).

All functions respect the CoinGecko Free API rate limit of 30 req/min by using
a 60-second TTL cache. On error the cache is NOT populated — stale data is
never silently returned.

Phase 2 integration:
  - fetch_coingecko_prices()  → BTC, ETH, SOL current price + 24h stats
  - fetch_coingecko_ohlcv()   → OHLCV candles for BTC/ETH/SOL
  - fetch_aapl_price()        → AAPL current price via yfinance (async wrapper)
  - _fetch_aapl_sync()        → synchronous yfinance implementation
"""

import asyncio
import logging
from typing import Any, Dict, List, cast

import httpx

from backend.app.core.cache import cache

logger = logging.getLogger("app")

COINGECKO_IDS: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_COINGECKO_PRICES_TTL = 60  # seconds
_COINGECKO_OHLCV_TTL = 300  # seconds
_AAPL_TTL = 60  # seconds
_RATE_LIMIT_RETRY_WAIT = 10.0  # seconds to wait on 429


# ──────────────────────────────────────────────────────────────────────────────
# CoinGecko integration
# ──────────────────────────────────────────────────────────────────────────────


async def fetch_coingecko_prices() -> Dict[str, Dict[str, float]]:
    """
    Fetches current price, 24h change, 24h high, 24h low, and volume for BTC, ETH, SOL.

    Uses CoinGecko /coins/markets endpoint. Caches the response for 60 seconds.

    Returns:
        Dict keyed by asset_id ('BTC', 'ETH', 'SOL'), each containing:
            - price: float — current USD price
            - change24h: float — 24h percentage change
            - high24h: float — 24h high in USD
            - low24h: float — 24h low in USD
            - volume24h: float — 24h volume in USD

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx after retry.
        httpx.RequestError: On network errors.
    """
    cache_key = "coingecko_prices"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(Dict[str, Dict[str, float]], cached)

    url = f"{_COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINGECKO_IDS.values()),
        "price_change_percentage": "24h",
    }

    result: Dict[str, Dict[str, float]] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await _coingecko_get(client, url, params)

    rows: List[Dict[str, Any]] = response.json()
    id_to_symbol = {v: k for k, v in COINGECKO_IDS.items()}

    for row in rows:
        coin_id: str = str(row.get("id", ""))
        symbol = id_to_symbol.get(coin_id)
        if not symbol:
            continue
        result[symbol] = {
            "price": float(row.get("current_price") or 0.0),
            "change24h": float(row.get("price_change_percentage_24h") or 0.0),
            "high24h": float(row.get("high_24h") or 0.0),
            "low24h": float(row.get("low_24h") or 0.0),
            "volume24h": float(row.get("total_volume") or 0.0),
        }

    cache.set(cache_key, result, _COINGECKO_PRICES_TTL)
    logger.info("coingecko_prices_fetched: symbols=%s", list(result.keys()))
    return result


async def fetch_coingecko_ohlcv(asset_id: str, days: int) -> List[List[float]]:
    """
    Fetches OHLCV candle data for a given CoinGecko-tracked asset.

    Uses CoinGecko /coins/{id}/ohlc endpoint. Caches responses for 300 seconds.

    Args:
        asset_id: Ticker symbol — must be one of 'BTC', 'ETH', 'SOL'.
        days: Number of days of candle history to fetch (1, 7, 14, 30, 90, 180, 365).

    Returns:
        List of [timestamp_ms, open, high, low, close] lists.

    Raises:
        ValueError: If asset_id is not a known CoinGecko asset.
        httpx.HTTPStatusError: On non-2xx responses after retry.
    """
    coin_id = COINGECKO_IDS.get(asset_id)
    if not coin_id:
        raise ValueError(
            f"fetch_coingecko_ohlcv: asset_id={asset_id!r} is not a CoinGecko asset"
        )

    cache_key = f"coingecko_ohlcv_{asset_id}_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(List[List[float]], cached)

    url = f"{_COINGECKO_BASE}/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": str(days)}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await _coingecko_get(client, url, params)

    data: List[List[float]] = response.json()
    cache.set(cache_key, data, _COINGECKO_OHLCV_TTL)
    logger.info(
        "coingecko_ohlcv_fetched: asset_id=%s days=%d candles=%d",
        asset_id,
        days,
        len(data),
    )
    return data


async def _coingecko_get(
    client: httpx.AsyncClient,
    url: str,
    params: Dict[str, str],
) -> httpx.Response:
    """
    Issues a GET request to the CoinGecko API with robust retry logic on HTTP 429.

    Supports up to 3 attempts with exponential backoff (e.g. 10s -> 20s delay).

    Args:
        client: Shared httpx async client.
        url: Full request URL.
        params: Query string parameters.

    Returns:
        The successful httpx.Response.

    Raises:
        httpx.HTTPStatusError: If the response is non-2xx after retries.
    """
    max_retries = 3
    retry_delay = _RATE_LIMIT_RETRY_WAIT
    response = None

    for attempt in range(max_retries):
        response = await client.get(url, params=params)

        if response.status_code == 429:
            if attempt == max_retries - 1:
                break

            logger.warning(
                "coingecko_rate_limited: url=%s attempt=%d/%d retrying_in=%.1fs",
                url,
                attempt + 1,
                max_retries,
                retry_delay,
            )
            await asyncio.sleep(retry_delay)
            retry_delay *= 2.0  # Exponential backoff
            continue

        return response

    # If we exited the loop and got an unsuccessful response, raise it
    if response is None or not response.is_success:
        status_code = response.status_code if response else "Unknown"
        response_text = response.text if response else ""
        raise httpx.HTTPStatusError(
            f"CoinGecko request failed: status_code={status_code} "
            f"url={url} body={response_text!r}",
            request=response.request if response else httpx.Request("GET", url),
            response=response if response else httpx.Response(500),
        )

    return response


# ──────────────────────────────────────────────────────────────────────────────
# yfinance integration for AAPL
# ──────────────────────────────────────────────────────────────────────────────


def _fetch_aapl_sync() -> Dict[str, float]:
    """
    Synchronous yfinance fetch for AAPL current price and 24h stats.

    Uses `fast_info` for low-latency current price. Falls back to the last
    available close price outside NYSE market hours.

    Returns:
        Dict with keys: price, change24h, high24h, low24h, volume24h.

    Raises:
        RuntimeError: If yfinance returns no usable price data.
    """
    import yfinance as yf  # type: ignore[import-untyped]

    ticker = yf.Ticker("AAPL")
    fast = ticker.fast_info

    current_price: float = float(fast.last_price or fast.previous_close or 0.0)
    if current_price == 0.0:
        raise RuntimeError("fetch_aapl_sync: yfinance returned no price data for AAPL")

    prev_close: float = float(fast.previous_close or current_price)
    change24h = (
        round(((current_price - prev_close) / prev_close) * 100, 2)
        if prev_close
        else 0.0
    )

    # Download 2 days to get today's high/low/volume
    hist = yf.download(
        "AAPL", period="2d", interval="1d", progress=False, auto_adjust=True
    )
    high24h = current_price
    low24h = current_price
    volume24h = 0

    if hist is not None and not hist.empty:
        # Flatten MultiIndex columns to single string names if necessary
        if hasattr(hist.columns, "levels"):
            hist.columns = hist.columns.get_level_values(0)
            
        last_row = hist.iloc[-1]
        high24h = float(last_row.get("High", current_price))
        low24h = float(last_row.get("Low", current_price))
        volume24h = int(last_row.get("Volume", 0))

    return {
        "price": round(current_price, 2),
        "change24h": change24h,
        "high24h": round(high24h, 2),
        "low24h": round(low24h, 2),
        "volume24h": float(volume24h),
    }


async def fetch_aapl_price() -> Dict[str, float]:
    """
    Async wrapper around `_fetch_aapl_sync` for AAPL market data.

    Runs the synchronous yfinance call in a thread-pool executor to avoid
    blocking the asyncio event loop. Caches the result for 60 seconds.

    Returns:
        Dict with keys: price, change24h, high24h, low24h, volume24h.

    Raises:
        RuntimeError: If yfinance returns no usable price data.
        Exception: Propagates any other yfinance errors after logging.
    """
    cache_key = "aapl_price"
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(Dict[str, float], cached)

    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, _fetch_aapl_sync)
    except Exception as exc:
        logger.warning("aapl_fetch_failed: error=%s", str(exc))
        raise

    cache.set(cache_key, data, _AAPL_TTL)
    logger.info(
        "aapl_price_fetched: price=%s change24h=%s", data["price"], data["change24h"]
    )
    return data
