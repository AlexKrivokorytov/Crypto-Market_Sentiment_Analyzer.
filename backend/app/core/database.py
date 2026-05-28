"""
Database connection module for MongoDB using motor.
"""

import datetime
from typing import Any, Dict

import pymongo
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
users_collection: AsyncIOMotorCollection[Dict[str, Any]] = db["users"]


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


async def ensure_indexes() -> None:
    """
    Creates all required MongoDB indexes on first run.

    Idempotent — safe to call on every startup.
    Indexes created:
      - assets.id (unique)
      - articles.id (unique)
      - articles.(asset_id, timestamp) compound
      - articles.timestamp_dt (TTL, 7 days)
      - historical.(asset_id, timeframe, timestamp_unix) compound unique
      - users.email (unique)
    """
    await assets_collection.create_index(
        [("id", pymongo.ASCENDING)],
        unique=True,
        background=True,
    )
    await articles_collection.create_index(
        [("id", pymongo.ASCENDING)],
        unique=True,
        background=True,
    )
    await articles_collection.create_index(
        [("asset_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
        background=True,
    )
    # TTL index requires a BSON Date field `timestamp_dt`
    await articles_collection.create_index(
        [("timestamp_dt", pymongo.ASCENDING)],
        expireAfterSeconds=604800,  # 7 days
        background=True,
    )
    await historical_collection.create_index(
        [
            ("asset_id", pymongo.ASCENDING),
            ("timeframe", pymongo.ASCENDING),
            ("timestamp_unix", pymongo.ASCENDING),
        ],
        unique=True,
        background=True,
    )
    await users_collection.create_index(
        [("email", pymongo.ASCENDING)],
        unique=True,
        background=True,
    )
