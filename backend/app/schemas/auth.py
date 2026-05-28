"""
Pydantic v2 schemas for authentication and user management.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """
    Request body schema for new user registration.
    """

    email: EmailStr = Field(..., description="Unique user email address.")
    password: str = Field(..., min_length=8, description="Plain-text password, minimum 8 chars.")
    display_name: str = Field(..., min_length=1, max_length=64, description="User display name.")


class UserPublic(BaseModel):
    """
    Public-facing user response schema. Never includes hashed_password.
    """

    id: str = Field(..., description="MongoDB ObjectId as a hex string.")
    email: str = Field(..., description="User email address.")
    display_name: str = Field(..., description="User display name.")
    watchlist: List[str] = Field(..., description="List of asset IDs the user is watching.")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Response schema returned after successful login.
    """

    access_token: str = Field(..., description="JWT access token.")
    token_type: Literal["bearer"] = Field("bearer", description="OAuth2 token type.")
    user: UserPublic = Field(..., description="Public profile of the authenticated user.")


class LoginRequest(BaseModel):
    """
    Request body schema for user login.
    """

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="Plain-text password.")


class WatchlistUpdateRequest(BaseModel):
    """
    Request body schema for adding or removing an asset from the watchlist.
    """

    asset_id: str = Field(..., description="Asset ticker symbol to add or remove.")
    action: Literal["add", "remove"] = Field(
        ..., description="'add' appends the asset; 'remove' removes it."
    )


class AlertCondition(BaseModel):
    """
    A single alert condition stored per-user per-asset.
    """

    id: str = Field(..., description="Unique alert ID (UUID4).")
    asset_id: str = Field(..., description="Asset ticker symbol to watch.")
    condition: Literal["PRICE_ABOVE", "PRICE_BELOW", "SENTIMENT_CHANGE"] = Field(
        ..., description="Trigger condition type."
    )
    target_value: float = Field(..., description="Numeric threshold to trigger on.")
    triggered: bool = Field(False, description="Whether this alert has fired yet.")


class AlertCreateRequest(BaseModel):
    """
    Request body schema for creating a new price or sentiment alert.
    """

    asset_id: str = Field(..., description="Asset ticker symbol to watch.")
    condition: Literal["PRICE_ABOVE", "PRICE_BELOW", "SENTIMENT_CHANGE"] = Field(
        ..., description="Trigger condition type."
    )
    target_value: float = Field(..., description="Numeric threshold to trigger on.")


class PortfolioPosition(BaseModel):
    """
    A single portfolio position stored per-user.
    """

    asset_id: str = Field(..., description="Asset ticker symbol.")
    quantity: float = Field(..., gt=0, description="Number of units held.")
    avg_buy_price: float = Field(..., gt=0, description="Average buy price in USD.")


class PortfolioUpsertRequest(BaseModel):
    """
    Request body schema for adding or updating a portfolio position.
    """

    asset_id: str = Field(..., description="Asset ticker symbol.")
    quantity: float = Field(..., gt=0, description="Number of units held.")
    avg_buy_price: float = Field(..., gt=0, description="Average buy price in USD.")


class PortfolioPositionResponse(BaseModel):
    """
    Response schema for a single portfolio position with current P&L data.
    """

    asset_id: str
    asset_name: str
    quantity: float
    avg_buy_price: float
    current_price: float
    pnl_usd: float
    pnl_pct: float

    model_config = ConfigDict(from_attributes=True)
