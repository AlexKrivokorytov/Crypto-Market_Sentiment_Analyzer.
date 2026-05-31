<script setup lang="ts">
/**
 * TerminalStatusBar — VS Code-style persistent bottom status bar.
 *
 * Displays: WebSocket connection LED, live asset price tickers,
 * last sweep timestamp, active LLM model, and session uptime counter.
 * Mounts globally outside the router in App.vue (shown only on app pages).
 */

import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import type { AssetMetrics } from '@/types/market'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

const sessionStart = ref(Date.now())
const uptimeDisplay = ref('00:00:00')
const isConnected = ref(true)

// Uptime counter — updates every second
let uptimeInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  uptimeInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - sessionStart.value) / 1000)
    const h = Math.floor(elapsed / 3600)
    const m = Math.floor((elapsed % 3600) / 60)
    const s = elapsed % 60
    uptimeDisplay.value = [h, m, s].map(n => String(n).padStart(2, '0')).join(':')
  }, 1000)
})

onUnmounted(() => {
  if (uptimeInterval) clearInterval(uptimeInterval)
})

// Pull asset prices from TanStack Query cache (already loaded by dashboard)
const { data: assets } = useQuery<AssetMetrics[]>({
  queryKey: ['assets'],
  queryFn: async () => {
    const resp = await fetch(`${API_BASE}/api/v1/assets`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    return resp.json() as Promise<AssetMetrics[]>
  },
  staleTime: 1000 * 15,
  refetchInterval: 1000 * 30,
})

/** Key assets to display in the status bar — BTC, ETH, SOL */
const statusAssets = computed(() => {
  if (!assets.value) return []
  return assets.value
    .filter(a => ['BTC', 'ETH', 'SOL'].includes(a.id))
    .slice(0, 3)
})

const llmModel = import.meta.env.VITE_LLM_MODEL ?? 'openrouter/free'
</script>

<template>
  <!-- Only render on non-auth pages (parent handles this via v-if) -->
  <div
    class="fixed bottom-0 right-0 z-40 h-6 flex items-center px-3 gap-4 select-none"
    style="
      left: var(--sidebar-width, 0px);
      background: rgba(3, 8, 15, 0.95);
      border-top: 1px solid rgba(0, 217, 126, 0.10);
      backdrop-filter: blur(12px);
      font-family: 'IBM Plex Mono', monospace;
    "
    role="status"
    aria-label="Application status"
  >
    <!-- Connection LED -->
    <div class="flex items-center gap-1.5 shrink-0">
      <span
        class="h-1.5 w-1.5 rounded-full"
        :class="isConnected ? 'bg-emerald-400' : 'bg-rose-500'"
        :style="isConnected ? 'box-shadow: 0 0 5px rgba(52,211,153,0.8)' : 'box-shadow: 0 0 5px rgba(255,62,108,0.8)'"
        aria-hidden="true"
      />
      <span
        class="text-[9px] font-semibold uppercase tracking-widest hidden sm:block"
        :class="isConnected ? 'text-emerald-500' : 'text-rose-500'"
      >
        {{ isConnected ? 'Live' : 'Offline' }}
      </span>
    </div>

    <span class="text-slate-700 hidden sm:block">|</span>

    <!-- Asset price pills -->
    <div class="flex items-center gap-3 overflow-hidden">
      <div
        v-for="asset in statusAssets"
        :key="asset.id"
        class="flex items-center gap-1.5 shrink-0"
      >
        <span class="text-[9px] font-bold text-slate-500">{{ asset.id }}</span>
        <span
          class="text-[10px] font-semibold price-mono"
          :class="{
            'text-emerald-400': asset.sentimentLabel === 'Bullish',
            'text-rose-400':    asset.sentimentLabel === 'Bearish',
            'text-slate-400':   asset.sentimentLabel === 'Neutral',
          }"
        >
          ${{ typeof asset.price === 'number' ? asset.price.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '--' }}
        </span>
      </div>
    </div>

    <!-- Spacer -->
    <div class="flex-1" />

    <!-- AI Model -->
    <div class="flex items-center gap-1.5 shrink-0 hidden md:flex">
      <span class="text-[9px] text-slate-600 uppercase tracking-widest">AI</span>
      <span class="text-[9px] text-slate-500 font-semibold">{{ llmModel }}</span>
    </div>

    <span class="text-slate-700 hidden md:block">|</span>

    <!-- Session uptime -->
    <div class="flex items-center gap-1 shrink-0 hidden sm:flex">
      <span class="text-[9px] text-slate-600 uppercase tracking-widest">Session</span>
      <span class="text-[10px] text-slate-500 price-mono font-semibold">{{ uptimeDisplay }}</span>
    </div>
  </div>
</template>
