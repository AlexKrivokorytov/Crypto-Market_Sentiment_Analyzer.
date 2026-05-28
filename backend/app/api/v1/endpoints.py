"""
API Endpoints v1 for the Market Sentiment Analyzer.

Exposes REST routes for:
  - Active assets, real-time metrics, historical candles, LLM news articles
  - Auth: /register, /login, /me
  - Watchlist: /watchlist
  - Alerts: /alerts
  - Portfolio: /portfolio
"""

import uuid
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import assets_collection, articles_collection, users_collection
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

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Market data routes
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/assets",
    response_model=List[AssetMetrics],
    status_code=status.HTTP_200_OK,
    summary="List all assets",
)
async def list_assets() -> List[AssetMetrics]:
    """
    Retrieves the list of all supported assets with their current metrics from MongoDB.

    Returns:
        A list of AssetMetrics schemas.
    """
    cursor = assets_collection.find({})
    assets = await cursor.to_list(length=100)
    return [AssetMetrics.model_validate(asset) for asset in assets]


@router.get(
    "/assets/{asset_id}/metrics",
    response_model=AssetMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get current metrics for a specific asset",
)
async def get_asset_metrics(asset_id: str) -> AssetMetrics:
    """
    Retrieves current market price, daily high/low range, and sentiment index for a single asset.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).

    Returns:
        AssetMetrics object.

    Raises:
        HTTPException: 404 if the asset_id is not found.
    """
    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )
    return AssetMetrics.model_validate(asset)


@router.get(
    "/assets/{asset_id}/sentiment",
    response_model=List[SentimentArticle],
    status_code=status.HTTP_200_OK,
    summary="Get processed news articles for a specific asset",
)
async def get_asset_sentiment(asset_id: str) -> List[SentimentArticle]:
    """
    Retrieves the list of recent news articles analyzed by the LLM for a single asset.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).

    Returns:
        A list of SentimentArticle objects.

    Raises:
        HTTPException: 404 if the asset_id is not found.
    """
    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found.",
        )

    cursor = articles_collection.find({"asset_id": asset_id}).sort("timestamp", -1)
    articles = await cursor.to_list(length=100)
    return [SentimentArticle.model_validate(art) for art in articles]


@router.get(
    "/assets/{asset_id}/historical",
    response_model=List[HistoricalDataPoint],
    status_code=status.HTTP_200_OK,
    summary="Get historical price and sentiment chart points",
)
async def get_asset_historical(
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
    from backend.app.core.config import settings

    return {
        "llm_configured": bool(settings.LLM_API_URL),
        "llm_model": settings.LLM_MODEL if settings.LLM_API_URL else "Simulated Model",
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
async def register(payload: UserCreate) -> UserPublic:
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
async def login(payload: LoginRequest) -> TokenResponse:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

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
        pnl_pct = round(((current_price - avg_buy) / avg_buy) * 100, 2) if avg_buy else 0.0

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    existing_positions: List[Any] = list(user_doc.get("portfolio", []))
    already_exists = any(str(p["asset_id"]) == payload.asset_id for p in existing_positions)

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
