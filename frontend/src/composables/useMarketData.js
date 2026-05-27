import { useQuery } from '@tanstack/vue-query';
import { computed } from 'vue';
import { marketApi } from '../services/api';
/**
 * Fetches and auto-refreshes the complete list of tracked assets with current price
 * and sentiment metrics. Polls the backend every 10 seconds to reflect live price ticks.
 */
export function useAssets() {
    return useQuery({
        queryKey: ['assets'],
        queryFn: () => marketApi.getAssets(),
        refetchInterval: 10000,
        staleTime: 9000,
    });
}
/**
 * Fetches real-time metrics for a single asset by its ticker ID (e.g. 'BTC').
 * Polling is disabled when `assetId` resolves to an empty string.
 *
 * @param assetId - Reactive or static asset ticker (RouteAssetId | string).
 * @returns TanStack Query result including `data`, `isLoading`, `isError`, and `refetch`.
 */
export function useAssetById(assetId) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    return useQuery({
        queryKey: ['asset', idRef],
        queryFn: () => marketApi.getAssetById(idRef.value),
        refetchInterval: 10000,
        staleTime: 9000,
        retry: 1,
        enabled: computed(() => !!idRef.value),
    });
}
/**
 * Fetches historical OHLCV candlestick data overlaid with LLM sentiment score.
 * Refetches every 45 seconds to keep the chart aligned with the current price.
 *
 * @param assetId - Reactive or static asset ticker.
 * @param timeframe - Reactive or static timeframe selector ('1H' | '24H' | '7D' | '30D').
 * @returns TanStack Query result including `data`, `isLoading`, `isError`, and `refetch`.
 */
export function useHistoricalData(assetId, timeframe) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    const tfRef = computed(() => (typeof timeframe === 'string' ? timeframe : timeframe.value));
    return useQuery({
        queryKey: ['historical', idRef, tfRef],
        queryFn: () => marketApi.getHistoricalData(idRef.value, tfRef.value),
        refetchInterval: 45000,
        staleTime: 40000,
        retry: 1,
        enabled: computed(() => !!idRef.value && !!tfRef.value),
    });
}
/**
 * Fetches the most recent RSS-ingested news articles with LLM sentiment scores
 * for a given asset. Polls every 30 seconds to surface newly processed articles.
 *
 * @param assetId - Reactive or static asset ticker.
 * @returns TanStack Query result including `data`, `isLoading`, `isError`, and `refetch`.
 */
export function useSentimentArticles(assetId) {
    const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value));
    return useQuery({
        queryKey: ['articles', idRef],
        queryFn: () => marketApi.getArticles(idRef.value),
        refetchInterval: 30000,
        staleTime: 25000,
        retry: 1,
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
