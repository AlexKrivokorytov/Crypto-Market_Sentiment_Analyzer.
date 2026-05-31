"""
Pydantic schemas for the Dynamic Registry (Assets & Lexicons).
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AssetConfig(BaseModel):
    """
    Schema representing a configured cryptocurrency asset in the system.
    """

    id: str = Field(..., description="The internal ticker/route ID, e.g., 'BTC'")
    type: str = Field("crypto", description="Asset type: 'crypto' or 'stock'")
    name: str = Field(..., description="The display name, e.g., 'Bitcoin'")
    aliases: List[str] = Field(
        default_factory=list, description="List of search aliases"
    )
    coingecko_id: Optional[str] = Field(None, description="The CoinGecko API ID")
    yfinance_ticker: Optional[str] = Field(
        None, description="The yfinance ticker symbol"
    )
    base_price: float = Field(default=1.0, description="Fallback starting price")
    volatility: float = Field(default=0.01, description="Simulation volatility")
    seed_volume: int = Field(default=1000000, description="Initial seed volume")
    seed_sentiment: int = Field(default=50, description="Initial seed sentiment")

    is_active: bool = Field(
        default=True, description="Whether the asset is currently tracked"
    )
    is_in_heatmap: bool = Field(
        default=False, description="Whether to display in the sentiment heatmap"
    )
    order: int = Field(default=99, description="Display order for the frontend widgets")

    model_config = ConfigDict(from_attributes=True)


class LexiconConfig(BaseModel):
    """
    Schema representing the dynamic sentiment lexicons.
    """

    id: str = Field(default="global", description="Lexicon singleton identifier")
    crypto_lexicon: dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary mapping terms to their valence scores",
    )
    multi_word_lexicon: dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary mapping multi-word phrases to scores",
    )

    model_config = ConfigDict(from_attributes=True)
