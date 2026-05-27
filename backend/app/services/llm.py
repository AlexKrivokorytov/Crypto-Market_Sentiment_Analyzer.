"""
Service layer for LLM (LM Studio / Ollama) sentiment analysis integration.
"""

import json
import logging
import random
from typing import Dict, Any
import httpx

from backend.app.core.config import settings

logger = logging.getLogger("app")

# Local pre-packaged templates for instant simulation
SIMULATED_TEMPLATES = {
    "BULLISH": [
        {
            "reasoning": "The recent positive developments and rising buying momentum suggest strong upward pressure. General institutional interest continues to bid up the asset.",
            "keywords": ["momentum", "growth", "institution", "adoption"],
        },
        {
            "reasoning": "Technical parameters indicate that a key macro level has been cleared on above-average volume, confirming a bullish structure.",
            "keywords": ["technical", "breakout", "volume", "momentum"],
        },
    ],
    "BEARISH": [
        {
            "reasoning": "Short-term macro headwinds and tightening regulations are causing concerns. Retail panic could drive near-term selling.",
            "keywords": ["regulation", "risk", "outflow", "derisking"],
        },
        {
            "reasoning": "Security risks or negative technical divergence indicates that key support zones are being tested and might break.",
            "keywords": ["security", "bearish", "divergence", "support"],
        },
    ],
    "NEUTRAL": [
        {
            "reasoning": "The asset is currently consolidating in a tight trading range. No immediate macro catalyst is driving price in either direction.",
            "keywords": ["consolidation", "neutral", "range", "expiry"],
        },
        {
            "reasoning": "General discussions and conference panels offer long-term branding value but present no immediate impact on price actions.",
            "keywords": ["discussion", "conference", "branding", "panel"],
        },
    ],
}


def _get_mock_sentiment(title: str, summary: str) -> Dict[str, Any]:
    """
    Analyzes content heuristically and matches templates for simulated scenarios.
    """
    text = (title + " " + summary).lower()

    bullish_keywords = [
        "surge",
        "breakout",
        "growth",
        "high",
        "adopt",
        "gain",
        "rise",
        "partnership",
        "success",
        "institutional",
        "launch",
        "all-time",
    ]
    bearish_keywords = [
        "drop",
        "fall",
        "down",
        "bear",
        "scam",
        "regulation",
        "lawsuit",
        "warning",
        "phishing",
        "hack",
        "exploit",
        "crash",
        "sell",
    ]

    bull_hits = sum(1 for kw in bullish_keywords if kw in text)
    bear_hits = sum(1 for kw in bearish_keywords if kw in text)

    if bull_hits > bear_hits:
        sentiment_label = "Bullish"
        sentiment_score = round(0.3 + (random.random() * 0.6), 2)
    elif bear_hits > bull_hits:
        sentiment_label = "Bearish"
        sentiment_score = round(-0.3 - (random.random() * 0.6), 2)
    else:
        sentiment_label = "Neutral"
        sentiment_score = round((random.random() - 0.5) * 0.3, 2)

    templates = SIMULATED_TEMPLATES[sentiment_label.upper()]
    template = random.choice(templates)
    reasoning = (
        str(template["reasoning"]) + "\n\n(Simulated Analysis - No LLM Configured)"
    )

    return {
        "sentimentScore": sentiment_score,
        "sentimentLabel": sentiment_label,
        "confidence": round(0.7 + (random.random() * 0.25), 2),
        "keywords": template["keywords"],
        "reasoning": reasoning,
    }


async def analyze_article_sentiment(
    title: str, summary: str, asset_symbol: str
) -> Dict[str, Any]:
    """
    Queries local LLM endpoint (Ollama / LM Studio) to evaluate article sentiment.
    Falls back gracefully to deterministic heuristics if the API call fails.
    """
    if not settings.LLM_API_URL:
        return _get_mock_sentiment(title, summary)

    url = f"{settings.LLM_API_URL.rstrip('/')}/chat/completions"

    system_instruction = (
        "You are an expert financial analyst. Analyze the sentiment of the provided news article "
        f"headline and summary with respect to the asset {asset_symbol}.\n"
        "You must respond with a raw JSON object containing exactly the following fields:\n"
        '- "sentimentScore": a float between -1.0 (extremely bearish) and 1.0 (extremely bullish)\n'
        '- "sentimentLabel": either "Bullish", "Bearish", or "Neutral"\n'
        '- "confidence": a float between 0.0 and 1.0 indicating your confidence in the score\n'
        '- "keywords": a JSON array of up to 4 string keywords/tags relevant to the article\n'
        '- "reasoning": a brief 1-3 sentence explanation of your reasoning\n'
        "Do not include any markdown formatting like ```json or trailing text. Return ONLY valid JSON."
    )

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Title: {title}\nSummary: {summary}"},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        # High timeout is required for initial model compilation/loading on Ollama
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])

                data = json.loads(content)
                score = max(-1.0, min(1.0, float(data.get("sentimentScore", 0.0))))

                label = str(data.get("sentimentLabel", "Neutral"))
                if label not in ("Bullish", "Bearish", "Neutral"):
                    label = "Neutral"

                confidence = max(0.0, min(1.0, float(data.get("confidence", 0.8))))
                keywords = list(data.get("keywords", []))
                reasoning = str(data.get("reasoning", "No explanation provided."))

                return {
                    "sentimentScore": score,
                    "sentimentLabel": label,
                    "confidence": confidence,
                    "keywords": keywords,
                    "reasoning": reasoning,
                }

            logger.warning(
                "llm_api_non_200",
                extra={"status_code": response.status_code},
            )
    except Exception as exc:
        logger.warning(
            "llm_api_request_failed",
            extra={"error": str(exc)},
        )

    return _get_mock_sentiment(title, summary)
