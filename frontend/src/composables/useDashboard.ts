import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import type { Ref } from 'vue'
import { marketApi } from '@/services/api'
import type { AssetMetrics, HistoricalDataPoint, SentimentArticle, RouteAssetId } from '@/types/market'

/**
 * Centrally manages TanStack server-state queries specifically for the dashboard widgets,
 * decoupling views and components from direct API requests and caching setups.
 */

/**
 * Fetches and polls the complete list of tracked assets with current prices.
 */
export function useAssetsQuery() {
  return useQuery<AssetMetrics[]>({
    queryKey: ['assets'],
    queryFn: () => marketApi.getAssets(),
    refetchInterval: 10000,
    staleTime: 9000,
  })
}

/**
 * Fetches latest ingested RSS articles with LLM VADER sentiment scores for a given asset ID.
 */
export function useSentimentQuery(assetId: Ref<RouteAssetId | string> | RouteAssetId | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))

  return useQuery<SentimentArticle[]>({
    queryKey: ['articles', idRef],
    queryFn: () => marketApi.getArticles(idRef.value),
    refetchInterval: 30000,
    staleTime: 25000,
    retry: 1,
    enabled: computed(() => !!idRef.value),
  })
}

/**
 * Fetches historical OHLCV candles overlaid with aggregated sentiment.
 */
export function useHistoricalQuery(
  assetId: Ref<RouteAssetId | string> | RouteAssetId | string,
  timeframe: Ref<string> | string,
) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))
  const tfRef = computed(() => (typeof timeframe === 'string' ? timeframe : timeframe.value))

  return useQuery<HistoricalDataPoint[]>({
    queryKey: ['historical', idRef, tfRef],
    queryFn: () => marketApi.getHistoricalData(idRef.value, tfRef.value),
    refetchInterval: 45000,
    staleTime: 40000,
    retry: 1,
    enabled: computed(() => !!idRef.value && !!tfRef.value),
  })
}
