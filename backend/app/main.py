"""
Main entry point for the FastAPI Market Sentiment Analyzer backend.

Configures CORS, middleware, global error handling, logging, and endpoints.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncIterator
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.endpoints import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


def log_event(level: int, event: str, **kwargs: Any) -> None:
    """
    Logs an event as a structured JSON string to stdout.

    Args:
        level: Logging level (e.g., logging.INFO).
        event: Stable snake_case event identifier.
        **kwargs: Key-value metadata contextual to the log.
    """
    log_data: Dict[str, Any] = {"event": event, "timestamp": time.time(), **kwargs}
    logger.log(level, json.dumps(log_data))


@asynccontextmanager
async def lifespan(app_inst: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan event manager starting/stopping database background simulation and parser processes.
    """
    from backend.app.core.database import ping_database
    from backend.app.services.market_data import (
        seed_database_if_empty,
        background_update_loop,
    )
    from backend.app.services.parser import rss_parser_loop

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
        await seed_database_if_empty()

    sim_task = asyncio.create_task(background_update_loop())
    rss_task = asyncio.create_task(rss_parser_loop())
    log_event(
        logging.INFO,
        "backend_started",
        details="MongoDB update and RSS parser loops spawned.",
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


app = FastAPI(
    title="Market Sentiment Analyzer API",
    description="Backend API providing price metrics and LLM-processed sentiment data.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:4173",  # Vite preview server
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",  # Docker container production port
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next: Any) -> Response:
    """
    Middleware that logs incoming requests and outgoing responses in a structured format.

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

    log_event(
        logging.INFO, "request_received", method=method, path=path, client=client_host
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
        )
        raise exc


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
        logging.WARNING, "validation_exception", path=request.url.path, errors=errors
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
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Simple API health check endpoint.

    Returns:
        Dictionary containing status verification.
    """
    return {"status": "healthy", "service": "Market Sentiment Analyzer API"}


app.include_router(api_router, prefix="/api/v1")
