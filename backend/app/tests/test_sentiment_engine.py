"""
Unit tests for the custom, self-contained local VADER-like Sentiment Engine.
"""

from backend.app.services.sentiment_engine import sentiment_engine


def test_vader_basic_scores() -> None:
    """
    Asserts basic classification labels and score directions for bullish/bearish/neutral items.
    """
    # Bullish headline
    res = sentiment_engine.analyze_sentiment_local(
        "Massive listing breakout", "Bitcoin rallies to new highs"
    )
    assert res["sentimentScore"] > 0.05
    assert res["sentimentLabel"] == "Bullish"

    # Bearish headline
    res = sentiment_engine.analyze_sentiment_local(
        "Major rugpull scam", "Hackers stolen millions in exploit"
    )
    assert res["sentimentScore"] < -0.05
    assert res["sentimentLabel"] == "Bearish"

    # Neutral headline
    res = sentiment_engine.analyze_sentiment_local(
        "Bitcoin consolidation continues", "Trading ranges narrow ahead of weekend"
    )
    assert -0.05 < res["sentimentScore"] < 0.05
    assert res["sentimentLabel"] == "Neutral"


def test_vader_negations() -> None:
    """
    Asserts that negation prefixes shift the valence index direction successfully.
    """
    # "not bullish" should switch to negative/bearish
    res = sentiment_engine.analyze_sentiment_local(
        "Bitcoin is not bullish today", "Fears rise"
    )
    assert res["sentimentScore"] < 0.0


def test_vader_intensifiers() -> None:
    """
    Asserts that adverbs scale the sentiment scoring absolute magnitude correctly.
    """
    # "very bullish" should be stronger than just "bullish"
    res_base = sentiment_engine.analyze_sentiment_local(
        "Solana is bullish", "Activity grows"
    )
    res_strong = sentiment_engine.analyze_sentiment_local(
        "Solana is very bullish", "Activity grows"
    )
    assert abs(res_strong["sentimentScore"]) > abs(res_base["sentimentScore"])

    # "slightly bearish" should be weaker than just "bearish"
    res_base_bear = sentiment_engine.analyze_sentiment_local(
        "Solana is bearish", "Activity falls"
    )
    res_weak_bear = sentiment_engine.analyze_sentiment_local(
        "Solana is slightly bearish", "Activity falls"
    )
    assert abs(res_weak_bear["sentimentScore"]) < abs(res_base_bear["sentimentScore"])


def test_vader_contrastive_but() -> None:
    """
    Asserts that contrastive splits weigh segments properly, prioritizing post-but clauses.
    """
    # Sentiment after 'but' carries 1.5x weight, while pre-but is dampened (*0.5)
    res = sentiment_engine.analyze_sentiment_local(
        "Breakout listing, but major rugpull scam exploit", "Activity drops"
    )
    assert res["sentimentScore"] < -0.05


def test_vader_boundaries() -> None:
    """
    Asserts that normalisation limits compound scores strictly to [-1.0, 1.0] under heavy loads.
    """
    # Massively highly charged positive text should not exceed 1.0 compound score
    res = sentiment_engine.analyze_sentiment_local(
        "MASSIVE BULLISH ATH BREAKOUT UPGRADE !!! ATH ATH MOON approve Listing !!! SUPER SUCCESS !!!",
        "Bullish rally soaring skyrocket breakout very highly Approved massively secured growth",
    )
    assert -1.0 <= res["sentimentScore"] <= 1.0
