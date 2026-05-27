import { useQuery } from '@tanstack/vue-query';
import { computed } from 'vue';
import { marketApi } from '../services/api';
/**
 * Fetches and auto-refreshes the complete list of tracked assets with current price
 * and sentiment metrics. Polls the backend every 7 seconds to reflect live price ticks.
 */
export function useAssets() {
    return useQuery({
        queryKey: ['assets'],
        queryFn: () => marketApi.getAssets(),
        refetchInterval: 7000,
        staleTime: 6500,
    });
}
/**
 * Fetches real-time metrics for a single asset by its ID (e.g. "BTC").
 * Polling is disabled when `assetId` is empty.
 *
 * @param assetId - Reactive or static asset identifier string.
 */
export function useAssetById(assetId) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    return useQuery({
        queryKey: ['asset', idRef],
        queryFn: () => marketApi.getAssetById(idRef.value),
        refetchInterval: 7000,
        staleTime: 6500,
        enabled: computed(() => !!idRef.value),
    });
}
/**
 * Fetches historical candlestick price and sentiment overlay data for a given asset
 * and timeframe. Refetches every 7 seconds to keep chart data current.
 *
 * @param assetId - Reactive or static asset identifier string.
 * @param timeframe - Reactive or static timeframe selector (1H | 24H | 7D | 30D).
 */
export function useHistoricalData(assetId, timeframe) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    const tfRef = computed(() => (typeof timeframe === 'string' ? timeframe : timeframe.value));
    return useQuery({
        queryKey: ['historical', idRef, tfRef],
        queryFn: () => marketApi.getHistoricalData(idRef.value, tfRef.value),
        refetchInterval: 7000,
        staleTime: 6500,
        enabled: computed(() => !!idRef.value && !!tfRef.value),
    });
}
/**
 * Fetches the list of recent news articles analyzed by the LLM for a given asset.
 * Polls every 7 seconds to surface newly ingested RSS feed articles.
 *
 * @param assetId - Reactive or static asset identifier string.
 */
export function useSentimentArticles(assetId) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    return useQuery({
        queryKey: ['articles', idRef],
        queryFn: () => marketApi.getArticles(idRef.value),
        refetchInterval: 7000,
        staleTime: 6500,
        enabled: computed(() => !!idRef.value),
    });
}
/**
 * Fetches backend configuration including the active LLM model name and whether
 * a live LLM endpoint is configured. Result is cached indefinitely (no polling).
 */
export function useBackendConfig() {
    return useQuery({
        queryKey: ['config'],
        queryFn: () => marketApi.getConfig(),
        staleTime: Infinity,
    });
}
