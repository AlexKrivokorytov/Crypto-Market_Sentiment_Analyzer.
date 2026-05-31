"""
Thin orchestrator for market data operations.

This module is the sole entry point for:
  - Database seeding at startup (seed_database_if_empty)
  - Live price sync background loop (background_update_loop)
  - Historical candle seeding and reading
  - Live 1H candle appender
  - Alert checking

All per-asset data fetching is delegated to the AssetHandlerFactory.
Adding a new coin requires only a one-line change in handlers/config.py.

Phase 1 refactor:
  - DEFAULT_ASSETS and per-asset constant blocks removed.
  - seed_database_if_empty iterates handler_factory.all().
  - background_update_loop iterates handler_factory.all() → handler.fetch_price().
  - seed_historical_candles calls handler.fetch_ohlcv() via the factory.
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
from backend.app.handlers.factory import handler_factory
from backend.app.schemas.market import HistoricalDataPoint
from backend.app.services.websocket_manager import manager as ws_manager

logger = logging.getLogger("app")


# ──────────────────────────────────────────────────────────────────────────────
# Article generation helpers
# ──────────────────────────────────────────────────────────────────────────────

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


def generate_single_mock_article(
    asset_id: str, asset_name: str, timestamp: datetime.datetime
) -> Dict[str, Any]:
    """
    Generates a single randomised mock sentiment article for seeding the database.

    Args:
        asset_id:   Ticker symbol of the asset.
        asset_name: Full display name of the asset.
        timestamp:  UTC datetime to stamp the article with.

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
# Database seeding — now fully driven by AssetHandlerFactory
# ──────────────────────────────────────────────────────────────────────────────


async def seed_database_if_empty() -> None:
    """
    Checks MongoDB collection states and seeds defaults if empty.
    Ensures newly added assets from handler_factory are automatically registered
    and seeded with initial articles and historical candles.
    """
    try:
        all_seed_articles = []
        
        for handler in handler_factory.all():
            existing_asset = await assets_collection.find_one({"id": handler.asset_id})
            if not existing_asset:
                logger.info(
                    "db_seed_asset_incremental: asset=%s display_name=%s registered.",
                    handler.asset_id,
                    handler.name,
                )
                await assets_collection.insert_one(handler.to_seed_document())

                art_count = await articles_collection.count_documents(
                    {"asset_id": handler.asset_id}
                )
                if art_count == 0:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    for i in range(10):
                        ts = now - datetime.timedelta(minutes=i * 45)
                        all_seed_articles.append(
                            generate_single_mock_article(
                                handler.asset_id, handler.name, ts
                            )
                        )

        if all_seed_articles:
            logger.info("db_seed: evaluating %d mock articles via Batched LLM...", len(all_seed_articles))
            from backend.app.services.llm import analyze_articles_batch, clean_text
            from backend.app.services.sentiment_engine import analyze_sentiment_local
            
            batch_input = []
            for a in all_seed_articles:
                batch_input.append({
                    "id": a["id"],
                    "asset_symbol": a["asset_id"],
                    "title": a["title"],
                    "summary": a["summary"]
                })
                
            batch_size = 15
            all_results = {}
            for i in range(0, len(batch_input), batch_size):
                chunk = batch_input[i:i + batch_size]
                logger.info("db_seed: sending chunk %d", (i//batch_size + 1))
                res = await analyze_articles_batch(chunk)
                all_results.update(res)
                await asyncio.sleep(2.0)
                
            for a in all_seed_articles:
                res = all_results.get(a["id"])
                if res:
                    vader_res = analyze_sentiment_local(clean_text(a["title"]), clean_text(a["summary"]))
                    a["sentimentScore"] = vader_res["sentimentScore"]
                    a["sentimentLabel"] = vader_res["sentimentLabel"]
                    a["confidence"] = res["confidence"]
                    a["keywords"] = res["keywords"]
                    a["llmReasoning"] = res.get("reasoning", "")
                    a["is_fallback"] = res.get("is_fallback", False)
                    
            await articles_collection.insert_many(all_seed_articles)

        # Seed historical candles for every asset × timeframe if not already present
        for handler in handler_factory.all():
            for timeframe in ("1H", "24H", "7D", "30D"):
                await seed_historical_candles(handler.asset_id, timeframe)

    except Exception as exc:
        logger.error("db_seed_failed: %s", str(exc))
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Historical candle helpers
# ──────────────────────────────────────────────────────────────────────────────


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
        ts:        UTC datetime of the candle.
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

    Delegates OHLCV fetching to the registered BaseAssetHandler.
    Falls back to random candle generation if the handler returns no data.

    Skips insertion if at least one candle already exists (idempotent).

    Args:
        asset_id:  Ticker symbol (e.g. 'BTC').
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
            "seed_historical_candles_skip: asset_id=%s not found in DB", asset_id
        )
        return

    # Attempt real OHLCV via the handler
    candles: List[Dict[str, Any]] = []
    try:
        handler = handler_factory.get(asset_id)
        days_map: Dict[str, int] = {"1H": 1, "24H": 1, "7D": 7, "30D": 30}
        days = days_map.get(timeframe, 1)
        ohlcv_rows = await handler.fetch_ohlcv(days)

        if ohlcv_rows:
            points_count = _timeframe_to_points_count(timeframe)
            sentiment_score: int = int(asset.get("sentimentScore", 50))
            volume24h: int = int(asset.get("volume24h", 1_000_000))

            for row in ohlcv_rows[-points_count:]:
                ts_unix = row.timestamp_ms // 1000
                ts_dt = datetime.datetime.fromtimestamp(
                    ts_unix, tz=datetime.timezone.utc
                )
                ts_str = _format_candle_timestamp(ts_dt, timeframe)
                candle_sentiment = min(
                    100,
                    max(0, int(sentiment_score + (random.random() - 0.5) * 20)),
                )
                vol = int(
                    row.volume
                    if row.volume > 0
                    else volume24h / max(len(ohlcv_rows), 1) * (0.5 + random.random())
                )
                candles.append(
                    {
                        "asset_id": asset_id,
                        "timeframe": timeframe,
                        "timestamp": ts_str,
                        "timestamp_unix": ts_unix,
                        "open": round(row.open, 2),
                        "high": round(row.high, 2),
                        "low": round(row.low, 2),
                        "close": round(row.close, 2),
                        "volume": vol,
                        "sentimentScore": candle_sentiment,
                    }
                )
    except (KeyError, Exception) as exc:
        logger.warning(
            "seed_historical_candles_handler_failed: asset_id=%s timeframe=%s error=%s "
            "— using random fallback",
            asset_id,
            timeframe,
            str(exc),
        )

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
                "seed_historical_candles_insert_failed: asset_id=%s timeframe=%s error=%s",
                asset_id,
                timeframe,
                str(exc),
            )


def _generate_random_candles(
    asset_id: str,
    timeframe: str,
    asset: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Fallback random candle generator used when real OHLCV APIs are unavailable.

    Derives per-candle volatility from the registered handler's volatility attribute,
    falling back to a conservative 0.005 if the handler is not found.

    Args:
        asset_id:  Ticker symbol.
        timeframe: Candle timeframe.
        asset:     MongoDB asset document with current price/volume/sentiment.

    Returns:
        List of candle dicts.
    """
    try:
        handler = handler_factory.get(asset_id)
        base_vol = handler.volatility
    except KeyError:
        base_vol = 0.005

    timeframe_multipliers: Dict[str, float] = {
        "1H": 0.1,
        "24H": 1.0,
        "7D": 2.5,
        "30D": 6.0,
    }
    vol_factor = base_vol * timeframe_multipliers.get(timeframe, 1.0)

    points_count = _timeframe_to_points_count(timeframe)
    step_minutes = _timeframe_to_step_minutes(timeframe)
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
        asset_id:  Ticker symbol (e.g. 'BTC').
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
      - PRICE_ABOVE:     triggers when current_price >= target_value
      - PRICE_BELOW:     triggers when current_price <= target_value
      - SENTIMENT_CHANGE: triggers when current_sentiment crosses target_value

    Args:
        asset_id:          Ticker symbol of the asset being checked.
        current_price:     Latest price for the asset.
        current_sentiment: Latest aggregated sentiment score (0–100).
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


# ──────────────────────────────────────────────────────────────────────────────
# Background price update loop — factory-driven, no per-asset conditionals
# ──────────────────────────────────────────────────────────────────────────────


async def background_update_loop() -> None:
    """
    Syncs real market prices for all registered assets every 60 seconds.

    Iterates AssetHandlerFactory.all() and calls handler.fetch_price() for each.
    On handler failure, logs a warning and skips to the next asset (non-fatal).

    On each tick per asset:
      1. Checks if the UTC date has rolled over; resets `openPriceToday` if so.
      2. Computes `change24h` as ((price - openPriceToday) / openPriceToday) * 100.
      3. Appends a new 1H candle and checks alerts.
      4. Broadcasts the updated AssetMetrics via WebSocket.
    """
    from backend.app.services.price_feed import fetch_onchain_metrics

    while True:
        try:
            await asyncio.sleep(60.0)

            now = datetime.datetime.now(datetime.timezone.utc)

            for handler in handler_factory.all():
                asset_id = handler.asset_id
                tick_price: float | None = None

                try:
                    tick = await handler.fetch_price()
                    tick_price = tick.price
                    high24h = tick.high24h
                    low24h = tick.low24h
                    volume24h = int(tick.volume24h)
                except Exception as exc:
                    logger.warning(
                        "price_fetch_failed: asset_id=%s error=%s — activating GBM simulator",
                        asset_id,
                        str(exc),
                    )
                    # GBM simulator fallback — keeps UI live with mathematically
                    # realistic prices while the primary source recovers.
                    from backend.app.services.simulator import simulate_price_tick

                    asset_doc = await assets_collection.find_one({"id": asset_id})
                    last_known_price: float = float(
                        asset_doc["price"] if asset_doc else handler.base_price
                    )
                    tick_price = simulate_price_tick(
                        current_price=last_known_price,
                        volatility=handler.volatility,
                    )
                    high24h = round(tick_price * 1.005, 8)
                    low24h = round(tick_price * 0.995, 8)
                    volume24h = int(
                        asset_doc.get("volume24h", handler.seed_volume)
                        if asset_doc
                        else handler.seed_volume
                    )
                    logger.info(
                        "price_fetch_simulator_fallback: asset_id=%s simulated_price=%.4f",
                        asset_id,
                        tick_price,
                    )

                if tick_price is None or tick_price <= 0.0:
                    continue

                # Load current DB state for this asset (may have been read already
                # in the simulator fallback branch; re-query to get the authoritative doc)
                asset = await assets_collection.find_one({"id": asset_id})
                if not asset:
                    continue

                open_price_today: float = float(asset.get("openPriceToday", tick_price))
                last_reset_str: str = str(asset.get("lastDayReset", now.isoformat()))
                sentiment_score: int = int(asset.get("sentimentScore", 50))

                # Daily reset check — price resets the 24h window at midnight UTC
                last_reset_date = datetime.datetime.fromisoformat(last_reset_str).date()
                if now.date() != last_reset_date:
                    open_price_today = tick_price
                    last_reset_str = now.isoformat()
                    await assets_collection.update_one(
                        {"id": asset_id},
                        {
                            "$set": {
                                "openPriceToday": open_price_today,
                                "lastDayReset": last_reset_str,
                                "high24h": tick_price,
                                "low24h": tick_price,
                            }
                        },
                    )

                if open_price_today == 0.0:
                    open_price_today = tick_price

                change24h = round(
                    ((tick_price - open_price_today) / open_price_today) * 100, 2
                )

                # Fetch on-chain metrics (ETH gas price, SOL TPS, TON stats)
                onchain_data = await fetch_onchain_metrics(asset_id)

                await assets_collection.update_one(
                    {"id": asset_id},
                    {
                        "$set": {
                            "price": tick_price,
                            "high24h": high24h,
                            "low24h": low24h,
                            "volume24h": volume24h,
                            "change24h": change24h,
                            "onchainMetrics": onchain_data if onchain_data else None,
                        }
                    },
                )

                # Push tick to the in-memory aggregator
                from backend.app.services.aggregator import aggregator

                normalized_vader = (sentiment_score - 50.0) / 50.0
                await aggregator.add_tick(asset_id, tick_price, normalized_vader)

                await append_latest_candle(asset_id)
                await check_alerts_for_asset(asset_id, tick_price, sentiment_score)

                # Broadcast updated metrics over WebSocket
                updated_asset = await assets_collection.find_one({"id": asset_id})
                if updated_asset:
                    from backend.app.schemas.market import AssetMetrics

                    validated = AssetMetrics.model_validate(updated_asset).model_dump()
                    await ws_manager.broadcast_asset_update(asset_id, validated)

                logger.info(
                    "price_sync_done: asset_id=%s price=%.4f change24h=%.2f",
                    asset_id,
                    tick_price,
                    change24h,
                )

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("price_sync_loop_error: %s", str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Hourly aggregation loop
# ──────────────────────────────────────────────────────────────────────────────


async def hourly_aggregation_loop() -> None:
    """
    Background worker that triggers the in-memory aggregator flush once an hour.
    """
    from backend.app.services.aggregator import aggregator

    while True:
        try:
            await asyncio.sleep(3600.0)
            await aggregator.aggregate_and_flush()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("hourly_aggregation_loop_error: %s", str(exc))
