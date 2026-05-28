import { onScopeDispose, watch, ref } from 'vue'
import type { Ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import type { AssetMetrics } from '../types/market'

/**
 * Creates and manages a WebSocket connection for real-time asset updates.
 *
 * Listens for 'asset_update' events and patches the TanStack Query cache
 * for both the single asset and the global assets list.
 *
 * Implements:
 *   - Auto-reconnect with exponential backoff.
 *   - 20-second keep-alive pings (prevents Render free tier 30s idle timeout).
 *   - Reactive WebSocket teardown and recreation when `assetId` changes.
 *
 * @param assetId - Reactive reference to the selected asset ticker ID (e.g. 'BTC').
 */
export function useAssetWebSocket(assetId: Ref<string>) {
  const queryClient = useQueryClient()
  const socketRef = ref<WebSocket | null>(null)
  const reconnectCount = ref(0)
  const isConnecting = ref(false)

  let pingIntervalId: number | null = null
  let reconnectTimeoutId: number | null = null

  const MAX_RECONNECT_ATTEMPTS = 5
  const PING_INTERVAL_MS = 20000 // 20 seconds

  /** Clean up active intervals and timeouts. */
  function clearTimers(): void {
    if (pingIntervalId !== null) {
      clearInterval(pingIntervalId)
      pingIntervalId = null
    }
    if (reconnectTimeoutId !== null) {
      clearTimeout(reconnectTimeoutId)
      reconnectTimeoutId = null
    }
  }

  /** Closes the active WebSocket and clears all timers. */
  function disconnect(): void {
    clearTimers()
    if (socketRef.value) {
      // Remove event handlers to prevent trigger of reconnect on manual disconnect
      socketRef.value.onclose = null
      socketRef.value.onerror = null
      socketRef.value.onmessage = null
      socketRef.value.onopen = null
      socketRef.value.close()
      socketRef.value = null
    }
  }

  /** Establishes a WebSocket connection for the current asset ID. */
  function connect(id: string): void {
    disconnect()

    if (!id) return

    isConnecting.value = true

    // Compute ws protocol and host from VITE_API_URL or fallback
    const rawApiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    const wsHost = rawApiUrl.replace(/^http/, 'ws')
    const wsUrl = `${wsHost}/api/v1/ws/${id}`

    try {
      const ws = new WebSocket(wsUrl)
      socketRef.value = ws

      ws.onopen = () => {
        isConnecting.value = false
        reconnectCount.value = 0
        console.log(`[WS] Connected to asset: ${id}`)

        // Send periodic keep-alive pings
        pingIntervalId = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, PING_INTERVAL_MS)
      };

      ws.onmessage = (event: MessageEvent) => {
        if (event.data === 'pong') {
          return // Keep-alive response
        }

        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'asset_update' && payload.asset) {
            const asset: AssetMetrics = payload.asset

            // 1. Update the single asset cache
            queryClient.setQueryData(['asset', id], asset)

            // 2. Update the full assets list cache
            queryClient.setQueryData<AssetMetrics[]>(['assets'], (oldAssets) => {
              if (!oldAssets) return oldAssets
              return oldAssets.map((a) => (a.id === asset.id ? { ...a, ...asset } : a))
            })
          }
        } catch (err) {
          console.error('[WS] Failed to parse message:', err)
        }
      };

      ws.onerror = (err) => {
        console.error('[WS] WebSocket error:', err)
      };

      ws.onclose = () => {
        isConnecting.value = false
        socketRef.value = null
        clearTimers()
        console.warn(`[WS] Connection closed for asset: ${id}`)

        // Attempt reconnection with exponential backoff
        if (reconnectCount.value < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.pow(2, reconnectCount.value) * 1000
          reconnectCount.value++
          console.log(`[WS] Reconnecting in ${delay}ms (Attempt ${reconnectCount.value}/${MAX_RECONNECT_ATTEMPTS})`)
          reconnectTimeoutId = window.setTimeout(() => {
            connect(id)
          }, delay)
        } else {
          console.error('[WS] Max reconnection attempts reached')
        }
      };
    } catch (err) {
      isConnecting.value = false
      console.error('[WS] Failed to create WebSocket:', err)
    }
  }

  // Reactively watch for assetId changes and reconnect to the new room
  watch(
    () => assetId.value,
    (newVal) => {
      connect(newVal)
    },
    { immediate: true }
  )

  // Ensure cleanup on unmount or scope destruction
  onScopeDispose(() => {
    disconnect()
  })

  return {
    isConnecting,
    reconnectCount,
  }
}
