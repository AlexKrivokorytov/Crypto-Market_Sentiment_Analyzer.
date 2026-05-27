import { useQuery } from '@tanstack/vue-query'
import { computed, Ref } from 'vue'
import { marketApi } from '../services/api'
import { AssetMetrics, HistoricalDataPoint, SentimentArticle } from '../types/market'

export function useAssets() {
  return useQuery<AssetMetrics[]>({
    queryKey: ['assets'],
    queryFn: () => marketApi.getAssets(),
    refetchInterval: 7000,
    staleTime: 6500,
  })
}

export function useAssetById(assetId: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))
  
  return useQuery<AssetMetrics | null>({
    queryKey: ['asset', idRef],
    queryFn: () => marketApi.getAssetById(idRef.value),
    refetchInterval: 7000,
    staleTime: 6500,
    enabled: computed(() => !!idRef.value),
  })
}

export function useHistoricalData(assetId: Ref<string> | string, timeframe: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))
  const tfRef = computed(() => (typeof timeframe === 'string' ? timeframe : timeframe.value))

  return useQuery<HistoricalDataPoint[]>({
    queryKey: ['historical', idRef, tfRef],
    queryFn: () => marketApi.getHistoricalData(idRef.value, tfRef.value),
    refetchInterval: 7000,
    staleTime: 6500,
    enabled: computed(() => !!idRef.value && !!tfRef.value),
  })
}

export function useSentimentArticles(assetId: Ref<string> | string) {
  const idRef = computed(() => (typeof assetId === 'string' ? assetId : assetId.value))

  return useQuery<SentimentArticle[]>({
    queryKey: ['articles', idRef],
    queryFn: () => marketApi.getArticles(idRef.value),
    refetchInterval: 7000,
    staleTime: 6500,
    enabled: computed(() => !!idRef.value),
  })
}
