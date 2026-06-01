"""
Article body enrichment service.

Resolves Google News redirect URLs and scrapes full article text
using newspaper4k. Designed to run entirely in the background
without blocking the async event loop.

Architecture:
    - All CPU-bound newspaper parsing runs in a thread executor
    - Up to MAX_CONCURRENT fetches run in parallel (semaphore)
    - 8-second hard timeout per article
    - Graceful fallback: returns None on any failure
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


logger = logging.getLogger("app")

# Max parallel scrapes per sweep — keeps Render free-tier RAM stable
_SCRAPE_SEMAPHORE = asyncio.Semaphore(4)
# Hard timeout per article scrape in seconds
_SCRAPE_TIMEOUT: float = 8.0
# Max chars to extract per article body (avoid huge tokens in LLM prompt)
_MAX_BODY_CHARS: int = 2000

# Google News redirect domains — we must resolve the actual URL first
_GOOGLE_REDIRECT_PATTERNS = re.compile(
    r"^https?://(news\.google\.com|newsroom\.google\.com)", re.IGNORECASE
)


async def _resolve_google_redirect(url: str) -> str:
    """
    Follows Google News tracking redirects to find the canonical article URL.

    Google News wraps all links in a redirect through their own domain.
    We do a HEAD request (no body) with follow_redirects=True to resolve it.

    Args:
        url: The raw Google News redirect URL.

    Returns:
        The resolved canonical URL, or the original URL on failure.
    """
    if not _GOOGLE_REDIRECT_PATTERNS.match(url):
        return url
    from backend.app.core.http_client import get_shared_client

    try:
        client = get_shared_client()
        # HEAD requests generally don't need body, follow_redirects can be passed per request or handled manually.
        # httpx client.head supports follow_redirects since httpx 0.20+
        resp = await client.head(url, follow_redirects=True, timeout=5.0)
        resolved = str(resp.url)
        logger.debug("redirect_resolved: original=%s resolved=%s", url, resolved)
        return resolved
    except Exception as exc:
        logger.debug("redirect_resolve_failed: url=%s error=%s", url, str(exc))
        return url


def _parse_article_sync(url: str) -> Optional[str]:
    """
    Synchronously downloads and parses the full article text via newspaper4k.

    This MUST be called inside run_in_executor to avoid blocking the event loop.

    Args:
        url: The resolved canonical article URL.

    Returns:
        Cleaned article body text (up to _MAX_BODY_CHARS), or None on any error.
    """
    try:
        # newspaper4k is an optional dependency; fail gracefully if not installed
        import newspaper  # type: ignore

        article = newspaper.Article(url)
        article.download()
        article.parse()

        text: str = article.text or ""
        if len(text) < 50:
            # Article text too short — likely a paywall or JS-rendered page
            return None

        return text[:_MAX_BODY_CHARS]
    except Exception as exc:
        logger.debug("article_parse_failed: url=%s error=%s", url, str(exc))
        return None


async def scrape_article_body(url: str) -> Optional[str]:
    """
    Asynchronously fetches and returns the full body text of a news article.

    Resolves Google News redirects, then parses the target page using
    newspaper4k in a thread executor to avoid blocking the event loop.
    Returns None if the article cannot be scraped within the timeout.

    Args:
        url: The raw article URL (may be a Google News redirect).

    Returns:
        Cleaned article body text capped at 2000 chars, or None on failure.
    """
    async with _SCRAPE_SEMAPHORE:
        try:
            canonical_url = await _resolve_google_redirect(url)

            # Validate the resolved URL has a proper domain
            parsed = urlparse(canonical_url)
            if not parsed.scheme or not parsed.netloc:
                return None

            loop = asyncio.get_event_loop()
            body = await asyncio.wait_for(
                loop.run_in_executor(None, _parse_article_sync, canonical_url),
                timeout=_SCRAPE_TIMEOUT,
            )

            if body:
                logger.debug(
                    "article_enriched: url=%s chars=%d", canonical_url, len(body)
                )

            return body

        except asyncio.TimeoutError:
            logger.debug("article_scrape_timeout: url=%s", url)
            return None
        except Exception as exc:
            logger.debug("article_scrape_error: url=%s error=%s", url, str(exc))
            return None


async def enrich_articles_batch(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Concurrently enriches a batch of articles with their full body text.

    Each article dict must have an `url` key. The function adds a
    `full_text` key to each article — either the scraped body or the
    existing `summary` field as a fallback.

    Args:
        articles: List of article dicts from the RSS parser.

    Returns:
        The same list with `full_text` populated on each item.
    """
    if not articles:
        return articles

    tasks = [scrape_article_body(art.get("url", "")) for art in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched_count = 0
    for art, result in zip(articles, results):
        if isinstance(result, str) and result:
            art["full_text"] = result
            art["body_snippet"] = result[:400]
            enriched_count += 1
        else:
            # Fall back to RSS summary for LLM context
            art["full_text"] = art.get("summary", art.get("title", ""))
            art["body_snippet"] = ""

    if enriched_count > 0:
        logger.info(
            "article_batch_enriched: total=%d enriched=%d fallback=%d",
            len(articles),
            enriched_count,
            len(articles) - enriched_count,
        )

    return articles
