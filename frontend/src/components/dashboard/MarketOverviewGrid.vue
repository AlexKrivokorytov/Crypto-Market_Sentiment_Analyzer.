<script setup lang="ts">
/**
 * MarketOverviewGrid — Bento-grid overview of all 7 tracked assets.
 *
 * Layout:
 *   - Desktop (≥ 1024px): 7-column 2-row bento grid.
 *     BTC is a "hero" card spanning 2 rows and 2 columns.
 *     ETH spans 1 col × 2 rows. Remaining 5 are normal 1×1 cells.
 *   - Tablet (640–1023px): 4 columns, 2 rows.
 *   - Mobile (< 640px): 2 columns.
 *
 * Each card shows: brand color accent, symbol, full name, live price (JetBrains Mono),
 * 24h % change with animated arrow, VADER compound score badge, 24h volume, and a
 * sentiment-tinted glassmorphism background. Clicking navigates to /asset/{id}.
 *
 * Data sourced from shared useAssets() cache; no additional requests issued.
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { TrendingUp, TrendingDown, Minus, ExternalLink } from '@lucide/vue'
import { useAssets } from '@/composables/useMarketData'
import {
  formatPrice,
  formatChange,
  formatVolume,
  formatVaderScore,
  sentimentIndexToVader,
  getAssetBrandColor,
  getAssetGradient,
  getSentimentBadgeClass,
} from '@/composables/useCryptoFormatters'
import type { RouteAssetId, AssetMetrics } from '@/types/market'

const router = useRouter()
const route = useRoute()

const { data: assets, isLoading } = useAssets()

/**
 * Asset display order for the bento grid.
 * BTC is first (hero position), then ETH (tall card), then the rest.
 */
const GRID_ORDER: RouteAssetId[] = ['BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA', 'AAPL']

/** Ordered asset list, filtered to only those returned by the API. */
const orderedAssets = computed<AssetMetrics[]>(() => {
  if (!assets.value) return []
  return GRID_ORDER
    .map(id => assets.value!.find(a => a.id === id))
    .filter((a): a is AssetMetrics => a !== undefined)
})

/** Currently active asset from route URL parameter. */
const activeAssetId = computed(() => route.params.id as string)

/**
 * Returns the Tailwind grid-placement class for a given asset position.
 * BTC → col-span-2 row-span-2 (hero). ETH → row-span-2. Others → 1×1.
 *
 * @param id - Asset ticker symbol.
 * @param index - Zero-based position in the ordered grid list.
 */
function gridCellClass(id: RouteAssetId): string {
  if (id === 'BTC') return 'lg:col-span-2 lg:row-span-2 sm:col-span-2'
  if (id === 'ETH') return 'lg:row-span-2'
  return ''
}

/**
 * Returns `true` if the card should use the larger "hero" layout variant.
 * Currently only BTC is a hero card.
 *
 * @param id - Asset ticker symbol.
 */
function isHeroCard(id: RouteAssetId): boolean {
  return id === 'BTC'
}

/**
 * Returns the VADER compound score derived from the 0–100 sentiment index.
 *
 * @param sentimentScore - 0–100 integer.
 */
function getVaderDisplay(sentimentScore: number): string {
  return formatVaderScore(sentimentIndexToVader(sentimentScore))
}

/**
 * Returns the Tailwind text-colour class for the 24h change value.
 *
 * @param change - 24h percentage change.
 */
function changeTextClass(change: number): string {
  if (change > 0) return 'text-emerald-400'
  if (change < 0) return 'text-rose-400'
  return 'text-slate-400'
}

/**
 * Returns the correct trend icon component for the given change value.
 *
 * @param change - 24h percentage change.
 */
function trendIcon(change: number) {
  if (change > 0) return TrendingUp
  if (change < 0) return TrendingDown
  return Minus
}

/**
 * Returns the CSS border-left accent style for the active card indicator.
 *
 * @param id     - Asset ticker symbol.
 * @param active - Whether this card is the currently viewed asset.
 */
function cardBorderStyle(id: RouteAssetId, active: boolean): Record<string, string> {
  const color = getAssetBrandColor(id)
  if (active) {
    return {
      borderColor: color,
      boxShadow: `0 0 20px -4px ${color}30`,
    }
  }
  return { borderColor: 'rgba(255,255,255,0.06)' }
}

/** Navigates to the selected asset dashboard. */
function handleCardClick(assetId: string): void {
  router.push(`/asset/${assetId}`)
}
</script>

<template>
  <section aria-label="Market Overview — All Assets">
    <!-- ── Loading skeleton grid ───────────────────────────────────────── -->
    <div
      v-if="isLoading"
      class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 auto-rows-[96px]"
    >
      <div
        v-for="i in 7"
        :key="i"
        class="rounded-2xl animate-pulse"
        :class="i === 1 ? 'col-span-2 row-span-2' : i === 2 ? 'row-span-2' : ''"
        style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);"
      />
    </div>

    <!-- ── Live bento grid ─────────────────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 auto-rows-[100px] lg:auto-rows-[108px]"
    >
      <button
        v-for="asset in orderedAssets"
        :key="asset.id"
        :class="[
          'bento-card relative flex flex-col justify-between p-3 sm:p-4 text-left',
          'cursor-pointer group overflow-hidden transition-all duration-250',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-white/30',
          gridCellClass(asset.id as RouteAssetId),
          isHeroCard(asset.id as RouteAssetId) ? 'sm:p-5' : '',
        ]"
        :style="{
          background: getAssetGradient(asset.id as RouteAssetId),
          ...cardBorderStyle(asset.id as RouteAssetId, activeAssetId === asset.id),
        }"
        :aria-label="`View ${asset.name} dashboard — ${formatPrice(asset.price, asset.id as RouteAssetId)}, ${formatChange(asset.change24h)}`"
        :aria-pressed="activeAssetId === asset.id"
        @click="handleCardClick(asset.id)"
      >
        <!-- Glass shine sweep on hover -->
        <div
          class="pointer-events-none absolute inset-0 bg-gradient-to-tr from-transparent via-white/[0.04] to-transparent
                 -translate-x-full group-hover:translate-x-full transition-transform duration-[900ms] ease-out"
          aria-hidden="true"
        />

        <!-- Active asset pulse dot -->
        <span
          v-if="activeAssetId === asset.id"
          class="absolute top-2 right-2 flex h-2 w-2"
          aria-hidden="true"
        >
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-60" />
          <span class="relative inline-flex rounded-full h-2 w-2 bg-white" />
        </span>

        <!-- ── TOP ROW: brand dot + symbol + external link icon ────────── -->
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center gap-1.5">
            <!-- Asset brand colour dot -->
            <span
              class="h-2.5 w-2.5 rounded-full shrink-0 shadow-sm"
              :style="{ backgroundColor: getAssetBrandColor(asset.id as RouteAssetId) }"
              aria-hidden="true"
            />
            <span
              class="font-bold tracking-wide text-white font-display uppercase"
              :class="isHeroCard(asset.id as RouteAssetId) ? 'text-base' : 'text-xs'"
            >
              {{ asset.symbol }}
            </span>
          </div>
          <ExternalLink
            class="h-3 w-3 text-white/20 group-hover:text-white/50 transition-colors shrink-0"
            aria-hidden="true"
          />
        </div>

        <!-- ── MIDDLE: asset name (hero only) + price ─────────────────── -->
        <div class="flex flex-col min-w-0">
          <span
            v-if="isHeroCard(asset.id as RouteAssetId)"
            class="text-[10px] text-slate-400 font-medium truncate mb-0.5"
          >
            {{ asset.name }}
          </span>
          <span
            class="font-bold price-mono tracking-tight text-white leading-none truncate"
            :class="isHeroCard(asset.id as RouteAssetId) ? 'text-xl sm:text-2xl' : 'text-sm sm:text-base'"
          >
            {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
          </span>
        </div>

        <!-- ── BOTTOM ROW: 24h change + sentiment badge ────────────────── -->
        <div class="flex items-center justify-between w-full mt-auto">
          <!-- 24h change -->
          <span
            class="flex items-center gap-0.5 text-[10px] font-bold price-mono"
            :class="changeTextClass(asset.change24h)"
          >
            <component
              :is="trendIcon(asset.change24h)"
              class="h-2.5 w-2.5 shrink-0"
              aria-hidden="true"
            />
            {{ formatChange(asset.change24h) }}
          </span>

          <!-- VADER sentiment badge -->
          <span
            class="text-[9px] font-bold px-1.5 py-0.5 rounded-full border price-mono shrink-0"
            :class="getSentimentBadgeClass(asset.sentimentLabel)"
          >
            {{ getVaderDisplay(asset.sentimentScore) }}
          </span>
        </div>

        <!-- Hero card only: extra row with volume + full name ──────────── -->
        <template v-if="isHeroCard(asset.id as RouteAssetId)">
          <div class="flex items-center justify-between w-full pt-1.5 border-t border-white/[0.06] mt-1">
            <span class="text-[10px] text-slate-500 font-medium">Vol 24h</span>
            <span class="text-[10px] font-semibold text-slate-300 price-mono">
              {{ formatVolume(asset.volume24h) }}
            </span>
          </div>
        </template>
      </button>
    </div>
  </section>
</template>
