<script setup lang="ts">
import { ref } from 'vue'
import type { SentimentArticle } from '@/types/market'
import { MessageSquare, ArrowRight, ChevronDown, ChevronUp, Cpu, Calendar, ShieldCheck, Sparkles, Loader2 } from '@lucide/vue'

const props = defineProps<{
  article: SentimentArticle
}>()

const isExpanded = ref(false)

const emit = defineEmits<{
  (e: 'requestAiAnalysis', articleId: string): void
}>()

const isAiRequestPending = ref(false)

const triggerAiAnalysis = () => {
  if (isAiRequestPending.value) return
  isAiRequestPending.value = true
  emit('requestAiAnalysis', props.article.id)
  
  // Simulate active spinner loader for 2 seconds to wow the user
  setTimeout(() => {
    isAiRequestPending.value = false
  }, 2000)
}


const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatDate = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleDateString([], { month: 'short', day: '2-digit' })
}
</script>

<template>
  <div
    class="glass-card p-5 rounded-2xl border transition-all duration-300 relative overflow-hidden group flex flex-col gap-3"
    :class="[
      article.sentimentLabel === 'Bullish'
        ? 'hover:border-bullish/30 hover:bg-bullish/5'
        : article.sentimentLabel === 'Bearish'
        ? 'hover:border-bearish/30 hover:bg-bearish/5'
        : 'hover:border-primary/20 hover:bg-muted/40'
    ]"
  >
    <!-- Card Header Info -->
    <div class="flex items-center justify-between text-xs font-semibold select-none">
      <div class="flex items-center gap-2 text-muted-foreground">
        <span class="text-foreground font-bold">{{ article.source }}</span>
        <span>•</span>
        <span class="flex items-center gap-1">
          <Calendar class="h-3 w-3" />
          {{ formatDate(article.timestamp) }} {{ formatTime(article.timestamp) }}
        </span>
      </div>

      <!-- Sentiment and Confidence Badges -->
      <div class="flex items-center gap-2">
        <span 
          class="px-2 py-0.5 rounded border text-[9px] uppercase font-extrabold tracking-wider"
          :class="[
            article.is_fallback 
              ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' 
              : 'bg-violet-500/10 text-violet-400 border-violet-500/20'
          ]"
        >
          {{ article.is_fallback ? 'Local Algorithm (VADER)' : 'AI Analysis (LLaMA)' }}
        </span>
        <span
          class="px-2 py-0.5 rounded border text-[9px] uppercase font-extrabold tracking-wider"
          :class="[
            article.sentimentLabel === 'Bullish'
              ? 'bg-bullish/10 text-bullish border-bullish/30'
              : article.sentimentLabel === 'Bearish'
              ? 'bg-bearish/10 text-bearish border-bearish/30'
              : 'bg-neutral/10 text-neutral border-neutral/30'
          ]"
        >
          {{ article.sentimentLabel }}
        </span>
        <span class="flex items-center gap-0.5 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-[9px] text-indigo-400 font-extrabold uppercase">
          <ShieldCheck class="h-3 w-3" />
          {{ Math.round(article.confidence * 100) }}%
        </span>
      </div>
    </div>

    <!-- Title & Summary -->
    <div>
      <h3 class="text-sm font-bold text-foreground leading-snug group-hover:text-primary transition-colors">
        {{ article.title }}
      </h3>
      <p class="text-xs text-slate-400 font-medium leading-relaxed mt-2 font-sans">
        {{ article.summary }}
      </p>
    </div>

    <!-- Keywords Tag List -->
    <div class="flex flex-wrap gap-1.5 mt-1">
      <span
        v-for="kw in article.keywords"
        :key="kw"
        class="text-[10px] font-semibold text-muted-foreground bg-muted/40 border border-border/60 px-2 py-0.5 rounded-md hover:bg-muted/80 transition-colors"
      >
        #{{ kw }}
      </span>
    </div>

    <!-- Expandable Actions -->
    <div class="border-t border-border/40 pt-3 mt-1 flex justify-between items-center select-none">
      <div class="flex items-center gap-4">
        <button
          @click="isExpanded = !isExpanded"
          class="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
        >
          <Cpu class="h-3.5 w-3.5 text-primary" :class="[isExpanded ? 'animate-pulse' : '']" />
          LLM Agent Analysis
          <component :is="isExpanded ? ChevronUp : ChevronDown" class="h-3 w-3 text-muted-foreground" />
        </button>

        <button
          @click="triggerAiAnalysis"
          :disabled="isAiRequestPending"
          class="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-wider text-indigo-400 hover:text-indigo-300 disabled:text-indigo-400/50 disabled:cursor-not-allowed transition-colors"
        >
          <component :is="isAiRequestPending ? Loader2 : Sparkles" class="h-3.5 w-3.5" :class="[isAiRequestPending ? 'animate-spin' : '']" />
          {{ isAiRequestPending ? 'Analyzing...' : 'Request Live AI Sentiment' }}
        </button>
      </div>
      
      <a
        :href="article.url"
        class="flex items-center gap-1 text-[10px] font-extrabold uppercase tracking-wider text-primary hover:text-white transition-colors"
      >
        Source Link
        <ArrowRight class="h-3 w-3" />
      </a>
    </div>

    <!-- Expandable Content Panel -->
    <div
      v-if="isExpanded"
      class="bg-muted/30 border border-border/50 rounded-xl p-4 mt-2 flex flex-col gap-2 transition-all duration-300"
    >
      <div class="flex items-center gap-1.5 text-xs font-bold text-foreground select-none">
        <MessageSquare class="h-3.5 w-3.5 text-primary" />
        Sentiment Reasoning (Chain of Thought):
      </div>
      
      <!-- Heuristic Explanation Banner -->
      <div 
        v-if="article.is_fallback" 
        class="p-3 rounded-xl bg-amber-500/5 border border-amber-500/10 text-[10px] text-amber-500/90 leading-relaxed"
      >
        <strong>💡 Local Fallback:</strong> The backend is running in standalone local fallback mode (remote LLM offline or unconfigured). Sentiment classification was computed instantly using optimized local natural language algorithms to guarantee fast response times and zero service interruption.
      </div>

      <p class="text-xs text-slate-400 leading-relaxed font-medium">
        {{ article.llmReasoning }}
      </p>
    </div>
  </div>
</template>
