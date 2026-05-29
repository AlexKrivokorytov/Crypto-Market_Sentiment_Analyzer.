"""
Base types and Abstract Base Class for all asset data handlers.

Every concrete handler must implement:
  - fetch_price()   → PriceTick
  - fetch_ohlcv()   → list[OHLCVRow]

This module intentionally contains zero business logic — only the contract.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PriceTick:
    """
    Immutable snapshot of an asset's market data at a single point in time.

    Attributes:
        asset_id:   Ticker symbol (e.g. 'BTC').
        price:      Current USD price.
        change24h:  24-hour percentage change.
        high24h:    24-hour high in USD.
        low24h:     24-hour low in USD.
        volume24h:  24-hour trading volume in USD.
        fetched_at: UTC timestamp when the tick was captured.
    """

    asset_id: str
    price: float
    change24h: float
    high24h: float
    low24h: float
    volume24h: float
    fetched_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


@dataclass(frozen=True)
class OHLCVRow:
    """
    Immutable OHLCV (Open / High / Low / Close / Volume) candle record.

    Attributes:
        timestamp_ms: Millisecond UNIX epoch timestamp of the candle open.
        open:         Opening price in USD.
        high:         Highest price during the candle.
        low:          Lowest price during the candle.
        close:        Closing price in USD.
        volume:       Trading volume during the candle period.
    """

    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class BaseAssetHandler(ABC):
    """
    Abstract base class (interface) that every asset data handler must satisfy.

    Concrete subclasses cover different data sources:
      - CryptoHandler  → CoinGecko / Alchemy
      - StockHandler   → yfinance

    Attributes:
        asset_id:         Ticker symbol (e.g. 'BTC', 'AAPL').
        name:             Full display name (e.g. 'Bitcoin').
        symbol:           Ticker symbol, mirrors asset_id for backwards compat.
        base_price:       Seed / fallback price used if no data source responds.
        volatility:       Per-tick sigma for Geometric Brownian Motion simulation.
        coingecko_id:     CoinGecko coin identifier. None for non-crypto assets.
        yfinance_ticker:  yfinance symbol. None for non-stock assets.
        seed_volume:      Approximate 24-hour volume used for DB seeding.
        seed_sentiment:   Initial sentiment score (0–100) for DB seeding.
    """

    def __init__(
        self,
        asset_id: str,
        name: str,
        base_price: float,
        volatility: float,
        seed_volume: int = 1_000_000_000,
        seed_sentiment: int = 50,
        coingecko_id: Optional[str] = None,
        yfinance_ticker: Optional[str] = None,
    ) -> None:
        """
        Initialises the handler with static asset configuration.

        Args:
            asset_id:        Ticker symbol (e.g. 'BTC').
            name:            Human-readable asset name.
            base_price:      Fallback / seed price in USD.
            volatility:      GBM sigma for the market simulator.
            seed_volume:     Approximate 24h volume used at DB seed time.
            seed_sentiment:  Initial sentiment index (0–100).
            coingecko_id:    CoinGecko API identifier. None for non-crypto.
            yfinance_ticker: yfinance symbol. None for non-stock assets.
        """
        self.asset_id = asset_id
        self.name = name
        self.symbol = asset_id  # mirrors asset_id for schema backwards-compat
        self.base_price = base_price
        self.volatility = volatility
        self.seed_volume = seed_volume
        self.seed_sentiment = seed_sentiment
        self.coingecko_id = coingecko_id
        self.yfinance_ticker = yfinance_ticker

    # ──────────────────────────────────────────────────────────────────────────
    # Abstract interface
    # ──────────────────────────────────────────────────────────────────────────

    @abstractmethod
    async def fetch_price(self) -> PriceTick:
        """
        Fetches the latest market price and 24-hour statistics for this asset.

        Returns:
            PriceTick: A frozen snapshot of the current market data.

        Raises:
            RuntimeError: If the data source returns no usable price.
            httpx.HTTPStatusError: On non-2xx API responses after retries.
        """

    @abstractmethod
    async def fetch_ohlcv(self, days: int) -> list[OHLCVRow]:
        """
        Fetches historical OHLCV candle data for a given number of calendar days.

        Args:
            days: Number of calendar days of history to retrieve (1, 7, 30, etc.).

        Returns:
            Chronologically ordered list of OHLCVRow objects, oldest first.
            Returns an empty list if the data source is unavailable.
        """

    # ──────────────────────────────────────────────────────────────────────────
    # Seed document helper — used by market_data.seed_database_if_empty
    # ──────────────────────────────────────────────────────────────────────────

    def to_seed_document(self) -> dict[str, object]:
        """
        Returns a MongoDB-ready seed document for this asset.

        Used once at startup when the assets collection is empty.
        All prices default to base_price; change24h starts at 0.

        Returns:
            dict: Complete asset document ready for `insert_many`.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        sentiment_label = "Neutral"
        if self.seed_sentiment >= 60:
            sentiment_label = "Bullish"
        elif self.seed_sentiment <= 40:
            sentiment_label = "Bearish"

        return {
            "id": self.asset_id,
            "name": self.name,
            "symbol": self.symbol,
            "price": self.base_price,
            "change24h": 0.0,
            "high24h": round(self.base_price * 1.01, 2),
            "low24h": round(self.base_price * 0.99, 2),
            "volume24h": self.seed_volume,
            "sentimentScore": self.seed_sentiment,
            "sentimentLabel": sentiment_label,
            "openPriceToday": self.base_price,
            "lastDayReset": now_iso,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} asset_id={self.asset_id!r}>"
