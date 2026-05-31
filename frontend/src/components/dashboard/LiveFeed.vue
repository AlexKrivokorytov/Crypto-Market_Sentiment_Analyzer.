<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSentimentArticles, useBackendConfig } from '@/composables/useMarketData'
import { useNewsStore } from '@/composables/useNewsStore'
import FeedItem from './FeedItem.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { Search, Filter, Sparkles, AlertTriangle, CheckCircle2 } from '@lucide/vue'
import type { RouteAssetId } from '@/types/market'
import { marketApi } from '@/services/api'
import { useQueryClient } from '@tanstack/vue-query'
import { useVirtualizer } from '@tanstack/vue-virtual'

/** Per-item component refs keyed by article ID, used to call setAnalysisError() directly. */
const feedItemRefs = new Map<string, InstanceType<typeof FeedItem>>()

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
}>()

const newsStore = useNewsStore()
const queryClient = useQueryClient()

// Trigger store hydration immediately on mount
onMounted(() => {
  newsStore.hydrateStore()
})

const { data: serverArticles, isLoading, isError, refetch } = useSentimentArticles(computed(() => props.assetId))
const { data: config } = useBackendConfig()

// Reactively watch for incoming API payloads and synchronize with the offline Pinia cache
watch(serverArticles, (newArticles) => {
  if (newArticles) {
    newsStore.setArticles(newArticles)
  }
}, { immediate: true })

const handleRequestAiAnalysis = async (articleId: string) => {
  try {
    const updatedArticle = await marketApi.analyzeArticle(articleId)
    if (updatedArticle) {
      newsStore.updateArticle(updatedArticle)
      queryClient.invalidateQueries({ queryKey: ['articles', props.assetId] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    }
  } catch (err) {
    // Look up the FeedItem by article ID so we can call setAnalysisError() on it
    const itemRef = feedItemRefs.get(articleId)

    if (err instanceof Error && err.message.includes('status=429')) {
      const msg = 'Rate limit reached — OpenRouter is busy. Wait ~30s and try again.'
      itemRef?.setAnalysisError(msg)
    } else if (err instanceof Error && err.message.includes('status=504')) {
      const msg = '⚠ AI service took too long to respond. Try again later.'
      itemRef?.setAnalysisError(msg)
    } else {
      itemRef?.setAnalysisError('Analysis failed. Please try again.')
    }
    console.error('[LiveFeed] Failed to run live AI analysis:', err)
  }
}

const searchQuery = ref('')
const selectedFilter = ref<'All' | 'Bullish' | 'Neutral' | 'Bearish'>('All')

// Compute filtered articles on top of the hydrated Pinia store rather than raw server states
const filteredArticles = computed(() => {
  return newsStore.articles.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.summary.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.keywords.some(kw => kw.toLowerCase().includes(searchQuery.value.toLowerCase()))

    const matchesSentiment = selectedFilter.value === 'All' || article.sentimentLabel === selectedFilter.value

    return matchesSearch && matchesSentiment
  })
})

const showSkeleton = computed(() => isLoading.value && newsStore.articles.length === 0)
const showEmptyState = computed(() => !isLoading.value && filteredArticles.value.length === 0)

const parentRef = ref<HTMLElement | null>(null)

const virtualizer = useVirtualizer(
  computed(() => ({
    count: filteredArticles.value.length,
    getScrollElement: () => parentRef.value,
    estimateSize: () => 140, // Base terminal log height estimate
    overscan: 5,
  }))
)

const virtualItems = computed(() => virtualizer.value.getVirtualItems())
</script>

<template>
  <div class="flex flex-col h-[450px] sm:h-[550px] lg:h-full select-none">
    <!-- Header Area -->
    <div class="flex items-center justify-between mb-4 shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <Sparkles class="h-4.5 w-4.5" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-slate-100">Live Sentiment Feed</h2>
          <p class="text-[10px] text-slate-400 font-semibold leading-tight mt-0.5">
            Real-time RSS news analysis processed by VADER engine.
          </p>
        </div>
      </div>
      
      <!-- Mini status pill mapping standard server wakeups -->
      <span 
        v-if="isLoading" 
        class="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full animate-pulse"
      >
        <AlertTriangle class="h-3 w-3" />
        Waking Server...
      </span>
      <span 
        v-else-if="isError"
        class="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-full"
      >
        <AlertTriangle class="h-3 w-3" />
        Cached View
      </span>
      <span 
        v-else
        class="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full"
      >
        <CheckCircle2 class="h-3 w-3" />
        Synced
      </span>
    </div>

    <!-- Offline Alert Banner (Graceful Degradation) -->
    <div 
      v-if="isError && newsStore.articles.length > 0"
      class="mb-3 p-2.5 rounded-xl bg-amber-500/5 border border-amber-500/10 text-[10px] text-amber-300 flex items-center justify-between gap-2 shrink-0 animate-fade-in"
    >
      <div class="flex items-center gap-2">
        <AlertTriangle class="h-4 w-4 text-amber-400 shrink-0" />
        <span>Backend temporarily unavailable. Showing cached articles.</span>
      </div>
      <button 
        @click="refetch()" 
        class="px-2 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-200 transition-all font-semibold uppercase text-[9px]"
      >
        Retry
      </button>
    </div>

    <!-- Filters & Search Bar -->
    <div class="space-y-3 mb-4 shrink-0">
      <!-- Search Input -->
      <div class="relative">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Filter articles, keywords or sources..."
          class="w-full bg-slate-900/40 border border-border/60 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 rounded-xl py-2 pl-9 pr-4 text-xs font-semibold text-slate-100 placeholder:text-slate-500 transition-all outline-none"
        />
      </div>

      <!-- Sentiment Filters -->
      <div class="flex items-center justify-between gap-1">
        <div class="flex gap-1 overflow-x-auto pb-1 sm:pb-0">
          <button
            v-for="filter in ['All', 'Bullish', 'Neutral', 'Bearish'] as const"
            :key="filter"
            @click="selectedFilter = filter"
            class="px-3 py-1.5 rounded-xl text-[10px] font-extrabold uppercase tracking-wider border transition-all shrink-0"
            :class="[
              selectedFilter === filter
                ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                : 'bg-slate-900/40 border-border/60 text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
            ]"
          >
            {{ filter }}
          </button>
        </div>
        
        <span class="text-[10px] text-slate-400 font-bold shrink-0">
          Found: {{ filteredArticles.length }}
        </span>
      </div>
    </div>

    <!-- Scrollable Feed Container -->
    <div ref="parentRef" class="flex-1 min-h-0 overflow-y-auto pr-1 relative">
      <!-- Active loading state when cache is empty -->
      <div v-if="showSkeleton" class="space-y-4">
        <div v-for="i in 3" :key="i" class="p-5 bg-slate-900/20 border border-border/20 rounded-2xl animate-pulse flex flex-col gap-3">
          <div class="flex justify-between items-center">
            <div class="h-4 w-28 bg-slate-800 rounded"></div>
            <div class="h-4 w-16 bg-slate-800 rounded"></div>
          </div>
          <div class="h-5 w-3/4 bg-slate-800 rounded"></div>
          <div class="h-10 w-full bg-slate-800 rounded"></div>
          <div class="flex gap-2">
            <div class="h-4 w-12 bg-slate-800 rounded"></div>
            <div class="h-4 w-12 bg-slate-800 rounded"></div>
          </div>
        </div>
      </div>

      <!-- Hard Error State (Only when absolutely no articles exist in cache) -->
      <ErrorState
        v-else-if="isError && newsStore.articles.length === 0"
        title="Failed to load news feed"
        description="RSS sentiment data is temporarily unavailable and no local cache was found."
        :on-retry="() => refetch()"
      />

      <!-- Empty State -->
      <div
        v-else-if="showEmptyState"
        class="h-full flex flex-col items-center justify-center text-center text-slate-400 p-6"
      >
        <div class="h-12 w-12 rounded-full border border-dashed border-border flex items-center justify-center mb-3">
          <Filter class="h-5 w-5 text-slate-500" />
        </div>
        <h3 class="text-xs font-bold text-slate-200">No matches found</h3>
        <p class="text-[10px] text-slate-400 max-w-xs mt-1">
          Adjust your filters or try a different search term to display processed articles.
        </p>
      </div>

      <!-- Virtualized Article list -->
      <div
        v-else
        class="relative w-full"
        :style="{ height: `${virtualizer.getTotalSize()}px` }"
      >
        <div
          v-for="virtualItem in virtualItems"
          :key="String(virtualItem.key)"
          :data-index="virtualItem.index"
          class="absolute top-0 left-0 w-full"
          :style="{
            transform: `translateY(${virtualItem.start}px)`,
          }"
          :ref="(el) => virtualizer.measureElement(el as Element | null)"
        >
          <div class="pb-4" v-if="filteredArticles[virtualItem.index]"> <!-- gap equivalent -->
            <FeedItem
              :ref="(el) => { if (el && filteredArticles[virtualItem.index]) feedItemRefs.set(filteredArticles[virtualItem.index]!.id, el as InstanceType<typeof FeedItem>) }"
              :article="filteredArticles[virtualItem.index]!"
              :model-name="config?.llm_model"
              @request-ai-analysis="handleRequestAiAnalysis"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Transition animation for live list items */
.feed-enter-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.feed-leave-active {
  transition: all 0.3s ease;
  position: absolute;
}
.feed-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.98);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
}
.feed-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.feed-move {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
</style>
