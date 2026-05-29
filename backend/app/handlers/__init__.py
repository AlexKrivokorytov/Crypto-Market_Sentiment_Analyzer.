"""
Asset handler package.

Provides the Factory Pattern for per-asset data retrieval:
  - BaseAssetHandler — abstract contract
  - CryptoHandler   — CoinGecko / Alchemy integration
  - StockHandler    — yfinance integration
  - AssetHandlerFactory — registry & dispatch
  - HANDLER_CONFIG  — single source of truth for tracked assets
"""
