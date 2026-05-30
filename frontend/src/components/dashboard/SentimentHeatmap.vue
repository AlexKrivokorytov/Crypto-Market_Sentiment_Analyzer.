<script setup lang="ts">
/**
 * SentimentHeatmap — Interactive VADER sentiment matrix for all 6 crypto assets,
 * upgraded in Sprint 5 with:
 *
 * 1. **Fear & Greed composite index** — arc gauge in the header computed as
 *    the average VADER compound score of all 6 assets mapped to 0–100.
 * 2. **Asset rank badges** — top bullish (#1, #2) and top bearish (#1) assets.
 * 3. **Brand-coloured tile accents** — each tile's active border uses asset colour.
 * 4. **useCryptoFormatters** — price and VADER display use the shared formatters.
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAssets } from '@/composables/useMarketData'
import {
  formatPrice,
  formatVaderScore,
  sentimentIndexToVader,
  getAssetBrandColor,
} from '@/composables/useCryptoFormatters'
import type { RouteAssetId, AssetMetrics } from '@/types/market'
import { Flame, TrendingUp, TrendingDown, RefreshCw } from '@lucide/vue'

const router = useRouter()
const route = useRoute()

const { data: assets, isLoading, isError, refetch } = useAssets()

/** Assets shown in the heatmap — crypto only (excludes AAPL). */
const GRID_ASSETS: RouteAssetId[] = ['BTC', 'ETH', 'TON', 'SOL', 'XRP', 'ADA']

/** The currently active asset ticker from the URL. */
const activeAssetId = computed(() => route.params.id as string)

/**
 * Filter and order assets matching our crypto grid list,
 * preserving GRID_ASSETS display order.
 */
const heatmapAssets = computed<AssetMetrics[]>(() => {
  if (!assets.value) return []
  return GRID_ASSETS
    .map(symbol => assets.value!.find(a => a.id === symbol))
    .filter((a): a is AssetMetrics => a !== undefined)
})

// ─── Fear & Greed Composite Index ──────────────────────────────────────────

/**
 * Computes the market Fear & Greed index as the mean 0–100 sentiment score
 * across all heatmap assets. Returns null while data is loading.
 *
 * A score of 0 = Extreme Fear, 100 = Extreme Greed.
 */
const fearGreedIndex = computed<number | null>(() => {
  if (heatmapAssets.value.length === 0) return null
  const total = heatmapAssets.value.reduce((sum, a) => sum + a.sentimentScore, 0)
  return Math.round(total / heatmapAssets.value.length)
})

/**
 * Returns a human-readable Fear & Greed label for the given index value.
 *
 * @param index - 0–100 composite sentiment score.
 */
function fearGreedLabel(index: number): string {
  if (index >= 75) return 'Extreme Greed'
  if (index >= 60) return 'Greed'
  if (index >= 45) return 'Neutral'
  if (index >= 30) return 'Fear'
  return 'Extreme Fear'
}

/**
 * Returns the text colour class matching the Fear & Greed label.
 *
 * @param index - 0–100 composite sentiment score.
 */
function fearGreedColorClass(index: number): string {
  if (index >= 75) return 'text-emerald-400'
  if (index >= 60) return 'text-emerald-300'
  if (index >= 45) return 'text-slate-400'
  if (index >= 30) return 'text-rose-300'
  return 'text-rose-400'
}

/**
 * Computes the SVG arc path `d` attribute for the Fear & Greed needle gauge.
 * Renders a 180° semicircle with a filled arc section from left to the
 * position corresponding to the index.
 *
 * @param index - 0–100 fear/greed value.
 * @returns CSS transform rotation degrees for the needle element.
 */
function gaugeNeedleDeg(index: number): number {
  // Map 0–100 to −90° … +90° (180° sweep)
  return -90 + (index / 100) * 180
}

// ─── Rank Badges ───────────────────────────────────────────────────────────

/** Top-2 bullish assets by sentimentScore, descending. */
const topBullish = computed<AssetMetrics[]>(() =>
  [...heatmapAssets.value]
    .sort((a, b) => b.sentimentScore - a.sentimentScore)
    .slice(0, 2),
)

/** Most bearish asset by sentimentScore, ascending. */
const topBearish = computed<AssetMetrics | null>(() =>
  heatmapAssets.value.reduce<AssetMetrics | null>(
    (min, a) => (min === null || a.sentimentScore < min.sentimentScore ? a : min),
    null,
  ),
)

// ─── Tile Styling ───────────────────────────────────────────────────────────

/**
 * Dynamic colour interpolation for each heatmap tile.
 * Maps sentimentScore (0–100) to normalized VADER compound in [-1.0, +1.0].
 *
 * @param score    - Asset sentimentScore 0–100.
 * @param assetId  - Asset ticker (for brand-colour active border).
 * @param isActive - Whether this tile is the currently viewed asset.
 */
function getTileStyle(
  score: number,
  assetId: RouteAssetId,
  isActive: boolean,
): Record<string, string> {
  const normalized = (score - 50) / 50
  const absVal = Math.abs(normalized)

  let bg: string
  let border: string
  let shadow: string

  if (normalized > 0) {
    bg     = `rgba(16, 185, 129, ${0.08 + absVal * 0.32})`
    border = `rgba(16, 185, 129, ${0.25 + absVal * 0.45})`
    shadow = `inset 0 1px 1px rgba(255,255,255,0.05), 0 0 ${12 + absVal * 16}px rgba(16, 185, 129, ${0.08 + absVal * 0.28})`
  } else if (normalized < 0) {
    bg     = `rgba(244, 63, 94, ${0.08 + absVal * 0.32})`
    border = `rgba(244, 63, 94, ${0.25 + absVal * 0.45})`
    shadow = `inset 0 1px 1px rgba(255,255,255,0.05), 0 0 ${12 + absVal * 16}px rgba(244, 63, 94, ${0.08 + absVal * 0.28})`
  } else {
    bg     = 'rgba(30, 41, 59, 0.40)'
    border = 'rgba(255,255,255,0.06)'
    shadow = 'inset 0 1px 1px rgba(255,255,255,0.02)'
  }

  if (isActive) {
    const brandColor = getAssetBrandColor(assetId)
    border = brandColor
    shadow = `${shadow}, 0 0 18px ${brandColor}40`
  }

  return { backgroundColor: bg, borderColor: border, boxShadow: shadow }
}

/** Navigates to the selected asset. */
function selectAsset(id: RouteAssetId): void {
  router.push(`/asset/${id}`)
}

/** Returns the rank badge label for a given asset (🥇🥈 for bullish, ⚠ for bearish). */
function rankBadge(asset: AssetMetrics): string | null {
  if (topBullish.value[0]?.id === asset.id) return '#1 Bull'
  if (topBullish.value[1]?.id === asset.id) return '#2 Bull'
  if (topBearish.value?.id === asset.id && heatmapAssets.value.length > 2) return '#1 Bear'
  return null
}

function rankBadgeClass(asset: AssetMetrics): string {
  if (topBullish.value[0]?.id === asset.id) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  if (topBullish.value[1]?.id === asset.id) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  return 'bg-rose-500/15 text-rose-300 border-rose-500/25'
}
</script>

<template>
  <div class="flex flex-col gap-4">

    <!-- ── Header ─────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 select-none shrink-0">

      <!-- Title block -->
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <Flame class="h-4 w-4 animate-pulse" aria-hidden="true" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground font-display">Market Sentiment Heatmap</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">
            Real-Time VADER Compound Scale [−1.0, +1.0]
          </p>
        </div>
      </div>

      <!-- Fear & Greed Gauge + Legend (right side) -->
      <div class="flex items-center gap-5 flex-wrap">

        <!-- Compact SVG arc gauge -->
        <div
          v-if="fearGreedIndex !== null"
          class="flex flex-col items-center gap-0.5 select-none"
          :aria-label="`Fear & Greed Index: ${fearGreedIndex} — ${fearGreedLabel(fearGreedIndex)}`"
        >
          <svg width="80" height="44" viewBox="0 0 80 44" aria-hidden="true">
            <!-- Background arc track -->
            <path
              d="M 8 40 A 32 32 0 0 1 72 40"
              fill="none"
              stroke="rgba(255,255,255,0.07)"
              stroke-width="6"
              stroke-linecap="round"
            />
            <!-- Filled arc: colour changes with index -->
            <path
              d="M 8 40 A 32 32 0 0 1 72 40"
              fill="none"
              :stroke="fearGreedIndex >= 60 ? '#10b981' : fearGreedIndex >= 45 ? '#94a3b8' : '#f43f5e'"
              stroke-width="6"
              stroke-linecap="round"
              stroke-dasharray="100.5"
              :stroke-dashoffset="100.5 - (fearGreedIndex / 100) * 100.5"
              style="transition: stroke-dashoffset 0.6s ease, stroke 0.4s ease;"
            />
            <!-- Needle -->
            <line
              x1="40" y1="40"
              x2="40" y2="12"
              stroke="white"
              stroke-width="2"
              stroke-linecap="round"
              :transform="`rotate(${gaugeNeedleDeg(fearGreedIndex)}, 40, 40)`"
              style="transition: transform 0.6s cubic-bezier(0.34,1.56,0.64,1);"
            />
            <!-- Centre pivot -->
            <circle cx="40" cy="40" r="3" fill="white" opacity="0.8" />
          </svg>
          <div class="text-center leading-none">
            <div
              class="text-sm font-extrabold price-mono"
              :class="fearGreedColorClass(fearGreedIndex)"
            >
              {{ fearGreedIndex }}
            </div>
            <div class="text-[9px] font-semibold text-slate-500 uppercase tracking-wide">
              {{ fearGreedLabel(fearGreedIndex) }}
            </div>
          </div>
        </div>

        <!-- Scale legend -->
        <div class="hidden md:flex items-center gap-3 text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
          <span class="flex items-center gap-1">
            <span class="h-2 w-2 rounded-full bg-bearish" aria-hidden="true" />
            Panic (−1.0)
          </span>
          <span class="flex items-center gap-1">
            <span class="h-2 w-2 rounded-full bg-slate-600" aria-hidden="true" />
            Neutral
          </span>
          <span class="flex items-center gap-1">
            <span class="h-2 w-2 rounded-full bg-bullish" aria-hidden="true" />
            Euphoria (+1.0)
          </span>
        </div>
      </div>
    </div>

    <!-- ── Grid area ──────────────────────────────────────────────────── -->
    <div class="relative min-h-[96px] w-full">

      <!-- Loading skeleton -->
      <div v-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 select-none">
        <div
          v-for="i in 6"
          :key="i"
          class="h-24 rounded-2xl bg-muted/20 border border-border/20 animate-pulse flex flex-col justify-between p-3"
          aria-hidden="true"
        >
          <div class="h-4 w-1/3 bg-muted/40 rounded" />
          <div class="h-6 w-2/3 bg-muted/40 rounded" />
        </div>
      </div>

      <!-- Error state -->
      <div
        v-else-if="isError"
        class="flex flex-col items-center justify-center p-6 border border-rose-500/20 rounded-2xl bg-rose-500/5 gap-2 text-center"
        role="alert"
      >
        <span class="text-xs font-semibold text-rose-400">Failed to load heatmap data</span>
        <button
          class="inline-flex items-center gap-1 px-3 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-[10px] font-extrabold uppercase text-rose-400 border border-rose-500/20 cursor-pointer transition-colors"
          @click="() => refetch()"
        >
          <RefreshCw class="h-3 w-3" aria-hidden="true" />
          Retry
        </button>
      </div>

      <!-- Live heatmap tiles -->
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <button
          v-for="asset in heatmapAssets"
          :key="asset.id"
          class="h-24 rounded-2xl border p-3 flex flex-col justify-between text-left
                 transition-all duration-300 relative group select-none
                 hover-scale-premium overflow-hidden
                 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
          :style="getTileStyle(asset.sentimentScore, asset.id as RouteAssetId, activeAssetId === asset.id)"
          :aria-label="`Switch to ${asset.name}: VADER ${formatVaderScore(sentimentIndexToVader(asset.sentimentScore))}`"
          :aria-pressed="activeAssetId === asset.id"
          @click="selectAsset(asset.id as RouteAssetId)"
        >
          <!-- Glass shine sweep -->
          <div
            class="absolute inset-0 bg-gradient-to-tr from-transparent via-white/[0.05] to-transparent
                   -translate-x-full group-hover:translate-x-full transition-transform duration-[900ms] ease-out pointer-events-none"
            aria-hidden="true"
          />

          <!-- TOP: symbol + brand dot + active indicator -->
          <div class="flex items-center justify-between w-full">
            <div class="flex items-center gap-1.5">
              <span
                class="h-2 w-2 rounded-full shrink-0"
                :style="{ backgroundColor: getAssetBrandColor(asset.id as RouteAssetId) }"
                aria-hidden="true"
              />
              <span class="font-extrabold text-sm tracking-wider uppercase text-white font-display">
                {{ asset.symbol }}
              </span>
            </div>
            <!-- Rank badge -->
            <span
              v-if="rankBadge(asset)"
              class="text-[8px] font-extrabold px-1.5 py-0.5 rounded-full border"
              :class="rankBadgeClass(asset)"
            >
              {{ rankBadge(asset) }}
            </span>
            <!-- Active ping dot (when no rank badge) -->
            <span
              v-else-if="activeAssetId === asset.id"
              class="flex h-2 w-2"
              aria-hidden="true"
            >
              <span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-white/60" />
              <span class="relative inline-flex rounded-full h-2 w-2 bg-white/80" />
            </span>
          </div>

          <!-- MID: VADER compound score (large mono) -->
          <div class="flex items-baseline gap-1 mt-1">
            <span class="font-black text-xl tracking-tight leading-none price-mono">
              {{ formatVaderScore(sentimentIndexToVader(asset.sentimentScore)) }}
            </span>
          </div>

          <!-- BOTTOM: price + 24h change -->
          <div class="flex justify-between items-center w-full text-[10px] font-semibold text-slate-300/80 mt-1 select-none">
            <span class="price-mono truncate max-w-[65%]">
              {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
            </span>
            <span
              class="flex items-center shrink-0"
              :class="asset.change24h >= 0 ? 'text-bullish' : 'text-bearish'"
            >
              <component
                :is="asset.change24h >= 0 ? TrendingUp : TrendingDown"
                class="h-2.5 w-2.5 mr-0.5 shrink-0"
                aria-hidden="true"
              />
              {{ asset.change24h >= 0 ? '+' : '' }}{{ asset.change24h }}%
            </span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
