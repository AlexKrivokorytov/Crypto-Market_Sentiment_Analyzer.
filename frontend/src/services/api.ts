import { AssetMetrics, HistoricalDataPoint, SentimentArticle } from '../types/market';

const BASE_URL = 'http://localhost:8000/api/v1';

export const marketApi = {
  /**
   * Fetches the list of all supported assets with their current metrics.
   * 
   * @returns A promise resolving to an array of AssetMetrics.
   * @throws An error if the request fails.
   */
  async getAssets(): Promise<AssetMetrics[]> {
    const response = await fetch(`${BASE_URL}/assets`);
    if (!response.ok) {
      throw new Error(`Failed to fetch assets: status=${response.status}`);
    }
    return response.json();
  },

  /**
   * Fetches current metrics (price, daily range, sentiment score) for a single asset.
   * 
   * @param id The unique identifier of the asset (e.g. BTC).
   * @returns A promise resolving to the AssetMetrics or null if not found.
   * @throws An error if the request fails.
   */
  async getAssetById(id: string): Promise<AssetMetrics | null> {
    const response = await fetch(`${BASE_URL}/assets/${id}/metrics`);
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`Failed to fetch asset metrics: id=${id} status=${response.status}`);
    }
    return response.json();
  },

  /**
   * Fetches historical candlestick price data overlaid with sentiment score over time.
   * 
   * @param assetId The unique identifier of the asset (e.g. BTC).
   * @param timeframe The charts timeframe (1H, 24H, 7D, 30D).
   * @returns A promise resolving to an array of HistoricalDataPoints.
   * @throws An error if the request fails.
   */
  async getHistoricalData(assetId: string, timeframe: string): Promise<HistoricalDataPoint[]> {
    const response = await fetch(`${BASE_URL}/assets/${assetId}/historical?timeframe=${timeframe}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch historical data: id=${assetId} timeframe=${timeframe} status=${response.status}`);
    }
    return response.json();
  },

  /**
   * Fetches the recent news articles processed by the LLM for a single asset.
   * 
   * @param assetId The unique identifier of the asset (e.g. BTC).
   * @returns A promise resolving to an array of SentimentArticles.
   * @throws An error if the request fails.
   */
  async getArticles(assetId: string): Promise<SentimentArticle[]> {
    const response = await fetch(`${BASE_URL}/assets/${assetId}/sentiment`);
    if (!response.ok) {
      throw new Error(`Failed to fetch articles: id=${assetId} status=${response.status}`);
    }
    return response.json();
  }
};
