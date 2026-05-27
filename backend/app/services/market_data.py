"""
Service layer for generating and managing mock market data and sentiment articles.
"""

import asyncio
import datetime
import random
from typing import Dict, List, cast
from backend.app.schemas.market import AssetMetrics, HistoricalDataPoint, SentimentArticle

# Templates matching the frontend
ARTICLE_TEMPLATES = {
    "bullish": [
        {
            "title": "Breakthrough Adoption: Major Institution Integrates {Asset}",
            "summary": "A top-tier global investment firm has announced a direct integration and custody solution for {Asset}, indicating significant institutional inflows.",
            "reasoning": "Institutional adoption is the strongest long-term catalyst. By integrating {Asset} into standard portfolios, the addressable market increases by orders of magnitude, providing a structural demand bid.",
            "keywords": ["adoption", "institutional", "integration", "inflow", "catalyst"]
        },
        {
            "title": "{Asset} Technical Breakout Confirmed by Analysts",
            "summary": "Analysts report that {Asset} has closed above its key resistance level on high trading volume, signaling the start of a new macro upward trend.",
            "reasoning": "The asset has cleared the 200-day moving average and consolidated. High relative volume on the breakout indicates strong buying interest and momentum support.",
            "keywords": ["breakout", "technical analysis", "resistance", "volume", "momentum"]
        },
        {
            "title": "Protocol Upgrade Boosts {Asset} Network Efficiency",
            "summary": "The core developers of {Asset} have successfully deployed the latest upgrade, cutting transaction overhead by 40% and increasing throughput.",
            "reasoning": "Scalability and efficiency improvements directly enhance the asset's utility value. Lower friction attracts developers and users, strengthening the ecosystem's fundamental moat.",
            "keywords": ["upgrade", "efficiency", "scalability", "development", "utility"]
        }
    ],
    "bearish": [
        {
            "title": "Regulatory Headwinds: New Compliance Guidelines Target {Asset}",
            "summary": "Regulatory agencies have proposed stricter compliance guidelines for trading and holding {Asset}, sparking sell-off concerns among retail users.",
            "reasoning": "Increased compliance costs and regulatory uncertainty discourage capital allocators. This creates short-term sell pressure and delays developer integration due to compliance risk.",
            "keywords": ["regulation", "compliance", "uncertainty", "restriction", "sell-off"]
        },
        {
            "title": "Macro Slowdown Triggers Capital Flight Out of {Asset}",
            "summary": "Rising global interest rates and macro liquidity tightening have pushed investors to derisk, leading to notable capital outflows from {Asset}.",
            "reasoning": "High interest rates increase the opportunity cost of holding risk-on assets. Capital naturally moves back to yield-bearing cash instruments, decreasing the liquidity pool for {Asset}.",
            "keywords": ["macro", "liquidity", "outflow", "derisking", "interest rates"]
        },
        {
            "title": "Security Alert: Phishing Campaign Targets {Asset} Holders",
            "summary": "Security researchers have flagged an active, highly sophisticated phishing campaign targeting wallets and accounts holding {Asset}.",
            "reasoning": "Security scares negatively affect user confidence, especially in retail segments. Fear of theft leads to temporary asset movement to cold storage or sales, damping short-term buy sentiment.",
            "keywords": ["security", "phishing", "scam", "wallet", "exploit"]
        }
    ],
    "neutral": [
        {
            "title": "{Asset} Consolidation Range Narrows Ahead of Key Options Expiry",
            "summary": "The price of {Asset} continues to trade in a tight range as options contracts worth billions are set to expire this Friday.",
            "reasoning": "Options expiry usually leads to market-maker hedging activity that pins the asset price to maximum pain points, compressing volatility until the expiry passes.",
            "keywords": ["options", "consolidation", "volatility", "expiry", "hedging"]
        },
        {
            "title": "Industry Conference Panel Discusses the Future of {Asset}",
            "summary": "Leaders gathered at the global tech summit discussed various development paths and use cases for {Asset}, with no immediate announcements.",
            "reasoning": "Broad theoretical panels provide general positive branding but lack short-term market-moving catalysts. The sentiment remains balanced and long-term oriented.",
            "keywords": ["conference", "summit", "discussion", "future", "use cases"]
        }
    ]
}

SOURCES = ["Reuters", "Bloomberg", "TechCrunch", "CoinDesk", "Wall Street Journal", "Financial Times", "X.com (Social)"]

# In-memory stores
ASSETS_DB: Dict[str, AssetMetrics] = {
    "BTC": AssetMetrics(
        id="BTC", name="Bitcoin", symbol="BTC",
        price=68420.50, change24h=2.45, high24h=69150.00, low24h=66800.00,
        volume24h=28450120000, sentimentScore=74, sentimentLabel="Bullish"
    ),
    "ETH": AssetMetrics(
        id="ETH", name="Ethereum", symbol="ETH",
        price=3482.10, change24h=-1.15, high24h=3590.00, low24h=3420.00,
        volume24h=14210980000, sentimentScore=48, sentimentLabel="Neutral"
    ),
    "SOL": AssetMetrics(
        id="SOL", name="Solana", symbol="SOL",
        price=154.85, change24h=8.68, high24h=156.40, low24h=140.20,
        volume24h=4120550000, sentimentScore=86, sentimentLabel="Bullish"
    ),
    "AAPL": AssetMetrics(
        id="AAPL", name="Apple Inc.", symbol="AAPL",
        price=185.35, change24h=-0.42, high24h=186.95, low24h=184.10,
        volume24h=8930400000, sentimentScore=54, sentimentLabel="Neutral"
    )
}

ARTICLES_DB: Dict[str, List[SentimentArticle]] = {}


def generate_single_article(asset_id: str, timestamp: datetime.datetime) -> SentimentArticle:
    """
    Generates a single randomized mock sentiment article for an asset.

    Args:
        asset_id: The ID of the asset.
        timestamp: Time of creation.

    Returns:
        SentimentArticle object.
    """
    asset = ASSETS_DB[asset_id]
    
    # Decide sentiment label
    rand = random.random()
    if asset.sentimentLabel == "Bullish":
        sentiment = "Bullish" if rand > 0.35 else "Neutral" if rand > 0.15 else "Bearish"
    else:
        sentiment = "Bullish" if rand > 0.6 else "Neutral" if rand > 0.25 else "Bearish"

    pool = ARTICLE_TEMPLATES[sentiment.lower()]
    template = random.choice(pool)

    title = cast(str, template["title"]).replace("{Asset}", asset.name)
    summary = cast(str, template["summary"]).replace("{Asset}", asset.name)
    reasoning = cast(str, template["reasoning"]).replace("{Asset}", asset.name)
    source = random.choice(SOURCES)

    if sentiment == "Bullish":
        sentiment_score = round(0.4 + random.random() * 0.55, 2)
    elif sentiment == "Bearish":
        sentiment_score = round(-0.4 - random.random() * 0.55, 2)
    else:
        sentiment_score = round((random.random() - 0.5) * 0.4, 2)

    return SentimentArticle(
        id=f"art_{random.randint(10000, 99999)}",
        timestamp=timestamp.isoformat(),
        source=source,
        title=title,
        url="#",
        summary=summary,
        sentimentScore=sentiment_score,
        sentimentLabel=sentiment,
        confidence=round(0.75 + random.random() * 0.22, 2),
        keywords=list(template["keywords"]),
        llmReasoning=reasoning
    )


def init_mock_data() -> None:
    """
    Initializes mock articles database with 10 historical articles per asset.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    for asset_id in ASSETS_DB.keys():
        ARTICLES_DB[asset_id] = []
        for i in range(10):
            timestamp = now - datetime.timedelta(minutes=i * 15)
            ARTICLES_DB[asset_id].append(generate_single_article(asset_id, timestamp))


# Run initial mock population
init_mock_data()


async def background_update_loop() -> None:
    """
    Background loop running every 7 seconds to simulate real-time price fluctuations
    and ingest new sentiment news articles.
    """
    import logging
    import json
    logger_obj = logging.getLogger("app")
    
    while True:
        try:
            await asyncio.sleep(7.0)
            now = datetime.datetime.now(datetime.timezone.utc)
            
            for asset_id, asset in ASSETS_DB.items():
                # Add new article
                new_art = generate_single_article(asset_id, now)
                ARTICLES_DB[asset_id].insert(0, new_art)
                if len(ARTICLES_DB[asset_id]) > 50:
                    ARTICLES_DB[asset_id].pop()
                
                # Affect price by sentiment
                change_percent = new_art.sentimentScore * 0.15 * (random.random() + 0.2)
                asset.price = round(asset.price * (1 + change_percent / 100), 2)
                
                # Adjust sentiment index
                asset.sentimentScore = min(100, max(0, int(asset.sentimentScore + new_art.sentimentScore * 6)))
                if asset.sentimentScore > 60:
                    asset.sentimentLabel = "Bullish"
                elif asset.sentimentScore < 40:
                    asset.sentimentLabel = "Bearish"
                else:
                    asset.sentimentLabel = "Neutral"

                # Update 24h metrics
                asset.high24h = max(asset.high24h, asset.price)
                asset.low24h = min(asset.low24h, asset.price)
                asset.change24h = round(asset.change24h + change_percent, 2)
                
            # Log successful tick
            log_data = {"event": "market_tick_simulated", "timestamp": now.timestamp()}
            logger_obj.info(json.dumps(log_data))
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log_data = {"event": "market_tick_failed", "error": str(e)}
            logger_obj.error(json.dumps(log_data))


def get_historical_candles(asset_id: str, timeframe: str) -> List[HistoricalDataPoint]:
    """
    Generates historical price candle details for ECharts overlays based on active timeframe.

    Args:
        asset_id: The ID of the asset (e.g. BTC).
        timeframe: The charts timeframe (1H, 24H, 7D, 30D).

    Returns:
        A list of HistoricalDataPoint objects.
    """
    asset = ASSETS_DB.get(asset_id)
    if not asset:
        return []

    points_count = 60 if timeframe == "1H" else 24 if timeframe == "24H" else 168 if timeframe == "7D" else 30
    step_minutes = 1 if timeframe == "1H" else 60 if timeframe in ("24H", "7D") else 1440
    volatility = 0.015 if asset_id == "SOL" else 0.005 if asset_id == "BTC" else 0.008 if asset_id == "ETH" else 0.003
    
    # Timeframe volatility factors
    vol_factor = volatility * 0.1 if timeframe == "1H" else volatility if timeframe == "24H" else volatility * 2.5 if timeframe == "7D" else volatility * 6
    
    data: List[HistoricalDataPoint] = []
    current_price = asset.price * (1 - asset.change24h / 100)
    base_price = asset.price
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
        open_val = current_price
        close_val = current_price + random_change
        high_val = max(open_val, close_val) + random.random() * (base_price * 0.002)
        low_val = min(open_val, close_val) - random.random() * (base_price * 0.002)
        volume = int(asset.volume24h / points_count * (0.5 + random.random()))
        
        score = min(100, max(0, int(asset.sentimentScore + (random.random() - 0.5) * 20)))

        data.append(HistoricalDataPoint(
            timestamp=ts_str,
            open=round(open_val, 2),
            high=round(high_val, 2),
            low=round(low_val, 2),
            close=round(close_val, 2),
            volume=volume,
            sentimentScore=score
        ))
        current_price = close_val

    # Align last close price to current price
    if data:
        data[-1].close = asset.price

    return data
