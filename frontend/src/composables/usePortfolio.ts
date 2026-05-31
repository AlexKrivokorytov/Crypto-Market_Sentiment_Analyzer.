import { useStorage } from '@vueuse/core'
import type { RouteAssetId } from '@/types/market'

export interface PortfolioPosition {
  asset_id: RouteAssetId
  quantity: number
  avg_buy_price: number
}

// Client-side portfolio stored in localStorage
export function usePortfolio() {
  const positions = useStorage<PortfolioPosition[]>('quant-hud-portfolio', [
    { asset_id: 'BTC', quantity: 0.15, avg_buy_price: 45000 },
    { asset_id: 'ETH', quantity: 1.5, avg_buy_price: 2200 },
  ])

  function upsertPosition(assetId: RouteAssetId, quantity: number, avgBuyPrice: number) {
    const existing = positions.value.find(p => p.asset_id === assetId)
    if (existing) {
      existing.quantity = quantity
      existing.avg_buy_price = avgBuyPrice
    } else {
      positions.value.push({ asset_id: assetId, quantity, avg_buy_price: avgBuyPrice })
    }
  }

  function deletePosition(assetId: RouteAssetId) {
    positions.value = positions.value.filter(p => p.asset_id !== assetId)
  }

  return {
    positions,
    upsertPosition,
    deletePosition,
  }
}
