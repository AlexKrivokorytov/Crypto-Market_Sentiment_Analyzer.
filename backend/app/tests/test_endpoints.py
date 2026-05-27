"""
Tests for the Market Sentiment Analyzer FastAPI endpoints.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check() -> None:
    """
    Verifies that the /health health check route returns a 200 OK status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Market Sentiment Analyzer API"}


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
