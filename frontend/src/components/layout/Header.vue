<script setup lang="ts">
import { useAppStore, Timeframe } from '@/composables/useAppStore'
import { useAssetById } from '@/composables/useMarketData'
import { Menu, X, RefreshCw } from '@lucide/vue'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { selectedAssetId, timeframe, sidebarCollapsed } = storeToRefs(store)

const { data: asset, isFetching } = useAssetById(selectedAssetId)

const timeframes: Timeframe[] = ['1H', '24H', '7D', '30D']
</script>

<template>
  <header class="glass-panel border-b border-border/40 h-16 flex items-center justify-between px-6 z-10 shrink-0">
    <div class="flex items-center gap-4">
      <!-- Collapse Toggle -->
      <button
        @click="store.toggleSidebar"
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 hover:border-border transition-all shrink-0"
      >
        <component :is="sidebarCollapsed ? Menu : X" class="h-4 w-4" />
      </button>

      <!-- Asset Title Info -->
      <div v-if="asset" class="flex items-center gap-2 select-none">
        <span class="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Dashboard</span>
        <span class="text-xs text-muted-foreground/40 font-bold">/</span>
        <span class="text-sm font-bold text-foreground">{{ asset.name }}</span>
        <span class="text-xs bg-muted border border-border/60 px-1.5 py-0.5 rounded font-mono text-muted-foreground">
          {{ asset.symbol }}/USD
        </span>
      </div>
      <div v-else class="h-5 w-32 bg-muted/30 border border-border/30 rounded animate-pulse" />
    </div>

    <!-- Right Controls -->
    <div class="flex items-center gap-4">
      <!-- Connection Status Pill -->
      <div class="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
        Mock Pipeline Live
      </div>

      <!-- Timeframe Selector -->
      <div class="flex p-0.5 bg-muted/60 border border-border/60 rounded-xl">
        <button
          v-for="tf in timeframes"
          :key="tf"
          @click="store.setTimeframe(tf)"
          class="px-3 py-1 rounded-lg text-xs font-bold transition-all"
          :class="[
            timeframe === tf
              ? 'bg-primary text-white shadow-md'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          ]"
        >
          {{ tf }}
        </button>
      </div>

      <!-- Status Indicator -->
      <button
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all cursor-default"
        :class="[isFetching ? 'animate-spin text-primary' : '']"
      >
        <RefreshCw class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>
