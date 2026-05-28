<script setup lang="ts">
/**
 * MetricsPanel — 4 KPI cards for the active asset (price, sentiment, range, volume).
 *
 * Sprint 5 upgrades:
 * - All price/volume values routed through useCryptoFormatters (DRY, tabular-nums).
 * - Price card has a live pulse indicator showing the card is receiving live ticks.
 * - 24h range bar uses a smooth CSS transition on width change.
 * - Internal formatCurrency / formatVolume helpers removed (now imported).
 */

import { computed } from 'vue'
import { useAssetById } from '@/composables/useMarketData'
import { ArrowUpRight, ArrowDownRight, DollarSign, Activity, Percent, Layers } from '@lucide/vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import type { RouteAssetId } from '@/types/market'
import {
  formatPrice,
  formatVolume,
} from '@/composables/useCryptoFormatters'

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
}>()

const { data: asset, isLoading, isError, refetch } = useAssetById(computed(() => props.assetId))

/**
 * Computes where the current price sits within the 24h high/low range as
 * a clamped 0–100 percentage, used to render the range progress bar.
 *
 * @param price - Current asset price.
 * @param low   - 24h low.
 * @param high  - 24h high.
 * @returns Clamped percentage in [0, 100].
 */
function getRangePercentage(price: number, low: number, high: number): number {
  if (high === low) return 50
  return Math.min(100, Math.max(0, ((price - low) / (high - low)) * 100))
}

/**
 * Returns a verbose sentiment label for the 0–100 index.
 *
 * @param score - Sentiment index 0–100.
 */
function getSentimentLabel(score: number): string {
  if (score >= 75) return 'Strong Bullish'
  if (score > 55)  return 'Moderate Bullish'
  if (score >= 45) return 'Neutral'
  if (score > 25)  return 'Moderate Bearish'
  return 'Strong Bearish'
}
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

    <!-- ── Loading skeleton ──────────────────────────────────────────── -->
    <template v-if="isLoading">
      <div
        v-for="i in 4"
        :key="i"
        class="h-28 bg-card border border-border/30 rounded-2xl animate-pulse"
        aria-hidden="true"
      />
    </template>

    <!-- ── Error state ───────────────────────────────────────────────── -->
    <div v-else-if="isError" class="col-span-full">
      <ErrorState
        title="Failed to load asset metrics"
        description="The backend may be starting up or temporarily unavailable."
        :on-retry="() => refetch()"
      />
    </div>

    <template v-else-if="asset">

      <!-- ── Card 1: Market Price ──────────────────────────────────── -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <!-- Ambient glow blob -->
        <div
          class="absolute top-0 right-0 w-24 h-24 rounded-full blur-2xl pointer-events-none transition-opacity duration-300 group-hover:opacity-100 opacity-60"
          :class="asset.change24h >= 0 ? 'bg-emerald-500/8' : 'bg-rose-500/8'"
          aria-hidden="true"
        />

        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">Market Price</span>
          <div class="flex items-center gap-2">
            <!-- Live pulse dot -->
            <span class="flex h-2 w-2" aria-label="Live data" title="Live data feed active">
              <span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-50" aria-hidden="true" />
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" aria-hidden="true" />
            </span>
            <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground group-hover:text-primary transition-colors">
              <DollarSign class="h-4 w-4" aria-hidden="true" />
            </div>
          </div>
        </div>

        <div class="mt-2 flex flex-col">
          <!-- Price uses JetBrains Mono tabular numerals via price-mono class -->
          <span class="text-2xl font-bold text-foreground price-mono tracking-tight transition-transform duration-200 group-hover:translate-x-0.5">
            {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
          </span>
          <span
            class="text-xs flex items-center font-semibold mt-1"
            :class="asset.change24h >= 0 ? 'text-bullish' : 'text-bearish'"
          >
            <component
              :is="asset.change24h >= 0 ? ArrowUpRight : ArrowDownRight"
              class="h-4 w-4 mr-0.5 shrink-0"
              aria-hidden="true"
            />
            {{ asset.change24h >= 0 ? '+' : '' }}{{ asset.change24h }}%
            <span class="text-[10px] text-muted-foreground font-medium ml-1.5">(24h)</span>
          </span>
        </div>
      </div>

      <!-- ── Card 2: VADER Sentiment Index ─────────────────────────── -->
      <div
        class="glass-card p-5 rounded-2xl border flex flex-col justify-between relative overflow-hidden group transition-all duration-300"
        :class="[
          asset.sentimentLabel === 'Bullish'
            ? 'border-bullish/30 animate-glow-bullish'
            : asset.sentimentLabel === 'Bearish'
            ? 'border-bearish/30 animate-glow-bearish'
            : 'border-border/40',
        ]"
      >
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">VADER Sentiment</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Activity class="h-4 w-4" aria-hidden="true" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <div class="flex items-baseline gap-2">
            <span
              class="text-3xl font-extrabold price-mono tracking-tight"
              :class="[
                asset.sentimentLabel === 'Bullish'
                  ? 'text-bullish text-glow-bullish'
                  : asset.sentimentLabel === 'Bearish'
                  ? 'text-bearish text-glow-bearish'
                  : 'text-foreground',
              ]"
              :aria-label="`Sentiment score: ${asset.sentimentScore} out of 100`"
            >
              {{ asset.sentimentScore }}
            </span>
            <span class="text-[10px] text-muted-foreground font-semibold">/100</span>
          </div>
          <span
            class="text-xs font-bold uppercase tracking-wide mt-1"
            :class="
              asset.sentimentLabel === 'Bullish'
                ? 'text-bullish'
                : asset.sentimentLabel === 'Bearish'
                ? 'text-bearish'
                : 'text-muted-foreground'
            "
          >
            {{ getSentimentLabel(asset.sentimentScore) }}
          </span>
        </div>
      </div>

      <!-- ── Card 3: 24h High/Low Range ────────────────────────────── -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">24h Range</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Percent class="h-4 w-4" aria-hidden="true" />
          </div>
        </div>
        <div class="mt-2 flex flex-col gap-1.5">
          <div class="flex justify-between items-center text-xs price-mono font-medium">
            <span class="text-muted-foreground">{{ formatPrice(asset.low24h, asset.id as RouteAssetId) }}</span>
            <span class="text-muted-foreground">{{ formatPrice(asset.high24h, asset.id as RouteAssetId) }}</span>
          </div>
          <!-- Animated range progress bar -->
          <div
            class="h-1.5 w-full bg-muted rounded-full overflow-hidden relative border border-border/40"
            role="meter"
            :aria-valuenow="getRangePercentage(asset.price, asset.low24h, asset.high24h)"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Price at ${getRangePercentage(asset.price, asset.low24h, asset.high24h).toFixed(0)}% of daily range`"
          >
            <div
              class="h-full rounded-full transition-all duration-700 ease-out"
              :class="asset.change24h >= 0 ? 'bg-bullish' : 'bg-bearish'"
              :style="{ width: `${getRangePercentage(asset.price, asset.low24h, asset.high24h)}%` }"
            />
          </div>
          <span class="text-[10px] text-muted-foreground text-center font-medium">
            At {{ getRangePercentage(asset.price, asset.low24h, asset.high24h).toFixed(0) }}% of daily range
          </span>
        </div>
      </div>

      <!-- ── Card 4: 24h Volume ─────────────────────────────────────── -->
      <div class="glass-card p-5 rounded-2xl border border-border/40 flex flex-col justify-between relative overflow-hidden group">
        <div class="flex items-center justify-between text-muted-foreground">
          <span class="text-xs font-semibold uppercase tracking-wider">24h Volume</span>
          <div class="h-8 w-8 rounded-lg bg-muted flex items-center justify-center border border-border/50 text-muted-foreground">
            <Layers class="h-4 w-4" aria-hidden="true" />
          </div>
        </div>
        <div class="mt-2 flex flex-col">
          <span class="text-2xl font-bold text-foreground price-mono tracking-tight">
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
