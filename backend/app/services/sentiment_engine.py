"""
Self-contained, highly optimized local VADER-like Sentiment Engine.
Applies OOP principles to inject lexicons via the dynamic registry.
"""

from backend.app.services.registry import dynamic_registry

import math
import re
from typing import Any, Dict, List, Set


class SentimentEngine:
    """
    Object-oriented sentiment engine.
    Lexicons are loaded dynamically from the registry via the constructor.
    """

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

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self.crypto_lexicon: Dict[str, float] = {}
        self.multi_word_lexicon: Dict[str, float] = {}

    async def reload(self) -> None:
        lexicon = await self.registry.get_lexicon()
        self.crypto_lexicon = lexicon.crypto_lexicon
        self.multi_word_lexicon = lexicon.multi_word_lexicon

    def _is_all_caps(self, text: str) -> bool:
        return text.isupper() and text.isalpha()

    def _tokenize_text(self, text: str) -> List[str]:
        cleaned = text.replace("\n", " ").replace("\r", "")
        cleaned = re.sub(r"([!?])", r" \1 ", cleaned)
        return cleaned.split()

    def _clean_token(self, token: str) -> str:
        return token.strip(".,;:\"'()[]{}*&-+@#%_").lower()

    def _check_multi_word_phrases(self, text: str) -> float:
        score = 0.0
        text_lower = text.lower()
        for phrase, val in self.multi_word_lexicon.items():
            if phrase in text_lower:
                score += val
        return score

    def _calculate_vader_score(self, text: str) -> float:
        tokens = self._tokenize_text(text)
        score: float = 0.0
        for i, token in enumerate(tokens):
            clean = self._clean_token(token)
            if not clean:
                continue
            valence = self.crypto_lexicon.get(clean, 0.0)
            if valence == 0.0:
                continue

            if self._is_all_caps(token) and abs(valence) > 0:
                valence += 0.733 if valence > 0 else -0.733

            preceding = [self._clean_token(tokens[j]) for j in range(max(0, i - 3), i)]
            if any(neg in self.NEGATIONS for neg in preceding):
                valence *= -0.74

            if i > 0:
                prev = self._clean_token(tokens[i - 1])
                valence += valence * self.INCREMENTAL_INTENSIFIERS.get(prev, 0.0)
                valence += valence * self.DECREMENTAL_INTENSIFIERS.get(prev, 0.0)
            score += valence

        lower = text.lower()
        if " but " in lower:
            parts = lower.split(" but ", 1)
            pre_score = self._calculate_vader_score(parts[0])
            post_score = self._calculate_vader_score(parts[1])
            score = pre_score * 0.5 + post_score * 1.5

        return score

    def analyze_sentiment_local(self, title: str, summary: str) -> Dict[str, Any]:
        title_score = self._calculate_vader_score(title)
        summary_score = self._calculate_vader_score(summary)

        title_bonus = self._check_multi_word_phrases(title)
        summary_bonus = self._check_multi_word_phrases(summary)

        title_score += title_bonus
        summary_score += summary_bonus

        combined = (title_score * 2.0 + summary_score) / 3.0

        text_combined = f"{title} {summary}".lower()
        if "unconfirmed" in text_combined or "rumor" in text_combined:
            combined *= 0.5

        norm = combined / math.sqrt(combined**2 + self.ALPHA)
        norm = max(-1.0, min(1.0, norm))

        if norm >= 0.15:
            label = "Bullish"
        elif norm <= -0.15:
            label = "Bearish"
        else:
            label = "Neutral"

        intensity = abs(norm)
        confidence = 0.5 + (intensity * 0.4)

        words = re.findall(r" [a-zA-Z-]+ ", text_combined)
        keywords = list(
            set(
                [
                    w
                    for w in words
                    if w in self.crypto_lexicon or w in self.multi_word_lexicon
                ]
            )
        )[:5]
        if not keywords:
            keywords = ["crypto"]

        return {
            "sentimentScore": round(norm, 2),
            "sentimentLabel": label,
            "confidence": round(confidence, 2),
            "keywords": keywords[:3],
            "reasoning": "VADER fallback generated sentiment based on lexicon matches.",
        }


sentiment_engine = SentimentEngine(dynamic_registry)
