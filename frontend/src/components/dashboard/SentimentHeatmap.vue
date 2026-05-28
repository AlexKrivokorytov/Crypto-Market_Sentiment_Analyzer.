<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAssets } from '@/composables/useMarketData'
import type { RouteAssetId, AssetMetrics } from '@/types/market'
import { Flame, TrendingUp, TrendingDown, RefreshCw } from '@lucide/vue'

const router = useRouter()
const route = useRoute()

// Fetch assets live
const { data: assets, isLoading, isError, refetch } = useAssets()

// The ordered list of assets for the Heatmap grid
const GRID_ASSETS: RouteAssetId[] = ['BTC', 'ETH', 'TON', 'SOL', 'XRP', 'ADA']

/** The currently active asset ticker, derived from the URL. */
const activeAssetId = computed(() => route.params.id as string)

/**
 * Filter and sort assets matching our specified grid list.
 */
const heatmapAssets = computed(() => {
  if (!assets.value) return []
  return GRID_ASSETS.map(symbol => {
    return assets.value.find(a => a.id === symbol)
  }).filter((a): a is AssetMetrics => !!a)
})

/**
 * Dynamic color interpolation & visual style heuristic.
 * Maps sentimentScore (0..100) to normalized continuous compound VADER scale [-1.0..1.0].
 * Returns custom styling with dynamic drop-shadow, border-glow, and color gradation.
 */
const getTileStyle = (score: number, isActive: boolean) => {
  const normalized = (score - 50) / 50
  const absVal = Math.abs(normalized)
  
  let bg = ''
  let border = ''
  let text = ''
  let shadow = ''
  
  if (normalized > 0) {
    // Euphoric Green glow
    bg = `rgba(16, 185, 129, ${0.08 + absVal * 0.35})`
    border = `rgba(16, 185, 129, ${0.25 + absVal * 0.45})`
    text = '#a7f3d0' // Emerald-200
    shadow = `inset 0 1px 1px rgba(255, 255, 255, 0.05), 0 0 ${12 + absVal * 16}px rgba(16, 185, 129, ${0.1 + absVal * 0.3})`
  } else if (normalized < 0) {
    // Panic Red glow
    bg = `rgba(244, 63, 94, ${0.08 + absVal * 0.35})`
    border = `rgba(244, 63, 94, ${0.25 + absVal * 0.45})`
    text = '#fecdd3' // Rose-200
    shadow = `inset 0 1px 1px rgba(255, 255, 255, 0.05), 0 0 ${12 + absVal * 16}px rgba(244, 63, 94, ${0.1 + absVal * 0.3})`
  } else {
    // Neutral Slate gray
    bg = 'rgba(30, 41, 59, 0.4)'
    border = 'rgba(255, 255, 255, 0.06)'
    text = '#94a3b8' // Slate-400
    shadow = 'inset 0 1px 1px rgba(255, 255, 255, 0.02)'
  }

  // Accentuate active asset border with strong white/primary highlight
  if (isActive) {
    border = '#6366f1' // Primary Indigo
    shadow = `${shadow ? shadow + ', ' : ''}0 0 15px rgba(99, 102, 241, 0.4)`
  }
  
  return {
    backgroundColor: bg,
    borderColor: border,
    color: text,
    boxShadow: shadow
  }
}

/** Navigates to selected asset to switch active dashboard asset. */
const selectAsset = (id: RouteAssetId): void => {
  router.push(`/asset/${id}`)
}

/** Format currency utility helper. */
const formatPrice = (val: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  }).format(val)
}
</script>

<template>
  <div class="glass-card p-5 rounded-3xl border border-border/40 flex flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between select-none shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <Flame class="h-4.5 w-4.5 animate-pulse" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground">Market Sentiment Heatmap Matrix</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">Real-Time VADER Normalization Compound Scale [-1.0, +1.0]</p>
        </div>
      </div>
      
      <!-- Legend indicators -->
      <div class="hidden md:flex items-center gap-4 text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
        <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-bearish"></span> Panic (-1.0)</span>
        <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-slate-600"></span> Neutral (0.0)</span>
        <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-bullish"></span> Euphoria (+1.0)</span>
      </div>
    </div>

    <!-- Live Grid -->
    <div class="relative min-h-[96px] w-full">
      <!-- Loading Skeleton Grid -->
      <div v-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 select-none">
        <div 
          v-for="i in 6" 
          :key="i" 
          class="h-24 rounded-2xl bg-muted/20 border border-border/20 animate-pulse flex flex-col justify-between p-3"
        >
          <div class="h-4 w-1/3 bg-muted/40 rounded"></div>
          <div class="h-6 w-2/3 bg-muted/40 rounded"></div>
        </div>
      </div>

      <!-- Error State -->
      <div 
        v-else-if="isError" 
        class="flex flex-col items-center justify-center p-6 border border-rose-500/20 rounded-2xl bg-rose-500/5 gap-2 text-center"
      >
        <span class="text-xs font-semibold text-rose-400">Failed to stream Live Heatmap Data</span>
        <button 
          @click="() => refetch()" 
          class="inline-flex items-center gap-1 px-3 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-[10px] font-extrabold uppercase text-rose-400 border border-rose-500/20 cursor-pointer"
        >
          <RefreshCw class="h-3 w-3" /> Retry Stream
        </button>
      </div>

      <!-- Premium Matrix Grid -->
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <button
          v-for="asset in heatmapAssets"
          :key="asset.id"
          @click="selectAsset(asset.id)"
          class="h-24 rounded-2xl border p-3 flex flex-col justify-between text-left transition-all duration-300 relative group select-none hover-scale-premium overflow-hidden"
          :style="getTileStyle(asset.sentimentScore, activeAssetId === asset.id)"
          :aria-label="`Switch dashboard to ${asset.name}`"
        >
          <!-- Shiny glass highlight effect on hover -->
          <div class="absolute inset-0 w-full h-full bg-gradient-to-tr from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-out pointer-events-none"></div>

          <!-- Top Row: Ticker symbol & Active GlowDot -->
          <div class="flex items-center justify-between w-full">
            <span class="font-extrabold text-sm tracking-wider uppercase text-white">{{ asset.symbol }}</span>
            <div class="flex items-center gap-1">
              <span v-if="activeAssetId === asset.id" class="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-ping"></span>
              <span 
                class="h-1.5 w-1.5 rounded-full"
                :class="[activeAssetId === asset.id ? 'bg-indigo-400' : 'bg-transparent']"
              ></span>
            </div>
          </div>

          <!-- Mid Row: VADER Compound Score -->
          <div class="flex items-baseline gap-1 mt-1">
            <span class="font-black text-xl tracking-tight leading-none font-mono">
              {{ (asset.sentimentScore - 50) / 50 >= 0 ? '+' : '' }}{{ ((asset.sentimentScore - 50) / 50).toFixed(2) }}
            </span>
          </div>

          <!-- Bottom Row: Price & 24h Shift -->
          <div class="flex justify-between items-center w-full text-[10px] font-semibold text-slate-300/80 mt-1 select-none">
            <span class="font-mono truncate max-w-[65%]">{{ formatPrice(asset.price) }}</span>
            <span 
              class="flex items-center shrink-0" 
              :class="[asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']"
            >
              <component :is="asset.change24h >= 0 ? TrendingUp : TrendingDown" class="h-2.5 w-2.5 mr-0.5 shrink-0" />
              {{ asset.change24h >= 0 ? '+' : '' }}{{ asset.change24h }}%
            </span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hover-scale-premium {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.hover-scale-premium:hover {
  transform: translateY(-2px) scale(1.02);
  filter: brightness(1.15);
}
</style>
