"""
Tests for AssetHandlerFactory and HANDLER_CONFIG.

Validates:
  - Factory bootstraps without error.
  - All expected asset IDs are registered.
  - Handler types match config entries.
  - get() returns correct handler.
  - get() raises KeyError for unknown assets.
  - to_seed_document() produces valid MongoDB-ready docs.
  - Adding a new HANDLER_CONFIG entry is the only change needed (OCP).
"""

import pytest

from backend.app.handlers.config import HANDLER_CONFIG
from backend.app.handlers.crypto_handler import CryptoHandler
from backend.app.handlers.factory import AssetHandlerFactory
from backend.app.handlers.stock_handler import StockHandler


@pytest.fixture()
def factory() -> AssetHandlerFactory:
    """Returns a freshly bootstrapped factory for each test."""
    f = AssetHandlerFactory()
    f.bootstrap()
    return f


# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap correctness
# ──────────────────────────────────────────────────────────────────────────────


def test_factory_bootstrap_registers_all_assets(factory: AssetHandlerFactory) -> None:
    """Every entry in HANDLER_CONFIG must appear as a registered handler."""
    expected_ids = {cfg["id"] for cfg in HANDLER_CONFIG}
    assert set(factory.asset_ids()) == expected_ids


def test_factory_len_matches_config(factory: AssetHandlerFactory) -> None:
    assert len(factory) == len(HANDLER_CONFIG)


def test_factory_bootstrap_is_idempotent() -> None:
    """Calling bootstrap() twice should not raise and should yield identical state."""
    f = AssetHandlerFactory()
    f.bootstrap()
    first_ids = f.asset_ids()
    f.bootstrap()
    assert f.asset_ids() == first_ids


# ──────────────────────────────────────────────────────────────────────────────
# Handler type dispatch
# ──────────────────────────────────────────────────────────────────────────────


def test_crypto_handlers_are_crypto_type(factory: AssetHandlerFactory) -> None:
    crypto_configs = [c for c in HANDLER_CONFIG if c["type"] == "crypto"]
    for cfg in crypto_configs:
        handler = factory.get(cfg["id"])
        assert isinstance(handler, CryptoHandler), (
            f"Expected CryptoHandler for {cfg['id']}, got {type(handler)}"
        )


def test_stock_handlers_are_stock_type(factory: AssetHandlerFactory) -> None:
    stock_configs = [c for c in HANDLER_CONFIG if c["type"] == "stock"]
    for cfg in stock_configs:
        handler = factory.get(cfg["id"])
        assert isinstance(handler, StockHandler), (
            f"Expected StockHandler for {cfg['id']}, got {type(handler)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# get() / all() API
# ──────────────────────────────────────────────────────────────────────────────


def test_get_known_asset_returns_handler(factory: AssetHandlerFactory) -> None:
    handler = factory.get("BTC")
    assert handler.asset_id == "BTC"
    assert handler.name == "Bitcoin"


def test_get_unknown_asset_raises_key_error(factory: AssetHandlerFactory) -> None:
    with pytest.raises(KeyError, match="DOGE"):
        factory.get("DOGE")


def test_all_returns_list_of_handlers(factory: AssetHandlerFactory) -> None:
    handlers = factory.all()
    assert isinstance(handlers, list)
    assert len(handlers) == len(HANDLER_CONFIG)


def test_iteration_over_factory(factory: AssetHandlerFactory) -> None:
    ids = [h.asset_id for h in factory]
    assert set(ids) == {cfg["id"] for cfg in HANDLER_CONFIG}


# ──────────────────────────────────────────────────────────────────────────────
# Seed document generation
# ──────────────────────────────────────────────────────────────────────────────


def test_seed_document_has_required_keys(factory: AssetHandlerFactory) -> None:
    required_keys = {
        "id",
        "name",
        "symbol",
        "price",
        "change24h",
        "high24h",
        "low24h",
        "volume24h",
        "sentimentScore",
        "sentimentLabel",
        "openPriceToday",
        "lastDayReset",
    }
    for handler in factory.all():
        doc = handler.to_seed_document()
        missing = required_keys - set(doc.keys())
        assert not missing, f"{handler.asset_id}: missing keys {missing}"


def test_seed_document_price_equals_base_price(factory: AssetHandlerFactory) -> None:
    for handler in factory.all():
        doc = handler.to_seed_document()
        assert doc["price"] == handler.base_price
        assert doc["openPriceToday"] == handler.base_price


def test_seed_document_change24h_is_zero(factory: AssetHandlerFactory) -> None:
    for handler in factory.all():
        doc = handler.to_seed_document()
        assert doc["change24h"] == 0.0


def test_seed_document_sentiment_label_mapping(factory: AssetHandlerFactory) -> None:
    """High seed_sentiment → Bullish, low → Bearish, mid → Neutral."""
    for handler in factory.all():
        doc = handler.to_seed_document()
        score = handler.seed_sentiment
        label = doc["sentimentLabel"]
        if score >= 60:
            assert label == "Bullish", f"{handler.asset_id}: expected Bullish"
        elif score <= 40:
            assert label == "Bearish", f"{handler.asset_id}: expected Bearish"
        else:
            assert label == "Neutral", f"{handler.asset_id}: expected Neutral"


# ──────────────────────────────────────────────────────────────────────────────
# Unknown handler type in config (Open/Closed validation)
# ──────────────────────────────────────────────────────────────────────────────


def test_unknown_handler_type_raises_value_error() -> None:
    """bootstrap() must raise ValueError for any unrecognised handler type."""
    f = AssetHandlerFactory()
    bad_config = [{"type": "futures", "id": "BAD", "name": "Bad Asset"}]

    # Patch inside the factory module — that is where bootstrap() reads the list
    import backend.app.handlers.factory as factory_module

    original = factory_module.HANDLER_CONFIG
    factory_module.HANDLER_CONFIG = bad_config
    try:
        with pytest.raises(ValueError, match="unknown handler type"):
            f.bootstrap()
    finally:
        factory_module.HANDLER_CONFIG = original
