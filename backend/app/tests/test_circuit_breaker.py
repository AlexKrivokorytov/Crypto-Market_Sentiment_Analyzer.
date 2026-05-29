"""
Tests for the generic 3-state Circuit Breaker FSM.

Validates:
  - CLOSED state passes primary results through.
  - Consecutive failures trip breaker to OPEN after threshold.
  - OPEN state routes immediately to fallback.
  - OPEN state transitions to HALF_OPEN after recovery_timeout.
  - HALF_OPEN → CLOSED on success.
  - HALF_OPEN → OPEN on failure.
  - Concurrent calls are handled safely (lock correctness).
  - status() returns expected shape.
  - failure_count resets after success.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.app.core.circuit_breaker import CircuitBreaker, CircuitBreakerState


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def make_breaker(
    failure_threshold: int = 3,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    return CircuitBreaker(
        name="test_breaker",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )


async def _primary_ok() -> str:
    return "primary_result"


async def _fallback_ok() -> str:
    return "fallback_result"


async def _primary_fail() -> str:
    raise RuntimeError("primary_error")


# ──────────────────────────────────────────────────────────────────────────────
# CLOSED state — normal operation
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_closed_primary_called_on_success() -> None:
    breaker = make_breaker()
    result = await breaker.call(primary=_primary_ok, fallback=_fallback_ok)
    assert result == "primary_result"
    assert breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_closed_failure_count_increments() -> None:
    breaker = make_breaker(failure_threshold=5)
    await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert breaker.failure_count == 1
    assert breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_closed_failure_below_threshold_stays_closed() -> None:
    breaker = make_breaker(failure_threshold=3)
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.failure_count == 2


@pytest.mark.asyncio
async def test_closed_success_resets_failure_count() -> None:
    breaker = make_breaker(failure_threshold=3)
    await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert breaker.failure_count == 1
    await breaker.call(primary=_primary_ok, fallback=_fallback_ok)
    assert breaker.failure_count == 0
    assert breaker.state == CircuitBreakerState.CLOSED


# ──────────────────────────────────────────────────────────────────────────────
# Tripping to OPEN
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trips_to_open_after_threshold() -> None:
    breaker = make_breaker(failure_threshold=3)
    for _ in range(3):
        result = await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert breaker.state == CircuitBreakerState.OPEN
    assert result == "fallback_result"


@pytest.mark.asyncio
async def test_open_uses_fallback_immediately() -> None:
    """Once OPEN, primary should never be called."""
    breaker = make_breaker(failure_threshold=2, recovery_timeout=9999.0)
    # Trip to OPEN
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert breaker.state == CircuitBreakerState.OPEN

    primary_mock = AsyncMock(return_value="primary_result")
    result = await breaker.call(primary=primary_mock, fallback=_fallback_ok)
    assert result == "fallback_result"
    primary_mock.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# HALF_OPEN probe logic
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_open_transitions_to_half_open_after_timeout() -> None:
    """Manually back-date _opened_at to force the OPEN → HALF_OPEN transition."""
    breaker = make_breaker(failure_threshold=2, recovery_timeout=0.0)
    # Trip to OPEN
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    state_after_trip = breaker.state
    assert state_after_trip == CircuitBreakerState.OPEN

    # With recovery_timeout=0, the very next call should probe
    # (recovery has already elapsed)
    result = await breaker.call(primary=_primary_ok, fallback=_fallback_ok)
    assert result == "primary_result"
    state_after_probe = breaker.state
    assert state_after_probe == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_half_open_success_closes_breaker() -> None:
    breaker = make_breaker(failure_threshold=2, recovery_timeout=0.0)
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    # Trigger probe (recovery_timeout=0 → immediate HALF_OPEN)
    result = await breaker.call(primary=_primary_ok, fallback=_fallback_ok)
    assert result == "primary_result"
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_half_open_failure_reopens_breaker() -> None:
    breaker = make_breaker(failure_threshold=2, recovery_timeout=0.0)
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    # Probe with failing primary — should go back to OPEN
    result = await breaker.call(primary=_primary_fail, fallback=_fallback_ok)
    assert result == "fallback_result"
    assert breaker.state == CircuitBreakerState.OPEN


# ──────────────────────────────────────────────────────────────────────────────
# status() and introspection
# ──────────────────────────────────────────────────────────────────────────────


def test_status_returns_expected_shape() -> None:
    breaker = CircuitBreaker(
        name="my_breaker", failure_threshold=5, recovery_timeout=30.0
    )
    s = breaker.status()
    assert s["name"] == "my_breaker"
    assert s["state"] == "CLOSED"
    assert s["failure_count"] == 0
    assert s["recovery_timeout_seconds"] == 30.0


def test_initial_state_is_closed() -> None:
    breaker = make_breaker()
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.failure_count == 0


# ──────────────────────────────────────────────────────────────────────────────
# Fallback itself raising — should propagate
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fallback_exception_propagates() -> None:
    """If both primary AND fallback fail, the fallback exception propagates."""
    breaker = make_breaker(failure_threshold=2, recovery_timeout=9999.0)
    # Trip to OPEN
    for _ in range(2):
        await breaker.call(primary=_primary_fail, fallback=_fallback_ok)

    async def _bad_fallback() -> str:
        raise ValueError("fallback_also_broken")

    with pytest.raises(ValueError, match="fallback_also_broken"):
        await breaker.call(primary=_primary_fail, fallback=_bad_fallback)


# ──────────────────────────────────────────────────────────────────────────────
# Concurrent safety — basic smoke test
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_calls_do_not_corrupt_state() -> None:
    """Fire 20 concurrent successful calls — state must remain CLOSED."""
    breaker = make_breaker(failure_threshold=3)
    results = await asyncio.gather(
        *[breaker.call(primary=_primary_ok, fallback=_fallback_ok) for _ in range(20)]
    )
    assert all(r == "primary_result" for r in results)
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.failure_count == 0
