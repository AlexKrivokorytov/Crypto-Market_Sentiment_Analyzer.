"""
Dynamic Registry Service for managing Assets and Lexicons via MongoDB.
Applies OOP principles for data management and state encapsulation.
"""

from typing import List, Optional, Any, Dict
from motor.motor_asyncio import AsyncIOMotorCollection

from backend.app.core.database import (
    registry_assets_collection,
    registry_lexicon_collection,
)

from backend.app.schemas.registry import AssetConfig, LexiconConfig


class DynamicRegistry:
    """
    Object-Oriented Registry for managing application configuration state.
    """

    def __init__(
        self,
        assets_collection: AsyncIOMotorCollection[Dict[str, Any]],
        lexicon_collection: AsyncIOMotorCollection[Dict[str, Any]],
    ) -> None:
        self._assets_collection = assets_collection
        self._lexicon_collection = lexicon_collection
        self._cached_assets: Optional[List[AssetConfig]] = None
        self._cached_lexicon: Optional[LexiconConfig] = None

    async def initialize_defaults(
        self, default_assets: List[AssetConfig], default_lexicon: LexiconConfig
    ) -> None:
        """
        Seeds the database with default assets and lexicons if they do not exist.
        """
        # Seed Assets
        for asset in default_assets:
            existing = await self._assets_collection.find_one({"id": asset.id})
            if not existing:
                await self._assets_collection.insert_one(
                    asset.model_dump(by_alias=True)
                )

        # Seed Lexicon
        existing_lexicon = await self._lexicon_collection.find_one(
            {"id": default_lexicon.id}
        )
        if not existing_lexicon:
            await self._lexicon_collection.insert_one(
                default_lexicon.model_dump(by_alias=True)
            )

    async def get_active_assets(self, force_refresh: bool = False) -> List[AssetConfig]:
        """
        Retrieves all active assets, utilizing in-memory cache unless forced.
        """
        if self._cached_assets is not None and not force_refresh:
            return self._cached_assets

        cursor = self._assets_collection.find({"is_active": True}).sort("order", 1)
        documents = await cursor.to_list(length=None)

        # We need to map MongoDB _id to string if it exists or ignore it
        self._cached_assets = [AssetConfig.model_validate(doc) for doc in documents]
        return self._cached_assets

    async def get_asset(self, asset_id: str) -> Optional[AssetConfig]:
        """
        Retrieves a single asset by ID.
        """
        doc = await self._assets_collection.find_one(
            {"id": asset_id, "is_active": True}
        )
        if doc:
            return AssetConfig.model_validate(doc)
        return None

    async def add_or_update_asset(self, asset: AssetConfig) -> AssetConfig:
        """
        Creates or updates an asset configuration.
        """
        await self._assets_collection.update_one(
            {"id": asset.id},
            {"$set": asset.model_dump(by_alias=True)},
            upsert=True,
        )
        self._cached_assets = None  # Invalidate cache
        return asset

    async def get_lexicon(self, force_refresh: bool = False) -> LexiconConfig:
        """
        Retrieves the global lexicon configuration.
        """
        if self._cached_lexicon is not None and not force_refresh:
            return self._cached_lexicon

        doc = await self._lexicon_collection.find_one({"id": "global"})
        if doc:
            self._cached_lexicon = LexiconConfig.model_validate(doc)
        else:
            self._cached_lexicon = LexiconConfig()
        return self._cached_lexicon

    async def update_lexicon(self, lexicon: LexiconConfig) -> LexiconConfig:
        """
        Updates the global lexicon configuration.
        """
        lexicon.id = "global"
        await self._lexicon_collection.update_one(
            {"id": "global"},
            {"$set": lexicon.model_dump(by_alias=True)},
            upsert=True,
        )
        self._cached_lexicon = None  # Invalidate cache
        return lexicon


dynamic_registry = DynamicRegistry(
    registry_assets_collection, registry_lexicon_collection
)
