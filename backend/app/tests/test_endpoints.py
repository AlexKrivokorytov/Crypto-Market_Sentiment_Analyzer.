"""
Tests for the Market Sentiment Analyzer FastAPI endpoints with mocked MongoDB motor collections.
"""

from typing import Any, List
from unittest.mock import AsyncMock, MagicMock
import backend.app.core.database as db

mock_assets = [
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
    },
]

mock_articles = [
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


class MockCursor:
    """
    Mock MongoDB cursor class mimicking motor's async find() behavior.
    """

    def __init__(self, data: List[Any]):
        self.data = data

    async def to_list(self, length: int) -> List[Any]:
        """
        Mock implementation of motor's to_list method.
        """
        return self.data[:length]

    def sort(self, key: str, direction: int = -1) -> "MockCursor":
        """
        Mock implementation of motor's sort method.
        """
        self.data = sorted(
            self.data, key=lambda x: x.get(key, ""), reverse=(direction == -1)
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
    Verifies that the GET /api/v1/assets endpoint returns the list of all mocked assets.
    """
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4
    symbols = {asset["symbol"] for asset in data}
    assert symbols == {"BTC", "ETH", "SOL", "AAPL"}


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
