<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, type Timeframe } from '@/composables/useAppStore'
import { useAssetById } from '@/composables/useMarketData'
import { Menu, X, RefreshCw } from '@lucide/vue'
import { storeToRefs } from 'pinia'

const route = useRoute()
const store = useAppStore()
const { timeframe, sidebarCollapsed, mobileMenuOpen } = storeToRefs(store)

/** Active asset derived from the URL parameter — single source of truth. */
const assetId = computed(() => route.params.id as string)

const { data: asset, isFetching } = useAssetById(assetId)

const timeframes: Timeframe[] = ['1H', '24H', '7D', '30D']

/** On mobile, toggles the Drawer. On desktop, collapses/expands the sidebar. */
const handleMenuToggle = (): void => {
  if (window.innerWidth < 1024) {
    store.toggleMobileMenu()
  } else {
    store.toggleSidebar()
  }
}
</script>

<template>
  <header class="glass-panel border-b border-border/40 h-16 flex items-center justify-between px-4 sm:px-6 z-10 shrink-0">
    <div class="flex items-center gap-3">
      <!-- Sidebar / Hamburger Toggle -->
      <button
        id="sidebar-toggle-btn"
        @click="handleMenuToggle"
        aria-label="Toggle navigation menu"
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 hover:border-border transition-all shrink-0"
      >
        <X v-if="mobileMenuOpen" class="h-4 w-4 lg:hidden" />
        <component v-else :is="sidebarCollapsed ? Menu : X" class="h-4 w-4 hidden lg:block" />
        <Menu class="h-4 w-4 lg:hidden" :class="{ 'hidden': mobileMenuOpen }" />
      </button>

      <!-- Asset Title Info -->
      <div v-if="asset" class="flex items-center gap-2 select-none">
        <span class="text-xs text-muted-foreground font-semibold uppercase tracking-wider hidden sm:block">Dashboard</span>
        <span class="text-xs text-muted-foreground/40 font-bold hidden sm:block">/</span>
        <span class="text-sm font-bold text-foreground">{{ asset.name }}</span>
        <span class="text-xs bg-muted border border-border/60 px-1.5 py-0.5 rounded font-mono text-muted-foreground">
          {{ asset.symbol }}/USD
        </span>
      </div>
      <div v-else class="h-5 w-32 bg-muted/30 border border-border/30 rounded animate-pulse" />
    </div>

    <!-- Right Controls -->
    <div class="flex items-center gap-2 sm:gap-4">
      <!-- Connection Status Pill -->
      <div class="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
        <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span>
        Live Feed
      </div>

      <!-- Timeframe Selector -->
      <div class="flex p-0.5 bg-muted/60 border border-border/60 rounded-xl">
        <button
          v-for="tf in timeframes"
          :key="tf"
          :id="`timeframe-${tf}`"
          @click="store.setTimeframe(tf)"
          class="px-2 sm:px-3 py-1 rounded-lg text-xs font-bold transition-all"
          :class="[
            timeframe === tf
              ? 'bg-primary text-white shadow-md'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
          ]"
        >
          {{ tf }}
        </button>
      </div>

      <!-- Fetch Spinner -->
      <button
        aria-label="Data refresh indicator"
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all cursor-default"
        :class="[isFetching ? 'animate-spin text-primary' : '']"
      >
        <RefreshCw class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

