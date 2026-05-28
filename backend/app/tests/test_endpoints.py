"""
Tests for the Market Sentiment Analyzer FastAPI endpoints with mocked MongoDB motor collections.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import backend.app.core.database as db

_NOW_ISO = "2026-05-28T00:00:00+00:00"

mock_assets: List[Dict[str, Any]] = [
    {
        "id": "BTC",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price": 68420.50,
        "change24h": 2.45,
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
        "change24h": -1.15,
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
        "change24h": 8.68,
        "high24h": 156.40,
        "low24h": 140.20,
        "volume24h": 4120550000,
        "sentimentScore": 86,
        "sentimentLabel": "Bullish",
        "openPriceToday": 154.85,
        "lastDayReset": _NOW_ISO,
    },
    {
        "id": "AAPL",
        "name": "Apple Inc.",
        "symbol": "AAPL",
        "price": 185.35,
        "change24h": -0.42,
        "high24h": 186.95,
        "low24h": 184.10,
        "volume24h": 8930400000,
        "sentimentScore": 54,
        "sentimentLabel": "Neutral",
        "openPriceToday": 185.35,
        "lastDayReset": _NOW_ISO,
    },
]

mock_articles: List[Dict[str, Any]] = [
    {
        "id": "art_1",
        "asset_id": "SOL",
        "timestamp": "2026-05-27T12:00:00Z",
        "source": "CoinDesk",
        "title": "Solana breaks out",
        "url": "#",
        "summary": "Solana surges high.",
        "sentimentScore": 0.85,
        "sentimentLabel": "Bullish",
        "confidence": 0.95,
        "keywords": ["solana", "breakout"],
        "llmReasoning": "Strong technical breakout on high volume.",
    }
]

# 24 mock candles for AAPL 24H timeframe test
mock_candles_aapl_24h: List[Dict[str, Any]] = [
    {
        "asset_id": "AAPL",
        "timeframe": "24H",
        "timestamp": f"May 28 {i:02d}:00",
        "timestamp_unix": 1748390400 + i * 3600,
        "open": 185.0 + i * 0.1,
        "high": 186.0 + i * 0.1,
        "low": 184.0 + i * 0.1,
        "close": 185.5 + i * 0.1,
        "volume": 1000000,
        "sentimentScore": 54,
    }
    for i in range(24)
]


class MockCursor:
    """
    Mock MongoDB cursor class mimicking motor's async find() behavior.
    """

    def __init__(self, data: List[Any]) -> None:
        """
        Args:
            data: The list of documents to return from this cursor.
        """
        self.data = data

    async def to_list(self, length: int) -> List[Any]:
        """
        Mock implementation of motor's to_list method.

        Args:
            length: Maximum number of documents to return.

        Returns:
            Up to `length` documents from the cursor's data.
        """
        return self.data[:length]

    def sort(self, key: Any, direction: int = -1) -> "MockCursor":
        """
        Mock implementation of motor's sort method.

        Args:
            key: Sort key field name, or list of (field, direction) pairs.
            direction: 1 for ascending, -1 for descending.

        Returns:
            Self, with data sorted in place.
        """
        sort_key = (
            key if isinstance(key, str) else key[0][0] if key else "timestamp_unix"
        )
        self.data = sorted(
            self.data,
            key=lambda x: x.get(sort_key, ""),
            reverse=(direction == -1),
        )
        return self


db.assets_collection = MagicMock()
db.assets_collection.find = MagicMock(return_value=MockCursor(mock_assets))
db.assets_collection.find_one = AsyncMock(
    side_effect=lambda query: next(
        (a for a in mock_assets if a["id"] == query.get("id")), None
    )
)

db.articles_collection = MagicMock()
db.articles_collection.find = MagicMock(
    side_effect=lambda query: MockCursor(
        [art for art in mock_articles if art["asset_id"] == query.get("asset_id")]
    )
)
db.articles_collection.find_one = AsyncMock(
    side_effect=lambda query: next(
        (art for art in mock_articles if art["id"] == query.get("id")), None
    )
)

db.historical_collection = MagicMock()
db.historical_collection.find = MagicMock(
    side_effect=lambda query, *args, **kwargs: MockCursor(
        [
            c
            for c in mock_candles_aapl_24h
            if c["asset_id"] == query.get("asset_id")
            and c["timeframe"] == query.get("timeframe")
        ]
    )
)
db.historical_collection.count_documents = AsyncMock(return_value=24)

db.ping_database = AsyncMock(return_value=True)

# Import TestClient and app after monkeypatching to prevent real DB connections on import
from fastapi.testclient import TestClient  # noqa: E402
from backend.app.main import app  # noqa: E402


client = TestClient(app)


def test_health_check() -> None:
    """
    Verifies that the /health health check route returns a 200 OK status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Market Sentiment Analyzer API",
    }


def test_list_assets() -> None:
    """
    Verifies that GET /api/v1/assets returns the list of all mocked assets.
    """
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4
    symbols = {asset["symbol"] for asset in data}
    assert symbols == {"BTC", "ETH", "SOL", "AAPL"}


def test_list_assets_have_open_price_today() -> None:
    """
    Verifies that assets returned by GET /api/v1/assets include openPriceToday and lastDayReset.
    """
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    for asset in data:
        assert "openPriceToday" in asset, f"Missing openPriceToday on {asset['id']}"
        assert "lastDayReset" in asset, f"Missing lastDayReset on {asset['id']}"
        assert asset["openPriceToday"] > 0


def test_get_asset_metrics() -> None:
    """
    Verifies GET /api/v1/assets/{id}/metrics with both valid and invalid IDs.
    """
    # Valid ID
    response = client.get("/api/v1/assets/BTC/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTC"
    assert "price" in data
    assert "sentimentScore" in data
    assert "openPriceToday" in data

    # Invalid ID
    response = client.get("/api/v1/assets/INVALID/metrics")
    assert response.status_code == 404
    assert response.json()["message"] == "Asset with ID 'INVALID' not found."


def test_get_asset_sentiment() -> None:
    """
    Verifies GET /api/v1/assets/{id}/sentiment route behavior.
    """
    # Valid ID
    response = client.get("/api/v1/assets/SOL/sentiment")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "title" in data[0]
    assert "sentimentScore" in data[0]

    # Invalid ID
    response = client.get("/api/v1/assets/INVALID/sentiment")
    assert response.status_code == 404


def test_get_asset_historical() -> None:
    """
    Verifies GET /api/v1/assets/{id}/historical with timeframe params.
    Historical data is now read from MongoDB (mocked with 24 candles for AAPL 24H).
    """
    # Valid ID and timeframe
    response = client.get("/api/v1/assets/AAPL/historical?timeframe=24H")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 24
    assert "timestamp" in data[0]
    assert "open" in data[0]
    assert "close" in data[0]

    # Invalid timeframe
    response = client.get("/api/v1/assets/AAPL/historical?timeframe=100D")
    assert response.status_code == 400
