"""
StockHandler — concrete BaseAssetHandler for yfinance-tracked instruments (e.g. AAPL).

Implements:
  - fetch_price()   via async yfinance wrapper
  - fetch_ohlcv()   via async yfinance download
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]

from backend.app.handlers.base import BaseAssetHandler, OHLCVRow, PriceTick

logger = logging.getLogger("app")

# Map from our internal timeframe labels to yfinance interval strings
_INTERVAL_MAP: dict[int, str] = {
    1: "1h",
    7: "1d",
    30: "1d",
}


def _sync_fetch_price(ticker: str) -> dict[str, float]:
    """
    Synchronous yfinance price fetch, executed in a thread-pool executor.

    Args:
        ticker: yfinance-compatible ticker symbol (e.g. 'AAPL').

    Returns:
        Dict with keys: price, change24h, high24h, low24h, volume24h.

    Raises:
        RuntimeError: If yfinance returns no usable price data.
    """
    t = yf.Ticker(ticker)
    fast = t.fast_info

    current_price: float = float(fast.last_price or fast.previous_close or 0.0)
    if current_price <= 0.0:
        raise RuntimeError(
            f"stock_handler_sync_fetch: ticker={ticker!r} yfinance returned no price"
        )

    prev_close: float = float(fast.previous_close or current_price)
    change24h = (
        round(((current_price - prev_close) / prev_close) * 100, 2)
        if prev_close
        else 0.0
    )

    hist = yf.download(
        ticker,
        period="2d",
        interval="1d",
        progress=False,
        auto_adjust=True,
    )

    high24h = current_price
    low24h = current_price
    volume24h = 0.0

    if hist is not None and not hist.empty:
        if hasattr(hist.columns, "levels"):
            hist.columns = hist.columns.get_level_values(0)
        last_row = hist.iloc[-1]
        high24h = float(last_row.get("High", current_price))
        low24h = float(last_row.get("Low", current_price))
        volume24h = float(last_row.get("Volume", 0))

    return {
        "price": round(current_price, 2),
        "change24h": change24h,
        "high24h": round(high24h, 2),
        "low24h": round(low24h, 2),
        "volume24h": volume24h,
    }


def _sync_fetch_ohlcv(ticker: str, days: int) -> list[dict[str, Any]]:
    """
    Synchronous yfinance OHLCV download, executed in a thread-pool executor.

    Args:
        ticker: yfinance-compatible ticker symbol.
        days:   Number of calendar days of history to fetch.

    Returns:
        List of raw OHLCV row dicts from yfinance. May be empty.
    """
    interval = _INTERVAL_MAP.get(days, "1d")
    period = f"{min(days, 60)}d"

    hist = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )

    if hist is None or hist.empty:
        return []

    if hasattr(hist.columns, "levels"):
        hist.columns = hist.columns.get_level_values(0)

    rows: list[dict[str, Any]] = []
    for dt_idx, row in hist.iterrows():
        rows.append(
            {
                "timestamp_ms": int(dt_idx.to_pydatetime().timestamp() * 1000),
                "open": float(row.get("Open", 0.0)),
                "high": float(row.get("High", 0.0)),
                "low": float(row.get("Low", 0.0)),
                "close": float(row.get("Close", 0.0)),
                "volume": float(row.get("Volume", 0.0)),
            }
        )
    return rows


class StockHandler(BaseAssetHandler):
    """
    Handles price and OHLCV data retrieval for yfinance-tracked instruments.

    Runs synchronous yfinance calls in asyncio's default thread-pool executor
    to avoid blocking the event loop.

    Raises on failure so the orchestrator can fall back to the GBM simulator.
    """

    async def fetch_price(self) -> PriceTick:
        """
        Retrieves the latest price and 24-hour market statistics via yfinance.

        Returns:
            PriceTick: Frozen snapshot of the current market data.

        Raises:
            RuntimeError: If yfinance returns no usable price data.
        """
        if not self.yfinance_ticker:
            raise RuntimeError(
                f"stock_handler_fetch_price: asset_id={self.asset_id!r} "
                "yfinance_ticker is not configured"
            )

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None, _sync_fetch_price, self.yfinance_ticker
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"stock_handler_fetch_price: asset_id={self.asset_id!r} "
                f"ticker={self.yfinance_ticker!r} error={exc!r}"
            ) from exc

        logger.info(
            "stock_handler_price_fetched: asset_id=%s price=%.2f change24h=%.2f",
            self.asset_id,
            data["price"],
            data["change24h"],
        )

        return PriceTick(
            asset_id=self.asset_id,
            price=data["price"],
            change24h=data["change24h"],
            high24h=data["high24h"],
            low24h=data["low24h"],
            volume24h=data["volume24h"],
        )

    async def fetch_ohlcv(self, days: int) -> list[OHLCVRow]:
        """
        Retrieves historical OHLCV candle data via yfinance.

        Args:
            days: Number of calendar days of history to fetch.

        Returns:
            Chronologically ordered list of OHLCVRow objects.
            Returns an empty list if yfinance is unavailable.
        """
        if not self.yfinance_ticker:
            return []

        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(
                None, _sync_fetch_ohlcv, self.yfinance_ticker, days
            )
        except Exception as exc:
            logger.warning(
                "stock_handler_ohlcv_failed: asset_id=%s days=%d error=%s",
                self.asset_id,
                days,
                str(exc),
            )
            return []

        rows = [
            OHLCVRow(
                timestamp_ms=r["timestamp_ms"],
                open=r["open"],
                high=r["high"],
                low=r["low"],
                close=r["close"],
                volume=r["volume"],
            )
            for r in raw
        ]

        logger.info(
            "stock_handler_ohlcv_fetched: asset_id=%s days=%d candles=%d",
            self.asset_id,
            days,
            len(rows),
        )
        return rows
