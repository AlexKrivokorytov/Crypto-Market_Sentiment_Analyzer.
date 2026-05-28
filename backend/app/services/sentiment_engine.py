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
    Evaluates text valence using self-contained token analysis and VADER scaling.
    Operates in microseconds, fully thread-safe, and 100% local.

    Args:
        title: The headline title of the article.
        summary: The summary or body of the article.

    Returns:
        Dict containing sentimentScore, sentimentLabel, confidence, keywords, and reasoning.
    """
    combined_text = f"{title} {summary}"
    tokens = _tokenize_text(combined_text)

    if not tokens:
        return {
            "sentimentScore": 0.0,
            "sentimentLabel": "Neutral",
            "confidence": 0.8,
            "keywords": [],
            "reasoning": "Text stream empty. Returned default neutral score.",
        }

    # Count exclamation marks and question marks for overall intensity adjustments
    exclamation_count = sum(1 for t in tokens if t == "!")
    question_count = sum(1 for t in tokens if t == "?")

    # Detect if the whole text is in ALL CAPS. If so, capitalization boosts are disabled.
    all_text_caps = combined_text.isupper()

    # Pre-split sentences around contrastive conjunction 'but'
    # Conjunction 'but' shifts valence: pre-but is dampened (*0.5), post-but is boosted (*1.5)
    # Note: Only the FIRST occurrence of 'but' is used for contrastive dampening.
    # Multiple 'but' clauses (e.g. "crashed but recovered but crashed") are intentionally
    # simplified to avoid over-engineering the MVP. Only the first pivot matters most.
    but_idx = -1
    for i, token in enumerate(tokens):
        if _clean_token(token) == "but":
            but_idx = i
            break

    scores: List[float] = []
    matched_keywords: Set[str] = set()

    for i, token in enumerate(tokens):
        cleaned = _clean_token(token)

        # Check if the word exists in our specialized crypto-lexicon
        if cleaned in CRYPTO_LEXICON:
            valence = CRYPTO_LEXICON[cleaned]
            matched_keywords.add(cleaned)

            # 1. Capitalization boost: increase valence magnitude by 0.733 if token is in ALL CAPS
            # (only if the whole sentence is not all caps)
            if not all_text_caps and _is_all_caps(token):
                if valence > 0:
                    valence += 0.733
                else:
                    valence -= 0.733

            # 2. Negation shift: check the preceding 2 tokens for negation words
            negated = False
            for step in range(1, 3):
                if i - step >= 0:
                    prev_cleaned = _clean_token(tokens[i - step])
                    # If there's a contrastive punctuation or another booster in between, stop checking negations
                    if prev_cleaned in [",", ";", ".", "!", "?"]:
                        break
                    if prev_cleaned in NEGATIONS:
                        negated = True
                        break
            if negated:
                valence *= -0.74

            # 3. Adverb intensifiers check: inspect the immediate predecessor
            if i - 1 >= 0:
                prev_word = _clean_token(tokens[i - 1])
                if prev_word in INCREMENTAL_INTENSIFIERS:
                    boost = INCREMENTAL_INTENSIFIERS[prev_word]
                    if valence > 0:
                        valence += boost
                    else:
                        valence -= boost
                elif prev_word in DECREMENTAL_INTENSIFIERS:
                    dampen = DECREMENTAL_INTENSIFIERS[prev_word]
                    if valence > 0:
                        valence += dampen  # dampen is negative
                    else:
                        valence -= dampen

            # 4. Contrastive BUT split check
            if but_idx != -1:
                if i < but_idx:
                    valence *= 0.5
                elif i > but_idx:
                    valence *= 1.5

            scores.append(valence)

    sum_valence = sum(scores)

    # 5. Exclamation marks boost: adds up to 0.876 of valence intensity
    if exclamation_count > 0:
        boost = min(exclamation_count, 3) * 0.292
        if sum_valence > 0:
            sum_valence += boost
        elif sum_valence < 0:
            sum_valence -= boost

    # 6. Apply VADER normalization to bring score strictly into [-1.0, 1.0]
    if sum_valence == 0:
        compound = 0.0
    else:
        compound = sum_valence / math.sqrt(sum_valence**2 + ALPHA)

    # 7. Question mark penalty: questions indicate uncertainty, dampen score absolute magnitude
    if question_count > 0:
        compound *= 0.85

    # Safe boundaries rounding
    compound = round(max(-1.0, min(1.0, compound)), 4)

    # Map score to label
    if compound >= 0.05:
        label = "Bullish"
    elif compound <= -0.05:
        label = "Bearish"
    else:
        label = "Neutral"

    # Compute custom deterministic classification confidence based on match density
    matched_count = len(scores)
    density = matched_count / len(tokens) if tokens else 0
    confidence = min(0.95, max(0.60, round(0.70 + density * 0.5, 2)))

    reasoning = (
        f"Deterministic local VADER-like compound score of {compound} computed successfully. "
        f"Analyzed {len(tokens)} tokens, found {matched_count} matches in specialized crypto-lexicon."
    )

    return {
        "sentimentScore": compound,
        "sentimentLabel": label,
        "confidence": confidence,
        "keywords": sorted(list(matched_keywords))[:4],
        "reasoning": reasoning,
    }
