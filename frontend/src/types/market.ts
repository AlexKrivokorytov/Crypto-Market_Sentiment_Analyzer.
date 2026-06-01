export type RouteAssetId = 'BTC' | 'ETH' | 'SOL' | 'AAPL' | 'TON' | 'XRP' | 'ADA' | 'DOGE' | 'DOT' | 'LINK' | 'AVAX' | 'MATIC' | 'SHIB' | 'LTC' | 'UNI' | 'NEAR' | 'ATOM' | (string & {})

/** Sentiment classification label produced by the LLM analysis engine. */
export type SentimentLabel = 'Bullish' | 'Bearish' | 'Neutral'

/** Alert condition trigger types. */
export type AlertConditionType = 'PRICE_ABOVE' | 'PRICE_BELOW' | 'SENTIMENT_CHANGE'

export interface AssetMetrics {
  id: RouteAssetId
  name: string
  symbol: string
  price: number
  change24h: number
  high24h: number
  low24h: number
  volume24h: number
  /** Aggregated sentiment index in the range 0–100. */
  sentimentScore: number
  sentimentLabel: SentimentLabel
  /** Opening price at the start of today (UTC), used for change24h calculation. */
  openPriceToday: number
  /** ISO 8601 timestamp when openPriceToday was last reset. */
  lastDayReset: string
}

export interface OrderBookImbalance {
  asset_id: string
  bids_volume: number
  asks_volume: number
  buy_pressure_percentage: number
}


export interface HistoricalDataPoint {
  /** Human-readable timestamp label used as the x-axis category on the chart. */
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  /** Sentiment index snapshot at this candle, range 0–100. */
  sentimentScore: number
}

export interface SentimentArticle {
  id: string
  timestamp: string
  source: string
  title: string
  url: string
  summary: string
  /** Raw LLM sentiment score in the range -1.0 (bearish) to +1.0 (bullish). */
  sentimentScore: number
  sentimentLabel: SentimentLabel
  /** Model confidence for the sentiment classification, range 0.0–1.0. */
  confidence: number
  keywords: string[]
  llmReasoning: string
  is_fallback: boolean
}

export interface UserPublic {
  id: string
  email: string
  display_name: string
  watchlist: string[]
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  user: UserPublic
}

export interface AlertCondition {
  id: string
  asset_id: string
  condition: AlertConditionType
  target_value: number
  triggered: boolean
}

export interface PortfolioPosition {
  asset_id: string
  asset_name: string
  quantity: number
  avg_buy_price: number
  current_price: number
  pnl_usd: number
  pnl_pct: number
}

/** WebSocket push message for live asset price updates. */
export interface AssetUpdateMessage {
  type: 'asset_update'
  asset: AssetMetrics
}

export interface RegistryAssetConfig {
  id: string
  type: string
  name: string
  aliases: string[]
  coingecko_id: string | null
  yfinance_ticker: string | null
  base_price: number
  volatility: number
  seed_volume: number
  seed_sentiment: number
  is_active: boolean
  is_in_heatmap: boolean
  order: number
}

export interface LexiconConfig {
  id: string
  crypto_lexicon: Record<string, number>
  multi_word_lexicon: Record<string, number>
}
