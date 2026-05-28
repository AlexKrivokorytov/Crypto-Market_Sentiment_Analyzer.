<script setup lang="ts">
import { defineAsyncComponent, computed } from 'vue'
import { useRoute } from 'vue-router'
import type { RouteAssetId } from '@/types/market'
import { useAppStore } from '@/composables/useAppStore'
import { storeToRefs } from 'pinia'
import { useAssetWebSocket } from '@/composables/useAssetWebSocket'

/**
 * The DashboardView derives the active asset ID from the URL parameter `:id`
 * rather than from Pinia, making each asset URL fully bookmarkable and shareable.
 *
 * Heavy chart and feed components are lazy-loaded via `defineAsyncComponent` to
 * reduce the initial JS bundle size and improve time-to-interactive.
 */

// Lazy-load heavy rendering components to split them from the main chunk
const MetricsPanel = defineAsyncComponent(() => import('@/components/dashboard/MetricsPanel.vue'))
const SentimentChart = defineAsyncComponent(() => import('@/components/dashboard/SentimentChart.vue'))
const LiveFeed = defineAsyncComponent(() => import('@/components/dashboard/LiveFeed.vue'))

const route = useRoute()
const store = useAppStore()
const { timeframe } = storeToRefs(store)

/** The current asset ID is always authoritative from the URL, not from store. */
const assetId = computed(() => route.params.id as RouteAssetId)

// Initialize WebSocket connection for real-time asset updates
useAssetWebSocket(assetId)
</script>

<template>
  <main class="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 space-y-4 lg:space-y-6">
    <!-- Page Header -->
    <div class="flex flex-col gap-1 select-none">
      <h1
        class="text-xl sm:text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent"
      >
        Market Intelligence Center
      </h1>
      <p class="text-xs text-slate-400 font-medium">
        Aggregated orderbook quotes overlaid with real-time LLM-processed sentiment metrics.
      </p>
    </div>

    <!-- Metrics Row — 4 KPI cards -->
    <Suspense>
      <MetricsPanel :asset-id="assetId" />
      <template #fallback>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div v-for="i in 4" :key="i" class="h-28 bg-card border border-border/30 rounded-2xl animate-pulse" />
        </div>
      </template>
    </Suspense>

    <!-- Chart + Feed Row -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6 items-stretch">
      <!-- Candlestick Chart (2/3 width on desktop) -->
      <div class="lg:col-span-2 flex flex-col">
        <Suspense>
          <SentimentChart :asset-id="assetId" :timeframe="timeframe" />
          <template #fallback>
            <div class="glass-card rounded-3xl border border-border/40 h-[320px] sm:h-[400px] lg:h-[480px] animate-pulse" />
          </template>
        </Suspense>
      </div>

      <!-- Live News Feed (1/3 width on desktop) -->
      <div class="lg:col-span-1 flex flex-col">
        <Suspense>
          <LiveFeed :asset-id="assetId" />
          <template #fallback>
            <div class="glass-card rounded-3xl border border-border/40 h-[400px] sm:h-[500px] animate-pulse" />
          </template>
        </Suspense>
      </div>
    </div>
  </main>
</template>
