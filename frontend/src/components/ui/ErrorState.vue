<script setup lang="ts">
import { AlertTriangle, RefreshCw } from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    /** Primary heading displayed in the error panel. */
    title?: string
    /** Secondary descriptive text explaining what went wrong. */
    description?: string
    /** When provided, a "Retry" button is rendered that calls this function on click. */
    onRetry?: () => void
  }>(),
  {
    title: 'Failed to load data',
    description: 'Check your connection and try again.',
  }
)
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-4 p-8 text-center rounded-2xl border border-destructive/20 bg-destructive/5 h-full min-h-[120px]"
  >
    <div
      class="flex items-center justify-center h-11 w-11 rounded-full border border-destructive/30 bg-destructive/10 text-destructive shrink-0"
    >
      <AlertTriangle class="h-5 w-5" />
    </div>

    <div class="flex flex-col gap-1 max-w-xs">
      <p class="text-sm font-bold text-foreground">{{ props.title }}</p>
      <p class="text-xs text-muted-foreground leading-relaxed">{{ props.description }}</p>
    </div>

    <button
      v-if="props.onRetry"
      @click="props.onRetry"
      class="flex items-center gap-2 px-4 py-1.5 rounded-lg border border-border/60 bg-muted/40 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-muted/80 hover:border-border transition-all"
    >
      <RefreshCw class="h-3.5 w-3.5" />
      Retry
    </button>
  </div>
</template>
