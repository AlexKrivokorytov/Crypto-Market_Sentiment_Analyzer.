const BASE_URL = 'http://localhost:8000/api/v1';
export const marketApi = {
    /**
     * Fetches the list of all supported assets with their current metrics.
     *
     * @returns A promise resolving to an array of AssetMetrics.
     * @throws An error if the request fails.
     */
    async getAssets() {
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
    async getAssetById(id) {
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
    async getHistoricalData(assetId, timeframe) {
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
    async getArticles(assetId) {
        const response = await fetch(`${BASE_URL}/assets/${assetId}/sentiment`);
        if (!response.ok) {
            throw new Error(`Failed to fetch articles: id=${assetId} status=${response.status}`);
        }
        return response.json();
    },
    /**
     * Fetches the backend's active LLM configuration — model name and whether a live
     * endpoint is configured. Used to display status in the sidebar footer.
     *
     * @returns A promise resolving to llm_configured flag and llm_model name.
     * @throws An error if the request fails.
     */
    async getConfig() {
        const response = await fetch(`${BASE_URL}/config`);
        if (!response.ok) {
            throw new Error(`Failed to fetch config: status=${response.status}`);
        }
        return response.json();
    }
};
