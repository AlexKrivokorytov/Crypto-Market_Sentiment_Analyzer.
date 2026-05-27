"""
Service layer for managing market data simulation, seeding, and database queries.
"""

import asyncio
import datetime
import logging
import random
from typing import Dict, List, Any, cast

from backend.app.core.database import assets_collection, articles_collection
from backend.app.schemas.market import HistoricalDataPoint

logger = logging.getLogger("app")

DEFAULT_ASSETS: List[Dict[str, Any]] = [
    {
        "id": "BTC",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price": 68420.50,
        "change24h": 2.45,
        "high24h": 69150.00,
        "low24h": 66800.00,
        "volume24h": 28450120000,
        "sentimentScore": 74,
        "sentimentLabel": "Bullish",
    },
    {
        "id": "ETH",
        "name": "Ethereum",
        "symbol": "ETH",
        "price": 3482.10,
        "change24h": -1.15,
        "high24h": 3590.00,
        "low24h": 3420.00,
        "volume24h": 14210980000,
        "sentimentScore": 48,
        "sentimentLabel": "Neutral",
    },
    {
        "id": "SOL",
        "name": "Solana",
        "symbol": "SOL",
        "price": 154.85,
        "change24h": 8.68,
        "high24h": 156.40,
        "low24h": 140.20,
        "volume24h": 4120550000,
        "sentimentScore": 86,
        "sentimentLabel": "Bullish",
    },
    {
        "id": "AAPL",
        "name": "Apple Inc.",
        "symbol": "AAPL",
        "price": 185.35,
        "change24h": -0.42,
        "high24h": 186.95,
        "low24h": 184.10,
        "volume24h": 8930400000,
        "sentimentScore": 54,
        "sentimentLabel": "Neutral",
    },
]

ARTICLE_TEMPLATES = {
    "bullish": [
        {
            "title": "Breakthrough Adoption: Major Institution Integrates {Asset}",
            "summary": "A top-tier global investment firm has announced a direct integration and custody solution for {Asset}, indicating significant institutional inflows.",
            "reasoning": "Institutional adoption is the strongest long-term catalyst. By integrating {Asset} into standard portfolios, the addressable market increases by orders of magnitude, providing a structural demand bid.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["adoption", "institutional", "integration", "inflow"],
        },
        {
            "title": "{Asset} Technical Breakout Confirmed by Analysts",
            "summary": "Analysts report that {Asset} has closed above its key resistance level on high trading volume, signaling the start of a new macro upward trend.",
            "reasoning": "The asset has cleared the 200-day moving average and consolidated. High relative volume on the breakout indicates strong buying interest and momentum support.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["breakout", "technical", "resistance", "volume"],
        },
    ],
    "bearish": [
        {
            "title": "Regulatory Headwinds: New Compliance Guidelines Target {Asset}",
            "summary": "Regulatory agencies have proposed stricter compliance guidelines for trading and holding {Asset}, sparking sell-off concerns.",
            "reasoning": "Increased compliance costs and regulatory uncertainty discourage capital allocators. This creates short-term sell pressure and delays developer integration due to compliance risk.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["regulation", "compliance", "uncertainty", "restriction"],
        },
        {
            "title": "Macro Slowdown Triggers Capital Flight Out of {Asset}",
            "summary": "Rising global interest rates and macro liquidity tightening have pushed investors to derisk, leading to capital outflows from {Asset}.",
            "reasoning": "High interest rates increase the opportunity cost of holding risk-on assets. Capital naturally moves back to yield-bearing cash instruments, decreasing the liquidity pool.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["macro", "liquidity", "outflow", "derisking"],
        },
    ],
    "neutral": [
        {
            "title": "{Asset} Consolidation Range Narrows Ahead of Key Options Expiry",
            "summary": "The price of {Asset} continues to trade in a tight range as options contracts worth billions are set to expire this Friday.",
            "reasoning": "Options expiry usually leads to market-maker hedging activity that pins the asset price to maximum pain points, compressing volatility until the expiry passes.\n\n(Simulated Analysis - Seed Data)",
            "keywords": ["options", "consolidation", "volatility", "expiry"],
        }
    ],
}

SOURCES = [
    "Reuters",
    "Bloomberg",
    "TechCrunch",
    "CoinDesk",
    "Wall Street Journal",
    "Financial Times",
]


def generate_single_mock_article(
    asset_id: str, asset_name: str, timestamp: datetime.datetime
) -> Dict[str, Any]:
    """
    Generates a single randomized mock sentiment article for seeding database.
    """
    sentiment = random.choice(["Bullish", "Bearish", "Neutral"])
    pool = ARTICLE_TEMPLATES[sentiment.lower()]
    template = random.choice(pool)

    title = cast(str, template["title"]).replace("{Asset}", asset_name)
    summary = cast(str, template["summary"]).replace("{Asset}", asset_name)
    reasoning = cast(str, template["reasoning"]).replace("{Asset}", asset_name)
    source = random.choice(SOURCES)

    if sentiment == "Bullish":
        sentiment_score = round(0.4 + random.random() * 0.55, 2)
    elif sentiment == "Bearish":
        sentiment_score = round(-0.4 - random.random() * 0.55, 2)
    else:
        sentiment_score = round((random.random() - 0.5) * 0.4, 2)

    art_id = f"art_seed_{asset_id}_{random.randint(10000, 99999)}"

    return {
        "id": art_id,
        "asset_id": asset_id,
        "timestamp": timestamp.isoformat(),
        "source": source,
        "title": title,
        "url": "#",
        "summary": summary,
        "sentimentScore": sentiment_score,
        "sentimentLabel": sentiment,
        "confidence": round(0.75 + random.random() * 0.2, 2),
        "keywords": list(template["keywords"]),
        "llmReasoning": reasoning,
    }


async def seed_database_if_empty() -> None:
    """
    Checks MongoDB collection states and seeds defaults if empty.
    """
    try:
        count = await assets_collection.count_documents({})
        if count == 0:
            logger.info("Assets collection is empty. Seeding defaults...")
            await assets_collection.insert_many(DEFAULT_ASSETS)
            logger.info("Assets seeded successfully.")

        art_count = await articles_collection.count_documents({})
        if art_count == 0:
            logger.info("Articles collection is empty. Seeding historical articles...")
            now = datetime.datetime.now(datetime.timezone.utc)
            seed_articles: List[Dict[str, Any]] = []

            for asset in DEFAULT_ASSETS:
                asset_id = str(asset["id"])
                asset_name = str(asset["name"])
                for i in range(10):
                    ts = now - datetime.timedelta(minutes=i * 45)
                    seed_articles.append(
                        generate_single_mock_article(asset_id, asset_name, ts)
                    )

            if seed_articles:
                await articles_collection.insert_many(seed_articles)
                logger.info(f"Seeded {len(seed_articles)} articles.")
    except Exception as exc:
        logger.error(f"Failed to seed MongoDB database: {str(exc)}")


async def background_update_loop() -> None:
    """
    Simulates real-time price ticks by applying minor fluctuations to prices.
    """
    while True:
        try:
            await asyncio.sleep(7.0)

            cursor = assets_collection.find({})
            async for asset in cursor:
                asset_id = asset["id"]
                current_price = asset["price"]
                sentiment_score = asset["sentimentScore"]

                # Random noise tick (-0.08% to +0.08%) + small sentiment trend bias
                fluc = (random.random() - 0.5) * 0.16
                sentiment_bias = (sentiment_score - 50) / 100.0 * 0.05
                change_percent = fluc + sentiment_bias

                new_price = max(
                    0.01, round(current_price * (1 + change_percent / 100), 2)
                )
                high24h = max(asset.get("high24h", new_price), new_price)
                low24h = min(asset.get("low24h", new_price), new_price)
                change24h = round(asset.get("change24h", 0.0) + change_percent, 2)

                await assets_collection.update_one(
                    {"id": asset_id},
                    {
                        "$set": {
                            "price": new_price,
                            "high24h": high24h,
                            "low24h": low24h,
                            "change24h": change24h,
                        }
                    },
                )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in price simulation tick: {str(exc)}")


async def get_historical_candles(
    asset_id: str, timeframe: str
) -> List[HistoricalDataPoint]:
    """
    Generates dynamic historical price candle arrays aligned with current database price.
    """
    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        return []

    points_count = (
        60
        if timeframe == "1H"
        else 24
        if timeframe == "24H"
        else 168
        if timeframe == "7D"
        else 30
    )
    step_minutes = (
        1 if timeframe == "1H" else 60 if timeframe in ("24H", "7D") else 1440
    )

    volatility = (
        0.015
        if asset_id == "SOL"
        else 0.005
        if asset_id == "BTC"
        else 0.008
        if asset_id == "ETH"
        else 0.003
    )
    vol_factor = (
        volatility * 0.1
        if timeframe == "1H"
        else volatility
        if timeframe == "24H"
        else volatility * 2.5
        if timeframe == "7D"
        else volatility * 6
    )

    data: List[HistoricalDataPoint] = []
    current_price = asset["price"] * (1 - asset["change24h"] / 100)
    base_price = asset["price"]
    now = datetime.datetime.now(datetime.timezone.utc)

    for i in range(points_count - 1, -1, -1):
        ts = now - datetime.timedelta(minutes=i * step_minutes)
        if timeframe == "1H":
            ts_str = ts.strftime("%H:%M:%S")
        elif timeframe == "24H":
            ts_str = ts.strftime("%b %d %H:%M")
        elif timeframe == "7D":
            ts_str = ts.strftime("%b %d %H:00")
        else:
            ts_str = ts.strftime("%b %d")

        random_change = (random.random() - 0.48) * (base_price * vol_factor)
        open_val = max(0.01, current_price)
        close_val = max(0.01, current_price + random_change)

        high_val = max(open_val, close_val) + random.random() * (base_price * 0.002)
        low_val = max(
            0.01, min(open_val, close_val) - random.random() * (base_price * 0.002)
        )

        volume = int(asset["volume24h"] / points_count * (0.5 + random.random()))
        score = min(
            100, max(0, int(asset["sentimentScore"] + (random.random() - 0.5) * 20))
        )

        data.append(
            HistoricalDataPoint(
                timestamp=ts_str,
                open=round(open_val, 2),
                high=round(high_val, 2),
                low=round(low_val, 2),
                close=round(close_val, 2),
                volume=volume,
                sentimentScore=score,
            )
        )
        current_price = close_val

    if data:
        data[-1].close = asset["price"]

    return data
