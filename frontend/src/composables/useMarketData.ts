import { useQuery } from '@tanstack/vue-query'
import { computed, Ref } from 'vue'
import { marketApi } from '../services/api'
import { AssetMetrics, HistoricalDataPoint, SentimentArticle } from '../types/market'

/**
 * Fetches and auto-refreshes the complete list of tracked assets with current price
 * and sentiment metrics. Polls the backend every 10 seconds to reflect live price ticks.
 */
export function useAssets() {
  return useQuery<AssetMetrics[]>({
    queryKey: ['assets'],
    queryFn: () => marketApi.getAssets(),
    refetchInterval: 10000,
    staleTime: 9000,
  })
}

/**
 * Fetches real-time metrics for a single asset by its ID (e.g. "BTC").
 * Polling is disabled when `assetId` is empty.
 *
 * @param assetId - Reactive or static asset identifier string.
 */
export function useAssetById(assetId: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))
  
  return useQuery<AssetMetrics | null>({
    queryKey: ['asset', idRef],
    queryFn: () => marketApi.getAssetById(idRef.value),
    refetchInterval: 10000,
    staleTime: 9000,
    enabled: computed(() => !!idRef.value),
  })
}

/**
 * Fetches historical candlestick price and sentiment overlay data for a given asset
 * and timeframe. Refetches every 45 seconds to keep chart data current.
 *
 * @param assetId - Reactive or static asset identifier string.
 * @param timeframe - Reactive or static timeframe selector (1H | 24H | 7D | 30D).
 */
export function useHistoricalData(assetId: Ref<string> | string, timeframe: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))
  const tfRef = computed(() => (typeof timeframe === 'string' ? timeframe : timeframe.value))

  return useQuery<HistoricalDataPoint[]>({
    queryKey: ['historical', idRef, tfRef],
    queryFn: () => marketApi.getHistoricalData(idRef.value, tfRef.value),
    refetchInterval: 45000,
    staleTime: 40000,
    enabled: computed(() => !!idRef.value && !!tfRef.value),
  })
}

/**
 * Fetches the list of recent news articles analyzed by the LLM for a given asset.
 * Polls every 30 seconds to surface newly ingested RSS feed articles.
 *
 * @param assetId - Reactive or static asset identifier string.
 */
export function useSentimentArticles(assetId: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))

  return useQuery<SentimentArticle[]>({
    queryKey: ['articles', idRef],
    queryFn: () => marketApi.getArticles(idRef.value),
    refetchInterval: 30000,
    staleTime: 25000,
    enabled: computed(() => !!idRef.value),
  })
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
  })
}
