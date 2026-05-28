"""
In-Memory Lock-Protected Aggregator Service.

Buffering incoming 1-minute price and VADER sentiment ticks in RAM,
persisting raw entries dynamically with 48h TTL constraints, and
periodically flushing aggregated hourly TickBucket documents to MongoDB.
"""

import asyncio
import datetime
import logging
from typing import Dict, List, Any

from backend.app.core.database import ticks_collection, ticks_buckets_collection
from backend.app.schemas.market import Tick

logger = logging.getLogger("app")


class InMemoryAggregator:
    """
    Asynchronous thread-safe manager for buffering real-time ticks in RAM
    and aggregating them hourly into MongoDB Tick Buckets.
    """

    def __init__(self) -> None:
        """
        Initializes the Lock and the primary dictionary cache buffer.
        """
        self._lock = asyncio.Lock()
        # Buffer mapping: asset_id -> list of raw ticks dicts in memory
        self._buffer: Dict[str, List[Dict[str, Any]]] = {}

    async def hydrate_from_db(self) -> None:
        """
        Hydrates the in-memory buffer on startup with ticks from the current hour
        to prevent data loss during application restarts/redeployments.
        """
        async with self._lock:
            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                # Compute strictly the starting boundary of the current hour in UTC
                hour_start = now.replace(minute=0, second=0, microsecond=0)
                hour_start_unix = int(hour_start.timestamp())

                logger.info(
                    "aggregator_hydration_started: hour_start=%s",
                    hour_start.isoformat(),
                )

                # Pull all raw ticks for the current hour from MongoDB
                cursor = ticks_collection.find(
                    {"timestamp_unix": {"$gte": hour_start_unix}}
                )

                count = 0
                async for doc in cursor:
                    asset_id = str(doc.get("asset_id", ""))
                    if not asset_id:
                        continue

                    if asset_id not in self._buffer:
                        self._buffer[asset_id] = []

                    self._buffer[asset_id].append(
                        {
                            "timestamp_unix": int(doc.get("timestamp_unix", 0)),
                            "timestamp": doc.get("timestamp"),
                            "price": float(doc.get("price", 0.0)),
                            "sentiment": float(doc.get("sentiment", 0.0)),
                        }
                    )
                    count += 1

                logger.info(
                    "aggregator_hydration_completed: total_ticks_hydrated=%d",
                    count,
                )
            except Exception as exc:
                logger.error(
                    "aggregator_hydration_failed: error=%s "
                    "The aggregator will start with an empty buffer.",
                    str(exc),
                )
                raise

    async def add_tick(self, asset_id: str, price: float, sentiment: float) -> None:
        """
        Appends a high-frequency tick of price & VADER sentiment to the RAM buffer
        and persists the raw tick immediately into MongoDB ticks collection with TTL.

        Args:
            asset_id: The unique asset symbol (e.g. BTC, ETH, SOL).
            price: Current USD market price.
            sentiment: Continuous VADER compound score in [-1.0, 1.0].
        """
        async with self._lock:
            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                timestamp_unix = int(now.timestamp())

                # Raw tick document
                tick_doc = {
                    "asset_id": asset_id,
                    "timestamp": now,
                    "timestamp_unix": timestamp_unix,
                    "price": price,
                    "sentiment": sentiment,
                }

                # 1. Save raw tick to MongoDB (expires in 48 hours via TTL)
                await ticks_collection.insert_one(dict(tick_doc))

                # 2. Append to internal RAM buffer
                if asset_id not in self._buffer:
                    self._buffer[asset_id] = []
                self._buffer[asset_id].append(tick_doc)

                logger.info(
                    "aggregator_tick_added: asset=%s price=%.4f sentiment=%.2f RAM_buffer_size=%d",
                    asset_id,
                    price,
                    sentiment,
                    len(self._buffer[asset_id]),
                )
            except Exception as exc:
                logger.error(
                    "aggregator_add_tick_failed: asset=%s error=%s",
                    asset_id,
                    str(exc),
                )
                raise

    async def aggregate_and_flush(self) -> None:
        """
        Aggregates the accumulated RAM buffer ticks into a single hourly document
        per asset, inserts it to MongoDB ticks_buckets collection, and flushes memory.
        """
        async with self._lock:
            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                # Compute strictly current hour start in UTC as requested
                bucket_start = now.replace(minute=0, second=0, microsecond=0)
                bucket_start_unix = int(bucket_start.timestamp())
                bucket_end = bucket_start + datetime.timedelta(hours=1)

                logger.info(
                    "aggregator_aggregation_started: bucket_start=%s bucket_end=%s",
                    bucket_start.isoformat(),
                    bucket_end.isoformat(),
                )

                for asset_id, ticks in list(self._buffer.items()):
                    if not ticks:
                        continue

                    # Filter ticks to only include those belonging to the bucket hour range
                    bucket_ticks = [
                        t
                        for t in ticks
                        if bucket_start_unix
                        <= t["timestamp_unix"]
                        < int(bucket_end.timestamp())
                    ]
                    if not bucket_ticks:
                        continue

                    # Extract price and sentiment values
                    prices = [t["price"] for t in bucket_ticks]
                    sentiments = [t["sentiment"] for t in bucket_ticks]

                    ohlc_open = prices[0]
                    ohlc_high = max(prices)
                    ohlc_low = min(prices)
                    ohlc_close = prices[-1]

                    # Average VADER compound sentiment (range -1.0 to 1.0)
                    avg_vader = sum(sentiments) / len(sentiments)
                    # Convert to standard index range (0 to 100) for traditional compatibility
                    avg_sentiment_idx = int(round((avg_vader * 50.0) + 50.0))
                    avg_sentiment_idx = min(100, max(0, avg_sentiment_idx))

                    # Parse ticks list to schemas/market.py Tick objects (using offset seconds)
                    ticks_list: List[Tick] = []
                    for t in bucket_ticks:
                        offset = max(0, t["timestamp_unix"] - bucket_start_unix)
                        discrete_sentiment = int(round((t["sentiment"] * 50.0) + 50.0))
                        discrete_sentiment = min(100, max(0, discrete_sentiment))
                        ticks_list.append(
                            Tick(
                                offset_seconds=offset,
                                price=t["price"],
                                sentiment=discrete_sentiment,
                            )
                        )

                    # Prepare hourly TickBucket document
                    bucket_document = {
                        "asset_id": asset_id,
                        "bucket_start": bucket_start,
                        "bucket_end": bucket_end,
                        "open": ohlc_open,
                        "high": ohlc_high,
                        "low": ohlc_low,
                        "close": ohlc_close,
                        "avg_sentiment": avg_vader,  # float [-1.0, 1.0]
                        "avg_sentiment_idx": avg_sentiment_idx,  # int [0, 100]
                        "count": len(bucket_ticks),
                        "ticks": [t.model_dump() for t in ticks_list],
                    }

                    # Write aggregated bucket to ticks_buckets collection
                    await ticks_buckets_collection.update_one(
                        {"asset_id": asset_id, "bucket_start": bucket_start},
                        {"$set": bucket_document},
                        upsert=True,
                    )

                    # Flush matching ticks from memory buffer
                    self._buffer[asset_id] = [
                        t
                        for t in ticks
                        if t["timestamp_unix"] >= int(bucket_end.timestamp())
                    ]

                    logger.info(
                        "aggregator_bucket_flushed: asset=%s count=%d open=%.4f high=%.4f low=%.4f close=%.4f avg_sentiment=%.2f",
                        asset_id,
                        len(bucket_ticks),
                        ohlc_open,
                        ohlc_high,
                        ohlc_low,
                        ohlc_close,
                        avg_vader,
                    )
            except Exception as exc:
                logger.error(
                    "aggregator_aggregation_failed: error=%s",
                    str(exc),
                )
                raise


# Global Aggregator Singleton Instance
aggregator = InMemoryAggregator()
