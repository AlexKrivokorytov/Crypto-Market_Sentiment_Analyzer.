import { useQuery } from '@tanstack/vue-query';
import { computed } from 'vue';
import { marketApi } from '../services/api';
export function useAssets() {
    return useQuery({
        queryKey: ['assets'],
        queryFn: () => marketApi.getAssets(),
        refetchInterval: 7000,
        staleTime: 6500,
    });
}
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
