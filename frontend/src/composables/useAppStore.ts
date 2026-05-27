import { ref } from 'vue'
import { defineStore } from 'pinia'

export type Timeframe = '1H' | '24H' | '7D' | '30D';

export const useAppStore = defineStore('app', () => {
  const selectedAssetId = ref<string>('BTC')
  const timeframe = ref<Timeframe>('24H')
  const sidebarCollapsed = ref<boolean>(false)

  const setAsset = (assetId: string) => {
    selectedAssetId.value = assetId
  }

  const setTimeframe = (newTimeframe: Timeframe) => {
    timeframe.value = newTimeframe
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    selectedAssetId,
    timeframe,
    sidebarCollapsed,
    setAsset,
    setTimeframe,
    toggleSidebar
  }
})
