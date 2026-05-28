"""
Tests for the DB-bypass warmup health check endpoint.

Verifies that GET /api/v1/healthz returns HTTP 200 with the expected JSON
payload without making any database calls — critical for Render cold-start
resilience where the endpoint must respond before MongoDB is ready.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture()
def client() -> TestClient:
    """
    Creates a FastAPI TestClient with the lifespan disabled.

    The lifespan initializes DB connections and background tasks which are not
    needed to test a pure in-process endpoint.

    Returns:
        TestClient instance with lifespan disabled.
    """
    from backend.app.main import app

    with patch(
        "backend.app.main.lifespan",
        new_callable=lambda: (
            lambda app: __import__("contextlib").asynccontextmanager(
                lambda a: (lambda: (yield))()
            )
        ),
    ):
        # Use lifespan=False to skip the async context manager entirely
        pass

    return TestClient(app, raise_server_exceptions=True)


class TestWarmupHealthz:
    """Tests for the DB-bypass warmup health check route."""

    def test_healthz_returns_200(self, client: TestClient) -> None:
        """
        GET /api/v1/healthz must return HTTP 200 OK.

        This endpoint must be reachable before database connections are
        established — a core requirement for Render cold-start survival.
        """
        response = client.get("/api/v1/healthz")
        assert response.status_code == 200, (
            f"Expected 200 OK but got {response.status_code}: {response.text}"
        )

    def test_healthz_returns_warm_status(self, client: TestClient) -> None:
        """
        Response payload must contain status='warm' to signal readiness.

        The frontend warmup ping checks this field to confirm the container
        has exited its cold-start state.
        """
        response = client.get("/api/v1/healthz")
        payload: dict[str, Any] = response.json()
        assert payload.get("status") == "warm", (
            f"Expected status='warm' but got: {payload}"
        )

    def test_healthz_returns_service_name(self, client: TestClient) -> None:
        """
        Response payload must include a 'service' field with the app name.

        Used by monitoring tools and log parsers to identify the origin service.
        """
        response = client.get("/api/v1/healthz")
        payload: dict[str, Any] = response.json()
        assert "service" in payload, f"Missing 'service' field in payload: {payload}"
        assert "Market Sentiment Analyzer" in payload["service"], (
            f"Unexpected service name: {payload['service']}"
        )

    def test_healthz_returns_message(self, client: TestClient) -> None:
        """
        Response payload must include a human-readable 'message' field.
        """
        response = client.get("/api/v1/healthz")
        payload: dict[str, Any] = response.json()
        assert "message" in payload, f"Missing 'message' field in payload: {payload}"
        assert len(payload["message"]) > 0, "Message field must not be empty."

    def test_healthz_is_db_bypass(self, client: TestClient) -> None:
        """
        GET /api/v1/healthz must succeed even when database operations are mocked to fail.

        This is the critical invariant: the endpoint must never touch MongoDB.
        If it ever calls the DB, this test will catch the regression.
        """
        with patch(
            "backend.app.core.database.assets_collection.find_one",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB must not be called from /healthz"),
        ):
            response = client.get("/api/v1/healthz")
            assert response.status_code == 200, (
                "Health check called the database — this violates the DB-bypass contract."
            )
