<script setup lang="ts">
import { useAssetById } from '@/composables/useMarketData'
import { ArrowUpRight, ArrowDownRight, DollarSign, Activity, Percent, Layers } from '@lucide/vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import type { RouteAssetId } from '@/types/market'
import { computed } from 'vue'

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
}>()

const { data: asset, isLoading, isError, refetch } = useAssetById(computed(() => props.assetId))



const formatCurrency = (val: number, symbol: string) => {
  const options = symbol === 'AAPL'
    ? { minimumFractionDigits: 2, maximumFractionDigits: 2 }
    : { minimumFractionDigits: 0, maximumFractionDigits: 2 };
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    ...options
  }).format(val)
}

const formatVolume = (val: number) => {
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`
  if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val)
}

const getRangePercentage = (price: number, low: number, high: number) => {
  if (high === low) return 50
  const pct = ((price - low) / (high - low)) * 100
  return Math.min(100, Math.max(0, pct))
}

const getSentimentLabel = (score: number) => {
  if (score >= 75) return 'Strong Bullish'
  if (score > 55) return 'Moderate Bullish'
  if (score >= 45) return 'Neutral'
  if (score > 25) return 'Moderate Bearish'
  return 'Strong Bearish'
}
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Skeleton while loading -->
    <template v-if="isLoading">
      <div v-for="i in 4" :key="i" class="h-28 bg-card border border-border/30 rounded-2xl animate-pulse" />
    </template>

    <!-- Error state -->
    <div v-else-if="isError" class="col-span-full">
      <ErrorState
        title="Failed to load asset metrics"
        description="The backend may be starting up or temporarily unavailable."
        :on-retry="() => refetch()"
      />
    </div>

    <template v-else-if="asset">

      <!-- Price Card -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <div class="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-2xl pointer-events-none transition-opacity duration-300 group-hover:bg-primary/10"></div>
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">Market Price</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground group-hover:text-primary transition-colors">
            <DollarSign class="h-4 w-4" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <span class="text-2xl font-bold text-foreground font-mono tracking-tight transition-transform duration-200 group-hover:translate-x-0.5">
            {{ formatCurrency(asset.price, asset.symbol) }}
          </span>
          <span
            class="text-xs flex items-center font-semibold mt-1"
            :class="[asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']"
          >
            <component :is="asset.change24h >= 0 ? ArrowUpRight : ArrowDownRight" class="h-4 w-4 mr-0.5 shrink-0" />
            {{ asset.change24h >= 0 ? '+' : '' }}{{ asset.change24h }}%
            <span class="text-[10px] text-muted-foreground font-medium ml-1.5">(24h)</span>
          </span>
        </div>
      </div>

      <!-- Sentiment Index Card -->
      <div
        class="glass-card p-5 rounded-2xl border flex flex-col justify-between relative overflow-hidden group transition-all duration-300"
        :class="[
          asset.sentimentLabel === 'Bullish'
            ? 'border-bullish/30 animate-glow-bullish bg-bullish/5'
            : asset.sentimentLabel === 'Bearish'
            ? 'border-bearish/30 animate-glow-bearish bg-bearish/5'
            : 'border-border/40'
        ]"
      >
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">LLM Sentiment Index</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Activity class="h-4 w-4" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <div class="flex items-baseline gap-2">
            <span
              class="text-3xl font-extrabold font-mono tracking-tight"
              :class="[
                asset.sentimentLabel === 'Bullish'
                  ? 'text-bullish text-glow-bullish'
                  : asset.sentimentLabel === 'Bearish'
                  ? 'text-bearish text-glow-bearish'
                  : 'text-foreground'
              ]"
            >
              {{ asset.sentimentScore }}
            </span>
            <span class="text-[10px] text-muted-foreground font-semibold">/100</span>
          </div>
          <span
            class="text-xs font-bold uppercase tracking-wide mt-1 animate-pulse"
            :class="[
              asset.sentimentLabel === 'Bullish' ? 'text-bullish' : asset.sentimentLabel === 'Bearish' ? 'text-bearish' : 'text-muted-foreground'
            ]"
          >
            {{ getSentimentLabel(asset.sentimentScore) }}
          </span>
        </div>
      </div>

      <!-- 24h High/Low Range Card -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">24h Range</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Percent class="h-4 w-4" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <div class="flex justify-between items-center text-xs font-mono font-medium mb-1.5">
            <span class="text-muted-foreground">{{ formatCurrency(asset.low24h, asset.symbol) }}</span>
            <span class="text-muted-foreground">{{ formatCurrency(asset.high24h, asset.symbol) }}</span>
          </div>
          <!-- Bar gauge -->
          <div class="h-1.5 w-full bg-muted rounded-full overflow-hidden relative border border-border/40">
            <div
              class="h-full rounded-full transition-all duration-300 ease-out"
              :class="[asset.change24h >= 0 ? 'bg-bullish' : 'bg-bearish']"
              :style="{ width: `${getRangePercentage(asset.price, asset.low24h, asset.high24h)}%` }"
            ></div>
          </div>
          <span class="text-[10px] text-muted-foreground mt-1.5 text-center font-medium">
            Current Price is at {{ getRangePercentage(asset.price, asset.low24h, asset.high24h).toFixed(0) }}% of daily range
          </span>
        </div>
      </div>

      <!-- 24h Volume Card -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">24h Volume</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Layers class="h-4 w-4" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <span class="text-2xl font-bold text-foreground font-mono tracking-tight">
            {{ formatVolume(asset.volume24h) }}
          </span>
          <span class="text-xs text-muted-foreground font-semibold mt-1">
            Institutional Quote Volume
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
