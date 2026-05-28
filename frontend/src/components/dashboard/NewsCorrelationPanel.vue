<script setup lang="ts">
/**
 * NewsCorrelationPanel — Displays the top-3 most sentiment-impactful news articles
 * for the currently viewed asset alongside a VADER-correlation bar chart.
 *
 * Sprint 5 features:
 * - Ranked by |sentimentScore − 50| (divergence from neutral) descending.
 * - Each card shows: rank badge, sentiment label/VADER value, title, source,
 *   age, impact bar, and relevant asset keyword tags.
 * - Asset brand colour used as impact-bar accent.
 * - formatRelativeTime from useCryptoFormatters for human-readable age.
 * - No extra API calls — shares useSentimentArticles cache.
 */

import { computed } from 'vue'
import { Zap, ExternalLink, TrendingUp, TrendingDown, Minus } from '@lucide/vue'
import { useSentimentArticles } from '@/composables/useMarketData'
import {
  formatRelativeTime,
  formatVaderScore,
  sentimentIndexToVader,
  getAssetBrandColor,
  getSentimentBadgeClass,
} from '@/composables/useCryptoFormatters'
import type { RouteAssetId, SentimentArticle } from '@/types/market'

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
}>()

const { data: articles, isLoading } = useSentimentArticles(computed(() => props.assetId))

/**
 * Returns the top-3 articles sorted by absolute VADER divergence (|score − 50|).
 * Articles closest to extreme sentiment dominate the panel.
 */
const topArticles = computed<SentimentArticle[]>(() => {
  if (!articles.value) return []
  return [...articles.value]
    .sort((a, b) => Math.abs(b.sentimentScore - 50) - Math.abs(a.sentimentScore - 50))
    .slice(0, 3)
})

/** Brand colour for the active asset (used on impact bars). */
const brandColor = computed(() => getAssetBrandColor(props.assetId))

/**
 * Computes the VADER compound string for display.
 *
 * @param score - Raw sentimentScore (0–100).
 */
function vaderDisplay(score: number): string {
  return formatVaderScore(sentimentIndexToVader(score))
}

/**
 * Returns the width percentage for the impact bar (0–100%) derived from
 * the absolute divergence from neutral (score=50) scaled to full range.
 *
 * @param score - Raw sentimentScore 0–100.
 */
function impactBarWidth(score: number): number {
  return Math.min(100, Math.abs(score - 50) * 2)
}

/**
 * Returns the impact bar colour based on sentiment direction.
 *
 * @param score - Raw sentimentScore 0–100.
 */
function impactBarColor(score: number): string {
  if (score > 55) return '#10b981'  // bullish green
  if (score < 45) return '#f43f5e'  // bearish red
  return '#6b7280'                   // neutral gray
}

/**
 * Returns rank medal emoji for the first three positions.
 *
 * @param index - Zero-based rank index.
 */
function rankLabel(index: number): string {
  return ['#1', '#2', '#3'][index] ?? `#${index + 1}`
}

/**
 * Returns the Lucide icon component for a sentiment score.
 *
 * @param score - Raw sentimentScore 0–100.
 */
function sentimentIcon(score: number) {
  if (score > 55) return TrendingUp
  if (score < 45) return TrendingDown
  return Minus
}

/**
 * Returns the text-colour class for the sentiment icon/label.
 *
 * @param score - Raw sentimentScore 0–100.
 */
function sentimentColorClass(score: number): string {
  if (score > 55) return 'text-emerald-400'
  if (score < 45) return 'text-rose-400'
  return 'text-slate-400'
}
</script>

<template>
  <div class="glass-card p-5 rounded-3xl border border-border/40 flex flex-col gap-4">

    <!-- ── Header ─────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between shrink-0 select-none">
      <div class="flex items-center gap-2">
        <div
          class="p-2 rounded-lg border"
          :style="{
            background: `${brandColor}18`,
            borderColor: `${brandColor}35`,
          }"
          aria-hidden="true"
        >
          <Zap class="h-4 w-4" :style="{ color: brandColor }" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground font-display">Top Impact News</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">
            Highest VADER divergence articles · {{ props.assetId }}
          </p>
        </div>
      </div>

      <!-- Article count badge -->
      <span
        v-if="articles"
        class="text-[10px] font-bold px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-slate-800/50"
      >
        {{ articles.length }} articles
      </span>
    </div>

    <!-- ── Loading skeleton ──────────────────────────────────────────── -->
    <div v-if="isLoading" class="flex flex-col gap-3">
      <div
        v-for="i in 3"
        :key="i"
        class="rounded-2xl p-4 flex flex-col gap-2 animate-pulse"
        style="background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.05);"
        aria-hidden="true"
      >
        <div class="flex justify-between">
          <div class="h-3 w-16 rounded bg-slate-800" />
          <div class="h-3 w-10 rounded bg-slate-800" />
        </div>
        <div class="h-4 w-3/4 rounded bg-slate-800" />
        <div class="h-2 w-full rounded-full bg-slate-800" />
      </div>
    </div>

    <!-- ── Empty state ───────────────────────────────────────────────── -->
    <div
      v-else-if="topArticles.length === 0"
      class="flex flex-col items-center justify-center py-8 text-slate-500 gap-2"
      aria-live="polite"
    >
      <Zap class="h-8 w-8 opacity-20" aria-hidden="true" />
      <p class="text-xs font-medium">No articles loaded yet</p>
    </div>

    <!-- ── Top-3 article cards ───────────────────────────────────────── -->
    <div v-else class="flex flex-col gap-3" aria-label="Top impact articles by VADER divergence">
      <article
        v-for="(article, index) in topArticles"
        :key="article.id"
        class="group relative flex flex-col gap-2 p-4 rounded-2xl border transition-all duration-200 hover:border-white/10 overflow-hidden"
        style="background: rgba(13, 16, 32, 0.45); border-color: rgba(255,255,255,0.06);"
      >
        <!-- Glass shine on hover -->
        <div
          class="pointer-events-none absolute inset-0 bg-gradient-to-tr from-transparent via-white/[0.03] to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-[800ms] ease-out"
          aria-hidden="true"
        />

        <!-- ── Top row: rank + sentiment + age ─────────────────────── -->
        <div class="flex items-center justify-between">
          <!-- Rank badge -->
          <span
            class="text-[10px] font-extrabold px-2 py-0.5 rounded-full border font-display"
            :style="{
              background: `${brandColor}18`,
              borderColor: `${brandColor}35`,
              color: brandColor,
            }"
          >
            {{ rankLabel(index) }}
          </span>

          <div class="flex items-center gap-2">
            <!-- VADER badge -->
            <span
              class="text-[9px] font-extrabold px-1.5 py-0.5 rounded-full border price-mono"
              :class="getSentimentBadgeClass(article.sentimentLabel)"
            >
              {{ vaderDisplay(article.sentimentScore) }}
            </span>

            <!-- Age -->
            <span class="text-[10px] text-slate-500 font-medium shrink-0">
              {{ formatRelativeTime(article.timestamp) }}
            </span>
          </div>
        </div>

        <!-- ── Article title ────────────────────────────────────────── -->
        <a
          :href="article.url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-start gap-1 group/link"
          :aria-label="`Read: ${article.title} (opens in new tab)`"
        >
          <p class="text-xs font-semibold text-slate-200 leading-snug line-clamp-2 group-hover/link:text-white transition-colors">
            {{ article.title }}
          </p>
          <ExternalLink class="h-3 w-3 text-slate-500 group-hover/link:text-slate-300 shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
        </a>

        <!-- ── Source + sentiment icon row ─────────────────────────── -->
        <div class="flex items-center justify-between">
          <span class="text-[10px] text-slate-500 font-medium truncate max-w-[60%]">{{ article.source }}</span>
          <span
            class="flex items-center gap-1 text-[10px] font-bold price-mono"
            :class="sentimentColorClass(article.sentimentScore)"
          >
            <component
              :is="sentimentIcon(article.sentimentScore)"
              class="h-3 w-3 shrink-0"
              aria-hidden="true"
            />
            {{ article.sentimentLabel }}
          </span>
        </div>

        <!-- ── Impact bar ───────────────────────────────────────────── -->
        <div
          class="h-1 w-full rounded-full overflow-hidden"
          style="background: rgba(255,255,255,0.05);"
          role="meter"
          :aria-valuenow="impactBarWidth(article.sentimentScore)"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="`Sentiment impact: ${impactBarWidth(article.sentimentScore).toFixed(0)}%`"
        >
          <div
            class="h-full rounded-full transition-all duration-700 ease-out"
            :style="{
              width: `${impactBarWidth(article.sentimentScore)}%`,
              background: impactBarColor(article.sentimentScore),
            }"
          />
        </div>

        <!-- ── Keyword tags ──────────────────────────────────────────── -->
        <div v-if="article.keywords?.length" class="flex flex-wrap gap-1">
          <span
            v-for="kw in article.keywords.slice(0, 4)"
            :key="kw"
            class="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60"
          >
            {{ kw }}
          </span>
        </div>
      </article>
    </div>
  </div>
</template>
