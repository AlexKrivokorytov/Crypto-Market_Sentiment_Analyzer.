"""
Service layer for fetching, parsing, and tagging Google News RSS feeds for assets.
Consolidates crypto sweeps into a single unified stream and tags assets dynamically using regex.
"""

import asyncio
import datetime
import email.utils
import hashlib
import logging
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
import httpx

from backend.app.core.database import articles_collection, assets_collection
from backend.app.services.article_scraper import enrich_articles_batch
from backend.app.services.llm import analyze_articles_batch, clean_text
from backend.app.services.sentiment_engine import sentiment_engine

from backend.app.core.config import settings
from backend.app.handlers.config import HANDLER_CONFIG

logger = logging.getLogger("app")


# Precompiled regular expressions for high-performance multi-asset tagging
def _build_asset_regex() -> dict[str, re.Pattern[str]]:
    """Derives per-asset keyword patterns from HANDLER_CONFIG.aliases."""
    regex: dict[str, re.Pattern[str]] = {}
    for cfg in HANDLER_CONFIG:
        asset_id = str(cfg["id"])
        raw_aliases: list[str] = list(cfg.get("aliases", [asset_id.lower()]))
        pattern = r"\b(" + "|".join(re.escape(a) for a in raw_aliases) + r")\b"
        regex[asset_id] = re.compile(pattern, re.IGNORECASE)
    return regex


ASSET_REGEX: dict[str, re.Pattern[str]] = _build_asset_regex()

# Maximum articles processed per sweep to cap blocking time per loop iteration.
MAX_ARTICLES_PER_SWEEP: int = settings.RSS_MAX_ARTICLES_PER_SWEEP
MAX_AAPL_ARTICLES_PER_SWEEP: int = settings.RSS_MAX_AAPL_ARTICLES


def _md5_hash(text: str) -> str:
    """
    Generates a deterministic MD5 hex hash for deduplication keys.
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# Memory buffer: sliding time window for article deduplication storing (timestamp, normalized_title_hash)
_processed_articles_window: List[Tuple[float, str]] = []


def _is_duplicate_in_window(title: str) -> bool:
    """
    Evaluates whether an article title is a duplicate inside a sliding 15-minute window.

    Args:
        title: The raw title headline of the article.

    Returns:
        bool: True if a match is found in the window (and thus duplicate), False otherwise.
    """
    global _processed_articles_window
    now = time.time()
    cutoff = now - 900  # 15 minutes window

    # Clean old items
    _processed_articles_window = [
        (ts, th) for ts, th in _processed_articles_window if ts >= cutoff
    ]

    # Normalize title: lowercase alphanumeric signature
    normalized = "".join(c for c in title.lower() if c.isalnum())
    title_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()

    for _, existing_hash in _processed_articles_window:
        if existing_hash == title_hash:
            return True

    # Register in the sliding window
    _processed_articles_window.append((now, title_hash))
    return False


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
            return str(response.text)

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


async def _apply_sentiment_to_asset(asset_id: str, sentiment_score: float) -> None:
    """
    Applies calculated sentiment shift reactively to the asset metrics (price/sentiment label),
    persists in MongoDB, and broadcasts to active WebSocket subscribers.
    """
    from backend.app.services.websocket_manager import manager as ws_manager

    asset = await assets_collection.find_one({"id": asset_id})
    if not asset:
        return

    # Normalised score from -1.0 to 1.0 mapped to index from 0 to 100
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
    current_price = float(asset.get("price", 100.0))
    new_price = max(0.01, round(current_price * (1 + change_percent / 100), 4))

    high24h = max(float(asset.get("high24h", new_price)), new_price)
    low24h = min(float(asset.get("low24h", new_price)), new_price)
    open_price_today = float(asset.get("openPriceToday", new_price))
    if open_price_today == 0.0:
        open_price_today = new_price
    change24h = round(((new_price - open_price_today) / open_price_today) * 100, 2)

    update_fields = {
        "price": new_price,
        "sentimentScore": new_asset_score,
        "sentimentLabel": new_label,
        "high24h": high24h,
        "low24h": low24h,
        "change24h": change24h,
    }

    await assets_collection.update_one(
        {"id": asset_id},
        {"$set": update_fields},
    )

    # Broadcast updated metrics directly to WebSocket room
    broadcast_doc = {**asset, **update_fields}
    from backend.app.schemas.market import AssetMetrics

    validated = AssetMetrics.model_validate(broadcast_doc).model_dump()
    await ws_manager.broadcast_asset_update(asset_id, validated)


async def process_unified_crypto_feed() -> None:
    """
    Ingests, deduplicates, tags, and evaluates the unified high-frequency crypto feed.
    """
    query = (
        "crypto OR cryptocurrency OR bitcoin OR ethereum OR solana OR toncoin OR ripple OR cardano "
        "OR dogecoin OR polkadot OR chainlink OR avalanche OR polygon OR shiba inu OR litecoin OR uniswap OR cosmos "
        "OR BTC OR ETH OR SOL OR TON OR XRP OR ADA OR DOGE OR DOT OR LINK OR AVAX OR MATIC OR SHIB OR LTC OR UNI OR NEAR OR ATOM"
    )
    xml_content = await fetch_rss_feed(query)
    if not xml_content:
        return

    parsed_items = parse_rss_xml(xml_content)
    new_articles_count = 0

    articles_to_analyze = []
    # To keep track of items that are already processed or cached
    pre_processed_sentiments = {}

    for item in parsed_items[:MAX_ARTICLES_PER_SWEEP]:
        await asyncio.sleep(0.1)

        if _is_duplicate_in_window(item["title"]):
            logger.info("rss_deduplication_hit: title=%r", item["title"])
            continue

        text_signature = f"{item['title']} {item['summary']}".lower()
        matched_assets = [
            aid for aid, pat in ASSET_REGEX.items() if pat.search(text_signature)
        ]

        if not matched_assets:
            continue

        url_hash = _md5_hash(item["url"])
        primary_asset = matched_assets[0]
        primary_id = f"art_{primary_asset}_{url_hash}"

        primary_existing = await articles_collection.find_one({"id": primary_id})

        if primary_existing:
            pre_processed_sentiments[primary_id] = {
                "sentimentScore": primary_existing["sentimentScore"],
                "sentimentLabel": primary_existing["sentimentLabel"],
                "confidence": primary_existing["confidence"],
                "keywords": primary_existing["keywords"],
                "reasoning": primary_existing.get("llmReasoning", ""),
                "is_fallback": primary_existing.get("is_fallback", True),
            }
        else:
            articles_to_analyze.append(
                {
                    "id": primary_id,
                    "asset_symbol": primary_asset,
                    "title": item["title"],
                    "summary": item["summary"],
                    "url_hash": url_hash,
                    "matched_assets": matched_assets,
                    "item": item,
                }
            )

    # Enrich articles with full text before sending to LLM
    if articles_to_analyze:
        articles_to_analyze = await enrich_articles_batch(articles_to_analyze)

    # Batch analysis — LLM now has full article body via `full_text` field
    batch_results = {}
    if articles_to_analyze:
        batch_results = await analyze_articles_batch(articles_to_analyze)

    # Insert into DB
    for data in articles_to_analyze:
        primary_id = data["id"]
        shared_sentiment = batch_results.get(primary_id)
        if not shared_sentiment:
            continue

        item = data["item"]
        # Enforce VADER for chart sentiment while keeping LLM for reasoning
        vader_res = sentiment_engine.analyze_sentiment_local(
            clean_text(item["title"]), clean_text(item["summary"])
        )
        shared_sentiment["sentimentScore"] = vader_res["sentimentScore"]
        shared_sentiment["sentimentLabel"] = vader_res["sentimentLabel"]

        for asset_id in data["matched_assets"]:
            article_id = f"art_{asset_id}_{data['url_hash']}"
            existing = await articles_collection.find_one({"id": article_id})
            if existing:
                continue

            item = data["item"]
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
                "url": item["url"],
                "summary": item["summary"],
                "bodySnippet": data.get("body_snippet", ""),
                "sentimentScore": shared_sentiment["sentimentScore"],
                "sentimentLabel": shared_sentiment["sentimentLabel"],
                "confidence": shared_sentiment["confidence"],
                "keywords": shared_sentiment["keywords"],
                "llmReasoning": shared_sentiment.get("reasoning", ""),
                "is_fallback": shared_sentiment.get("is_fallback", False),
            }
            await articles_collection.insert_one(article_doc)
            new_articles_count += 1
            await _apply_sentiment_to_asset(
                asset_id, shared_sentiment["sentimentScore"]
            )

    if new_articles_count > 0:
        logger.info(
            "rss_unified_crypto_sweep_complete: enqueued=%d", new_articles_count
        )


async def process_aapl_feed() -> None:
    """
    Ingests and processes isolated stock RSS feeds for AAPL.
    """
    query = "Apple stock OR AAPL"
    xml_content = await fetch_rss_feed(query)
    if not xml_content:
        return

    parsed_items = parse_rss_xml(xml_content)
    new_articles_count = 0
    articles_to_analyze = []

    for item in parsed_items[:MAX_AAPL_ARTICLES_PER_SWEEP]:
        await asyncio.sleep(0.1)

        if _is_duplicate_in_window(item["title"]):
            continue

        url_hash = _md5_hash(item["url"])
        article_id = f"art_AAPL_{url_hash}"

        existing = await articles_collection.find_one({"id": article_id})
        if existing:
            continue

        articles_to_analyze.append(
            {
                "id": article_id,
                "asset_symbol": "AAPL",
                "title": item["title"],
                "summary": item["summary"],
                "url_hash": url_hash,
                "item": item,
            }
        )

    batch_results = {}
    if articles_to_analyze:
        batch_results = await analyze_articles_batch(articles_to_analyze)

    for data in articles_to_analyze:
        article_id = data["id"]
        sentiment_data = batch_results.get(article_id)
        if not sentiment_data:
            continue

        item = data["item"]
        # Enforce VADER for chart sentiment while keeping LLM for reasoning
        vader_res = sentiment_engine.analyze_sentiment_local(
            clean_text(item["title"]), clean_text(item["summary"])
        )
        sentiment_data["sentimentScore"] = vader_res["sentimentScore"]
        sentiment_data["sentimentLabel"] = vader_res["sentimentLabel"]

        item = data["item"]
        try:
            ts_dt = datetime.datetime.fromisoformat(item["timestamp"])
        except ValueError:
            ts_dt = datetime.datetime.now(datetime.timezone.utc)

        article_doc = {
            "id": article_id,
            "asset_id": "AAPL",
            "timestamp": item["timestamp"],
            "timestamp_dt": ts_dt,
            "source": item["source"],
            "title": item["title"],
            "url": item["url"],
            "summary": item["summary"],
            "sentimentScore": sentiment_data["sentimentScore"],
            "sentimentLabel": sentiment_data["sentimentLabel"],
            "confidence": sentiment_data["confidence"],
            "keywords": sentiment_data["keywords"],
            "llmReasoning": sentiment_data.get("reasoning", ""),
            "is_fallback": sentiment_data.get("is_fallback", False),
        }
        await articles_collection.insert_one(article_doc)
        new_articles_count += 1

        await _apply_sentiment_to_asset("AAPL", sentiment_data["sentimentScore"])

    if new_articles_count > 0:
        logger.info("rss_aapl_sweep_complete: enqueued=%d", new_articles_count)


async def rss_parser_loop() -> None:
    """
    Background worker loop periodic ingestion.
    Runs unified crypto and isolated AAPL feeds sequentially.
    """
    await asyncio.sleep(5.0)  # Initial boot cooldown

    while True:
        try:
            logger.info("rss_sweep_start")

            # 1. Consolidated crypto sweeps
            await process_unified_crypto_feed()
            await asyncio.sleep(2.0)

            # 2. Apple Inc. isolated sweep
            await process_aapl_feed()

            logger.info("rss_sweep_complete")
            await asyncio.sleep(120.0)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("rss_loop_error: %s", str(exc))
            await asyncio.sleep(60.0)
