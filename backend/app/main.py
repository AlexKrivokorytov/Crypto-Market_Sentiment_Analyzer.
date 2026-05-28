"""
Main entry point for the FastAPI Market Sentiment Analyzer backend.

Configures CORS, middleware, global error handling, logging, and endpoints.

Phase 1 changes:
  - seed_database_if_empty() runs in a background task to avoid blocking startup.
  - supervised_task() wraps background coroutines with exponential-backoff restart.
  - ensure_indexes() is called at startup before tasks are spawned.
  - Correlation ID middleware injects X-Request-ID into every request and response.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Coroutine, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.endpoints import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# Structured logging helper
# ──────────────────────────────────────────────────────────────────────────────


def log_event(level: int, event: str, **kwargs: Any) -> None:
    """
    Logs a structured JSON event to stdout.

    Args:
        level: Logging level constant (e.g. logging.INFO).
        event: Stable snake_case event identifier.
        **kwargs: Additional key-value metadata for the log entry.
    """
    log_data: Dict[str, Any] = {"event": event, "timestamp": time.time(), **kwargs}
    logger.log(level, json.dumps(log_data))


# ──────────────────────────────────────────────────────────────────────────────
# Supervised background task wrapper
# ──────────────────────────────────────────────────────────────────────────────

_BACKOFF_START_SECONDS = 5.0
_BACKOFF_MAX_SECONDS = 300.0
_HEALTHY_RUN_SECONDS = 60.0


async def supervised_task(
    coro_fn: Callable[[], Coroutine[Any, Any, None]],
    name: str,
) -> None:
    """
    Runs a coroutine factory in a supervised loop with exponential backoff.

    On every crash the coroutine is restarted after a delay that doubles on
    each consecutive failure, capped at _BACKOFF_MAX_SECONDS. The backoff
    counter resets if the coroutine runs for at least _HEALTHY_RUN_SECONDS.

    Args:
        coro_fn: Zero-argument callable that returns the coroutine to supervise.
        name: Human-readable task name used in log events.
    """
    backoff = _BACKOFF_START_SECONDS

    while True:
        started_at = time.monotonic()
        try:
            await coro_fn()
            # If the coroutine returns normally, treat it as a healthy run
            backoff = _BACKOFF_START_SECONDS
        except asyncio.CancelledError:
            log_event(logging.INFO, "task_cancelled", task=name)
            return
        except Exception as exc:
            elapsed = time.monotonic() - started_at
            if elapsed >= _HEALTHY_RUN_SECONDS:
                backoff = _BACKOFF_START_SECONDS

            log_event(
                logging.ERROR,
                "task_crashed",
                task=name,
                error=str(exc),
                backoff_seconds=backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _BACKOFF_MAX_SECONDS)


# ──────────────────────────────────────────────────────────────────────────────
# Application lifespan
# ──────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app_inst: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan event manager.

    Startup sequence:
      1. Ping MongoDB.
      2. Ensure all indexes exist.
      3. Seed the database in a background task (non-blocking).
      4. Spawn supervised background workers.

    Shutdown:
      Cancels all spawned tasks and awaits their termination.
    """
    from backend.app.core.database import ping_database, ensure_indexes
    from backend.app.services.market_data import (
        seed_database_if_empty,
        background_update_loop,
    )
    from backend.app.services.parser import rss_parser_loop

    is_render = os.environ.get("RENDER", "").lower() in ("true", "1", "yes")

    db_ok = await ping_database()
    if not db_ok:
        log_event(
            logging.CRITICAL,
            "db_connection_failed",
            details="Could not ping MongoDB at startup.",
        )
    else:
        log_event(
            logging.INFO,
            "db_connection_established",
            details="MongoDB ping successful.",
        )
        await ensure_indexes()
        log_event(logging.INFO, "db_indexes_ensured", details="MongoDB indexes ready.")

    if is_render:
        llm_url = os.environ.get("LLM_API_URL", "")
        if not llm_url:
            log_event(
                logging.WARNING,
                "llm_not_configured",
                details="LLM_API_URL is not set — running in simulation mode.",
            )

    # Non-blocking seed so Render health checks pass immediately
    asyncio.create_task(seed_database_if_empty())

    sim_task = asyncio.create_task(
        supervised_task(background_update_loop, "background_update_loop")
    )
    rss_task = asyncio.create_task(
        supervised_task(rss_parser_loop, "rss_parser_loop")
    )

    log_event(
        logging.INFO,
        "app_startup_complete",
        details="Listening for requests.",
    )

    yield

    sim_task.cancel()
    rss_task.cancel()
    try:
        await asyncio.gather(sim_task, rss_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    log_event(
        logging.INFO, "backend_stopped", details="Background tasks cleanly cancelled."
    )


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Market Sentiment Analyzer API",
    description="Backend API providing price metrics and LLM-processed sentiment data.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:4173",   # Vite preview server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",   # Docker container production port
    "http://127.0.0.1:8080",
    "https://crypto-market-sentiment-analyzer-1.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Any) -> Response:
    """
    Injects a correlation ID into every request for end-to-end traceability.

    Reads X-Request-ID from the incoming headers if present; otherwise generates
    a new UUID4. Stores the value in `request.state.correlation_id` and echoes
    it back in the response header X-Request-ID.

    Args:
        request: The incoming Starlette request.
        call_next: The next middleware or route handler.

    Returns:
        The response with X-Request-ID header attached.
    """
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = correlation_id
    return response


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next: Any) -> Response:
    """
    Logs every incoming request and its response in a structured format.

    Args:
        request: The Starlette/FastAPI request object.
        call_next: The next request handler in the middleware chain.

    Returns:
        The response returned by the route handler.
    """
    start_time: float = time.time()
    path: str = request.url.path
    method: str = request.method
    client_host: str = request.client.host if request.client else "unknown"
    correlation_id: str = getattr(request.state, "correlation_id", "")

    log_event(
        logging.INFO,
        "request_received",
        method=method,
        path=path,
        client=client_host,
        correlation_id=correlation_id,
    )

    try:
        response: Response = await call_next(request)
        process_time: float = time.time() - start_time
        log_event(
            logging.INFO,
            "request_processed",
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=round(process_time * 1000, 2),
            correlation_id=correlation_id,
        )
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        log_event(
            logging.ERROR,
            "request_failed",
            method=method,
            path=path,
            error_class=exc.__class__.__name__,
            error_message=str(exc),
            duration_ms=round(process_time * 1000, 2),
            correlation_id=correlation_id,
        )
        raise exc


# ──────────────────────────────────────────────────────────────────────────────
# Exception handlers
# ──────────────────────────────────────────────────────────────────────────────


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Global handler for Starlette/FastAPI HTTPExceptions.

    Args:
        request: The Starlette/FastAPI request object.
        exc: The HTTP exception raised.

    Returns:
        JSONResponse with details of the HTTP error.
    """
    log_event(
        logging.WARNING,
        "http_exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_EXCEPTION",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Global handler for Pydantic input validation exceptions.

    Args:
        request: The Starlette/FastAPI request object.
        exc: The validation exception raised.

    Returns:
        JSONResponse detailing the validation parameters that failed.
    """
    errors = exc.errors()
    log_event(
        logging.WARNING,
        "validation_exception",
        path=request.url.path,
        errors=errors,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Input validation failed.",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global catch-all handler for unhandled exceptions.

    Args:
        request: The Starlette/FastAPI request object.
        exc: The unhandled exception raised.

    Returns:
        JSONResponse with a generic error code and message.
    """
    log_event(
        logging.CRITICAL,
        "unhandled_system_exception",
        path=request.url.path,
        error_class=exc.__class__.__name__,
        error_message=str(exc),
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Simple API health check endpoint for uptime monitors.

    Returns:
        Dictionary with status and service name.
    """
    return {"status": "healthy", "service": "Market Sentiment Analyzer API"}


# ──────────────────────────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")
