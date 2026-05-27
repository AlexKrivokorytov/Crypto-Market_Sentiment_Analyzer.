"""
API Endpoints v1 for the Market Sentiment Analyzer.

Exposes REST routes for active assets, real-time metrics, historical candles,
and LLM-processed news articles.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.market import AssetMetrics, HistoricalDataPoint, SentimentArticle
from backend.app.services.market_data import ASSETS_DB, ARTICLES_DB, get_historical_candles

router = APIRouter()


@router.get(
    "/assets",
    response_model=List[AssetMetrics],
    status_code=status.HTTP_200_OK,
    summary="List all assets"
)
async def list_assets() -> List[AssetMetrics]:
    """
    Retrieves the list of all supported assets with their current metrics.

    Returns:
        A list of AssetMetrics schemas.
    """
    return list(ASSETS_DB.values())


@router.get(
    "/assets/{asset_id}/metrics",
    response_model=AssetMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get current metrics for a specific asset"
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
    asset = ASSETS_DB.get(asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found."
        )
    return asset


@router.get(
    "/assets/{asset_id}/sentiment",
    response_model=List[SentimentArticle],
    status_code=status.HTTP_200_OK,
    summary="Get processed news articles for a specific asset"
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
    if asset_id not in ASSETS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found."
        )
    
    return ARTICLES_DB.get(asset_id, [])


@router.get(
    "/assets/{asset_id}/historical",
    response_model=List[HistoricalDataPoint],
    status_code=status.HTTP_200_OK,
    summary="Get historical price and sentiment chart points"
)
async def get_asset_historical(
    asset_id: str,
    timeframe: str = Query("24H", description="Charts timeframe (1H, 24H, 7D, 30D)")
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
    if asset_id not in ASSETS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found."
        )
    
    supported_timeframes = {"1H", "24H", "7D", "30D"}
    if timeframe not in supported_timeframes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeframe '{timeframe}' is not supported. Choose from {supported_timeframes}."
        )

    return get_historical_candles(asset_id, timeframe)
