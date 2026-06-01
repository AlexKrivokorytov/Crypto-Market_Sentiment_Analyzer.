<script setup lang="ts">
import { computed } from 'vue'
import { useOrderBookImbalance } from '@/composables/useMarketData'
import type { RouteAssetId } from '@/types/market'
import { Activity, TrendingUp, TrendingDown, RefreshCcw } from '@lucide/vue'

const props = defineProps<{
  assetId: RouteAssetId
}>()

const { data: orderbook, isLoading } = useOrderBookImbalance(computed(() => props.assetId))

const buyPressure = computed(() => orderbook.value?.buy_pressure_percentage ?? 50)
const sellPressure = computed(() => 100 - buyPressure.value)

const formattedBids = computed(() => {
  if (!orderbook.value) return '0.00'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(orderbook.value.bids_volume)
})

const formattedAsks = computed(() => {
  if (!orderbook.value) return '0.00'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(orderbook.value.asks_volume)
})

const dominantTrend = computed(() => {
  if (buyPressure.value > 55) return 'bullish'
  if (buyPressure.value < 45) return 'bearish'
  return 'neutral'
})
</script>

<template>
  <div class="glass-card p-5 rounded-3xl border border-border/40 flex flex-col h-full w-full relative overflow-hidden group gap-3">
    <!-- Ambient glow reflecting the dominant trend -->
    <div 
      class="absolute inset-0 opacity-[0.05] pointer-events-none transition-all duration-1000 group-hover:opacity-[0.12]"
      :style="{
        background: dominantTrend === 'bullish' ? 'radial-gradient(circle at left, #10b981, transparent 70%)' :
                    dominantTrend === 'bearish' ? 'radial-gradient(circle at right, #f43f5e, transparent 70%)' :
                    'radial-gradient(circle at center, #64748b, transparent 70%)',
        mixBlendMode: 'screen'
      }"
      aria-hidden="true"
    />

    <!-- Header -->
    <div class="flex items-center justify-between shrink-0 select-none relative z-10">
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg border bg-slate-800/50 border-slate-700/50">
          <Activity class="h-4 w-4 text-slate-300" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground font-display">Order Book Depth</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">
            Live bid/ask volume imbalance · {{ props.assetId }}
          </p>
        </div>
      </div>
      
      <div v-if="isLoading" class="animate-spin text-slate-500">
        <RefreshCcw class="h-3 w-3" />
      </div>
    </div>

    <!-- Main Tug-of-war Bar -->
    <div class="flex-1 flex flex-col justify-center gap-3 relative z-10">
      <div class="flex justify-between items-end px-1">
        <!-- Bids (Bulls) -->
        <div class="flex flex-col gap-0.5 text-left">
          <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
            <TrendingUp class="h-3 w-3" /> Bids (Buy)
          </span>
          <span class="text-xl font-extrabold price-mono text-emerald-300">${{ formattedBids }}</span>
        </div>
        
        <!-- Asks (Bears) -->
        <div class="flex flex-col gap-0.5 text-right">
          <span class="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1 justify-end">
            Asks (Sell) <TrendingDown class="h-3 w-3" />
          </span>
          <span class="text-xl font-extrabold price-mono text-rose-300">${{ formattedAsks }}</span>
        </div>
      </div>

      <!-- The Bar -->
      <div class="relative h-4 w-full rounded-full bg-slate-900 overflow-hidden border border-white/5 flex shadow-inner">
        <!-- Buy Pressure -->
        <div 
          class="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 transition-all duration-700 ease-out relative"
          :style="{ width: `${buyPressure}%` }"
        >
          <div class="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white/20 to-transparent" />
        </div>
        <!-- Sell Pressure -->
        <div 
          class="h-full bg-gradient-to-l from-rose-600 to-rose-400 transition-all duration-700 ease-out relative"
          :style="{ width: `${sellPressure}%` }"
        >
          <div class="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-white/20 to-transparent" />
        </div>
        
        <!-- Center marker -->
        <div class="absolute left-1/2 top-0 bottom-0 w-0.5 bg-slate-900/50 -translate-x-1/2 z-10" />
      </div>

      <!-- Percentages -->
      <div class="flex justify-between items-center px-2">
        <span class="text-[10px] font-bold text-emerald-400/80">{{ buyPressure.toFixed(1) }}%</span>
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Pressure</span>
        <span class="text-[10px] font-bold text-rose-400/80">{{ sellPressure.toFixed(1) }}%</span>
      </div>
    </div>
  </div>
</template>
