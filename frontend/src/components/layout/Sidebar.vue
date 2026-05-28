<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/composables/useAppStore'
import { useAuthStore } from '@/composables/useAuthStore'
import { useAssets, useBackendConfig } from '@/composables/useMarketData'
import { Activity, Cpu, TrendingDown, TrendingUp } from '@lucide/vue'
import { storeToRefs } from 'pinia'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const authStore = useAuthStore()
const { sidebarCollapsed, mobileMenuOpen } = storeToRefs(store)

/** The currently active asset ticker, derived from the URL. */
const selectedAssetId = computed(() => route.params.id as string)

const { data: assets, isLoading } = useAssets()
const { data: config, isLoading: configLoading, isError: configError } = useBackendConfig()

const formatCurrency = (val: number, symbol: string) => {
  const options =
    symbol === 'AAPL'
      ? { minimumFractionDigits: 2, maximumFractionDigits: 2 }
      : { minimumFractionDigits: 0, maximumFractionDigits: 2 }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', ...options }).format(val)
}

/** Navigates to the selected asset route and closes the mobile Drawer. */
const selectAsset = (assetId: string): void => {
  router.push(`/asset/${assetId}`)
  store.closeMobileMenu()
}

/** Logs out and navigates to the login page. */
function handleLogout(): void {
  authStore.logout()
  router.push('/login')
  store.closeMobileMenu()
}
</script>

<template>
  <aside
    class="glass-panel border-r border-border/40 h-screen transition-all duration-300 ease-in-out flex flex-col z-40
           fixed inset-y-0 left-0 lg:relative lg:z-20"
    :class="[
      sidebarCollapsed ? 'lg:w-20' : 'lg:w-72',
      mobileMenuOpen ? 'w-72 translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
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
        @click="selectAsset(asset.id)"
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

    <!-- Portfolio nav link -->
    <div class="px-3 pb-1">
      <button
        id="sidebar-portfolio-link"
        class="w-full text-left p-3 rounded-xl flex items-center gap-3 transition-all duration-200 border group"
        :class="[
          route.name === 'portfolio'
            ? 'glass-card border-primary/30 text-foreground'
            : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground'
        ]"
        @click="router.push('/portfolio'); store.closeMobileMenu()"
        aria-label="Go to Portfolio"
      >
        <div
          class="h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0"
          :class="route.name === 'portfolio' ? 'bg-primary/20 text-white border border-primary/30' : 'bg-muted/50 border border-border/40 text-muted-foreground'"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M2 5.5h12M2 5.5v7a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-7M2 5.5V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
            <path d="M6 3V2.5a2 2 0 0 1 4 0V3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
          </svg>
        </div>
        <span
          class="font-semibold text-sm transition-all duration-200"
          :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']"
        >
          Portfolio
        </span>
      </button>
    </div>

    <!-- Sidebar Footer -->
    <div class="p-4 border-t border-border/40 flex flex-col gap-2 overflow-hidden">
      <!-- LLM status -->
      <div class="flex items-center gap-3" :class="[sidebarCollapsed ? 'justify-center' : '']">
        <div 
          class="h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border"
          :class="[
            configError 
              ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' 
              : configLoading 
              ? 'bg-blue-500/10 border-blue-500/20 text-blue-400 animate-pulse' 
              : config?.llm_configured 
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
              : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
          ]"
        >
          <Cpu class="h-4 w-4" :class="[!configError ? 'animate-pulse' : '']" />
        </div>
        <div class="flex flex-col min-w-0 transition-all duration-200" :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']">
          <span class="text-xs font-semibold text-foreground truncate">
            {{ configError ? 'Server Offline' : configLoading ? 'Connecting...' : (config?.llm_model || 'Simulated Model') }}
          </span>
          <span
            class="text-[10px] font-medium flex items-center gap-1"
            :class="[
              configError 
                ? 'text-rose-400' 
                : configLoading 
                ? 'text-blue-400' 
                : config?.llm_configured 
                ? 'text-emerald-400' 
                : 'text-amber-400'
            ]"
          >
            <span
              class="h-1.5 w-1.5 rounded-full animate-ping"
              :class="[
                configError 
                  ? 'bg-rose-400' 
                  : configLoading 
                  ? 'bg-blue-400' 
                  : config?.llm_configured 
                  ? 'bg-emerald-400' 
                  : 'bg-amber-400'
              ]"
            ></span>
            {{ configError ? 'Backend Unreachable' : configLoading ? 'Checking API...' : (config?.llm_configured ? 'Live AI Active' : 'Simulation Mode') }}
          </span>
        </div>
      </div>

      <!-- Auth: Login / Logout -->
      <div :class="[sidebarCollapsed ? 'hidden' : 'block']">
        <button
          v-if="authStore.isAuthenticated"
          id="sidebar-logout-btn"
          class="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all duration-150"
          @click="handleLogout"
          aria-label="Log out"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M5.5 2H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h2.5M9.5 10l2.5-3-2.5-3M12 7H5.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Sign out ({{ authStore.user?.display_name }})
        </button>
        <button
          v-else
          id="sidebar-login-btn"
          class="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-indigo-400 hover:bg-indigo-500/10 transition-all duration-150"
          @click="router.push('/login')"
          aria-label="Sign in"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M8.5 2H11a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H8.5M4.5 10l-2.5-3 2.5-3M2 7h6.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Sign in
        </button>
      </div>
    </div>
  </aside>
</template>
