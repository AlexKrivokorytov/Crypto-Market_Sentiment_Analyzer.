"""
WebSocket connection manager for real-time asset updates.

Manages active connections grouped by asset_id (rooms) with private queues
to isolate network performance between subscribers and prevent blocking the loop.
"""

import asyncio
import logging
from typing import Any, Dict
from fastapi import WebSocket

logger = logging.getLogger("app")


class ConnectionManager:
    """
    Manages WebSocket client connections partitioned by asset ID (rooms).

    Leverages non-blocking asyncio.Queue buffers per client to shield the main
    event loop from slow network sinks.
    """

    def __init__(self) -> None:
        """
        Initializes the manager mapping asset channels to active connections and their queues.
        """
        # Map: asset_id -> { WebSocket: asyncio.Queue[Dict[str, Any]] }
        self.active_connections: Dict[
            str, Dict[WebSocket, asyncio.Queue[Dict[str, Any]]]
        ] = {}

    async def connect(
        self, asset_id: str, websocket: WebSocket
    ) -> asyncio.Queue[Dict[str, Any]]:
        """
        Accepts the connection, initializes a private queue, and registers it to the asset channel.

        Args:
            asset_id: The asset channel identifier.
            websocket: The FastAPI WebSocket object.

        Returns:
            The dedicated asyncio Queue for this socket instance.
        """
        await websocket.accept()
        if asset_id not in self.active_connections:
            self.active_connections[asset_id] = {}

        # Buffer of 100 updates before discarding old ticks (prevents memory leak)
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=100)
        self.active_connections[asset_id][websocket] = queue

        logger.info(
            "websocket_connected: asset_id=%s active_for_asset=%d",
            asset_id,
            len(self.active_connections[asset_id]),
        )
        return queue

    async def disconnect(self, asset_id: str, websocket: WebSocket) -> None:
        """
        Removes the websocket and its queue registration, clearing out room memory.

        Args:
            asset_id: The asset channel identifier.
            websocket: The FastAPI WebSocket object.
        """
        if asset_id in self.active_connections:
            self.active_connections[asset_id].pop(websocket, None)
            if not self.active_connections[asset_id]:
                del self.active_connections[asset_id]

            logger.info(
                "websocket_disconnected: asset_id=%s active_for_asset=%d",
                asset_id,
                len(self.active_connections.get(asset_id, {})),
            )

    async def broadcast_asset_update(
        self, asset_id: str, asset_data: Dict[str, Any]
    ) -> None:
        """
        Pushes updates to all registered queues for the given asset.
        Runs in absolute non-blocking time, avoiding waits for slow client transmissions.

        Args:
            asset_id: The asset identifier channel.
            asset_data: The update payload dictionary.
        """
        if asset_id not in self.active_connections:
            return

        message = {
            "type": "asset_update",
            "asset_id": asset_id,
            "asset": asset_data,
        }

        # Safely enqueue to all active subscriber queues
        for websocket, queue in list(self.active_connections[asset_id].items()):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Discard the oldest message to make room for fresh data (Slow Client Shield)
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(message)
                except Exception as exc:
                    logger.debug("websocket_queue_fallback_failed: %s", str(exc))
                logger.warning(
                    "websocket_queue_overflow: asset_id=%s websocket=%s - dropped oldest tick",
                    asset_id,
                    id(websocket),
                )


manager = ConnectionManager()
