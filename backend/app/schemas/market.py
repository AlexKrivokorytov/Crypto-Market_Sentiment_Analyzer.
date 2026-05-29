"""
Pydantic schemas for the Market Sentiment Analyzer API.
"""

import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class OnChainMetrics(BaseModel):
    """
    On-chain blockchain metrics for Web3 network tracking.
    """

    gasPrice: float = Field(
        ...,
        description="Current network gas price (in Gwei for ETH, SOL/TON equivalent)",
    )
    txVolume1h: int = Field(
        ..., description="Estimated transaction volume in the last hour"
    )

    model_config = ConfigDict(from_attributes=True)


class AssetMetrics(BaseModel):
    """
    Schema representing market metrics and current sentiment index for an asset.
    """

    id: str = Field(..., description="Unique identifier for the asset (e.g. BTC)")
    name: str = Field(..., description="Full name of the asset")
    symbol: str = Field(..., description="Ticker symbol of the asset")
    price: float = Field(..., description="Current market price in USD")
    change24h: float = Field(..., description="24h price percentage change")
    high24h: float = Field(..., description="24h high price limit in USD")
    low24h: float = Field(..., description="24h low price limit in USD")
    volume24h: int = Field(..., description="24h trading volume in USD")
    sentimentScore: int = Field(
        ..., ge=0, le=100, description="Sentiment score index from 0 to 100"
    )
    sentimentLabel: str = Field(
        ..., description="Sentiment label (e.g. Bullish, Bearish, Neutral)"
    )
    openPriceToday: float = Field(
        ..., description="Opening price at the start of the current UTC day in USD"
    )
    lastDayReset: str = Field(
        ..., description="ISO 8601 timestamp when openPriceToday was last reset"
    )
    onchainMetrics: Optional[OnChainMetrics] = Field(
        None, description="Optional real-time on-chain blockchain metrics"
    )

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "openPriceToday" not in data:
                data["openPriceToday"] = data.get("price", 0.0)
            if "lastDayReset" not in data:
                import datetime

                data["lastDayReset"] = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
            if "name" not in data:
                data["name"] = data.get("id", "Unknown Asset")
            if "symbol" not in data:
                data["symbol"] = data.get("id", "UNKNOWN")
            if "volume24h" not in data:
                data["volume24h"] = 0
            if "high24h" not in data:
                data["high24h"] = data.get("price", 0.0)
            if "low24h" not in data:
                data["low24h"] = data.get("price", 0.0)
        return data

    model_config = ConfigDict(from_attributes=True)


class HistoricalDataPoint(BaseModel):
    """
    Schema representing a single historical candlestick chart point with sentiment.
    """

    timestamp: str = Field(..., description="Time point (ISO or human-readable format)")
    open: float = Field(..., description="Opening price in USD")
    high: float = Field(..., description="Highest price in USD during the step")
    low: float = Field(..., description="Lowest price in USD during the step")
    close: float = Field(..., description="Closing price in USD during the step")
    volume: int = Field(..., description="Trading volume during the step")
    sentimentScore: int = Field(
        ..., ge=0, le=100, description="Average sentiment score index during the step"
    )

    model_config = ConfigDict(from_attributes=True)


class SentimentArticle(BaseModel):
    """
    Schema representing a news article processed by the LLM.
    """

    id: str = Field(..., description="Unique article identifier")
    timestamp: str = Field(..., description="ISO 8601 creation timestamp")
    source: str = Field(..., description="News publisher source name")
    title: str = Field(..., description="Article headline title")
    url: str = Field(..., description="Direct hyperlink to the article source")
    summary: str = Field(..., description="Short text summary of the article contents")
    sentimentScore: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="LLM continuous sentiment score between -1.0 and 1.0",
    )
    sentimentLabel: str = Field(
        ..., description="Sentiment category label (Bullish, Bearish, Neutral)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM classification confidence score between 0.0 and 1.0",
    )
    keywords: List[str] = Field(
        default_factory=list, description="Extracted entity keywords tags"
    )
    llmReasoning: str = Field(
        ...,
        description="LLM Chain-of-thought analysis explaining the classification reasoning",
    )
    is_fallback: bool = Field(
        False,
        description="Indicates if the sentiment was evaluated using the local VADER fallback",
    )

    model_config = ConfigDict(from_attributes=True)


class RawTick(BaseModel):
    """
    Schema representing a single raw tick inserted into MongoDB.
    Uses timestamp_unix (absolute) and timestamp (BSON date) for TTL.
    """

    asset_id: str = Field(..., description="Unique ticker identifier")
    timestamp: datetime.datetime = Field(
        ..., description="BSON datetime object for TTL expiration"
    )
    timestamp_unix: int = Field(..., description="Absolute UNIX timestamp in seconds")
    price: float = Field(..., description="Current price")
    sentiment: float = Field(
        ..., ge=-1.0, le=1.0, description="Current VADER sentiment score [-1.0, 1.0]"
    )

    model_config = ConfigDict(from_attributes=True)


class Tick(BaseModel):
    """
    Schema representing a single high-frequency tick measurement (price & sentiment).

    Fields:
        offset_seconds: Seconds elapsed relative to the bucket_start parent datetime.
        price: Price value of the asset at this specific tick.
        sentiment: Aggregated sentiment index score from 0 to 100.
    """

    offset_seconds: int = Field(
        ..., description="Seconds offset relative to bucket_start parent datetime"
    )
    price: float = Field(..., description="Price of the asset at this tick")
    sentiment: int = Field(
        ..., ge=0, le=100, description="Sentiment score (0-100) at this tick"
    )

    model_config = ConfigDict(from_attributes=True)


class TickBucket(BaseModel):
    """
    Schema representing a bucket grouping ticks by asset and time range (Bucket Pattern).

    Fields:
        asset_id: Ticker symbol (e.g. BTC, ETH).
        bucket_start: Datetime marking the start of the bucket.
        bucket_end: Datetime marking the end of the bucket.
        count: Number of ticks currently grouped in this bucket.
        ticks: List of raw tick elements.
    """

    asset_id: str = Field(..., description="Unique ticker identifier (e.g. BTC)")
    bucket_start: datetime.datetime = Field(
        ..., description="Starting datetime of the bucket (e.g. hour start)"
    )
    bucket_end: datetime.datetime = Field(
        ..., description="Ending datetime of the bucket (e.g. hour end)"
    )
    count: int = Field(0, description="Number of ticks in the bucket")
    ticks: List[Tick] = Field(
        default_factory=list, description="Array of raw tick elements"
    )

    model_config = ConfigDict(from_attributes=True)
