"""
CryptoHandler — concrete BaseAssetHandler for CoinGecko / Alchemy-tracked tokens.

Implements:
  - fetch_price()   via Alchemy price API → CoinGecko fallback
  - fetch_ohlcv()   via CoinGecko /ohlc endpoint

No per-asset branching inside this class. All configuration comes from the
constructor arguments supplied by AssetHandlerFactory at startup.
"""

from __future__ import annotations

import logging

from backend.app.handlers.base import BaseAssetHandler, OHLCVRow, PriceTick

logger = logging.getLogger("app")


class CryptoHandler(BaseAssetHandler):
    """
    Handles price and OHLCV data retrieval for any CoinGecko-tracked crypto asset.

    Data flow:
      fetch_price()  → fetch_alchemy_prices() → fetch_coingecko_prices() fallback
      fetch_ohlcv()  → fetch_coingecko_ohlcv()

    Raises on total failure so the caller (market_data orchestrator) can invoke
    the GBM simulator as a last-resort fallback.
    """

    async def fetch_price(self) -> PriceTick:
        """
        Retrieves the latest price and 24-hour market statistics.

        Tries Alchemy first (lower latency, richer data for ETH/SOL/TON/BTC).
        Falls back to CoinGecko public API on failure or missing Alchemy key.

        Returns:
            PriceTick: Frozen snapshot of the current market data.

        Raises:
            RuntimeError: If both Alchemy and CoinGecko return no data for this asset.
        """
        from backend.app.services.price_feed import (
            fetch_alchemy_prices,
            fetch_coingecko_prices,
        )

        # Attempt Alchemy (includes CoinGecko enrichment internally)
        try:
            all_prices = await fetch_alchemy_prices()
        except Exception as exc:
            logger.warning(
                "crypto_handler_alchemy_failed: asset_id=%s error=%s — trying CoinGecko",
                self.asset_id,
                str(exc),
            )
            all_prices = {}

        if self.asset_id not in all_prices:
            # Direct CoinGecko call as secondary fallback
            try:
                all_prices = await fetch_coingecko_prices()
            except Exception as exc:
                logger.warning(
                    "crypto_handler_coingecko_failed: asset_id=%s error=%s",
                    self.asset_id,
                    str(exc),
                )
                raise RuntimeError(
                    f"fetch_price failed: asset_id={self.asset_id!r} "
                    "both Alchemy and CoinGecko returned no data"
                ) from exc

        feed = all_prices.get(self.asset_id)
        if not feed or feed.get("price", 0.0) <= 0.0:
            raise RuntimeError(
                f"fetch_price failed: asset_id={self.asset_id!r} "
                f"price={feed!r} — invalid data received"
            )

        return PriceTick(
            asset_id=self.asset_id,
            price=float(feed["price"]),
            change24h=float(feed.get("change24h", 0.0)),
            high24h=float(feed.get("high24h", feed["price"])),
            low24h=float(feed.get("low24h", feed["price"])),
            volume24h=float(feed.get("volume24h", 0.0)),
        )

    async def fetch_ohlcv(self, days: int) -> list[OHLCVRow]:
        """
        Retrieves historical OHLCV candle data from CoinGecko.

        Args:
            days: Number of calendar days of history to fetch (1, 7, 30, etc.).

        Returns:
            Chronologically ordered list of OHLCVRow objects.
            Returns an empty list if the CoinGecko API is unavailable.
        """
        from backend.app.services.price_feed import fetch_coingecko_ohlcv

        if not self.coingecko_id:
            logger.warning(
                "crypto_handler_ohlcv_skip: asset_id=%s coingecko_id=None",
                self.asset_id,
            )
            return []

        try:
            raw: list[list[float]] = await fetch_coingecko_ohlcv(self.asset_id, days)
        except Exception as exc:
            logger.warning(
                "crypto_handler_ohlcv_failed: asset_id=%s days=%d error=%s",
                self.asset_id,
                days,
                str(exc),
            )
            return []

        rows: list[OHLCVRow] = []
        for entry in raw:
            if len(entry) < 5:
                continue
            rows.append(
                OHLCVRow(
                    timestamp_ms=int(entry[0]),
                    open=float(entry[1]),
                    high=float(entry[2]),
                    low=float(entry[3]),
                    close=float(entry[4]),
                    volume=0.0,  # CoinGecko /ohlc does not return volume
                )
            )

        logger.info(
            "crypto_handler_ohlcv_fetched: asset_id=%s days=%d candles=%d",
            self.asset_id,
            days,
            len(rows),
        )
        return rows
