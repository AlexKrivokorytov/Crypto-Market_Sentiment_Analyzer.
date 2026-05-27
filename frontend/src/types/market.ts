export type SentimentLabel = 'Bullish' | 'Bearish' | 'Neutral';

export interface AssetMetrics {
  id: string;
  name: string;
  symbol: string;
  price: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: number;
  sentimentScore: number; // 0 to 100 index
  sentimentLabel: SentimentLabel;
}

export interface HistoricalDataPoint {
  timestamp: string; // ISO or human-readable
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sentimentScore: number; // 0 to 100 sentiment score index
}

export interface SentimentArticle {
  id: string;
  timestamp: string;
  source: string;
  title: string;
  url: string;
  summary: string;
  sentimentScore: number; // -1.0 to 1.0
  sentimentLabel: SentimentLabel;
  confidence: number; // 0.0 to 1.0
  keywords: string[];
  llmReasoning: string;
}

