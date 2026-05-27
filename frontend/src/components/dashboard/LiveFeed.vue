<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSentimentArticles } from '@/composables/useMarketData'

import FeedItem from './FeedItem.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { Search, Filter, Sparkles } from '@lucide/vue'
import type { RouteAssetId } from '@/types/market'

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
}>()

const { data: articles, isLoading, isError, refetch } = useSentimentArticles(computed(() => props.assetId))



const searchQuery = ref('')
const selectedFilter = ref<'All' | 'Bullish' | 'Neutral' | 'Bearish'>('All')

const filteredArticles = computed(() => {
  if (!articles.value) return []
  
  return articles.value.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.summary.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      article.keywords.some(kw => kw.toLowerCase().includes(searchQuery.value.toLowerCase()))

    const matchesSentiment = selectedFilter.value === 'All' || article.sentimentLabel === selectedFilter.value

    return matchesSearch && matchesSentiment
  })
})
</script>

<template>
  <div class="glass-card p-6 rounded-3xl border border-border/40 flex flex-col h-[450px] sm:h-[550px] lg:h-full">
    <!-- Header with Ticker -->
    <div class="flex items-center justify-between mb-4 shrink-0 select-none">
      <div class="flex items-center gap-2">
        <div class="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <Sparkles class="h-4.5 w-4.5" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground">Live LLM Feed</h2>
          <p class="text-[10px] text-muted-foreground font-semibold leading-tight">
            Real-time RSS news analysis.
            <span class="text-[9px] text-slate-500 font-medium block mt-0.5">
              Startup seed data is simulated to bypass initial model loading lags.
            </span>
          </p>
        </div>
      </div>
      
      <!-- Mini indicator showing 7s updates -->
      <span class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground bg-muted border border-border/60 px-2.5 py-1 rounded-full">
        <span class="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-ping"></span>
        7s Polling
      </span>
    </div>

    <!-- Filters & Search -->
    <div class="space-y-3 mb-4 shrink-0">
      <!-- Search Input -->
      <div class="relative">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Filter articles, keywords or sources..."
          class="w-full bg-muted/40 border border-border/60 focus:border-primary/50 focus:ring-1 focus:ring-primary/20 rounded-xl py-2 pl-9 pr-4 text-xs font-semibold text-foreground placeholder:text-muted-foreground/60 transition-all outline-none"
        />
      </div>

      <!-- Sentiment Filters -->
      <div class="flex items-center justify-between gap-1 select-none">
        <div class="flex gap-1 overflow-x-auto pb-1 sm:pb-0">
          <button
            v-for="filter in ['All', 'Bullish', 'Neutral', 'Bearish'] as const"
            :key="filter"
            @click="selectedFilter = filter"
            class="px-3 py-1.5 rounded-xl text-[10px] font-extrabold uppercase tracking-wider border transition-all shrink-0"
            :class="[
              selectedFilter === filter
                ? 'bg-primary border-primary text-white shadow-md'
                : 'bg-muted/40 border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/80'
            ]"
          >
            {{ filter }}
          </button>
        </div>
        
        <span class="text-[10px] text-muted-foreground font-bold shrink-0">
          Found: {{ filteredArticles.length }}
        </span>
      </div>
    </div>

    <!-- Scrollable Feed Container -->
    <div class="flex-1 min-h-0 overflow-y-auto pr-1">
      <div v-if="isLoading" class="space-y-4">
        <div v-for="i in 3" :key="i" class="p-5 bg-card/40 border border-border/20 rounded-2xl animate-pulse flex flex-col gap-3">
          <div class="flex justify-between items-center">
            <div class="h-4 w-28 bg-muted rounded"></div>
            <div class="h-4 w-16 bg-muted rounded"></div>
          </div>
          <div class="h-5 w-3/4 bg-muted rounded"></div>
          <div class="h-10 w-full bg-muted rounded"></div>
          <div class="flex gap-2">
            <div class="h-4 w-12 bg-muted rounded"></div>
            <div class="h-4 w-12 bg-muted rounded"></div>
          </div>
        </div>
      </div>

      <!-- Error state -->
      <ErrorState
        v-else-if="isError"
        title="Failed to load news feed"
        description="RSS sentiment data is temporarily unavailable."
        :on-retry="() => refetch()"
      />

      <!-- Empty State -->

      <div
        v-else-if="filteredArticles.length === 0"
        class="h-full flex flex-col items-center justify-center text-center text-muted-foreground p-6"
      >
        <div class="h-12 w-12 rounded-full border border-dashed border-border flex items-center justify-center mb-3">
          <Filter class="h-5 w-5 text-muted-foreground/60" />
        </div>
        <h3 class="text-xs font-bold text-foreground">No matches found</h3>
        <p class="text-[10px] text-muted-foreground max-w-xs mt-1">
          Adjust your filters or try a different search term to display processed articles.
        </p>
      </div>

      <!-- Article list with smooth entry transitions -->
      <TransitionGroup
        v-else
        name="feed"
        tag="div"
        class="space-y-4"
      >
        <FeedItem
          v-for="article in filteredArticles"
          :key="article.id"
          :article="article"
        />
      </TransitionGroup>
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
</style>
