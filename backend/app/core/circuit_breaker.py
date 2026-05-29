"""
Generic async-safe Circuit Breaker implementing the 3-state FSM.

States
------
CLOSED     Normal operation. All calls go to the primary function.
           After `failure_threshold` consecutive failures → OPEN.

OPEN       Degraded / failing. All calls go to the fallback function immediately.
           After `recovery_timeout` seconds → HALF_OPEN (probe mode).

HALF_OPEN  Probe mode. The next call attempts the primary function.
           Success → CLOSED (reset).
           Failure → OPEN (reset timer).

Usage
-----
    breaker = CircuitBreaker(name="sentiment_engine", failure_threshold=3)

    result = await breaker.call(
        primary=lambda: real_analysis(text),
        fallback=lambda: mock_analysis(text),
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum, auto
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("app")

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Enumeration of the three circuit breaker states."""

    CLOSED = auto()  # Normal operation — primary path active
    OPEN = auto()  # Failure mode — fallback path active
    HALF_OPEN = auto()  # Probe mode — single primary attempt pending


class CircuitBreaker:
    """
    Async-safe 3-state FSM circuit breaker.

    Wraps an async `primary` callable with a `fallback` callable.
    Transitions between CLOSED, OPEN, and HALF_OPEN automatically
    based on consecutive failure count and elapsed recovery time.

    All state transitions emit structured log events at WARNING level
    to facilitate Grafana / ELK alerting.

    Attributes:
        name:              Human-readable breaker identifier (used in logs).
        failure_threshold: Number of consecutive primary failures before OPEN.
        recovery_timeout:  Seconds to wait in OPEN state before probing (HALF_OPEN).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        """
        Initialises the circuit breaker in CLOSED state.

        Args:
            name:              Identifier used in log events (e.g. 'sentiment_engine').
            failure_threshold: Consecutive primary failures that trip the breaker.
            recovery_timeout:  Seconds in OPEN state before attempting a probe.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def call(
        self,
        primary: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]],
    ) -> T:
        """
        Executes the primary callable, routing to fallback when the breaker is OPEN.

        Decision flow:
          CLOSED    → try primary → success: reset counter
                                 → failure: increment counter; if threshold: → OPEN
          OPEN      → check timeout; if elapsed: → HALF_OPEN; else: → fallback
          HALF_OPEN → try primary → success: → CLOSED
                                 → failure: → OPEN (reset timer)

        Args:
            primary:  Zero-argument async callable with the real implementation.
            fallback: Zero-argument async callable used when the breaker is OPEN.

        Returns:
            The result of whichever callable was executed.

        Raises:
            Exception: Re-raises any exception from `fallback` if it also fails.
        """
        async with self._lock:
            current_state = self._state

            if current_state == CircuitBreakerState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._transition_to(CircuitBreakerState.HALF_OPEN)
                    current_state = CircuitBreakerState.HALF_OPEN
                else:
                    # Still in OPEN — use fallback immediately
                    return await fallback()

        if current_state in (
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.HALF_OPEN,
        ):
            try:
                result = await primary()
                await self._on_success(current_state)
                return result
            except Exception as exc:
                await self._on_failure(current_state, exc)
                logger.warning(
                    "circuit_breaker_fallback_activated: breaker=%s state=%s error=%s",
                    self.name,
                    current_state.name,
                    str(exc),
                )
                return await fallback()

        # Unreachable — satisfies mypy exhaustiveness
        return await fallback()  # pragma: no cover

    # ──────────────────────────────────────────────────────────────────────────
    # State introspection (for health checks / metrics)
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitBreakerState:
        """Returns the current state without acquiring the lock (read-only)."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Returns the current consecutive failure count."""
        return self._failure_count

    def status(self) -> dict[str, object]:
        """
        Returns a dict suitable for health-check endpoints or Prometheus metrics.

        Returns:
            Dict with keys: name, state, failure_count, recovery_timeout.
        """
        return {
            "name": self.name,
            "state": self._state.name,
            "failure_count": self._failure_count,
            "recovery_timeout_seconds": self.recovery_timeout,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Private transition helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _on_success(self, prior_state: CircuitBreakerState) -> None:
        """Handles a successful primary call — resets counter and closes if needed."""
        async with self._lock:
            self._failure_count = 0
            if prior_state == CircuitBreakerState.HALF_OPEN:
                self._transition_to(CircuitBreakerState.CLOSED)

    async def _on_failure(
        self, prior_state: CircuitBreakerState, exc: Exception
    ) -> None:
        """Handles a primary call failure — increments counter and opens if threshold hit."""
        async with self._lock:
            self._failure_count += 1
            if prior_state == CircuitBreakerState.HALF_OPEN:
                # Probe failed — go straight back to OPEN
                self._transition_to(CircuitBreakerState.OPEN)
            elif (
                prior_state == CircuitBreakerState.CLOSED
                and self._failure_count >= self.failure_threshold
            ):
                self._transition_to(CircuitBreakerState.OPEN)
            else:
                logger.warning(
                    "circuit_breaker_failure_recorded: breaker=%s "
                    "failure_count=%d threshold=%d error=%s",
                    self.name,
                    self._failure_count,
                    self.failure_threshold,
                    str(exc),
                )

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """
        Performs an unconditional state transition and emits a structured log event.

        MUST be called while the caller holds `self._lock`.

        Args:
            new_state: The state to transition into.
        """
        old_state = self._state
        self._state = new_state

        if new_state == CircuitBreakerState.OPEN:
            self._opened_at = time.monotonic()
            self._failure_count = 0  # reset for the next probe cycle

        logger.warning(
            "circuit_breaker_state_change: breaker=%s %s→%s "
            "failure_threshold=%d recovery_timeout=%.1fs",
            self.name,
            old_state.name,
            new_state.name,
            self.failure_threshold,
            self.recovery_timeout,
        )
