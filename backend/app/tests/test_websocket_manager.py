"""
Unit tests for the high-performance WebSocket ConnectionManager.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import WebSocket
from backend.app.services.websocket_manager import ConnectionManager


@pytest.mark.anyio
async def test_connection_registration() -> None:
    """
    Verifies that ConnectionManager registers connections to asset channels
    and returns a dedicated asyncio.Queue instance.
    """
    manager = ConnectionManager()
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()

    queue = await manager.connect("BTC", mock_websocket)

    assert isinstance(queue, asyncio.Queue)
    assert "BTC" in manager.active_connections
    assert mock_websocket in manager.active_connections["BTC"]
    assert manager.active_connections["BTC"][mock_websocket] is queue


@pytest.mark.anyio
async def test_broadcast_delivers_to_queues() -> None:
    """
    Verifies that calling broadcast_asset_update enqueues messages for active clients.
    """
    manager = ConnectionManager()
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()

    queue = await manager.connect("BTC", mock_websocket)
    update_payload = {"price": 68000.0, "sentimentScore": 75}

    await manager.broadcast_asset_update("BTC", update_payload)

    assert queue.qsize() == 1
    msg = queue.get_nowait()
    assert msg["type"] == "asset_update"
    assert msg["asset_id"] == "BTC"
    assert msg["asset"] == update_payload


@pytest.mark.anyio
async def test_slow_client_dropped_ticks() -> None:
    """
    Verifies that slow clients with overflowing queues do not block the event loop,
    and have their oldest queued messages discarded to make room for new ticks.
    """
    manager = ConnectionManager()
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()

    queue = await manager.connect("BTC", mock_websocket)

    # Fill queue to maximum capacity (100 elements)
    for i in range(100):
        await manager.broadcast_asset_update("BTC", {"index": i})

    assert queue.qsize() == 100

    # Broadcast 1 more update. This will overflow the queue, triggering the drop mechanism.
    await manager.broadcast_asset_update("BTC", {"index": 101})

    # The size must remain capped at 100
    assert queue.qsize() == 100

    # The oldest message (index 0) must have been dropped.
    # The new front message should now be index 1.
    front_msg = queue.get_nowait()
    assert front_msg["asset"]["index"] == 1


@pytest.mark.anyio
async def test_disconnection_cleans_memory() -> None:
    """
    Verifies that disconnect removes connections and deletes empty rooms.
    """
    manager = ConnectionManager()
    mock_websocket_1 = MagicMock(spec=WebSocket)
    mock_websocket_1.accept = AsyncMock()
    mock_websocket_2 = MagicMock(spec=WebSocket)
    mock_websocket_2.accept = AsyncMock()

    await manager.connect("BTC", mock_websocket_1)
    await manager.connect("BTC", mock_websocket_2)

    assert len(manager.active_connections["BTC"]) == 2

    # Disconnect one client
    await manager.disconnect("BTC", mock_websocket_1)
    assert len(manager.active_connections["BTC"]) == 1
    assert mock_websocket_2 in manager.active_connections["BTC"]
    assert mock_websocket_1 not in manager.active_connections["BTC"]

    # Disconnect the final client
    await manager.disconnect("BTC", mock_websocket_2)
    assert "BTC" not in manager.active_connections
