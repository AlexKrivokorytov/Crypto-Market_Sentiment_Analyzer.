"""
API Endpoints v1 for the Market Sentiment Analyzer.

Exposes REST routes for active assets, real-time metrics, historical candles,
and LLM-processed news articles stored in MongoDB.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.core.database import assets_collection, articles_collection
from backend.app.schemas.market import (
    AssetMetrics,
    HistoricalDataPoint,
    SentimentArticle,
)
from backend.app.services.market_data import get_historical_candles

router = APIRouter()


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
        HTTPException: If the asset_id is invalid.
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
        HTTPException: If the asset_id is invalid.
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
    Generates historical price and sentiment overlay points for charts.

    Args:
        asset_id: The ID of the asset (e.g. BTC, ETH, SOL, AAPL).
        timeframe: Active timeframe selector.

    Returns:
        A list of HistoricalDataPoint objects.

    Raises:
        HTTPException: If the asset_id is invalid or timeframe is unsupported.
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
        Dict[str, Any]: Config dict containing llm_configured and llm_model.
    """
    from backend.app.core.config import settings

    return {
        "llm_configured": bool(settings.LLM_API_URL),
        "llm_model": settings.LLM_MODEL if settings.LLM_API_URL else "Simulated Model",
    }
