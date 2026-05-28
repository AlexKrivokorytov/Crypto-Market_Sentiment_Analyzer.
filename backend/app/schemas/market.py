"""
Pydantic schemas for the Market Sentiment Analyzer API.
"""

from typing import Any, List
from pydantic import BaseModel, Field, ConfigDict, model_validator


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

    model_config = ConfigDict(from_attributes=True)
