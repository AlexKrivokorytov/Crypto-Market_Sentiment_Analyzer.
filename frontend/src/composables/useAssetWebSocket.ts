import { ref, watch, onScopeDispose } from 'vue'
import type { Ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import type { AssetMetrics, AssetUpdateMessage } from '../types/market'
import { useWebSocketManager } from './useWebSocketManager'
import type { ConnectionStatus } from './useWebSocketManager'
import { useToast } from './useToast'

// Module-level shared reactive connection state to allow any visual component
// (e.g. the Header Navbar) to monitor the active socket channel.
const globalStatus = ref<ConnectionStatus>('DISCONNECTED')
const globalReconnectCount = ref(0)
let triggerReconnectFn: (() => void) | null = null

/**
 * Creates and manages a WebSocket connection for real-time asset updates.
 * Under the hood, delegates to the robust, throttled `useWebSocketManager`.
 *
 * Updates TanStack Query caches for `['asset', id]` and `['assets']` on incoming ticks.
 * Triggers a premium Toast notice with a CTA on reconnection failure.
 *
 * @param assetId Reactive reference to the selected asset ticker symbol.
 */
export function useAssetWebSocket(assetId: Ref<string>) {
  const queryClient = useQueryClient()
  const toast = useToast()

  // Track the ID of the active toast so we can dismiss it on success
  let activeToastId: string | null = null

  /**
   * Processes the throttled real-time tick message.
   */
  function handleMessage(payload: AssetUpdateMessage | Record<string, unknown>): void {
    // If a connection failure toast is visible, dismiss it now that we are receiving messages
    if (activeToastId) {
      toast.dismiss(activeToastId)
      activeToastId = null
    }

    if (payload?.type === 'asset_update' && 'asset' in payload && payload.asset) {
      const asset: AssetMetrics = payload.asset as AssetMetrics

      // 1. Update single asset cached record
      queryClient.setQueryData(['asset', asset.id], asset)

      // 2. Update list query data reactively
      queryClient.setQueryData<AssetMetrics[]>(['assets'], (oldAssets) => {
        if (!oldAssets) return oldAssets
        return oldAssets.map((a) => (a.id === asset.id ? { ...a, ...asset } : a))
      })
    }
  }

  /**
   * Triggered when all exponential backoff connection attempts are exhausted.
   * Renders a persistent critical Toast notification.
   */
  function handleReconnectFailure(): void {
    if (activeToastId) return // Avoid duplicate toast alerts

    activeToastId = toast.showConnectionFailedToast(() => {
      // Trigger reconnection retry callback
      if (triggerReconnectFn) {
        console.log('[useAssetWebSocket] Manually triggered reconnect attempt.')
        triggerReconnectFn()
      }
    })
  }

  // Instantiate the WebSocket manager
  const { connectionStatus, reconnectCount, reconnect, disconnect } = useWebSocketManager<AssetUpdateMessage>(
    assetId,
    handleMessage,
    handleReconnectFailure
  )

  // Sync WebSocket states to module-level global variables
  watch(connectionStatus, (newVal) => {
    globalStatus.value = newVal
    
    // Auto-dismiss the connection toast if we transition back to CONNECTED
    if (newVal === 'CONNECTED' && activeToastId) {
      toast.dismiss(activeToastId)
      activeToastId = null
    }
  }, { immediate: true })

  watch(reconnectCount, (newVal) => {
    globalReconnectCount.value = newVal
  }, { immediate: true })

  // Keep a reference to the reconnect function so the Toast CTA can invoke it
  triggerReconnectFn = reconnect

  // Make sure we cleanly disconnect when the using scope is unmounted
  onScopeDispose(() => {
    // We only disconnect if this was the final active watcher
    disconnect()
    if (activeToastId) {
      toast.dismiss(activeToastId)
      activeToastId = null
    }
  })

  return {
    connectionStatus,
    reconnectCount,
    reconnect,
  }
}

/**
 * Global accessor function allowing top bar widgets and headers to monitor
 * real-time server stream state without duplicating WebSocket allocations.
 */
export function useWebSocketState() {
  return {
    status: globalStatus,
    reconnectCount: globalReconnectCount,
    triggerManualReconnect: () => {
      if (triggerReconnectFn) triggerReconnectFn()
    }
  }
}
