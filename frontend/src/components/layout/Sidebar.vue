<script setup lang="ts">
import { useAppStore } from '@/composables/useAppStore'
import { useAssets, useBackendConfig } from '@/composables/useMarketData'
import { Activity, Cpu, TrendingDown, TrendingUp } from '@lucide/vue'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { selectedAssetId, sidebarCollapsed } = storeToRefs(store)

const { data: assets, isLoading } = useAssets()
const { data: config } = useBackendConfig()

const formatCurrency = (val: number, symbol: string) => {
  const options = symbol === 'AAPL' 
    ? { minimumFractionDigits: 2, maximumFractionDigits: 2 }
    : { minimumFractionDigits: 0, maximumFractionDigits: 2 };
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    ...options
  }).format(val)
}
</script>

<template>
  <aside
    class="glass-panel border-r border-border/40 h-screen transition-all duration-300 ease-in-out flex flex-col z-20"
    :class="[sidebarCollapsed ? 'w-20' : 'w-72']"
  >
    <!-- Logo & Brand Header -->
    <div class="h-16 flex items-center px-6 border-b border-border/40 gap-3 overflow-hidden select-none">
      <div class="flex items-center justify-center p-2 rounded-xl bg-primary/10 border border-primary/20 shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.15)]">
        <Activity class="h-5 w-5 text-primary animate-pulse" />
      </div>
      <div class="flex flex-col transition-all duration-200" :class="[sidebarCollapsed ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']">
        <span class="font-extrabold text-sm tracking-wider uppercase bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
          SentimentAI
        </span>
        <span class="text-[10px] text-muted-foreground font-medium tracking-tight">Market Analyzer v1.0</span>
      </div>
    </div>

    <!-- Navigation Header -->
    <div class="px-4 py-3 flex items-center text-xs font-semibold text-muted-foreground tracking-wider uppercase overflow-hidden">
      <span :class="[sidebarCollapsed ? 'mx-auto' : 'pl-2']">Assets</span>
    </div>

    <!-- Asset List Container -->
    <div class="flex-1 px-3 overflow-y-auto space-y-1">
      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="space-y-2 p-2">
        <div v-for="i in 4" :key="i" class="h-14 bg-muted/30 border border-border/30 rounded-xl animate-pulse" />
      </div>

      <!-- Asset List Items -->
      <button
        v-else
        v-for="asset in assets"
        :key="asset.id"
        @click="store.setAsset(asset.id)"
        class="w-full text-left p-3 rounded-xl flex items-center transition-all duration-200 border group"
        :class="[
          selectedAssetId === asset.id
            ? 'glass-card border-primary/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_0_20px_-5px_rgba(99,102,241,0.15)] text-foreground'
            : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground'
        ]"
      >
        <!-- Mini Ticker Icon -->
        <div
          class="h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-transform duration-200 group-hover:scale-105"
          :class="[
            selectedAssetId === asset.id
              ? 'bg-primary/20 text-white border border-primary/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]'
              : 'bg-muted/50 border border-border/40 text-muted-foreground group-hover:border-border/80'
          ]"
        >
          {{ asset.symbol }}
        </div>

        <!-- Asset Info & Spark-pill -->
        <div
          class="ml-3 flex-1 flex justify-between items-center transition-all duration-200 overflow-hidden"
          :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']"
        >
          <div class="flex flex-col min-w-0">
            <span class="font-semibold text-sm truncate">{{ asset.name }}</span>
            <span class="text-xs text-muted-foreground truncate">{{ formatCurrency(asset.price, asset.symbol) }}</span>
          </div>

          <!-- Sentiment Mini Spark Badge -->
          <div class="flex flex-col items-end shrink-0">
            <span
              class="text-[10px] font-bold px-2 py-0.5 rounded-full border shadow-sm transition-all"
              :class="[
                asset.sentimentLabel === 'Bullish'
                  ? 'bg-bullish/10 text-bullish border-bullish/30 shadow-bullish/5'
                  : asset.sentimentLabel === 'Bearish'
                  ? 'bg-bearish/10 text-bearish border-bearish/30 shadow-bearish/5'
                  : 'bg-neutral/10 text-neutral border-neutral/30'
              ]"
            >
              {{ asset.sentimentScore }}
            </span>
            <span
              class="text-[10px] flex items-center font-semibold mt-1"
              :class="[asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']"
            >
              <component :is="asset.change24h >= 0 ? TrendingUp : TrendingDown" class="h-3 w-3 mr-0.5 shrink-0" />
              {{ asset.change24h >= 0 ? '+' : '' }}{{ asset.change24h }}%
            </span>
          </div>
        </div>
      </button>
    </div>

    <!-- Sidebar Footer -->
    <div class="p-4 border-t border-border/40 flex items-center overflow-hidden">
      <div class="flex items-center gap-3 w-full" :class="[sidebarCollapsed ? 'justify-center' : '']">
        <div class="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
          <Cpu class="h-4 w-4 text-indigo-400 animate-pulse" />
        </div>
        <div class="flex flex-col min-w-0 transition-all duration-200" :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']">
          <span class="text-xs font-semibold text-foreground truncate">
            {{ config?.llm_model || 'Loading model...' }}
          </span>
          <span 
            class="text-[10px] font-medium flex items-center gap-1"
            :class="[config?.llm_configured ? 'text-emerald-400' : 'text-amber-400']"
          >
            <span 
              class="h-1.5 w-1.5 rounded-full animate-ping"
              :class="[config?.llm_configured ? 'bg-emerald-400' : 'bg-amber-400']"
            ></span>
            {{ config?.llm_configured ? 'Live AI Active' : 'Simulation Mode' }}
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>
