"""
Service layer for fetching and parsing Google News RSS feeds for assets.
"""

import asyncio
import datetime
import email.utils
import hashlib
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import httpx

from backend.app.core.database import articles_collection, assets_collection
from backend.app.services.llm import analyze_article_sentiment

logger = logging.getLogger("app")

ASSET_QUERIES: Dict[str, str] = {
    "BTC": "Bitcoin OR BTC",
    "ETH": "Ethereum OR ETH",
    "SOL": "Solana OR SOL",
    "AAPL": "Apple stock OR AAPL",
}


def _md5_hash(text: str) -> str:
    """
    Generates a deterministic MD5 hex hash for deduplication keys.
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# Global reusable HTTP client to leverage connection pooling and keep-alive
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Returns a shared singleton instance of AsyncClient for connection reuse.
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def fetch_rss_feed(query: str) -> Optional[str]:
    """
    Retrieves the search-based RSS feed from Google News for the specified query.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        client = get_http_client()
        response = await client.get(url)
        if response.status_code == 200:
            return response.text

        logger.warning(
            "rss_fetch_failed",
            extra={"query": query, "status_code": response.status_code},
        )
    except Exception as exc:
        logger.error(
            "rss_fetch_error",
            extra={"query": query, "error": str(exc)},
        )

    return None


def parse_rss_xml(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parses Google News RSS XML payload and extracts structured items.
    """
    articles: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        if channel is None:
            return articles

        for item in channel.findall("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")
            desc_el = item.find("description")
            source_el = item.find("source")

            title = title_el.text if title_el is not None and title_el.text else ""
            link = link_el.text if link_el is not None and link_el.text else ""
            desc = desc_el.text if desc_el is not None and desc_el.text else ""

            # Extract plain text from description or fallback to title
            summary = desc if desc else title
            if "<" in summary:
                try:
                    summary = "".join(
                        ET.fromstring(f"<span>{summary}</span>").itertext()
                    )
                except Exception:
                    summary = title

            # Extract publisher source
            source = "Google News"
            if source_el is not None and source_el.text:
                source = source_el.text
            elif " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    title = parts[0]
                    source = parts[1]

            # Parse RFC 822 publication date
            pub_date_str = (
                pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""
            )
            timestamp = datetime.datetime.now(datetime.timezone.utc)
            if pub_date_str:
                try:
                    parsed_dt = email.utils.parsedate_to_datetime(pub_date_str)
                    if parsed_dt:
                        timestamp = parsed_dt
                except Exception:
                    pass

            articles.append(
                {
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source": source,
                    "timestamp": timestamp.isoformat(),
                    "timestamp_dt": timestamp,
                }
            )
    except Exception as exc:
        logger.error("rss_xml_parse_error", extra={"error": str(exc)})

    return articles


async def process_rss_feed_for_asset(asset_id: str) -> None:
    """
    Ingests and processes the latest RSS feed articles for a given asset ticker.
    Determines sentiment using the LLM engine and persists updates.
    """
    query = ASSET_QUERIES.get(asset_id)
    if not query:
        return

    xml_content = await fetch_rss_feed(query)
    if not xml_content:
        return

    parsed_items = parse_rss_xml(xml_content)
    new_articles_count = 0

    for item in parsed_items[:3]:
        article_url = item["url"]
        article_id = f"art_{_md5_hash(article_url)}"

        existing = await articles_collection.find_one({"id": article_id})
        if existing:
            continue

        sentiment_data = await analyze_article_sentiment(
            title=item["title"], summary=item["summary"], asset_symbol=asset_id
        )

        # Parse the ISO timestamp string back into a datetime for the TTL index field
        try:
            ts_dt = datetime.datetime.fromisoformat(item["timestamp"])
        except ValueError:
            ts_dt = datetime.datetime.now(datetime.timezone.utc)

        article_doc = {
            "id": article_id,
            "asset_id": asset_id,
            "timestamp": item["timestamp"],
            "timestamp_dt": ts_dt,
            "source": item["source"],
            "title": item["title"],
            "url": article_url,
            "summary": item["summary"],
            "sentimentScore": sentiment_data["sentimentScore"],
            "sentimentLabel": sentiment_data["sentimentLabel"],
            "confidence": sentiment_data["confidence"],
            "keywords": sentiment_data["keywords"],
            "llmReasoning": sentiment_data["reasoning"],
        }

        await articles_collection.insert_one(article_doc)
        new_articles_count += 1

        # Adjust price and sentiment indices reactively based on news results
        asset = await assets_collection.find_one({"id": asset_id})
        if asset:
            sentiment_score = sentiment_data["sentimentScore"]
            mapped_score = int((sentiment_score + 1.0) * 50)

            # Move metrics dynamically (20% weight per new article)
            current_score = asset.get("sentimentScore", 50)
            new_asset_score = int(current_score * 0.8 + mapped_score * 0.2)
            new_asset_score = max(0, min(100, new_asset_score))

            if new_asset_score > 60:
                new_label = "Bullish"
            elif new_asset_score < 40:
                new_label = "Bearish"
            else:
                new_label = "Neutral"

            # Apply price impact formula: higher sentiment index pushes prices up
            change_percent = sentiment_score * 0.25
            current_price = asset.get("price", 100.0)
            new_price = max(0.01, round(current_price * (1 + change_percent / 100), 2))

            high24h = max(float(asset.get("high24h", new_price)), new_price)
            low24h = min(float(asset.get("low24h", new_price)), new_price)
            open_price_today = float(asset.get("openPriceToday", new_price))
            if open_price_today == 0.0:
                open_price_today = new_price
            change24h = round(
                ((new_price - open_price_today) / open_price_today) * 100, 2
            )

            await assets_collection.update_one(
                {"id": asset_id},
                {
                    "$set": {
                        "price": new_price,
                        "sentimentScore": new_asset_score,
                        "sentimentLabel": new_label,
                        "high24h": high24h,
                        "low24h": low24h,
                        "change24h": change24h,
                    }
                },
            )

    if new_articles_count > 0:
        logger.info(
            "rss_sweep_ingested",
            extra={"asset_id": asset_id, "count": new_articles_count},
        )


async def rss_parser_loop() -> None:
    """
    Background worker loop pulling Google News updates periodically.
    """
    await asyncio.sleep(5.0)  # Initial boot cooldown

    while True:
        try:
            logger.info("rss_sweep_start")
            for asset_id in ASSET_QUERIES.keys():
                await process_rss_feed_for_asset(asset_id)
                await asyncio.sleep(2.0)  # Sequential delay to avoid rate limits

            logger.info("rss_sweep_complete")
            await asyncio.sleep(60.0)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("rss_loop_error", extra={"error": str(exc)})
            await asyncio.sleep(60.0)
