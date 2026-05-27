/** Discriminated union of all valid asset ticker symbols tracked by the backend. */
export type RouteAssetId = 'BTC' | 'ETH' | 'SOL' | 'AAPL'

/** Sentiment classification label produced by the LLM analysis engine. */
export type SentimentLabel = 'Bullish' | 'Bearish' | 'Neutral'

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
}
