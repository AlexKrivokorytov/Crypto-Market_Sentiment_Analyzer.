<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { TrendingDown, Home } from '@lucide/vue'
import { DEFAULT_ASSET } from '@/router/index'
</script>

<template>
  <main class="flex-1 flex flex-col items-center justify-center p-6 text-center select-none">
    <!-- Glowing icon -->
    <div
      class="flex items-center justify-center h-20 w-20 rounded-3xl bg-bearish/10 border border-bearish/20 text-bearish mb-6 shadow-[0_0_40px_rgba(244,63,94,0.1)]"
    >
      <TrendingDown class="h-10 w-10" />
    </div>

    <!-- Error Code -->
    <span
      class="text-8xl font-extrabold font-mono bg-gradient-to-r from-slate-600 via-slate-400 to-slate-600 bg-clip-text text-transparent leading-none mb-4"
    >
      404
    </span>

    <h1 class="text-xl font-bold text-foreground mb-2">Page not found</h1>
    <p class="text-sm text-muted-foreground max-w-sm mb-8">
      The route you requested doesn't exist or the asset ticker is not tracked by this platform.
    </p>

    <RouterLink
      :to="`/asset/${DEFAULT_ASSET}`"
      class="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary/10 border border-primary/30 text-primary text-sm font-bold hover:bg-primary/20 hover:border-primary/50 transition-all shadow-[0_0_20px_rgba(99,102,241,0.1)] hover:shadow-[0_0_30px_rgba(99,102,241,0.2)]"
    >
      <Home class="h-4 w-4" />
      Back to Dashboard
    </RouterLink>
  </main>
</template>
