"""
Geometric Brownian Motion (GBM) market price simulator.

Used exclusively as a last-resort fallback when all primary data handlers fail
to return a usable price. The simulator keeps the UI alive and data flowing
while preserving mathematical realism.

GBM Formula
-----------
  S(t+Δt) = S(t) · exp((μ - σ²/2)·Δt + σ·√Δt·Z)

Where:
  S(t)   = current price
  μ      = drift (annualised, ≈ 0.08 for equities)
  σ      = per-asset volatility (from BaseAssetHandler.volatility)
  Δt     = time step in years (e.g. 1 minute = 1/525_600)
  Z      = random standard normal draw ~ N(0,1)

Why GBM?
  - Log-normal output guarantees price is always > 0.
  - Matches the classic Black–Scholes assumption for short-horizon simulation.
  - Simple enough to be CPU-bound in microseconds, safe to run on the event loop.

Non-blocking design
-------------------
All calculations are pure math on scalars. CPython executes them in a single
time-slice without syscalls, so `await asyncio.to_thread(...)` is NOT needed
for one-step ticks. For bulk candle generation (hundreds of steps) we use
`asyncio.to_thread` to push the work off the event loop entirely.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import math
import random
from typing import Final

from backend.app.handlers.base import OHLCVRow

logger = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# Physical constants
# ──────────────────────────────────────────────────────────────────────────────

# Trading minutes per year (365.25 days × 24 h × 60 min) — used for Δt scaling
_MINUTES_PER_YEAR: Final[float] = 525_960.0

# Default annualised drift (μ) — mild positive drift simulates long-run equity
# growth bias. Intentionally small so it does not dominate short simulations.
_DEFAULT_DRIFT: Final[float] = 0.05

# Minimum price floor — prevents log(0) on extreme down-moves.
_MIN_PRICE: Final[float] = 1e-8


# ──────────────────────────────────────────────────────────────────────────────
# Core GBM step — pure, stateless, intentionally tiny
# ──────────────────────────────────────────────────────────────────────────────


def _gbm_step(
    current_price: float,
    volatility: float,
    drift: float,
    delta_t_years: float,
) -> float:
    """
    Advances a GBM price by one time step using the exact log-normal solution.

    Pure function — no side effects, no I/O. Safe to call from any context.

    Args:
        current_price:  Current asset price in USD.
        volatility:     Per-step σ (standard deviation of log-returns).
        drift:          Annualised drift μ. Defaults to _DEFAULT_DRIFT in callers.
        delta_t_years:  Time step expressed in fractional years.

    Returns:
        New price, always > _MIN_PRICE.
    """
    z: float = random.gauss(0.0, 1.0)
    exponent = (drift - 0.5 * volatility**2) * delta_t_years + volatility * math.sqrt(
        delta_t_years
    ) * z
    return max(_MIN_PRICE, current_price * math.exp(exponent))


# ──────────────────────────────────────────────────────────────────────────────
# Single-tick public API — used by background_update_loop on handler failure
# ──────────────────────────────────────────────────────────────────────────────


def simulate_price_tick(
    current_price: float,
    volatility: float,
    interval_minutes: float = 1.0,
    drift: float = _DEFAULT_DRIFT,
) -> float:
    """
    Returns the next simulated price for a single 60-second update cycle.

    Called synchronously from the async update loop. The operation is
    CPU-bound but completes in nanoseconds — no off-thread dispatch needed.

    Args:
        current_price:     Last known price in USD.
        volatility:        Per-asset σ from BaseAssetHandler.volatility.
        interval_minutes:  Update interval in minutes. Default: 1 (one tick/min).
        drift:             Annualised drift. Default: 0.05 (5% p.a.).

    Returns:
        New simulated price in USD, guaranteed > 0.

    Raises:
        ValueError: If current_price <= 0 or volatility < 0.
    """
    if current_price <= 0.0:
        raise ValueError(
            f"simulate_price_tick: current_price must be > 0, got {current_price!r}"
        )
    if volatility < 0.0:
        raise ValueError(
            f"simulate_price_tick: volatility must be >= 0, got {volatility!r}"
        )

    delta_t = interval_minutes / _MINUTES_PER_YEAR
    new_price = _gbm_step(current_price, volatility, drift, delta_t)

    logger.debug(
        "simulator_tick: price_before=%.4f price_after=%.4f volatility=%.4f",
        current_price,
        new_price,
        volatility,
    )
    return round(new_price, 8)


# ──────────────────────────────────────────────────────────────────────────────
# Bulk candle generator — CPU-bound, dispatched via asyncio.to_thread
# ──────────────────────────────────────────────────────────────────────────────


def _generate_candles_sync(
    base_price: float,
    volatility: float,
    n_candles: int,
    candle_minutes: int,
    drift: float,
) -> list[OHLCVRow]:
    """
    Generates a sequence of synthetic OHLCV candles using GBM (synchronous).

    Each candle is built from `_INTRA_CANDLE_STEPS` internal sub-steps, which
    produces realistic high/low wicks rather than flat open=close bars.

    Intended to run inside `asyncio.to_thread` — never call directly from
    an async function with many candles.

    Args:
        base_price:      Starting price in USD.
        volatility:      Per-asset σ.
        n_candles:       Number of candles to produce.
        candle_minutes:  Duration of each candle in minutes.
        drift:           Annualised drift.

    Returns:
        Chronologically ordered list of OHLCVRow objects.
    """
    _INTRA_CANDLE_STEPS: int = 10  # sub-ticks per candle for realistic wicks
    delta_t_per_step = (candle_minutes / _INTRA_CANDLE_STEPS) / _MINUTES_PER_YEAR

    now_unix_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    candle_ms = candle_minutes * 60 * 1000

    rows: list[OHLCVRow] = []
    price = base_price

    for i in range(n_candles - 1, -1, -1):
        timestamp_ms = now_unix_ms - i * candle_ms
        open_price = price
        high_price = price
        low_price = price

        for _ in range(_INTRA_CANDLE_STEPS):
            price = _gbm_step(price, volatility, drift, delta_t_per_step)
            if price > high_price:
                high_price = price
            if price < low_price:
                low_price = price

        rows.append(
            OHLCVRow(
                timestamp_ms=timestamp_ms,
                open=round(open_price, 8),
                high=round(high_price, 8),
                low=round(low_price, 8),
                close=round(price, 8),
                volume=0.0,
            )
        )

    return rows


async def simulate_ohlcv_candles(
    base_price: float,
    volatility: float,
    n_candles: int,
    candle_minutes: int = 60,
    drift: float = _DEFAULT_DRIFT,
) -> list[OHLCVRow]:
    """
    Generates synthetic OHLCV candles asynchronously via a thread-pool executor.

    Dispatches the CPU-bound simulation to `asyncio.to_thread` to avoid
    blocking the ASGI event loop during bulk generation (e.g. 168 × 1H candles).

    Args:
        base_price:      Starting price in USD.
        volatility:      Per-asset σ from BaseAssetHandler.volatility.
        n_candles:       Number of candles to generate.
        candle_minutes:  Duration of each candle in minutes (default: 60).
        drift:           Annualised drift (default: 0.05).

    Returns:
        Chronologically ordered list of OHLCVRow objects.

    Raises:
        ValueError: If base_price <= 0, volatility < 0, or n_candles < 1.
    """
    if base_price <= 0.0:
        raise ValueError(
            f"simulate_ohlcv_candles: base_price must be > 0, got {base_price!r}"
        )
    if volatility < 0.0:
        raise ValueError(
            f"simulate_ohlcv_candles: volatility must be >= 0, got {volatility!r}"
        )
    if n_candles < 1:
        raise ValueError(
            f"simulate_ohlcv_candles: n_candles must be >= 1, got {n_candles!r}"
        )

    rows = await asyncio.to_thread(
        _generate_candles_sync,
        base_price,
        volatility,
        n_candles,
        candle_minutes,
        drift,
    )

    logger.info(
        "simulator_candles_generated: n_candles=%d candle_minutes=%d "
        "base_price=%.4f volatility=%.4f",
        len(rows),
        candle_minutes,
        base_price,
        volatility,
    )
    return rows
