"""
Unit tests for the Lock-protected InMemoryAggregator in services/aggregator.py.
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import datetime
from typing import Any

from backend.app.services.aggregator import InMemoryAggregator


@pytest.mark.anyio
@patch("backend.app.services.aggregator.ticks_collection")
@patch("backend.app.services.aggregator.ticks_buckets_collection")
async def test_aggregator_add_tick_and_flush(
    mock_buckets_coll: AsyncMock,
    mock_ticks_coll: AsyncMock,
) -> None:
    """
    Verifies that add_tick appends to RAM buffer and inserts to database ticks,
    and aggregate_and_flush correctly calculates OHLCV and average VADER sentiment indices.
    """
    # 1. Initialize aggregator instance
    agg = InMemoryAggregator()

    mock_ticks_coll.insert_one = AsyncMock(return_value=None)
    mock_buckets_coll.update_one = AsyncMock(return_value=None)

    # 2. Add ticks
    await agg.add_tick("BTC", 50000.0, 0.8)  # Bullish VADER (+0.80)
    await agg.add_tick("BTC", 51000.0, 0.4)  # Mid Bullish VADER (+0.40)

    # Assert raw ticks were persisted to MongoDB
    assert mock_ticks_coll.insert_one.call_count == 2

    # Check RAM buffer contents
    assert "BTC" in agg._buffer
    assert len(agg._buffer["BTC"]) == 2
    assert agg._buffer["BTC"][0]["price"] == 50000.0
    assert agg._buffer["BTC"][1]["price"] == 51000.0
    assert agg._buffer["BTC"][0]["sentiment"] == 0.8
    assert agg._buffer["BTC"][1]["sentiment"] == 0.4

    # 3. Trigger aggregation and flush
    await agg.aggregate_and_flush()

    # Verify aggregated data was upserted into ticks_buckets collection
    mock_buckets_coll.update_one.assert_called_once()

    call_args = mock_buckets_coll.update_one.call_args[0]
    query = call_args[0]
    update_doc = call_args[1]["$set"]

    assert query["asset_id"] == "BTC"
    assert update_doc["open"] == 50000.0
    assert update_doc["high"] == 51000.0
    assert update_doc["low"] == 50000.0
    assert update_doc["close"] == 51000.0
    # Average sentiment = (0.8 + 0.4) / 2 = 0.6
    assert abs(update_doc["avg_sentiment"] - 0.6) < 1e-5
    # Index = round(0.6 * 50 + 50) = 80
    assert update_doc["avg_sentiment_idx"] == 80
    assert update_doc["count"] == 2

    # RAM buffer should be flushed for this period
    assert len(agg._buffer["BTC"]) == 0


@pytest.mark.anyio
@patch("backend.app.services.aggregator.ticks_collection")
async def test_aggregator_hydration(mock_ticks_coll: AsyncMock) -> None:
    """
    Verifies that startup hydration queries the raw ticks collection for current-hour
    ticks and successfully populates the internal memory state.
    """
    agg = InMemoryAggregator()

    # Setup mock cursor to simulate database documents
    mock_cursor = MagicMock()
    mock_docs = [
        {
            "asset_id": "SOL",
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "timestamp_unix": int(
                datetime.datetime.now(datetime.timezone.utc).timestamp()
            ),
            "price": 150.0,
            "sentiment": 0.5,
        }
    ]

    async def mock_async_for(*args: Any, **kwargs: Any) -> Any:
        for doc in mock_docs:
            yield doc

    mock_cursor.__aiter__ = mock_async_for
    mock_ticks_coll.find.return_value = mock_cursor

    # Trigger hydration
    await agg.hydrate_from_db()

    # RAM buffer should recover the data
    assert "SOL" in agg._buffer
    assert len(agg._buffer["SOL"]) == 1
    assert agg._buffer["SOL"][0]["price"] == 150.0
    assert agg._buffer["SOL"][0]["sentiment"] == 0.5
