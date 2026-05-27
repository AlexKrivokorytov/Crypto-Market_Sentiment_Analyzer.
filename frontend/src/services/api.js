const BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`;
/**
 * Centralized fetch wrapper that normalizes all HTTP error responses into thrown
 * Error instances, making TanStack Query's `isError` flag work reliably.
 *
 * @param url - Absolute URL to request.
 * @returns Parsed JSON body typed as T.
 * @throws Error with status code and URL on any non-2xx response.
 */
async function apiFetch(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`API request failed: status=${response.status} url=${url}`);
    }
    return response.json();
}
export const marketApi = {
    /**
     * Fetches the list of all supported assets with their current price and sentiment metrics.
     *
     * @returns A promise resolving to an array of AssetMetrics.
     * @throws Error if the network request fails or the server returns a non-2xx status.
     */
    getAssets() {
        return apiFetch(`${BASE_URL}/assets`);
    },
    /**
     * Fetches current price and sentiment metrics for a single asset by its ticker ID.
     * Returns null when the backend responds with 404 (asset not found).
     *
     * @param id - Ticker symbol of the asset (e.g. 'BTC', 'ETH').
     * @returns A promise resolving to AssetMetrics or null if the asset is not found.
     * @throws Error if the network request fails or the server returns a non-2xx, non-404 status.
     */
    async getAssetById(id) {
        const response = await fetch(`${BASE_URL}/assets/${id}/metrics`);
        if (response.status === 404)
            return null;
        if (!response.ok) {
            throw new Error(`API request failed: status=${response.status} url=${BASE_URL}/assets/${id}/metrics`);
        }
        return response.json();
    },
    /**
     * Fetches historical OHLCV candlestick data overlaid with LLM sentiment score for
     * the given asset and timeframe.
     *
     * @param assetId - Ticker symbol of the asset (e.g. 'BTC').
     * @param timeframe - Chart timeframe selector ('1H' | '24H' | '7D' | '30D').
     * @returns A promise resolving to an array of HistoricalDataPoint objects.
     * @throws Error if the network request fails or the server returns a non-2xx status.
     */
    getHistoricalData(assetId, timeframe) {
        return apiFetch(`${BASE_URL}/assets/${assetId}/historical?timeframe=${timeframe}`);
    },
    /**
     * Fetches the most recent news articles processed by the LLM sentiment engine
     * for a given asset.
     *
     * @param assetId - Ticker symbol of the asset (e.g. 'BTC').
     * @returns A promise resolving to an array of SentimentArticle objects.
     * @throws Error if the network request fails or the server returns a non-2xx status.
     */
    getArticles(assetId) {
        return apiFetch(`${BASE_URL}/assets/${assetId}/sentiment`);
    },
    /**
     * Fetches backend runtime configuration: active LLM model name and whether a live
     * LLM API endpoint is configured. Result is meant to be cached indefinitely (no polling).
     *
     * @returns A promise resolving to the LLM configuration object.
     * @throws Error if the network request fails or the server returns a non-2xx status.
     */
    getConfig() {
        return apiFetch(`${BASE_URL}/config`);
    },
};
