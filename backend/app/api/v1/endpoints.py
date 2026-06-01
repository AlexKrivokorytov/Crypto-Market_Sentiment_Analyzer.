"""
API Endpoints v1 for the Market Sentiment Analyzer.

Exposes REST routes for:
  - Active assets, real-time metrics, historical candles, LLM news articles
  - Auth: /register, /login, /me
  - Watchlist: /watchlist
  - Alerts: /alerts
  - Portfolio: /portfolio
"""

import asyncio
import datetime
import logging
import uuid
import httpx
from typing import Any, Dict, List, cast

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
    Request,
)

from backend.app.api.dependencies import get_current_user
from backend.app.services.websocket_manager import manager as ws_manager
from backend.app.core.limiter import limiter
from backend.app.core.database import (
    assets_collection,
    articles_collection,
    users_collection,
)
from backend.app.schemas.auth import (
    AlertCondition,
    AlertCreateRequest,
    LoginRequest,
    PortfolioPositionResponse,
    PortfolioUpsertRequest,
    TokenResponse,
    UserCreate,
    UserPublic,
    WatchlistUpdateRequest,
)
from backend.app.schemas.market import (
    AssetMetrics,
    ChatRequest,
    ChatResponse,
    HistoricalDataPoint,
    SentimentArticle,
)
from backend.app.services.auth import (
    add_to_watchlist,
    authenticate_user,
    create_access_token,
    create_user,
    remove_from_watchlist,
)
from backend.app.services.market_data import get_historical_candles
from backend.app.core.cache import cache as app_cache
from backend.app.core.config import settings
from backend.app.core.http_client import get_shared_client
from backend.app.services.llm import (
    llm_cache,
    analyze_article_sentiment,
    clean_text,
)
from backend.app.services.chat import chat_service

router = APIRouter()
logger = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# In-memory cache for Fear & Greed (3600s TTL, zero infra cost)
# ──────────────────────────────────────────────────────────────────────────────
# Using shared app_cache from core instead of individual TTLCaches

# ──────────────────────────────────────────────────────────────────────────────
# Fear & Greed Index
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/fear-greed",
    status_code=status.HTTP_200_OK,
    summary="Crypto Fear & Greed Index (cached 1 hour)",
)
@limiter.limit("30/minute")
async def get_fear_greed(request: Request) -> Dict[str, Any]:
    """
    Proxies and caches the Crypto Fear & Greed Index from Alternative.me.

    Caches the response for 1 hour to minimise outbound requests from the
    free Render instance. Returns the latest value, classification label,
    and the last 7 historical data points for the sparkline.

    Returns:
        Dict with `value`, `classification`, `timestamp`, and `history` list.

    Raises:
        HTTPException: 502 if the upstream API is unreachable.
    """
    cached_fng = app_cache.get("fng")
    if cached_fng is not None:
        return cast(Dict[str, Any], cached_fng)

    try:
        # Added User-Agent to prevent 403 Forbidden from alternative.me
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        client = get_shared_client()
        resp = await client.get(
            "https://api.alternative.me/fng/",
            params={"limit": 8, "format": "json"},
            headers=headers,
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("fear_greed_fetch_failed: error=%s", str(exc))
        cached_fng = app_cache.get("fng")
        if cached_fng is not None:
            return cast(
                Dict[str, Any], cached_fng
            )  # return stale cache on upstream error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch Fear & Greed Index.",
        )

    records = data.get("data", [])
    if not records:
        raise HTTPException(status_code=502, detail="Empty Fear & Greed response.")

    latest = records[0]
    history = [
        {
            "value": int(r["value"]),
            "classification": r["value_classification"],
            "timestamp": datetime.datetime.fromtimestamp(
                int(r["timestamp"]), tz=datetime.timezone.utc
            ).isoformat(),
        }
        for r in records[1:8]
    ]

    result: Dict[str, Any] = {
        "value": int(latest["value"]),
        "classification": latest["value_classification"],
        "timestamp": datetime.datetime.fromtimestamp(
            int(latest["timestamp"]), tz=datetime.timezone.utc
        ).isoformat(),
        "history": history,
    }

    app_cache.set("fng", result, 3600)
    logger.info(
        "fear_greed_fetched: value=%d label=%s",
        result["value"],
        result["classification"],
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# AI Chat Assistant
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="AI market assistant — contextual Q&A powered by LLM",
)
@limiter.limit("4/minute")
async def ai_chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Answers a user question about current market sentiment.

    Delegates all business logic to ChatService, which:
      - Short-circuits immediately when LLM is not configured.
      - Builds live context from MongoDB (prices + headlines).
      - Iterates through the model fallback chain from settings.
      - Returns a ChatResponse; never raises to the caller on LLM failures.

    Rate-limited to 4 requests per minute to protect the free OpenRouter budget.

    Args:
        request: FastAPI Request object (required by the rate-limiter decorator).
        body:    Validated ChatRequest containing `message` and optional `asset_id`.

    Returns:
        ChatResponse with `reply` and `fallback` flag.
    """
    return await chat_service.answer(body)


# ──────────────────────────────────────────────────────────────────────────────
# Market data routes
# ──────────────────────────────────────────────────────────────────────────────

# Caches are now handled by app_cache


@router.get(
    "/assets",
    response_model=List[AssetMetrics],
    status_code=status.HTTP_200_OK,
    summary="List all assets",
)
@limiter.limit("30/minute")
async def list_assets(request: Request) -> List[AssetMetrics]:
    """
    Retrieves the list of all supported assets with their current metrics from MongoDB.

    Returns:
        A list of AssetMetrics schemas.
    """
    cached_assets = app_cache.get("assets_all")
    if cached_assets is not None:
        return cast(List[AssetMetrics], cached_assets)

    cursor = assets_collection.find({})
    assets = await cursor.to_list(length=100)
    result = [AssetMetrics.model_validate(asset) for asset in assets]

    app_cache.set("assets_all", result, 15)
    return result


@router.get(
    "/assets/{asset_id}/metrics",
    response_model=AssetMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get current metrics for a specific asset",
)
@limiter.limit("30/minute")
async def get_asset_metrics(request: Request, asset_id: str) -> AssetMetrics:
    """
    Retrieves current market price, daily high/low range, and sentiment index for a single asset.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).

    Returns:
        AssetMetrics object.

    Raises:
        HTTPException: 404 if the asset_id is not found.
    """
    cached_metrics = app_cache.get(f"metrics_{asset_id}")
    if cached_metrics is not None:
        return cast(AssetMetrics, cached_metrics)

    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    result = AssetMetrics.model_validate(asset)
    app_cache.set(f"metrics_{asset_id}", result, 15)
    return result


@router.get(
    "/assets/{asset_id}/sentiment",
    response_model=List[SentimentArticle],
    status_code=status.HTTP_200_OK,
    summary="Get processed news articles for a specific asset",
)
@limiter.limit("30/minute")
async def get_asset_sentiment(
    request: Request, asset_id: str
) -> List[SentimentArticle]:
    """
    Retrieves the list of recent news articles analyzed by the LLM for a single asset.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).

    Returns:
        A list of SentimentArticle objects.

    Raises:
        HTTPException: 404 if the asset_id is not found.
    """
    cached_sentiment = app_cache.get(f"sentiment_{asset_id}")
    if cached_sentiment is not None:
        return cast(List[SentimentArticle], cached_sentiment)

    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    cursor = articles_collection.find({"asset_id": asset_id}).sort("timestamp", -1)
    articles = await cursor.to_list(length=100)
    result = [SentimentArticle.model_validate(art) for art in articles]

    app_cache.set(f"sentiment_{asset_id}", result, 30)
    return result


@router.post(
    "/articles/{article_id}/analyze",
    response_model=SentimentArticle,
    status_code=status.HTTP_200_OK,
    summary="Trigger live AI sentiment analysis for an article",
)
@limiter.limit("10/minute")
async def analyze_article_sentiment_endpoint(
    request: Request,
    article_id: str,
) -> SentimentArticle:
    """
    Triggers live AI sentiment analysis of an existing article.
    Queries the remote LLM bypassing the local cache to get a fresh response.
    Saves the updated sentiment to MongoDB and updates the asset metrics.

    Args:
        request: The FastAPI Request object (needed for rate limiter).
        article_id: The ID of the article to analyze.

    Returns:
        The updated SentimentArticle schema.
    """
    article = await articles_collection.find_one({"id": article_id})
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID '{article_id}' not found.",
        )

    cleaned_title = clean_text(article["title"])
    cleaned_summary = clean_text(article["summary"])
    cache_key = f"{article['asset_id']}:{cleaned_title}:{cleaned_summary}"

    # Remove from local in-memory cache to force a fresh LLM call
    async with llm_cache.lock:
        llm_cache.cache.pop(cache_key, None)

    # Perform analysis with robust HTTP error handling
    try:
        sentiment_data = await analyze_article_sentiment(
            title=article["title"],
            summary=article["summary"],
            asset_symbol=article["asset_id"],
            bypass_breaker=True,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OpenRouter rate limit exceeded. Please wait a minute and try again.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenRouter API returned error {status_code}: {exc.response.text}",
        )
    except (httpx.TimeoutException, httpx.RequestError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenRouter API request timed out or failed to connect.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis processing failed: {str(exc)}",
        )

    # Update MongoDB article document
    update_doc = {
        "sentimentScore": sentiment_data["sentimentScore"],
        "sentimentLabel": sentiment_data["sentimentLabel"],
        "confidence": sentiment_data["confidence"],
        "keywords": sentiment_data["keywords"],
        "llmReasoning": sentiment_data["reasoning"],
        "is_fallback": sentiment_data.get("is_fallback", False),
    }

    await articles_collection.update_one(
        {"id": article_id},
        {"$set": update_doc},
    )

    # Reactively apply sentiment shift to asset metrics
    from backend.app.services.parser import _apply_sentiment_to_asset

    await _apply_sentiment_to_asset(
        article["asset_id"], sentiment_data["sentimentScore"]
    )

    # Fetch and return the updated article
    updated = await articles_collection.find_one({"id": article_id})
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article could not be reloaded after analysis.",
        )
    return SentimentArticle.model_validate(updated)


@router.get(
    "/assets/{asset_id}/historical",
    response_model=List[HistoricalDataPoint],
    status_code=status.HTTP_200_OK,
    summary="Get historical price and sentiment chart points",
)
@limiter.limit("30/minute")
async def get_asset_historical(
    request: Request,
    asset_id: str,
    timeframe: str = Query("24H", description="Charts timeframe (1H, 24H, 7D, 30D)"),
) -> List[HistoricalDataPoint]:
    """
    Returns persisted historical price and sentiment overlay points for charts.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).
        timeframe: Active timeframe selector.

    Returns:
        A list of HistoricalDataPoint objects sorted oldest to newest.

    Raises:
        HTTPException: 404 if asset not found, 400 if timeframe unsupported.
    """
    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    supported_timeframes = {"1H", "24H", "7D", "30D"}
    if timeframe not in supported_timeframes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeframe '{timeframe}' is not supported. Choose from {supported_timeframes}.",
        )

    return await get_historical_candles(asset_id, timeframe)


@router.get(
    "/config",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get backend LLM configuration",
)
async def get_config() -> Dict[str, Any]:
    """
    Retrieves the backend's active LLM configuration.

    Returns:
        Dict containing llm_configured and llm_model.
    """

    return {
        "llm_configured": bool(settings.LLM_API_URL),
        "llm_model": settings.LLM_MODEL if settings.LLM_API_URL else "Simulated Model",
    }


@router.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    summary="Bypass-DB Warmup health check for Render cold starts",
)
async def warmup_healthz() -> Dict[str, str]:
    """
    Rapid lightweight database-bypass warmup check to wake up sleeping Render containers.

    Returns:
        Static JSON payload confirming service availability.
    """
    return {
        "status": "warm",
        "service": "Market Sentiment Analyzer API",
        "message": "FastAPI container awake and ready.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Auth routes
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/auth/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("10/minute")
async def register(request: Request, payload: UserCreate) -> UserPublic:
    """
    Creates a new user account.

    Args:
        payload: UserCreate schema with email, password, and display_name.

    Returns:
        The created user's public profile.

    Raises:
        HTTPException: 409 if the email is already registered.
    """
    try:
        return await create_user(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and receive a JWT token",
)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest) -> TokenResponse:
    """
    Authenticates a user and issues a signed JWT access token.

    Args:
        payload: LoginRequest with email and password.

    Returns:
        TokenResponse with access_token, token_type, and user profile.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = await authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get(
    "/auth/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user's profile",
)
async def get_me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    """
    Returns the authenticated user's public profile.

    Args:
        current_user: Injected by the get_current_user dependency.

    Returns:
        UserPublic schema.
    """
    return current_user


# ──────────────────────────────────────────────────────────────────────────────
# Watchlist routes
# ──────────────────────────────────────────────────────────────────────────────


@router.put(
    "/watchlist",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Add or remove an asset from the authenticated user's watchlist",
)
async def update_watchlist(
    payload: WatchlistUpdateRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """
    Adds or removes an asset from the authenticated user's watchlist.

    Args:
        payload: WatchlistUpdateRequest with asset_id and action ('add' or 'remove').
        current_user: Injected by the get_current_user dependency.

    Returns:
        Updated UserPublic profile.

    Raises:
        HTTPException: 404 if the asset_id does not exist in the assets collection.
        HTTPException: 400 for unknown action values.
    """
    # Verify the asset exists before adding to watchlist
    asset = await assets_collection.find_one({"id": payload.asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{payload.asset_id}' not found.",
        )

    if payload.action == "add":
        return await add_to_watchlist(current_user.id, payload.asset_id)
    return await remove_from_watchlist(current_user.id, payload.asset_id)


# ──────────────────────────────────────────────────────────────────────────────
# Alert routes
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/alerts",
    response_model=List[AlertCondition],
    status_code=status.HTTP_200_OK,
    summary="List all alerts for the authenticated user",
)
async def list_alerts(
    current_user: UserPublic = Depends(get_current_user),
) -> List[AlertCondition]:
    """
    Returns all alerts (triggered and untriggered) for the authenticated user.

    Args:
        current_user: Injected by the get_current_user dependency.

    Returns:
        List of AlertCondition schemas.
    """
    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    doc = await users_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    raw_alerts: List[Any] = list(doc.get("alerts", []))
    return [AlertCondition.model_validate(a) for a in raw_alerts]


@router.post(
    "/alerts",
    response_model=AlertCondition,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new price or sentiment alert",
)
async def create_alert(
    payload: AlertCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> AlertCondition:
    """
    Creates a new alert for the authenticated user.

    Args:
        payload: AlertCreateRequest with asset_id, condition, and target_value.
        current_user: Injected by the get_current_user dependency.

    Returns:
        The created AlertCondition schema.

    Raises:
        HTTPException: 404 if the asset does not exist.
    """
    asset = await assets_collection.find_one({"id": payload.asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{payload.asset_id}' not found.",
        )

    alert_doc: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "asset_id": payload.asset_id,
        "condition": payload.condition,
        "target_value": payload.target_value,
        "triggered": False,
    }

    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    await users_collection.update_one(
        {"_id": oid},
        {"$push": {"alerts": alert_doc}},
    )

    return AlertCondition.model_validate(alert_doc)


@router.delete(
    "/alerts/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an alert by ID",
)
async def delete_alert(
    alert_id: str,
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    """
    Deletes an alert by its UUID.

    Args:
        alert_id: UUID string of the alert to delete.
        current_user: Injected by the get_current_user dependency.

    Raises:
        HTTPException: 404 if the alert is not found.
    """
    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    result = await users_collection.update_one(
        {"_id": oid},
        {"$pull": {"alerts": {"id": alert_id}}},
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Portfolio routes
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/portfolio",
    response_model=List[PortfolioPositionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated user's portfolio with live P&L",
)
async def get_portfolio(
    current_user: UserPublic = Depends(get_current_user),
) -> List[PortfolioPositionResponse]:
    """
    Returns the authenticated user's portfolio positions with current price and P&L data.

    Args:
        current_user: Injected by the get_current_user dependency.

    Returns:
        List of PortfolioPositionResponse schemas with live P&L calculations.
    """
    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    doc = await users_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    raw_portfolio: List[Any] = list(doc.get("portfolio", []))
    if not raw_portfolio:
        return []

    # Batch-fetch all asset prices in a single query
    asset_ids = [str(pos["asset_id"]) for pos in raw_portfolio]
    assets_cursor = assets_collection.find({"id": {"$in": asset_ids}})
    assets_list = await assets_cursor.to_list(length=100)
    price_map: Dict[str, Dict[str, Any]] = {str(a["id"]): a for a in assets_list}

    positions: List[PortfolioPositionResponse] = []
    for pos in raw_portfolio:
        asset_id = str(pos["asset_id"])
        asset_doc = price_map.get(asset_id)
        current_price = float(asset_doc["price"]) if asset_doc else 0.0
        asset_name = str(asset_doc["name"]) if asset_doc else asset_id
        qty = float(pos["quantity"])
        avg_buy = float(pos["avg_buy_price"])
        pnl_usd = round((current_price - avg_buy) * qty, 2)
        pnl_pct = (
            round(((current_price - avg_buy) / avg_buy) * 100, 2) if avg_buy else 0.0
        )

        positions.append(
            PortfolioPositionResponse(
                asset_id=asset_id,
                asset_name=asset_name,
                quantity=qty,
                avg_buy_price=avg_buy,
                current_price=current_price,
                pnl_usd=pnl_usd,
                pnl_pct=pnl_pct,
            )
        )

    return positions


@router.put(
    "/portfolio",
    response_model=PortfolioPositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add or update a portfolio position",
)
async def upsert_portfolio_position(
    payload: PortfolioUpsertRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> PortfolioPositionResponse:
    """
    Creates or updates a portfolio position for the authenticated user.

    Uses $set on the matching array element if the position already exists,
    otherwise $push to add a new entry (manual upsert on embedded array).

    Args:
        payload: PortfolioUpsertRequest with asset_id, quantity, and avg_buy_price.
        current_user: Injected by the get_current_user dependency.

    Returns:
        PortfolioPositionResponse with live P&L.

    Raises:
        HTTPException: 404 if the asset does not exist.
    """
    asset_doc = await assets_collection.find_one({"id": payload.asset_id})
    if not asset_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{payload.asset_id}' not found.",
        )

    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    user_doc = await users_collection.find_one({"_id": oid})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    existing_positions: List[Any] = list(user_doc.get("portfolio", []))
    already_exists = any(
        str(p["asset_id"]) == payload.asset_id for p in existing_positions
    )

    if already_exists:
        await users_collection.update_one(
            {"_id": oid, "portfolio.asset_id": payload.asset_id},
            {
                "$set": {
                    "portfolio.$.quantity": payload.quantity,
                    "portfolio.$.avg_buy_price": payload.avg_buy_price,
                }
            },
        )
    else:
        await users_collection.update_one(
            {"_id": oid},
            {
                "$push": {
                    "portfolio": {
                        "asset_id": payload.asset_id,
                        "quantity": payload.quantity,
                        "avg_buy_price": payload.avg_buy_price,
                    }
                }
            },
        )

    current_price = float(asset_doc["price"])
    pnl_usd = round((current_price - payload.avg_buy_price) * payload.quantity, 2)
    pnl_pct = round(
        ((current_price - payload.avg_buy_price) / payload.avg_buy_price) * 100, 2
    )

    return PortfolioPositionResponse(
        asset_id=payload.asset_id,
        asset_name=str(asset_doc["name"]),
        quantity=payload.quantity,
        avg_buy_price=payload.avg_buy_price,
        current_price=current_price,
        pnl_usd=pnl_usd,
        pnl_pct=pnl_pct,
    )


@router.delete(
    "/portfolio/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a portfolio position",
)
async def delete_portfolio_position(
    asset_id: str,
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    """
    Removes a portfolio position for the authenticated user.

    Args:
        asset_id: Ticker symbol of the position to remove.
        current_user: Injected by the get_current_user dependency.

    Raises:
        HTTPException: 404 if the position is not found.
    """
    try:
        oid = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID."
        ) from exc

    result = await users_collection.update_one(
        {"_id": oid},
        {"$pull": {"portfolio": {"asset_id": asset_id}}},
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio position for '{asset_id}' not found.",
        )


@router.websocket("/ws/{asset_id}")
async def websocket_endpoint(websocket: WebSocket, asset_id: str) -> None:
    """
    WebSocket endpoint for real-time asset updates.

    Registers a client-specific asyncio queue to isolate client bandwidth.
    Concurrently runs a keep-alive reader loop and a queue-pull writer loop.

    Args:
        websocket: The FastAPI WebSocket object.
        asset_id: The asset identifier channel.
    """
    queue = await ws_manager.connect(asset_id, websocket)

    async def write_loop() -> None:
        """
        Pulls messages from the socket's private queue and transmits them.
        """
        try:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
                queue.task_done()
        except Exception as exc:
            logger.debug(
                "websocket_write_loop_stopped: asset_id=%s error=%s",
                asset_id,
                str(exc),
            )

    # Spawn the write loop in the background
    write_task = asyncio.create_task(write_loop())

    # Keep active reader loop on the main connection thread to monitor keep-alives and disconnects
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(
            "websocket_read_loop_error: asset_id=%s error=%s",
            asset_id,
            str(exc),
        )
    finally:
        # Clean shutdown: stop write task and drop registrations from connection manager
        write_task.cancel()
        try:
            await write_task
        except asyncio.CancelledError:
            pass
        await ws_manager.disconnect(asset_id, websocket)
