"""
Database seeding data.
Contains the default assets and sentiment lexicons to populate the database on first run.
"""

from backend.app.handlers.config import HANDLER_CONFIG

from typing import Dict, Any, List

DEFAULT_CRYPTO_LEXICON: Dict[str, float] = {
    # High Bullish (+3.0 to +4.0)
    "bullish": 3.5,
    "breakout": 3.2,
    "halving": 3.5,
    "partnership": 3.0,
    "integration": 3.0,
    "mainnet": 2.8,
    "upgrade": 2.5,
    "ath": 3.8,
    "all-time-high": 3.8,
    "moon": 3.0,
    "listing": 3.0,
    "listings": 3.0,
    "institutional": 3.2,
    "adoption": 3.5,
    "approve": 3.0,
    "approved": 3.0,
    "approval": 3.0,
    "accumulating": 2.5,
    "supportive": 2.0,
    # Mid Bullish (+1.5 to +2.9)
    "growth": 2.0,
    "surge": 2.5,
    "gain": 2.2,
    "gains": 2.2,
    "launch": 2.0,
    "success": 2.0,
    "successful": 2.0,
    "defy": 1.8,
    "buy": 1.5,
    "pump": 2.0,
    "bull": 2.0,
    "accumulate": 1.8,
    "accumulation": 1.8,
    "secure": 1.5,
    "secured": 1.5,
    "rise": 1.8,
    "rising": 1.8,
    "soar": 2.5,
    "soaring": 2.5,
    "skyrocket": 2.8,
    "rally": 2.5,
    "rallies": 2.5,
    # High Bearish (-3.0 to -4.0)
    "rugpull": -4.0,
    "exploit": -3.8,
    "scam": -4.0,
    "hack": -3.8,
    "hacked": -3.8,
    "phishing": -3.5,
    "crash": -3.5,
    "dump": -3.0,
    "lawsuit": -3.0,
    "sec": -3.0,
    "lawsuits": -3.0,
    "heist": -3.8,
    "stolen": -3.5,
    "bankrupt": -4.0,
    "bankruptcy": -4.0,
    "fraud": -3.8,
    "exploiters": -3.5,
    "stole": -3.5,
    # Mid Bearish (-1.5 to -2.9)
    "drop": -1.8,
    "fall": -1.8,
    "bearish": -2.5,
    "outflow": -2.0,
    "outflows": -2.0,
    "panic": -2.5,
    "warning": -1.8,
    "restriction": -1.8,
    "regulations": -1.5,
    "fears": -1.8,
    "jitters": -1.8,
    "bleed": -2.2,
    "bleeding": -2.2,
    "sell": -1.5,
    "dumped": -2.5,
    "liabilities": -1.5,
    "suspend": -1.8,
    "suspension": -1.8,
    "investigation": -1.5,
    "investigate": -1.5,
    "fud": -2.5,
    "rekt": -3.0,
    "unconfirmed": -0.5,
    "rumor": -0.5,
    "speculation": 0.0,
    "fomo": 2.5,
}

DEFAULT_MULTI_WORD_LEXICON: Dict[str, float] = {
    "all time high": 4.0,
    "rug pull": -4.0,
    "smart contract exploit": -3.8,
    "sec lawsuit": -3.5,
    "chapter 11": -4.0,
    "strategic partnership": 3.0,
    "mainnet launch": 3.0,
    "bull run": 3.5,
    "bear market": -3.0,
    "etf approval": 3.8,
    "mass adoption": 3.5,
}

# Reading the original config to make sure we include all old handlers


def get_default_assets() -> List[Dict[str, Any]]:
    assets: List[Dict[str, Any]] = []
    for cfg in HANDLER_CONFIG:
        asset_id = str(cfg["id"])
        # Map fields to our new AssetConfig model
        asset = {
            "id": asset_id,
            "type": cfg.get("type", "crypto"),
            "name": cfg.get("name", ""),
            "aliases": cfg.get("aliases", []),
            "coingecko_id": cfg.get("coingecko_id"),
            "yfinance_ticker": cfg.get("yfinance_ticker"),
            "base_price": cfg.get("base_price", 1.0),
            "volatility": cfg.get("volatility", 0.01),
            "seed_volume": cfg.get("seed_volume", 1000000),
            "seed_sentiment": cfg.get("seed_sentiment", 50),
            "is_active": True,
            "is_in_heatmap": asset_id in ["BTC", "ETH", "TON", "SOL", "XRP", "ADA"],
            "order": len(assets),
        }
        assets.append(asset)
    return assets
