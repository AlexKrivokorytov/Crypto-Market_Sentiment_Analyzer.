"""
Database connection module for MongoDB using motor.
"""

from typing import Any, Dict
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from backend.app.core.config import settings

client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(settings.MONGODB_URL)
db: AsyncIOMotorDatabase[Dict[str, Any]] = client[settings.MONGODB_DB_NAME]

# Collections
assets_collection: AsyncIOMotorCollection[Dict[str, Any]] = db["assets"]
articles_collection: AsyncIOMotorCollection[Dict[str, Any]] = db["articles"]
historical_collection: AsyncIOMotorCollection[Dict[str, Any]] = db["historical"]


async def ping_database() -> bool:
    """
    Pings the database to verify the connection is active.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        # The ping command is cheap and does not require auth
        await db.command("ping")
        return True
    except Exception:
        return False
