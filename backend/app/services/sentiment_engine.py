"""
Self-contained, highly optimized local VADER-like Sentiment Engine.
Implements token valence scaling, negation checking, capitalizations, adverbs intensifiers,
exclamation/question weighting, and contractive 'BUT' splits without remote dataset downloads.
"""

import math
import re
from typing import Any, Dict, List, Set

# Custom specialized crypto-native vocabulary mapping concepts to valence scores (-4.0 to 4.0)
CRYPTO_LEXICON: Dict[str, float] = {
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
}

# Improved VADER Lexicon with Multi-Word Phrases
MULTI_WORD_LEXICON: Dict[str, float] = {
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

# Add standard lexicon additions
CRYPTO_LEXICON.update({
    "scam": -4.0,
    "fud": -2.5,
    "fomo": 2.5,
    "rekt": -3.0,
    "unconfirmed": -0.5,
    "rumor": -0.5,
    "speculation": 0.0,
})

def _check_multi_word_phrases(text: str) -> float:
    score = 0.0
    text_lower = text.lower()
    for phrase, val in MULTI_WORD_LEXICON.items():
        if phrase in text_lower:
            score += val
    return score

NEGATIONS: Set[str] = {
    "not",
    "never",
    "no",
    "without",
    "didnt",
    "cant",
    "wont",
    "neither",
    "nor",
    "lack",
    "dont",
    "wasnt",
    "arent",
    "shouldnt",
    "wouldnt",
    "couldnt",
    "hadnt",
    "hasnt",
    "havent",
}

INCREMENTAL_INTENSIFIERS: Dict[str, float] = {
    "very": 0.292,
    "extremely": 0.350,
    "massively": 0.350,
    "highly": 0.292,
    "incredibly": 0.350,
    "super": 0.250,
    "supremely": 0.350,
    "really": 0.250,
    "quite": 0.150,
    "much": 0.150,
    "substantially": 0.292,
}

DECREMENTAL_INTENSIFIERS: Dict[str, float] = {
    "barely": -0.292,
    "slightly": -0.200,
    "partially": -0.200,
    "somewhat": -0.200,
    "minor": -0.200,
    "little": -0.200,
    "hardly": -0.292,
}

ALPHA: float = 15.0


def _is_all_caps(text: str) -> bool:
    """
    Checks if a token is completely capitalized, ignoring numerical signatures.
    """
    return text.isupper() and text.isalpha()


def _tokenize_text(text: str) -> List[str]:
    """
    Splits text into cleaned lowercase tokens for dictionary matching,
    while preserving trailing characters if they represent punctuation cues.
    """
    # Remove emojis or characters that do not serve grammar weighting
    cleaned = text.replace("\n", " ").replace("\r", "")
    # Maintain space around !, ? to capture trailing tags
    cleaned = re.sub(r"([!?])", r" \1 ", cleaned)
    tokens = cleaned.split()
    return tokens


def _clean_token(token: str) -> str:
    """
    Removes standard punctuation marks around a token, leaving it lowercase.
    """
    cleaned = token.strip(".,;:\"'()[]{}*&-+@#%_").lower()
    return cleaned


def analyze_sentiment_local(title: str, summary: str) -> Dict[str, Any]:
    """
    Evaluates text using the improved local VADER engine.
    Applies 2x weighting to the title and incorporates multi-word phrase detection.
    """
    title_score = _calculate_vader_score(title)
    summary_score = _calculate_vader_score(summary)

    # Multi-word phrase bonuses
    title_bonus = _check_multi_word_phrases(title)
    summary_bonus = _check_multi_word_phrases(summary)

    title_score += title_bonus
    summary_score += summary_bonus

    # Title carries 2x weight relative to summary
    combined = (title_score * 2.0 + summary_score) / 3.0

    # Dampening logic
    text_combined = f"{title} {summary}".lower()
    if "unconfirmed" in text_combined or "rumor" in text_combined:
        combined *= 0.5

    # Normalize to -1.0 to 1.0 safely
    norm = combined / math.sqrt(combined**2 + ALPHA)
    # Clip between -1.0 and 1.0
    norm = max(-1.0, min(1.0, norm))

    if norm >= 0.15:
        label = "Bullish"
    elif norm <= -0.15:
        label = "Bearish"
    else:
        label = "Neutral"

    # Derive confidence based on intensity
    intensity = abs(norm)
    confidence = 0.5 + (intensity * 0.4)

    # Extract keywords
    words = re.findall(r"[a-zA-Z-]+", text_combined)
    keywords = list(set([w for w in words if w in CRYPTO_LEXICON or w in MULTI_WORD_LEXICON])[:5])
    if not keywords:
        keywords = ["crypto"]

    return {
        "sentimentScore": round(norm, 2),
        "sentimentLabel": label,
        "confidence": round(confidence, 2),
        "keywords": keywords[:3],
        "reasoning": "VADER fallback generated sentiment based on lexicon matches.",
    }
