<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { SentimentArticle } from '@/types/market'

const props = defineProps<{
  article: SentimentArticle
  modelName?: string
}>()

const isExpanded = ref(false)

const emit = defineEmits<{
  (e: 'requestAiAnalysis', articleId: string): void
}>()

const isAiRequestPending = ref(false)
const aiError = ref<string | null>(null)

const triggerAiAnalysis = () => {
  if (isAiRequestPending.value) return
  isAiRequestPending.value = true
  aiError.value = null
  emit('requestAiAnalysis', props.article.id)
  
  // Safety timeout: auto-reset loader after 35s (covers 10s retry backoff + API call time)
  setTimeout(() => {
    isAiRequestPending.value = false
  }, 35000)
}

// Reset spinner when the article is successfully analyzed by LLM
watch(() => props.article.is_fallback, (newFallback) => {
  if (!newFallback) {
    isAiRequestPending.value = false
    aiError.value = null
  }
})

// Exposed so LiveFeed.vue can reset the spinner and show an error on 429
const setAnalysisError = (message: string) => {
  isAiRequestPending.value = false
  aiError.value = message
}

defineExpose({ setAnalysisError })

const displayModelName = computed(() => {
  if (!props.modelName) return 'AI Analysis (LLM)'
  const modelPart = props.modelName.split('/').pop() || 'LLM'
  const cleanName = (modelPart.split(':')[0] || 'LLM')
    .replace(/-it|-preview|-instruct/g, '')
    .replace(/-/g, ' ')
    .toUpperCase()
  return `AI Analysis (${cleanName})`
})

const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div class="p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors relative group scanline-overlay text-xs font-mono">
    <!-- Log Header -->
    <div class="flex flex-wrap items-center gap-2 mb-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
      <span class="text-slate-500">[{{ formatTime(article.timestamp) }}]</span>
      
      <span class="text-violet-400">[{{ article.source }}]</span>
      
      <span
        :class="[
          article.sentimentLabel === 'Bullish' ? 'text-signal' : 
          article.sentimentLabel === 'Bearish' ? 'text-alarm' : 
          'text-slate-400'
        ]"
      >
        [{{ article.sentimentLabel }}]
      </span>
      
      <span class="text-slate-600">[CONF:{{ Math.round(article.confidence * 100) }}%]</span>

      <span v-if="article.is_fallback" class="text-amber-500">[VADER_LOCAL]</span>
      <span v-else class="text-slate-500">[{{ displayModelName }}]</span>
    </div>

    <!-- Title & Content -->
    <div class="mb-2">
      <span class="text-signal opacity-50 mr-2">&gt;</span>
      <a :href="article.url" target="_blank" rel="noopener noreferrer" class="text-slate-200 group-hover:text-white font-bold hover:underline">
        {{ article.title }}
      </a>
    </div>
    
    <div class="pl-4 border-l border-white/10 text-slate-400 mb-2 leading-relaxed whitespace-pre-wrap">
      {{ article.summary }}
    </div>

    <!-- Keywords -->
    <div class="flex flex-wrap gap-1.5 pl-4 mb-2">
      <span
        v-for="kw in article.keywords"
        :key="kw"
        class="text-[10px] text-slate-500 bg-white/5 px-1.5 py-0.5 rounded"
      >
        #{{ kw }}
      </span>
    </div>

    <!-- Actions & Expansion -->
    <div class="flex items-center gap-4 pl-4 mt-2">
      <button
        @click="isExpanded = !isExpanded"
        class="text-[10px] uppercase tracking-widest text-slate-500 hover:text-signal transition-colors flex items-center gap-1"
      >
        <span v-if="isExpanded">[-] HIDE_TRACE</span>
        <span v-else>[+] VIEW_TRACE</span>
      </button>

      <button
        @click="triggerAiAnalysis"
        :disabled="isAiRequestPending"
        class="text-[10px] uppercase tracking-widest text-violet-500 hover:text-violet-300 disabled:opacity-50 transition-colors flex items-center gap-1"
      >
        <span v-if="isAiRequestPending" class="animate-pulse">[*] RECALCULATING...</span>
        <span v-else>[>] FORCE_RECALC</span>
      </button>
    </div>

    <!-- Rate-limit inline warning -->
    <div
      v-if="aiError"
      class="mt-2 pl-4 text-[10px] text-alarm font-bold animate-pulse"
    >
      [ERR] {{ aiError }}
    </div>

    <!-- Expanded Trace -->
    <div
      v-if="isExpanded"
      class="mt-3 pl-4 pt-2 border-t border-white/5 text-slate-500"
    >
      <div class="mb-1 text-[10px] text-slate-600">--- LLM CHAIN OF THOUGHT ---</div>
      
      <div 
        v-if="article.is_fallback" 
        class="mb-2 text-[10px] text-amber-500/80"
      >
        [WARN] Remote LLM unreachable. Computed via optimized local heuristic (VADER fallback).
      </div>

      <div class="leading-relaxed">
        {{ article.llmReasoning }}
      </div>
      
      <div class="mt-1 text-[10px] text-slate-600">--- END TRACE ---</div>
    </div>
  </div>
</template>
