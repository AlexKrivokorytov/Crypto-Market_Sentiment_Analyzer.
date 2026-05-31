"""
AssetHandlerFactory — registry and dispatch for all asset data handlers.

The factory is populated once at startup by `bootstrap()`, which reads
HANDLER_CONFIG and instantiates the correct concrete handler for each entry.

Usage:
    from backend.app.handlers.factory import handler_factory

    # Get a specific handler
    btc = handler_factory.get("BTC")
    tick = await btc.fetch_price()

    # Iterate all registered handlers
    for handler in handler_factory.all():
        tick = await handler.fetch_price()
"""

from __future__ import annotations

import logging
from typing import Iterator

from backend.app.handlers.base import BaseAssetHandler
from backend.app.services.registry import DynamicRegistry
from backend.app.handlers.config import HANDLER_CONFIG as HANDLER_CONFIG
from backend.app.handlers.crypto_handler import CryptoHandler
from backend.app.handlers.stock_handler import StockHandler

logger = logging.getLogger("app")


class AssetHandlerFactory:
    """
    Registry that maps asset IDs to their concrete handler instances.

    Follows the Open/Closed Principle: new asset types are added by extending
    HANDLER_CONFIG and, if a new data source is required, adding a new
    BaseAssetHandler subclass — without modifying this class.

    Attributes:
        _registry: Ordered dict of asset_id → handler instance.
    """

    def __init__(self) -> None:
        """Initialises an empty registry."""
        self._registry: dict[str, BaseAssetHandler] = {}

    async def bootstrap(self, registry: "DynamicRegistry") -> None:
        """
        Reads configured assets from the registry and instantiates all configured handlers.

        Called once during application startup (lifespan event).
        Idempotent — calling it multiple times is safe (re-registers same handlers).

        Raises:
            ValueError: If an unsupported handler type is encountered in the config.
        """
        self._registry.clear()

        assets = await registry.get_active_assets()

        for cfg in assets:
            asset_type: str = str(cfg.type)
            asset_id: str = str(cfg.id)
            name: str = str(cfg.name)
            base_price: float = float(cfg.base_price)
            volatility: float = float(cfg.volatility)
            seed_volume: int = int(cfg.seed_volume)
            seed_sentiment: int = int(cfg.seed_sentiment)

            if asset_type == "crypto":
                handler: BaseAssetHandler = CryptoHandler(
                    asset_id=asset_id,
                    name=name,
                    base_price=base_price,
                    volatility=volatility,
                    seed_volume=seed_volume,
                    seed_sentiment=seed_sentiment,
                    coingecko_id=cfg.coingecko_id,
                )
            elif asset_type == "stock":
                handler = StockHandler(
                    asset_id=asset_id,
                    name=name,
                    base_price=base_price,
                    volatility=volatility,
                    seed_volume=seed_volume,
                    seed_sentiment=seed_sentiment,
                    yfinance_ticker=cfg.yfinance_ticker,
                )
            else:
                raise ValueError(
                    f"factory_bootstrap_error: unknown handler type={asset_type!r} "
                    f"for asset_id={asset_id!r}. "
                    "Add a new BaseAssetHandler subclass and register it here."
                )

            self._registry[asset_id] = handler
            logger.info(
                "factory_handler_registered: asset_id=%s type=%s handler=%s",
                asset_id,
                asset_type,
                handler.__class__.__name__,
            )

        logger.info(
            "factory_bootstrap_complete: total_assets=%d assets=%s",
            len(self._registry),
            list(self._registry.keys()),
        )

    def get(self, asset_id: str) -> BaseAssetHandler:
        """
        Returns the handler registered for the given asset ID.

        Args:
            asset_id: Ticker symbol (e.g. 'BTC').

        Returns:
            The concrete BaseAssetHandler instance.

        Raises:
            KeyError: If no handler is registered for the given asset_id.
        """
        handler = self._registry.get(asset_id)
        if handler is None:
            raise KeyError(
                f"factory_get_error: no handler registered for asset_id={asset_id!r}. "
                "Add it to HANDLER_CONFIG in handlers/config.py."
            )
        return handler

    def all(self) -> list[BaseAssetHandler]:
        """
        Returns all registered handler instances in insertion order.

        Returns:
            List of BaseAssetHandler instances.
        """
        return list(self._registry.values())

    def asset_ids(self) -> list[str]:
        """
        Returns all registered asset IDs in insertion order.

        Returns:
            List of ticker symbol strings.
        """
        return list(self._registry.keys())

    def __iter__(self) -> Iterator[BaseAssetHandler]:
        """Allows `for handler in handler_factory:` iteration."""
        return iter(self._registry.values())

    def __len__(self) -> int:
        """Returns the number of registered handlers."""
        return len(self._registry)

    def __repr__(self) -> str:
        return f"<AssetHandlerFactory assets={self.asset_ids()!r}>"


# Module-level singleton — import this instance everywhere
handler_factory = AssetHandlerFactory()
