<script setup lang="ts">
import { computed } from 'vue'
import { useHistoricalData } from '@/composables/useMarketData'
import { getAssetBrandColor } from '@/composables/useCryptoFormatters'
import type { RouteAssetId } from '@/types/market'
import { Radar } from '@lucide/vue'

const props = defineProps<{
  assetId: RouteAssetId
}>()

// Use 7D historical data to calculate RSI and Volatility (assuming 1H candles = 168 data points)
const { data: history, isLoading } = useHistoricalData(computed(() => props.assetId), '7D')

const brandColor = computed(() => getAssetBrandColor(props.assetId))

/**
 * Basic RSI (14 period) calculation.
 * Since we have 1H candles, 14 periods = 14 hours. We use the most recent 15 data points.
 */
const rsi = computed(() => {
  const hist = history.value
  if (!hist || hist.length < 15) return 50.0

  const closes = hist.slice(-15).map(d => d.close)
  let gains = 0
  let losses = 0

  for (let i = 1; i < closes.length; i++) {
    const current = closes[i]
    const previous = closes[i - 1]
    if (current === undefined || previous === undefined) continue
    
    const diff = current - previous
    if (diff > 0) gains += diff
    else losses -= diff
  }

  const avgGain = gains / 14
  const avgLoss = losses / 14
  if (avgLoss === 0) return 100.0

  const rs = avgGain / avgLoss
  return 100 - (100 / (1 + rs))
})

const rsiLabel = computed(() => {
  const val = rsi.value
  if (val >= 70) return 'Overbought'
  if (val <= 30) return 'Oversold'
  return 'Neutral'
})

const rsiColor = computed(() => {
  const val = rsi.value
  if (val >= 70) return '#f43f5e' // Red (overbought, likely to dump)
  if (val <= 30) return '#10b981' // Green (oversold, likely to pump)
  return '#f59e0b' // Yellow (neutral)
})

/**
 * Volatility (ATR-like approach as a percentage of price).
 * We take the average (High - Low) / Close over the last 24 periods (24 hours).
 */
const volatility = computed(() => {
  const hist = history.value
  if (!hist || hist.length < 24) return 0.0

  const recent = hist.slice(-24)
  let sumPct = 0

  for (const candle of recent) {
    if (candle.close > 0) {
      sumPct += (candle.high - candle.low) / candle.close
    }
  }

  return (sumPct / 24) * 100 // Convert to percentage
})

const volatilityLabel = computed(() => {
  const val = volatility.value
  if (val >= 3.0) return 'High Volatility'
  if (val <= 1.0) return 'Low Volatility'
  return 'Moderate'
})

</script>

<template>
  <div class="glass-card p-5 rounded-3xl border border-border/40 flex flex-col h-full w-full relative overflow-hidden group gap-4">
    <!-- Subtle gradient background -->
    <div 
      class="absolute inset-0 opacity-[0.06] pointer-events-none transition-opacity duration-1000 group-hover:opacity-[0.12]"
      :style="`background: radial-gradient(circle at bottom right, ${brandColor}, transparent 60%); mix-blend-mode: screen;`"
      aria-hidden="true"
    />

    <!-- Header -->
    <div class="flex items-center justify-between shrink-0 select-none relative z-10">
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg border" :style="{ background: `${brandColor}15`, borderColor: `${brandColor}30` }">
          <Radar class="h-4 w-4" :style="{ color: brandColor }" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground font-display">Technical Pulse</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">
            RSI & Volatility Math Models
          </p>
        </div>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div v-if="!isLoading" class="flex-1 flex items-center justify-between gap-4 relative z-10 px-2">
      
      <!-- RSI Block -->
      <div class="flex flex-col flex-1 gap-2">
        <div class="flex justify-between items-baseline">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RSI (14)</span>
          <span class="text-[10px] font-extrabold" :style="{ color: rsiColor }">{{ rsiLabel }}</span>
        </div>
        <div class="text-3xl font-extrabold price-mono" :style="{ color: rsiColor }">
          {{ rsi.toFixed(1) }}
        </div>
        
        <!-- RSI Bar -->
        <div class="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden mt-1 relative">
          <div 
            class="h-full rounded-full transition-all duration-700"
            :style="{ width: `${rsi}%`, background: rsiColor }"
          />
          <!-- 30 and 70 lines -->
          <div class="absolute left-[30%] top-0 bottom-0 w-px bg-white/20" />
          <div class="absolute left-[70%] top-0 bottom-0 w-px bg-white/20" />
        </div>
      </div>

      <div class="w-px h-12 bg-border/40" /> <!-- Divider -->

      <!-- Volatility Block -->
      <div class="flex flex-col flex-1 gap-2">
        <div class="flex justify-between items-baseline">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">ATR Vol.</span>
          <span class="text-[10px] font-extrabold text-slate-300">{{ volatilityLabel }}</span>
        </div>
        <div class="text-3xl font-extrabold price-mono text-slate-200">
          {{ volatility.toFixed(2) }}%
        </div>
        
        <!-- Volatility Bar (0 to 5%) -->
        <div class="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden mt-1">
          <div 
            class="h-full bg-indigo-400 rounded-full transition-all duration-700"
            :style="{ width: `${Math.min((volatility / 5.0) * 100, 100)}%` }"
          />
        </div>
      </div>

    </div>

    <!-- Loading State -->
    <div v-else class="flex-1 flex flex-col justify-center gap-4 animate-pulse px-2">
      <div class="flex gap-4">
        <div class="flex-1 space-y-2">
          <div class="h-3 w-16 bg-slate-800 rounded" />
          <div class="h-8 w-24 bg-slate-800 rounded" />
        </div>
        <div class="flex-1 space-y-2">
          <div class="h-3 w-16 bg-slate-800 rounded" />
          <div class="h-8 w-24 bg-slate-800 rounded" />
        </div>
      </div>
    </div>
  </div>
</template>
