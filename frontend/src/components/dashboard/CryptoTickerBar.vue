<script setup lang="ts">
/**
 * CryptoTickerBar — A scrolling marquee strip displaying live prices and
 * 24-hour change percentages for all 7 tracked assets.
 *
 * Implementation notes:
 * - The DOM list is duplicated once so the CSS marquee loops seamlessly.
 * - All motion runs via `transform: translateX` on a GPU-composited layer
 *   (`will-change: transform`) to avoid layout thrashing during live ticks.
 * - Animation pauses on pointer-hover so users can read individual values.
 * - The ticker strip halts completely when `prefers-reduced-motion` is active
 *   (handled via `.ticker-track` in index.css).
 * - Data is sourced from the shared `useAssets()` TanStack Query cache;
 *   no extra network request is issued here.
 */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { TrendingUp, TrendingDown, Minus, Activity } from '@lucide/vue'
import { useAssets } from '@/composables/useMarketData'
import {
  formatPrice,
  formatChange,
  getAssetBrandColor,
} from '@/composables/useCryptoFormatters'
import type { RouteAssetId } from '@/types/market'
import type { AssetMetrics } from '@/types/market'

const router = useRouter()
const { data: assets, isLoading } = useAssets()

/**
 * Ordered display list — crypto assets first, then equities.
 * Falls back to an empty array while the query is loading.
 */
const orderedAssets = computed<AssetMetrics[]>(() => {
  if (!assets.value) return []
  const cryptoOrder: RouteAssetId[] = ['BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA']
  const cryptos = cryptoOrder
    .map(id => assets.value!.find(a => a.id === id))
    .filter((a): a is AssetMetrics => a !== undefined)
  const others = assets.value.filter(a => !cryptoOrder.includes(a.id as RouteAssetId))
  return [...cryptos, ...others]
})

/**
 * Returns the Lucide icon component to render next to the percentage change.
 *
 * @param change - 24h percentage change value.
 */
function changeIcon(change: number) {
  if (change > 0) return TrendingUp
  if (change < 0) return TrendingDown
  return Minus
}

/**
 * Returns the Tailwind text-colour class for the percentage change label.
 *
 * @param change - 24h percentage change value.
 */
function changeClass(change: number): string {
  if (change > 0) return 'text-emerald-400'
  if (change < 0) return 'text-rose-400'
  return 'text-slate-400'
}

/** Navigates to the asset dashboard when a ticker item is clicked. */
function handleAssetClick(assetId: string): void {
  router.push(`/asset/${assetId}`)
}
</script>

<template>
  <!-- Sticky top strip with hardware-accelerated overflow clip -->
  <div
    class="relative w-full overflow-hidden border-b border-white/[0.04] z-30 select-none"
    style="background: rgba(6, 8, 18, 0.88); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"
    aria-label="Live crypto price ticker"
    role="marquee"
  >
    <!-- ── Left fade mask ────────────────────────────────────────────── -->
    <div
      class="pointer-events-none absolute inset-y-0 left-0 w-12 z-10"
      style="background: linear-gradient(to right, rgba(6,8,18,0.95) 0%, transparent 100%);"
    />

    <!-- ── Right fade mask ───────────────────────────────────────────── -->
    <div
      class="pointer-events-none absolute inset-y-0 right-0 w-12 z-10"
      style="background: linear-gradient(to left, rgba(6,8,18,0.95) 0%, transparent 100%);"
    />

    <!-- ── Live indicator dot + label ───────────────────────────────── -->
    <div class="absolute left-3 top-1/2 -translate-y-1/2 z-20 hidden sm:flex items-center gap-1.5">
      <Activity class="h-3 w-3 text-gold animate-pulse" aria-hidden="true" />
      <span class="text-[9px] font-bold uppercase tracking-widest text-gold/70 font-display">Live</span>
    </div>

    <!-- ── Loading skeleton ──────────────────────────────────────────── -->
    <div
      v-if="isLoading"
      class="flex items-center gap-6 px-4 py-2.5 sm:pl-20"
    >
      <div
        v-for="i in 7"
        :key="i"
        class="h-3.5 rounded-full skeleton-shimmer shrink-0"
        :style="{ width: `${60 + i * 8}px`, background: 'rgba(255,255,255,0.05)' }"
        aria-hidden="true"
      />
    </div>

    <!-- ── Scrolling ticker track ─────────────────────────────────────── -->
    <!--
      The inner list is rendered twice (v-for on both) so the tail of the
      first copy meets the head of the second copy seamlessly when the
      CSS animation wraps at -50% translateX.
    -->
    <div
      v-else
      class="ticker-track flex items-center gap-0 h-10 sm:pl-16"
      aria-live="polite"
      aria-atomic="false"
    >
      <!--
        Render the list twice in a single flat flex row so the two halves
        are siblings (not nested), keeping the marquee loop pixel-perfect.
      -->
      <template v-for="pass in 2" :key="pass">
        <button
          v-for="asset in orderedAssets"
          :key="`${pass}-${asset.id}`"
          class="flex items-center gap-2 px-4 py-1 shrink-0 rounded-md
                 hover:bg-white/[0.04] transition-colors duration-150 cursor-pointer
                 border-r border-white/[0.04] last:border-r-0 group"
          :aria-label="`${asset.name}: ${formatPrice(asset.price, asset.id as RouteAssetId)}, ${formatChange(asset.change24h)}`"
          @click="handleAssetClick(asset.id)"
        >
          <!-- Asset colour dot -->
          <span
            class="h-2 w-2 rounded-full shrink-0 transition-all duration-200 group-hover:scale-125"
            :style="{ backgroundColor: getAssetBrandColor(asset.id as RouteAssetId) }"
            aria-hidden="true"
          />

          <!-- Symbol -->
          <span class="text-[11px] font-bold text-slate-300 font-display tracking-wide group-hover:text-white transition-colors">
            {{ asset.symbol }}
          </span>

          <!-- Price (JetBrains Mono for tabular numerals) -->
          <span class="text-[11px] font-semibold text-white price-mono tracking-tight">
            {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
          </span>

          <!-- 24h change icon + percentage -->
          <span
            class="flex items-center gap-0.5 text-[10px] font-bold price-mono"
            :class="changeClass(asset.change24h)"
          >
            <component
              :is="changeIcon(asset.change24h)"
              class="h-2.5 w-2.5 shrink-0"
              aria-hidden="true"
            />
            {{ formatChange(asset.change24h) }}
          </span>
        </button>
      </template>
    </div>
  </div>
</template>
