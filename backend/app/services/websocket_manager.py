"""
WebSocket connection manager for real-time asset updates.

Manages active connections grouped by asset_id (ticker symbol),
and broadcasts price and sentiment updates to subscribed clients.
"""

import logging
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("app")


class ConnectionManager:
    """
    Manages WebSocket connections partitioned by asset ID (e.g., 'BTC', 'ETH').
    """

    def __init__(self) -> None:
        # Maps asset_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, asset_id: str, websocket: WebSocket) -> None:
        """
        Accepts a connection and registers it to the specified asset ID.
        """
        await websocket.accept()
        if asset_id not in self.active_connections:
            self.active_connections[asset_id] = set()
        self.active_connections[asset_id].add(websocket)
        logger.info(
            "websocket_connected: asset_id=%s active_for_asset=%d",
            asset_id,
            len(self.active_connections[asset_id]),
        )

    async def disconnect(self, asset_id: str, websocket: WebSocket) -> None:
        """
        Removes a connection from the registered asset ID.
        """
        if asset_id in self.active_connections:
            self.active_connections[asset_id].discard(websocket)
            if not self.active_connections[asset_id]:
                del self.active_connections[asset_id]
            logger.info(
                "websocket_disconnected: asset_id=%s active_for_asset=%d",
                asset_id,
                len(self.active_connections.get(asset_id, set())),
            )

    async def broadcast_asset_update(
        self, asset_id: str, asset_data: Dict[str, Any]
    ) -> None:
        """
        Sends an asset update payload to all active connections for that asset.

        Removes stale or dead connections dynamically if send fails.
        """
        if asset_id not in self.active_connections:
            return

        dead_connections: Set[WebSocket] = set()
        message = {"type": "asset_update", "asset_id": asset_id, "asset": asset_data}

        # Iterate over a copy of the set to avoid modification issues
        for websocket in list(self.active_connections[asset_id]):
            try:
                await websocket.send_json(message)
            except Exception as exc:
                logger.warning(
                    "websocket_send_failed: asset_id=%s error=%s", asset_id, str(exc)
                )
                dead_connections.add(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            await self.disconnect(asset_id, websocket)


# Module-level singleton manager
manager = ConnectionManager()
