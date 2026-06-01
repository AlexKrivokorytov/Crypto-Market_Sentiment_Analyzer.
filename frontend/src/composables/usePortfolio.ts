import { computed } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { portfolioApi } from '@/services/api'
import { useAuthStore } from '@/composables/useAuthStore'
import type { PortfolioPosition } from '@/types/market'

export function usePortfolio() {
  const authStore = useAuthStore()
  const queryClient = useQueryClient()

  const { data: positions, isLoading, isError } = useQuery<PortfolioPosition[]>({
    queryKey: ['portfolio'],
    queryFn: () => portfolioApi.getPortfolio(),
    enabled: computed(() => authStore.isAuthenticated),
    staleTime: 30_000,
    initialData: [],
  })

  const upsertMutation = useMutation({
    mutationFn: ({ assetId, quantity, avgBuyPrice }: {
      assetId: string; quantity: number; avgBuyPrice: number
    }) => portfolioApi.upsertPosition(assetId, quantity, avgBuyPrice),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (assetId: string) => portfolioApi.deletePosition(assetId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
  })

  return {
    positions: computed(() => positions.value ?? []),
    isLoading,
    isError,
    isSubmitting: computed(
      () => upsertMutation.isPending.value || deleteMutation.isPending.value
    ),
    upsertPosition: (assetId: string, qty: number, avgBuy: number) =>
      upsertMutation.mutate({ assetId, quantity: qty, avgBuyPrice: avgBuy }),
    deletePosition: (assetId: string) => deleteMutation.mutate(assetId),
  }
}
