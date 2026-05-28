"""
Unit tests for the Web3 Alchemy/Toncenter on-chain metric feeds in services/price_feed.py.
"""

from unittest.mock import patch, MagicMock
import pytest
from backend.app.services.price_feed import fetch_onchain_metrics


@pytest.mark.anyio
@patch("backend.app.services.price_feed.httpx.AsyncClient")
async def test_fetch_onchain_metrics_fallbacks_and_limits(
    mock_client_class: MagicMock,
) -> None:
    """
    Verifies that fetch_onchain_metrics correctly maps non-crypto or unsupported assets to empty profiles,
    and returns correct bounded fallback metrics when keys or connections fail.
    """
    # 1. Non-crypto asset (AAPL) or unmapped (BTC) should return an empty profile immediately
    res_aapl = await fetch_onchain_metrics("AAPL")
    assert res_aapl == {}

    res_btc = await fetch_onchain_metrics("BTC")
    assert res_btc == {}

    # 2. Active crypto assets should return valid, bounded fallback structures on network failure
    res_eth = await fetch_onchain_metrics("ETH")
    assert "gasPrice" in res_eth
    assert "txVolume1h" in res_eth
    assert 15.0 <= res_eth["gasPrice"] <= 30.0
    assert 4000 <= res_eth["txVolume1h"] <= 5500

    res_sol = await fetch_onchain_metrics("SOL")
    assert "gasPrice" in res_sol
    assert "txVolume1h" in res_sol
    assert 0.00005 <= res_sol["gasPrice"] <= 0.0002
    assert 120000 <= res_sol["txVolume1h"] <= 180000

    res_ton = await fetch_onchain_metrics("TON")
    assert "gasPrice" in res_ton
    assert "txVolume1h" in res_ton
    assert 0.002 <= res_ton["gasPrice"] <= 0.0035
    assert 7000 <= res_ton["txVolume1h"] <= 11000
