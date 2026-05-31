"""
Unit tests for the consolidated dynamic multi-asset tagged RSS parser in services/parser.py.
"""

from unittest.mock import AsyncMock, patch
import pytest

from backend.app.services.parser import parse_rss_xml, process_unified_crypto_feed

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Google News search: BTC and ETH</title>
    <item>
      <title>Bitcoin surges but Ethereum lags behind - Bloomberg</title>
      <link>https://example.com/btc-eth-news</link>
      <pubDate>Thu, 28 May 2026 12:00:00 GMT</pubDate>
      <description>General details outlining Bitcoin surge while Ethereum remains consolidation range.</description>
      <source>Bloomberg</source>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_xml() -> None:
    """
    Asserts standard Google News RSS XML maps correctly to structured dictionaries.
    """
    items = parse_rss_xml(SAMPLE_RSS_XML)
    assert len(items) == 1
    assert items[0]["title"] == "Bitcoin surges but Ethereum lags behind - Bloomberg"
    assert items[0]["source"] == "Bloomberg"
    assert items[0]["url"] == "https://example.com/btc-eth-news"


@pytest.mark.anyio
@patch("backend.app.services.parser.fetch_rss_feed", new_callable=AsyncMock)
@patch("backend.app.services.parser.articles_collection")
@patch("backend.app.services.parser.assets_collection")
@patch("backend.app.services.parser.analyze_articles_batch", new_callable=AsyncMock)
@patch(
    "backend.app.services.websocket_manager.manager.broadcast_asset_update",
    new_callable=AsyncMock,
)
async def test_process_unified_crypto_feed_multi_tag(
    mock_broadcast: AsyncMock,
    mock_analyze: AsyncMock,
    mock_assets_coll: AsyncMock,
    mock_articles_coll: AsyncMock,
    mock_fetch: AsyncMock,
) -> None:
    """
    Verifies that a single article mentioning both BTC and ETH is duplicated
    and saved with idempotent unique IDs, triggering respective pricing changes and broadcasts.
    """
    mock_fetch.return_value = SAMPLE_RSS_XML

    # Configure AsyncMock methods for MongoDB collections
    mock_articles_coll.find_one = AsyncMock(return_value=None)
    mock_articles_coll.insert_one = AsyncMock(return_value=None)

    mock_assets_coll.update_one = AsyncMock(return_value=None)
    mock_assets_coll.find_one = AsyncMock(
        side_effect=lambda q: {
            "id": q["id"],
            "price": 100.0,
            "sentimentScore": 50,
            "sentimentLabel": "Neutral",
            "openPriceToday": 100.0,
            "lastDayReset": "2026-05-28T00:00:00Z",
        }
    )

    # Mock sentiment engine responses
    mock_analyze.return_value = {
        "art_BTC_8e9892e5c4706019c8b14fc62ede7bc3": {
            "sentimentScore": 0.45,
            "sentimentLabel": "Bullish",
            "confidence": 0.85,
            "keywords": ["bitcoin", "ethereum"],
            "reasoning": "VADER analysis computed.",
            "fallback": False,
        }
    }

    # Execute dynamic feed sweeper
    await process_unified_crypto_feed()

    # Assertions
    # 1. Fetch RSS was invoked once
    mock_fetch.assert_called_once()

    # 2. Sentiments parsed and analyzed once (for the primary asset context, BTC) and reused for ETH
    assert mock_analyze.call_count == 1
    mock_analyze.assert_called_once()

    # 3. Two articles successfully persisted with custom idempotent composite primary keys
    assert mock_articles_coll.insert_one.call_count == 2

    inserted_docs = [
        args[0][0] for args in mock_articles_coll.insert_one.call_args_list
    ]
    assert any(doc["id"].startswith("art_BTC_") for doc in inserted_docs)
    assert any(doc["id"].startswith("art_ETH_") for doc in inserted_docs)

    # 4. Broadcasted WebSocket updates sent to both rooms BTC and ETH
    assert mock_broadcast.call_count == 2
