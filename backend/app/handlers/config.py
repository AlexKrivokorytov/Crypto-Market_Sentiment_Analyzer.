"""
Single source of truth for all tracked assets.

To add a new asset (e.g. DOT, DOGE, AVAX), append one dict here.
No other file needs to change.

Keys for "crypto" type:
    type:          "crypto"
    id:            Ticker symbol used throughout the system.
    name:          Human-readable display name.
    coingecko_id:  CoinGecko /coins/markets identifier.
    base_price:    Seed fallback price in USD (updated by the live feed on first tick).
    volatility:    Per-tick sigma for the GBM market simulator.
    seed_volume:   Approximate 24-hour trading volume for initial DB seeding.
    seed_sentiment: Initial sentiment score 0–100.

Keys for "stock" type:
    type:             "stock"
    id:               Ticker symbol.
    name:             Human-readable display name.
    yfinance_ticker:  Exact ticker string used by yfinance.
    base_price:       Seed fallback price in USD.
    volatility:       Per-tick sigma for the GBM market simulator.
    seed_volume:      Approximate 24-hour trading volume for initial DB seeding.
    seed_sentiment:   Initial sentiment score 0–100.
"""

from typing import Any

HANDLER_CONFIG: list[dict[str, Any]] = [
    # ── Crypto assets ──────────────────────────────────────────────────────
    {
        "type": "crypto",
        "id": "BTC",
        "name": "Bitcoin",
        "coingecko_id": "bitcoin",
        "base_price": 68_420.50,
        "volatility": 0.005,
        "seed_volume": 28_450_120_000,
        "seed_sentiment": 74,
    },
    {
        "type": "crypto",
        "id": "ETH",
        "name": "Ethereum",
        "coingecko_id": "ethereum",
        "base_price": 3_482.10,
        "volatility": 0.008,
        "seed_volume": 14_210_980_000,
        "seed_sentiment": 48,
    },
    {
        "type": "crypto",
        "id": "SOL",
        "name": "Solana",
        "coingecko_id": "solana",
        "base_price": 154.85,
        "volatility": 0.015,
        "seed_volume": 4_120_550_000,
        "seed_sentiment": 86,
    },
    {
        "type": "crypto",
        "id": "TON",
        "name": "Toncoin",
        "coingecko_id": "the-open-network",
        "base_price": 6.20,
        "volatility": 0.012,
        "seed_volume": 350_000_000,
        "seed_sentiment": 62,
    },
    {
        "type": "crypto",
        "id": "XRP",
        "name": "Ripple",
        "coingecko_id": "ripple",
        "base_price": 0.52,
        "volatility": 0.010,
        "seed_volume": 980_000_000,
        "seed_sentiment": 50,
    },
    {
        "type": "crypto",
        "id": "ADA",
        "name": "Cardano",
        "coingecko_id": "cardano",
        "base_price": 0.45,
        "volatility": 0.010,
        "seed_volume": 380_000_000,
        "seed_sentiment": 50,
    },
    # ── Stock / ETF assets ─────────────────────────────────────────────────
    {
        "type": "stock",
        "id": "AAPL",
        "name": "Apple Inc.",
        "yfinance_ticker": "AAPL",
        "base_price": 185.35,
        "volatility": 0.003,
        "seed_volume": 8_930_400_000,
        "seed_sentiment": 54,
    },
    {
        "type": "crypto",
        "id": "DOGE",
        "name": "Dogecoin",
        "coingecko_id": "dogecoin",
        "base_price": 0.1425,
        "volatility": 0.022,
        "seed_volume": 1_250_000_000,
        "seed_sentiment": 65,
    },
    {
        "type": "crypto",
        "id": "DOT",
        "name": "Polkadot",
        "coingecko_id": "polkadot",
        "base_price": 7.20,
        "volatility": 0.014,
        "seed_volume": 250_000_000,
        "seed_sentiment": 50,
    },
    {
        "type": "crypto",
        "id": "LINK",
        "name": "Chainlink",
        "coingecko_id": "chainlink",
        "base_price": 16.50,
        "volatility": 0.016,
        "seed_volume": 350_000_000,
        "seed_sentiment": 58,
    },
    {
        "type": "crypto",
        "id": "AVAX",
        "name": "Avalanche",
        "coingecko_id": "avalanche-2",
        "base_price": 36.80,
        "volatility": 0.018,
        "seed_volume": 450_000_000,
        "seed_sentiment": 52,
    },
    {
        "type": "crypto",
        "id": "MATIC",
        "name": "Polygon",
        "coingecko_id": "matic-network",
        "base_price": 0.7250,
        "volatility": 0.018,
        "seed_volume": 300_000_000,
        "seed_sentiment": 50,
    },
    {
        "type": "crypto",
        "id": "SHIB",
        "name": "Shiba Inu",
        "coingecko_id": "shiba-inu",
        "base_price": 0.00002450,
        "volatility": 0.028,
        "seed_volume": 850_000_000,
        "seed_sentiment": 60,
    },
    {
        "type": "crypto",
        "id": "LTC",
        "name": "Litecoin",
        "coingecko_id": "litecoin",
        "base_price": 82.50,
        "volatility": 0.012,
        "seed_volume": 420_000_000,
        "seed_sentiment": 48,
    },
    {
        "type": "crypto",
        "id": "UNI",
        "name": "Uniswap",
        "coingecko_id": "uniswap",
        "base_price": 7.80,
        "volatility": 0.018,
        "seed_volume": 220_000_000,
        "seed_sentiment": 54,
    },
    {
        "type": "crypto",
        "id": "NEAR",
        "name": "Near Protocol",
        "coingecko_id": "near",
        "base_price": 6.85,
        "volatility": 0.020,
        "seed_volume": 340_000_000,
        "seed_sentiment": 70,
    },
    {
        "type": "crypto",
        "id": "ATOM",
        "name": "Cosmos",
        "coingecko_id": "cosmos",
        "base_price": 8.40,
        "volatility": 0.015,
        "seed_volume": 180_000_000,
        "seed_sentiment": 50,
    },
    # ── Add new assets below — zero other files need editing ───────────────
    # {
    #     "type": "crypto",
    #     "id": "DOT",
    #     "name": "Polkadot",
    #     "coingecko_id": "polkadot",
    #     "base_price": 7.50,
    #     "volatility": 0.012,
    #     "seed_volume": 300_000_000,
    #     "seed_sentiment": 50,
    # },
]
