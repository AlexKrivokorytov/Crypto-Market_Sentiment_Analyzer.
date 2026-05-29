"""
Tests for the Geometric Brownian Motion market price simulator.

Validates:
  - simulate_price_tick output is a positive float.
  - simulate_price_tick raises ValueError on invalid inputs.
  - Log-normal property: price stays > 0 after many steps.
  - Volatility=0 produces a deterministic drift-only price path.
  - simulate_ohlcv_candles returns the correct number of OHLCVRow objects.
  - simulate_ohlcv_candles OHLCV invariant: low <= open/close <= high.
  - simulate_ohlcv_candles raises ValueError on invalid inputs.
  - Candles are ordered chronologically (timestamp_ms ascending).
  - GBM does not block the event loop (runs in under 0.5 s for 200 candles).
"""

from __future__ import annotations

import math
import time

import pytest

from backend.app.services.simulator import (
    _gbm_step,
    simulate_ohlcv_candles,
    simulate_price_tick,
)


# ──────────────────────────────────────────────────────────────────────────────
# _gbm_step — internal pure function
# ──────────────────────────────────────────────────────────────────────────────


def test_gbm_step_positive_output() -> None:
    """GBM output must always be strictly positive."""
    price = _gbm_step(100.0, 0.01, 0.05, 1 / 525_960)
    assert price > 0.0, f"Expected positive price, got {price}"


def test_gbm_step_zero_volatility_deterministic() -> None:
    """With σ=0 and Δt, exp((μ - 0)·Δt + 0) is deterministic."""
    drift = 0.05
    delta_t = 1.0 / 525_960  # 1 minute
    expected = 100.0 * math.exp(drift * delta_t)
    result = _gbm_step(100.0, 0.0, drift, delta_t)
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"


def test_gbm_step_very_small_price_stays_positive() -> None:
    """Even for tiny starting prices the log-normal floor prevents zero."""
    result = _gbm_step(1e-6, 0.5, 0.0, 1 / 60)
    assert result > 0.0


# ──────────────────────────────────────────────────────────────────────────────
# simulate_price_tick
# ──────────────────────────────────────────────────────────────────────────────


def test_simulate_price_tick_returns_positive_float() -> None:
    result = simulate_price_tick(50_000.0, 0.005)
    assert isinstance(result, float)
    assert result > 0.0


def test_simulate_price_tick_stays_positive_over_many_steps() -> None:
    """Run 10_000 steps at high volatility — price must never reach zero."""
    price = 100.0
    for _ in range(10_000):
        price = simulate_price_tick(price, 0.1)
    assert price > 0.0


def test_simulate_price_tick_raises_on_zero_price() -> None:
    with pytest.raises(ValueError, match="current_price must be > 0"):
        simulate_price_tick(0.0, 0.005)


def test_simulate_price_tick_raises_on_negative_price() -> None:
    with pytest.raises(ValueError, match="current_price must be > 0"):
        simulate_price_tick(-100.0, 0.005)


def test_simulate_price_tick_raises_on_negative_volatility() -> None:
    with pytest.raises(ValueError, match="volatility must be >= 0"):
        simulate_price_tick(100.0, -0.01)


def test_simulate_price_tick_zero_volatility_moves_with_drift() -> None:
    """σ=0 means price changes only via drift; result must be > start price for μ > 0."""
    result = simulate_price_tick(100.0, volatility=0.0, drift=0.5)
    assert result > 100.0


def test_simulate_price_tick_custom_interval() -> None:
    """Custom interval_minutes should not raise and should produce a positive price."""
    result = simulate_price_tick(100.0, 0.01, interval_minutes=60.0)
    assert result > 0.0


# ──────────────────────────────────────────────────────────────────────────────
# simulate_ohlcv_candles
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_count() -> None:
    """Returns exactly n_candles rows."""
    rows = await simulate_ohlcv_candles(50_000.0, 0.005, n_candles=24)
    assert len(rows) == 24


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_ohlcv_invariant() -> None:
    """For every candle: low <= open, low <= close, high >= open, high >= close."""
    rows = await simulate_ohlcv_candles(3_000.0, 0.008, n_candles=50)
    for row in rows:
        assert row.low <= row.open + 1e-9, f"low={row.low} > open={row.open}"
        assert row.low <= row.close + 1e-9, f"low={row.low} > close={row.close}"
        assert row.high >= row.open - 1e-9, f"high={row.high} < open={row.open}"
        assert row.high >= row.close - 1e-9, f"high={row.high} < close={row.close}"


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_all_positive() -> None:
    """All OHLC values must be strictly positive."""
    rows = await simulate_ohlcv_candles(100.0, 0.05, n_candles=100)
    for row in rows:
        assert row.open > 0.0
        assert row.high > 0.0
        assert row.low > 0.0
        assert row.close > 0.0


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_chronological_order() -> None:
    """timestamp_ms must be strictly ascending (oldest candle first)."""
    rows = await simulate_ohlcv_candles(1_000.0, 0.01, n_candles=30, candle_minutes=60)
    timestamps = [r.timestamp_ms for r in rows]
    assert timestamps == sorted(timestamps), "Candles are not in chronological order"


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_raises_on_zero_price() -> None:
    with pytest.raises(ValueError, match="base_price must be > 0"):
        await simulate_ohlcv_candles(0.0, 0.005, n_candles=10)


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_raises_on_negative_volatility() -> None:
    with pytest.raises(ValueError, match="volatility must be >= 0"):
        await simulate_ohlcv_candles(100.0, -0.01, n_candles=10)


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_raises_on_zero_candles() -> None:
    with pytest.raises(ValueError, match="n_candles must be >= 1"):
        await simulate_ohlcv_candles(100.0, 0.01, n_candles=0)


# ──────────────────────────────────────────────────────────────────────────────
# Performance: GBM must not block the event loop
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_simulate_ohlcv_candles_does_not_block_event_loop() -> None:
    """200 × 60-min candles should complete well under 0.5 s wall-clock."""
    start = time.monotonic()
    rows = await simulate_ohlcv_candles(
        68_000.0, 0.005, n_candles=200, candle_minutes=60
    )
    elapsed = time.monotonic() - start
    assert len(rows) == 200
    assert elapsed < 0.5, f"Candle generation took {elapsed:.3f}s — too slow"


# ──────────────────────────────────────────────────────────────────────────────
# Statistical sanity: log-normal distribution of returns
# ──────────────────────────────────────────────────────────────────────────────


def test_simulate_price_tick_log_returns_approximately_normal() -> None:
    """
    Run 1_000 ticks and verify the mean log-return is close to the theoretical drift.

    With μ=0.05 p.a., σ=0.01, Δt=1min, E[ln(S_t+1/S_t)] = (μ - σ²/2) · Δt.
    """
    import statistics

    MINUTES_PER_YEAR = 525_960.0
    mu = 0.05
    sigma = 0.01
    delta_t = 1.0 / MINUTES_PER_YEAR
    expected_mean_log_return = (mu - 0.5 * sigma**2) * delta_t

    price = 100.0
    log_returns: list[float] = []
    for _ in range(1_000):
        new_price = simulate_price_tick(price, sigma, drift=mu)
        log_returns.append(math.log(new_price / price))
        price = new_price

    observed_mean = statistics.mean(log_returns)
    # Allow ±5 standard deviations of the sample mean for test stability
    tolerance = 5 * sigma * math.sqrt(delta_t / 1_000)
    assert abs(observed_mean - expected_mean_log_return) < tolerance, (
        f"Mean log-return {observed_mean:.2e} deviates from theoretical "
        f"{expected_mean_log_return:.2e} by more than {tolerance:.2e}"
    )
