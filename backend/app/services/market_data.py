"""
Service layer for managing market data, price seeding, historical candle persistence,
and database queries.

Phase 1 + 2 changes:
  - change24h computed as ((price - openPriceToday) / openPriceToday) * 100.
  - Historical candles are seeded once into MongoDB via real OHLCV APIs (with random fallback).
  - A 60-second candle appender writes live candle data to the 1H collection.
  - Daily openPriceToday resets managed per asset at tick time.
  - Real price sync from CoinGecko (BTC/ETH/SOL) and yfinance (AAPL) every 60 seconds.
"""

import asyncio
import datetime
import logging
import random
from typing import Any, Dict, List, cast

from backend.app.core.database import (
    assets_collection,
    articles_collection,
    historical_collection,
)
from backend.app.schemas.market import HistoricalDataPoint
from backend.app.services.websocket_manager import manager as ws_manager

logger = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# Default seed data
# ──────────────────────────────────────────────────────────────────────────────

_NOW_ISO = datetime.datetime.now(datetime.timezone.utc).isoformat()

DEFAULT_ASSETS: List[Dict[str, Any]] = [
    {
        "id": "BTC",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price": 68420.50,
        "change24h": 0.0,
        "high24h": 69150.00,
        "low24h": 66800.00,
        "volume24h": 28450120000,
        "sentimentScore": 74,
        "sentimentLabel": "Bullish",
        "openPriceToday": 68420.50,
        "lastDayReset": _NOW_ISO,
    },
    {
        "id": "ETH",
        "name": "Ethereum",
        "symbol": "ETH",
        "price": 3482.10,
        "change24h": 0.0,
        "high24h": 3590.00,
        "low24h": 3420.00,
        "volume24h": 14210980000,
        "sentimentScore": 48,
        "sentimentLabel": "Neutral",
        "openPriceToday": 3482.10,
        "lastDayReset": _NOW_ISO,
    },
    {
        "id": "SOL",
        "name": "Solana",
        "symbol": "SOL",
        "price": 154.85,
        "change24h": 0.0,
        "high24h": 156.40,
        "low24h": 140.20,
        "volume24h": 4120550000,
        "sentimentScore": 86,
        "sentimentLabel": "Bullish",
        "openPriceToday": 154.85,
        "lastDayReset": _NOW_ISO,
    },
    {
        "id": "TON",
        "name": "Toncoin",
        "symbol": "TON",
        "price": 6.20,
        "change24h": 0.0,
        "high24h": 6.50,
        "low24h": 6.00,
        "volume24h": 350000000,
        "sentimentScore": 62,
        "sentimentLabel": "Bullish",
        "openPriceToday": 6.20,
        "lastDayReset": _NOW_ISO,
    },
    {
        "id": "AAPL",
        "name": "Apple Inc.",
        "symbol": "AAPL",
        "price": 185.35,
        "change24h": 0.0,
        "high24h": 186.95,
        "low24h": 184.10,
        "volume24h": 8930400000,
        "sentimentScore": 54,
        "sentimentLabel": "Neutral",
        "openPriceToday": 185.35,
        "lastDayReset": _NOW_ISO,
    },
]

ARTICLE_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "bullish": [
        {
            "title": "Breakthrough Adoption: Major Institution Integrates {Asset}",
            "summary": "A top-tier global investment firm has announced a direct integration and custody solution for {Asset}, indicating significant institutional inflows.",
            "reasoning": "Institutional adoption is the strongest long-term catalyst. By integrating {Asset} into standard portfolios, the addressable market increases by orders of magnitude, providing a structural demand bid.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["adoption", "institutional", "integration", "inflow"],
        },
        {
            "title": "{Asset} Technical Breakout Confirmed by Analysts",
            "summary": "Analysts report that {Asset} has closed above its key resistance level on high trading volume, signaling the start of a new macro upward trend.",
            "reasoning": "The asset has cleared the 200-day moving average and consolidated. High relative volume on the breakout indicates strong buying interest and momentum support.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["breakout", "technical", "resistance", "volume"],
        },
    ],
    "bearish": [
        {
            "title": "Regulatory Headwinds: New Compliance Guidelines Target {Asset}",
            "summary": "Regulatory agencies have proposed stricter compliance guidelines for trading and holding {Asset}, sparking sell-off concerns.",
            "reasoning": "Increased compliance costs and regulatory uncertainty discourage capital allocators. This creates short-term sell pressure and delays developer integration due to compliance risk.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["regulation", "compliance", "uncertainty", "restriction"],
        },
        {
            "title": "Macro Slowdown Triggers Capital Flight Out of {Asset}",
            "summary": "Rising global interest rates and macro liquidity tightening have pushed investors to derisk, leading to capital outflows from {Asset}.",
            "reasoning": "High interest rates increase the opportunity cost of holding risk-on assets. Capital naturally moves back to yield-bearing cash instruments, decreasing the liquidity pool.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["macro", "liquidity", "outflow", "derisking"],
        },
    ],
    "neutral": [
        {
            "title": "{Asset} Consolidation Range Narrows Ahead of Key Options Expiry",
            "summary": "The price of {Asset} continues to trade in a tight range as options contracts worth billions are set to expire this Friday.",
            "reasoning": "Options expiry usually leads to market-maker hedging activity that pins the asset price to maximum pain points, compressing volatility until the expiry passes.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["options", "consolidation", "volatility", "expiry"],
        }
    ],
}

SOURCES: List[str] = [
    "Reuters",
    "Bloomberg",
    "TechCrunch",
    "CoinDesk",
    "Wall Street Journal",
    "Financial Times",
]


# ──────────────────────────────────────────────────────────────────────────────
# Article generation helpers
# ──────────────────────────────────────────────────────────────────────────────


def generate_single_mock_article(
    asset_id: str, asset_name: str, timestamp: datetime.datetime
) -> Dict[str, Any]:
    """
    Generates a single randomized mock sentiment article for seeding the database.

    Args:
        asset_id: Ticker symbol of the asset.
        asset_name: Full display name of the asset.
        timestamp: UTC datetime to stamp the article with.

    Returns:
        A dict representing a complete article document ready for insertion.
    """
    sentiment = random.choice(["Bullish", "Bearish", "Neutral"])
    pool = ARTICLE_TEMPLATES[sentiment.lower()]
    template = random.choice(pool)

    title = cast(str, template["title"]).replace("{Asset}", asset_name)
    summary = cast(str, template["summary"]).replace("{Asset}", asset_name)
    reasoning = cast(str, template["reasoning"]).replace("{Asset}", asset_name)
    source = random.choice(SOURCES)

    if sentiment == "Bullish":
        sentiment_score = round(0.4 + random.random() * 0.55, 2)
    elif sentiment == "Bearish":
        sentiment_score = round(-0.4 - random.random() * 0.55, 2)
    else:
        sentiment_score = round((random.random() - 0.5) * 0.4, 2)

    art_id = f"art_seed_{asset_id}_{random.randint(10000, 99999)}"

    return {
        "id": art_id,
        "asset_id": asset_id,
        "timestamp": timestamp.isoformat(),
        "timestamp_dt": timestamp,
        "source": source,
        "title": title,
        "url": "#",
        "summary": summary,
        "sentimentScore": sentiment_score,
        "sentimentLabel": sentiment,
        "confidence": round(0.75 + random.random() * 0.2, 2),
        "keywords": list(template["keywords"]),
        "llmReasoning": reasoning,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Database seeding
# ──────────────────────────────────────────────────────────────────────────────


async def seed_database_if_empty() -> None:
    """
    Checks MongoDB collection states and seeds defaults if empty.

    Seeds:
      - DEFAULT_ASSETS into `assets_collection` when empty.
      - Mock articles into `articles_collection` when empty.
      - Historical candles for all assets and timeframes when empty.

    Raises:
        Exception: Propagates any MongoDB error after logging it.
    """
    try:
        asset_count = await assets_collection.count_documents({})
        if asset_count == 0:
            logger.info("Assets collection empty — seeding defaults.")
            await assets_collection.insert_many(DEFAULT_ASSETS)
            logger.info("Assets seeded successfully.")

        art_count = await articles_collection.count_documents({})
        if art_count == 0:
            logger.info("Articles collection empty — seeding historical articles.")
            now = datetime.datetime.now(datetime.timezone.utc)
            seed_articles: List[Dict[str, Any]] = []

            for asset in DEFAULT_ASSETS:
                asset_id = str(asset["id"])
                asset_name = str(asset["name"])
                for i in range(10):
                    ts = now - datetime.timedelta(minutes=i * 45)
                    seed_articles.append(
                        generate_single_mock_article(asset_id, asset_name, ts)
                    )

            if seed_articles:
                await articles_collection.insert_many(seed_articles)
                logger.info("Seeded %d articles.", len(seed_articles))

        # Seed historical candles for every asset x timeframe combination
        for asset in DEFAULT_ASSETS:
            asset_id = str(asset["id"])
            for timeframe in ("1H", "24H", "7D", "30D"):
                await seed_historical_candles(asset_id, timeframe)

    except Exception as exc:
        logger.error("db_seed_failed: %s", str(exc))
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Historical candle helpers
# ──────────────────────────────────────────────────────────────────────────────


def _build_candle_volatility(asset_id: str, timeframe: str) -> float:
    """
    Returns the per-candle volatility factor for a given asset and timeframe.

    Args:
        asset_id: Ticker symbol.
        timeframe: One of '1H', '24H', '7D', '30D'.

    Returns:
        Float volatility multiplier for candle generation.
    """
    base: float = (
        0.015
        if asset_id == "SOL"
        else 0.005
        if asset_id == "BTC"
        else 0.008
        if asset_id == "ETH"
        else 0.003
    )
    return (
        base * 0.1
        if timeframe == "1H"
        else base
        if timeframe == "24H"
        else base * 2.5
        if timeframe == "7D"
        else base * 6.0
    )


def _timeframe_to_step_minutes(timeframe: str) -> int:
    """
    Returns the candle duration in minutes for the given timeframe.

    Args:
        timeframe: One of '1H', '24H', '7D', '30D'.

    Returns:
        Step size in minutes.
    """
    if timeframe == "1H":
        return 1
    if timeframe in ("24H", "7D"):
        return 60
    return 1440


def _timeframe_to_points_count(timeframe: str) -> int:
    """
    Returns the number of candle data points for the given timeframe.

    Args:
        timeframe: One of '1H', '24H', '7D', '30D'.

    Returns:
        Number of candle points.
    """
    if timeframe == "1H":
        return 60
    if timeframe == "24H":
        return 24
    if timeframe == "7D":
        return 168
    return 30


def _format_candle_timestamp(ts: datetime.datetime, timeframe: str) -> str:
    """
    Formats a UTC datetime into the display string expected by frontend charts.

    Args:
        ts: UTC datetime of the candle.
        timeframe: One of '1H', '24H', '7D', '30D'.

    Returns:
        Human-readable timestamp string.
    """
    if timeframe == "1H":
        return ts.strftime("%H:%M:%S")
    if timeframe == "24H":
        return ts.strftime("%b %d %H:%M")
    if timeframe == "7D":
        return ts.strftime("%b %d %H:00")
    return ts.strftime("%b %d")


# ──────────────────────────────────────────────────────────────────────────────
# Historical candle seeding
# ──────────────────────────────────────────────────────────────────────────────


async def seed_historical_candles(asset_id: str, timeframe: str) -> None:
    """
    Generates and bulk-inserts the initial candle history for an asset+timeframe pair.

    For BTC, ETH, SOL: attempts to fetch real OHLCV from CoinGecko. Falls back to
    random generation if the API is unavailable at seed time.
    For AAPL: uses yfinance historical data. Falls back to random generation.

    Skips insertion if at least one candle already exists (idempotent).

    Args:
        asset_id: Ticker symbol (e.g. 'BTC').
        timeframe: One of '1H', '24H', '7D', '30D'.

    Raises:
        Exception: Propagates MongoDB errors after logging.
    """
    existing_count = await historical_collection.count_documents(
        {"asset_id": asset_id, "timeframe": timeframe}
    )
    if existing_count > 0:
        return

    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        logger.warning(
            "seed_historical_candles_skip: asset not found asset_id=%s", asset_id
        )
        return

    candles = await _seed_from_real_ohlcv(asset_id, timeframe, asset)
    if not candles:
        candles = _generate_random_candles(asset_id, timeframe, asset)

    if candles:
        try:
            await historical_collection.insert_many(candles, ordered=False)
            logger.info(
                "seed_historical_candles_done: asset_id=%s timeframe=%s count=%d",
                asset_id,
                timeframe,
                len(candles),
            )
        except Exception as exc:
            logger.error(
                "seed_historical_candles_failed: asset_id=%s timeframe=%s error=%s",
                asset_id,
                timeframe,
                str(exc),
            )


async def _seed_from_real_ohlcv(
    asset_id: str,
    timeframe: str,
    asset: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Attempts to build candle documents from real OHLCV API data.

    Returns an empty list if the API is unavailable or the asset is not supported.

    Args:
        asset_id: Ticker symbol.
        timeframe: Candle timeframe ('1H', '24H', '7D', '30D').
        asset: MongoDB asset document with current price/volume.

    Returns:
        List of candle dicts ready for MongoDB insertion, or empty list on failure.
    """
    from backend.app.services.price_feed import (
        fetch_coingecko_ohlcv,
        COINGECKO_IDS,
    )

    days_map: Dict[str, int] = {"1H": 1, "24H": 1, "7D": 7, "30D": 30}
    days = days_map.get(timeframe, 1)

    try:
        if asset_id in COINGECKO_IDS:
            raw = await fetch_coingecko_ohlcv(asset_id, days)
            return _coingecko_ohlcv_to_candles(asset_id, timeframe, raw, asset)

        if asset_id == "AAPL":
            return await _aapl_ohlcv_to_candles(asset_id, timeframe, days, asset)

    except Exception as exc:
        logger.warning(
            "real_ohlcv_seed_failed: asset_id=%s timeframe=%s error=%s — using random fallback",
            asset_id,
            timeframe,
            str(exc),
        )

    return []


def _coingecko_ohlcv_to_candles(
    asset_id: str,
    timeframe: str,
    raw: List[List[float]],
    asset: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Converts CoinGecko OHLCV rows to the internal MongoDB candle document format.

    Args:
        asset_id: Ticker symbol.
        timeframe: Candle timeframe.
        raw: List of [timestamp_ms, open, high, low, close] from CoinGecko.
        asset: MongoDB asset document.

    Returns:
        List of candle dicts.
    """
    sentiment_score: int = int(asset.get("sentimentScore", 50))
    volume24h: int = int(asset.get("volume24h", 1000000))
    points_count = _timeframe_to_points_count(timeframe)
    candles: List[Dict[str, Any]] = []

    for row in raw[-points_count:]:
        if len(row) < 5:
            continue
        ts_ms = int(row[0])
        ts_unix = ts_ms // 1000
        ts_dt = datetime.datetime.fromtimestamp(ts_unix, tz=datetime.timezone.utc)
        ts_str = _format_candle_timestamp(ts_dt, timeframe)
        candle_sentiment = min(
            100, max(0, int(sentiment_score + (random.random() - 0.5) * 20))
        )
        candles.append(
            {
                "asset_id": asset_id,
                "timeframe": timeframe,
                "timestamp": ts_str,
                "timestamp_unix": ts_unix,
                "open": round(float(row[1]), 2),
                "high": round(float(row[2]), 2),
                "low": round(float(row[3]), 2),
                "close": round(float(row[4]), 2),
                "volume": int(volume24h / max(len(raw), 1) * (0.5 + random.random())),
                "sentimentScore": candle_sentiment,
            }
        )

    return candles


async def _aapl_ohlcv_to_candles(
    asset_id: str,
    timeframe: str,
    days: int,
    asset: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Fetches AAPL historical OHLCV from yfinance and converts to candle format.

    Args:
        asset_id: Should always be 'AAPL'.
        timeframe: Candle timeframe.
        days: Number of calendar days of history to request.
        asset: MongoDB asset document.

    Returns:
        List of candle dicts.
    """
    import yfinance as yf  # type: ignore[import-untyped]

    loop = asyncio.get_event_loop()
    interval = "1h" if timeframe in ("1H", "24H") else "1d"
    period = f"{days}d" if days <= 60 else "60d"

    def _download() -> Any:
        return yf.download(
            "AAPL",
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )

    hist = await loop.run_in_executor(None, _download)
    if hist is None or hist.empty:
        return []

    # Flatten MultiIndex columns to single string names if necessary
    if hasattr(hist.columns, "levels"):
        hist.columns = hist.columns.get_level_values(0)

    sentiment_score: int = int(asset.get("sentimentScore", 50))
    volume24h: int = int(asset.get("volume24h", 1000000))
    points_count = _timeframe_to_points_count(timeframe)
    candles: List[Dict[str, Any]] = []

    for dt_idx, row in hist.tail(points_count).iterrows():
        ts_dt = dt_idx.to_pydatetime().replace(tzinfo=datetime.timezone.utc)
        ts_unix = int(ts_dt.timestamp())
        ts_str = _format_candle_timestamp(ts_dt, timeframe)
        candle_sentiment = min(
            100, max(0, int(sentiment_score + (random.random() - 0.5) * 20))
        )
        candles.append(
            {
                "asset_id": asset_id,
                "timeframe": timeframe,
                "timestamp": ts_str,
                "timestamp_unix": ts_unix,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row.get("Volume", volume24h // points_count)),
                "sentimentScore": candle_sentiment,
            }
        )

    return candles


def _generate_random_candles(
    asset_id: str,
    timeframe: str,
    asset: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Fallback random candle generator used when real OHLCV APIs are unavailable.

    Args:
        asset_id: Ticker symbol.
        timeframe: Candle timeframe.
        asset: MongoDB asset document with current price/volume/sentiment.

    Returns:
        List of candle dicts.
    """
    points_count = _timeframe_to_points_count(timeframe)
    step_minutes = _timeframe_to_step_minutes(timeframe)
    vol_factor = _build_candle_volatility(asset_id, timeframe)
    base_price: float = float(asset["price"])
    volume24h: int = int(asset["volume24h"])
    sentiment_score: int = int(asset["sentimentScore"])

    now = datetime.datetime.now(datetime.timezone.utc)
    current_price = base_price
    candles: List[Dict[str, Any]] = []

    for i in range(points_count - 1, -1, -1):
        ts = now - datetime.timedelta(minutes=i * step_minutes)
        ts_unix = int(ts.timestamp())
        ts_str = _format_candle_timestamp(ts, timeframe)

        random_change = (random.random() - 0.48) * (base_price * vol_factor)
        open_val = max(0.01, current_price)
        close_val = max(0.01, current_price + random_change)
        high_val = max(open_val, close_val) + random.random() * (base_price * 0.002)
        low_val = max(
            0.01,
            min(open_val, close_val) - random.random() * (base_price * 0.002),
        )
        volume = int(volume24h / points_count * (0.5 + random.random()))
        candle_sentiment = min(
            100, max(0, int(sentiment_score + (random.random() - 0.5) * 20))
        )

        candles.append(
            {
                "asset_id": asset_id,
                "timeframe": timeframe,
                "timestamp": ts_str,
                "timestamp_unix": ts_unix,
                "open": round(open_val, 2),
                "high": round(high_val, 2),
                "low": round(low_val, 2),
                "close": round(close_val, 2),
                "volume": volume,
                "sentimentScore": candle_sentiment,
            }
        )
        current_price = close_val

    if candles:
        candles[-1]["close"] = base_price

    return candles


# ──────────────────────────────────────────────────────────────────────────────
# Historical candle read
# ──────────────────────────────────────────────────────────────────────────────


async def get_historical_candles(
    asset_id: str, timeframe: str
) -> List[HistoricalDataPoint]:
    """
    Queries MongoDB for persisted historical candles for the given asset and timeframe.

    Returns candles sorted by `timestamp_unix` ascending (oldest to newest).

    Args:
        asset_id: Ticker symbol (e.g. 'BTC').
        timeframe: One of '1H', '24H', '7D', '30D'.

    Returns:
        A list of HistoricalDataPoint objects, empty if none found.
    """
    cursor = historical_collection.find(
        {"asset_id": asset_id, "timeframe": timeframe},
        {"_id": 0},
    ).sort("timestamp_unix", 1)

    raw = await cursor.to_list(length=1000)
    return [HistoricalDataPoint.model_validate(doc) for doc in raw]


# ──────────────────────────────────────────────────────────────────────────────
# Live candle appender
# ──────────────────────────────────────────────────────────────────────────────


async def append_latest_candle(asset_id: str) -> None:
    """
    Appends a new 1H candle to the historical collection using the current price.

    Called every 60 seconds from `background_update_loop`. Uses upsert with
    `$setOnInsert` to be idempotent — the compound unique index prevents duplicates.

    Args:
        asset_id: Ticker symbol (e.g. 'BTC').
    """
    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    ts_minute = now.replace(second=0, microsecond=0)
    ts_unix = int(ts_minute.timestamp())
    ts_str = _format_candle_timestamp(ts_minute, "1H")

    current_price: float = float(asset["price"])
    volume24h: int = int(asset["volume24h"])
    sentiment_score: int = int(asset["sentimentScore"])

    high_val = current_price + random.random() * (current_price * 0.002)
    low_val = max(0.01, current_price - random.random() * (current_price * 0.002))
    volume = int(volume24h / 1440 * (0.5 + random.random()))
    candle_sentiment = min(
        100, max(0, int(sentiment_score + (random.random() - 0.5) * 10))
    )

    await historical_collection.update_one(
        {"asset_id": asset_id, "timeframe": "1H", "timestamp_unix": ts_unix},
        {
            "$setOnInsert": {
                "asset_id": asset_id,
                "timeframe": "1H",
                "timestamp": ts_str,
                "timestamp_unix": ts_unix,
                "open": current_price,
                "high": round(high_val, 2),
                "low": round(low_val, 2),
                "close": current_price,
                "volume": volume,
                "sentimentScore": candle_sentiment,
            }
        },
        upsert=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Background price update loop (Phase 2 — real data)
# ──────────────────────────────────────────────────────────────────────────────


async def background_update_loop() -> None:
    """
    Syncs real market prices from CoinGecko (BTC/ETH/SOL) and yfinance (AAPL) every 60 seconds.

    On each tick:
      1. Checks if the UTC date has rolled over; resets `openPriceToday` if so.
      2. Fetches current prices from external APIs (cached at 60s TTL).
      3. Computes `change24h` as ((price - openPriceToday) / openPriceToday) * 100.
      4. Appends a new 1H candle and checks alerts.
    """
    from backend.app.services.price_feed import fetch_alchemy_prices, fetch_aapl_price

    while True:
        try:
            await asyncio.sleep(60.0)

            now = datetime.datetime.now(datetime.timezone.utc)

            try:
                alchemy_data = await fetch_alchemy_prices()
            except Exception as exc:
                logger.warning(
                    "alchemy_fetch_failed: error=%s — skipping tick", str(exc)
                )
                alchemy_data = {}

            try:
                aapl_data = await fetch_aapl_price()
            except Exception as exc:
                logger.warning(
                    "aapl_fetch_failed: error=%s — skipping AAPL tick", str(exc)
                )
                aapl_data = {}

            cursor = assets_collection.find({})
            async for asset in cursor:
                asset_id: str = str(asset["id"])
                current_price: float = float(asset["price"])
                open_price_today: float = float(
                    asset.get("openPriceToday", current_price)
                )
                last_reset_str: str = str(asset.get("lastDayReset", now.isoformat()))
                sentiment_score: int = int(asset["sentimentScore"])

                if asset_id in alchemy_data:
                    feed = alchemy_data[asset_id]
                    new_price: float = feed["price"]
                    high24h: float = feed["high24h"]
                    low24h: float = feed["low24h"]
                    vol24h: int = int(feed["volume24h"])
                elif asset_id == "AAPL" and aapl_data:
                    new_price = aapl_data["price"]
                    high24h = aapl_data["high24h"]
                    low24h = aapl_data["low24h"]
                    vol24h = int(aapl_data["volume24h"])
                else:
                    continue

                if new_price <= 0.0:
                    continue

                # Daily reset check
                last_reset_date = datetime.datetime.fromisoformat(last_reset_str).date()
                if now.date() != last_reset_date:
                    open_price_today = new_price
                    last_reset_str = now.isoformat()
                    await assets_collection.update_one(
                        {"id": asset_id},
                        {
                            "$set": {
                                "openPriceToday": open_price_today,
                                "lastDayReset": last_reset_str,
                                "high24h": new_price,
                                "low24h": new_price,
                            }
                        },
                    )

                if open_price_today == 0.0:
                    open_price_today = new_price
                change24h = round(
                    ((new_price - open_price_today) / open_price_today) * 100, 2
                )

                await assets_collection.update_one(
                    {"id": asset_id},
                    {
                        "$set": {
                            "price": new_price,
                            "high24h": high24h,
                            "low24h": low24h,
                            "volume24h": vol24h,
                            "change24h": change24h,
                        }
                    },
                )

                await append_latest_candle(asset_id)
                await check_alerts_for_asset(asset_id, new_price, sentiment_score)

                # Fetch the freshly updated asset document and broadcast
                updated_asset = await assets_collection.find_one({"id": asset_id})
                if updated_asset:
                    updated_asset.pop("_id", None)
                    await ws_manager.broadcast_asset_update(asset_id, updated_asset)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("price_sync_error: %s", str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Alert checking
# ──────────────────────────────────────────────────────────────────────────────


async def check_alerts_for_asset(
    asset_id: str,
    current_price: float,
    current_sentiment: int,
) -> None:
    """
    Checks all untriggered user alerts for a given asset and triggers matching ones.

    Condition types:
      - PRICE_ABOVE: triggers when current_price >= target_value
      - PRICE_BELOW: triggers when current_price <= target_value
      - SENTIMENT_CHANGE: triggers when current_sentiment crosses target_value

    Args:
        asset_id: Ticker symbol of the asset being checked.
        current_price: Latest price for the asset.
        current_sentiment: Latest aggregated sentiment score (0-100).
    """
    from backend.app.core.database import users_collection

    cursor = users_collection.find(
        {
            "alerts": {
                "$elemMatch": {
                    "asset_id": asset_id,
                    "triggered": False,
                }
            }
        }
    )

    async for user in cursor:
        alerts: List[Dict[str, Any]] = list(user.get("alerts", []))
        for alert in alerts:
            if alert.get("asset_id") != asset_id:
                continue
            if alert.get("triggered"):
                continue

            condition: str = str(alert.get("condition", ""))
            target: float = float(alert.get("target_value", 0.0))
            alert_id: str = str(alert.get("id", ""))
            triggered = False

            if condition == "PRICE_ABOVE" and current_price >= target:
                triggered = True
            elif condition == "PRICE_BELOW" and current_price <= target:
                triggered = True
            elif condition == "SENTIMENT_CHANGE" and (
                current_sentiment >= target or current_sentiment <= target
            ):
                triggered = True

            if triggered:
                await users_collection.update_one(
                    {"_id": user["_id"], "alerts.id": alert_id},
                    {"$set": {"alerts.$.triggered": True}},
                )
                logger.info(
                    "alert_triggered: user_id=%s alert_id=%s condition=%s asset_id=%s",
                    str(user.get("id", "")),
                    alert_id,
                    condition,
                    asset_id,
                )
