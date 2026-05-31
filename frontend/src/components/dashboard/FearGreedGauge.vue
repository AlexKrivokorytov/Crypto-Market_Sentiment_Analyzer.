<script setup lang="ts">
/**
 * FearGreedGauge — Animated arc gauge showing the Crypto Fear & Greed Index.
 *
 * Data: fetched from /api/v1/fear-greed (Alternative.me proxy, cached 1h).
 * Visual: SVG arc gauge (0–180°) + 7-day sparkline dots + classification badge.
 */

import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { TrendingUp, TrendingDown, Minus, RefreshCw } from '@lucide/vue'
import { marketApi, type FearGreedData } from '@/services/api'

const { data, isLoading, isError, refetch } = useQuery<FearGreedData>({
  queryKey: ['fear-greed'],
  queryFn: () => marketApi.getFearGreedIndex(),
  staleTime: 1000 * 60 * 60, // 1 hour — mirrors backend cache
  gcTime: 1000 * 60 * 70,
  retry: 2,
})

/** Converts 0–100 value to SVG arc path degrees (0 = left, 180 = right). */
const arcAngle = computed(() => {
  if (!data.value) return 0
  return (data.value.value / 100) * 180
})

/**
 * Generates the SVG `d` attribute for a partial circle arc.
 * Uses a 120×60 viewBox with a semicircle centred at (60,60).
 */
const arcPath = computed(() => {
  const cx = 60
  const cy = 60
  const r = 50
  const startAngle = 180 // degrees (left side)
  const endAngle = 180 + arcAngle.value
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const x1 = cx + r * Math.cos(toRad(startAngle))
  const y1 = cy + r * Math.sin(toRad(startAngle))
  const x2 = cx + r * Math.cos(toRad(endAngle))
  const y2 = cy + r * Math.sin(toRad(endAngle))
  const largeArc = arcAngle.value > 180 ? 1 : 0
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
})

/** Returns a tailwind colour class for the current F&G classification. */
const classificationColor = computed(() => {
  if (!data.value) return 'text-slate-400'
  const label = data.value.classification.toLowerCase()
  if (label.includes('extreme fear')) return 'text-rose-500'
  if (label.includes('fear')) return 'text-orange-400'
  if (label.includes('neutral')) return 'text-slate-300'
  if (label.includes('greed') && !label.includes('extreme')) return 'text-emerald-400'
  if (label.includes('extreme greed')) return 'text-emerald-300'
  return 'text-slate-400'
})

/** Returns the SVG arc stroke colour for the gauge needle. */
const arcColor = computed(() => {
  if (!data.value) return '#64748b'
  const v = data.value.value
  if (v <= 25) return '#ef4444'
  if (v <= 45) return '#f97316'
  if (v <= 55) return '#94a3b8'
  if (v <= 75) return '#34d399'
  return '#6ee7b7'
})

/** Returns the icon component for the current sentiment direction. */
const SentimentIcon = computed(() => {
  if (!data.value) return Minus
  const v = data.value.value
  if (v < 45) return TrendingDown
  if (v > 55) return TrendingUp
  return Minus
})

/** 7-day sparkline: normalise values to a 0–100 range for dot height. */
const sparklineDots = computed((): Array<{ x: number; y: number; value: number }> => {
  const h = data.value?.history ?? []
  if (!h.length) return []
  return h.map((point, idx) => ({
    x: (idx / Math.max(h.length - 1, 1)) * 100,
    y: 100 - point.value, // invert so high = top
    value: point.value,
  }))
})
</script>

<template>
  <div class="flex flex-col items-center gap-4 p-4 h-full overflow-y-auto custom-scrollbar select-none">

    <!-- Loading state -->
    <div v-if="isLoading" class="flex-1 flex items-center justify-center">
      <RefreshCw class="h-6 w-6 text-slate-500 animate-spin" />
    </div>

    <!-- Error state -->
    <div v-else-if="isError" class="flex-1 flex flex-col items-center justify-center gap-2">
      <p class="text-xs text-rose-400">Failed to load index</p>
      <button
        @click="refetch()"
        class="text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
      >
        Retry
      </button>
    </div>

    <!-- Main content -->
    <template v-else-if="data">
      <!-- SVG Arc Gauge -->
      <div class="relative flex items-end justify-center w-full">
        <svg
          viewBox="0 0 120 70"
          class="w-full max-w-[220px]"
          aria-label="Fear and Greed Index gauge"
        >
          <!-- Background track -->
          <path
            d="M 60 60 m -50 0 a 50 50 0 0 1 100 0"
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            stroke-width="8"
            stroke-linecap="round"
          />

          <!-- Colour segments (background gradient bands) -->
          <path d="M 10 60 A 50 50 0 0 1 29.3 21.7" fill="none" stroke="#ef4444" stroke-width="7" stroke-linecap="round" opacity="0.2" />
          <path d="M 29.3 21.7 A 50 50 0 0 1 60 10" fill="none" stroke="#f97316" stroke-width="7" stroke-linecap="round" opacity="0.2" />
          <path d="M 60 10 A 50 50 0 0 1 90.7 21.7" fill="none" stroke="#94a3b8" stroke-width="7" stroke-linecap="round" opacity="0.2" />
          <path d="M 90.7 21.7 A 50 50 0 0 1 110 60" fill="none" stroke="#34d399" stroke-width="7" stroke-linecap="round" opacity="0.2" />

          <!-- Active arc (value indicator) -->
          <path
            :d="arcPath"
            fill="none"
            :stroke="arcColor"
            stroke-width="8"
            stroke-linecap="round"
            style="filter: drop-shadow(0 0 6px currentColor)"
          />

          <!-- Needle dot at arc tip -->
          <circle
            :cx="60 + 50 * Math.cos(((180 + arcAngle) * Math.PI) / 180)"
            :cy="60 + 50 * Math.sin(((180 + arcAngle) * Math.PI) / 180)"
            r="4"
            :fill="arcColor"
            style="filter: drop-shadow(0 0 8px currentColor)"
          />
        </svg>

        <!-- Centre value label (absolute over SVG) -->
        <div class="absolute bottom-0 flex flex-col items-center pb-1">
          <span class="text-3xl font-black price-mono leading-none" :class="classificationColor">
            {{ data.value }}
          </span>
          <span class="text-[9px] text-slate-500 font-bold uppercase tracking-widest">/100</span>
        </div>
      </div>

      <!-- Classification badge -->
      <div class="flex items-center gap-2">
        <component :is="SentimentIcon" class="h-4 w-4 shrink-0" :class="classificationColor" />
        <span class="text-sm font-bold tracking-tight" :class="classificationColor">
          {{ data.classification }}
        </span>
      </div>

      <!-- 7-day sparkline -->
      <div class="w-full" v-if="sparklineDots.length">
        <p class="text-[10px] text-slate-600 font-semibold uppercase tracking-wider mb-2">7-Day History</p>
        <div class="relative h-12 w-full">
          <svg
            viewBox="0 0 100 100"
            class="w-full h-full"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <!-- Sparkline line -->
            <polyline
              :points="sparklineDots.map(d => `${d.x},${d.y}`).join(' ')"
              fill="none"
              :stroke="arcColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              opacity="0.6"
            />
            <!-- Data dots -->
            <circle
              v-for="dot in sparklineDots"
              :key="dot.x"
              :cx="dot.x"
              :cy="dot.y"
              r="4"
              :fill="arcColor"
              opacity="0.9"
            />
          </svg>

          <!-- Hover value labels -->
          <div class="absolute inset-0 flex items-end justify-between px-1">
            <span
              v-for="dot in sparklineDots"
              :key="dot.x"
              class="text-[8px] price-mono text-slate-500 leading-none"
            >
              {{ dot.value }}
            </span>
          </div>
        </div>
      </div>

      <!-- Last updated -->
      <p class="text-[10px] text-slate-600 font-mono mt-auto">
        Updated: {{ new Date(data.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric' }) }}
      </p>
    </template>

  </div>
</template>
