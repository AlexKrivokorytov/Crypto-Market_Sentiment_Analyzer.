<script setup lang="ts">
/**
 * Header — Global top navigation bar.
 *
 * Sprint 5 upgrades:
 * - All user-facing strings translated to English.
 * - Active timeframe pill uses gold accent colour instead of generic primary.
 * - Watchlist star shows gold glow animation when active.
 * - Refresh button shows gold spin when fetching.
 * - WS status indicator rendered on medium screens.
 */

import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore, type Timeframe } from '@/composables/useAppStore'
import { useAssetById } from '@/composables/useMarketData'
import { useWebSocketState } from '@/composables/useAssetWebSocket'
import { useAuthStore } from '@/composables/useAuthStore'
import { useToast } from '@/composables/useToast'
import { authApi } from '@/services/api'
import StatusIndicator from '@/components/dashboard/StatusIndicator.vue'
import { Menu, X, RefreshCw, Star } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import { getAssetBrandColor } from '@/composables/useCryptoFormatters'
import type { RouteAssetId } from '@/types/market'

const route = useRoute()
const store = useAppStore()
const authStore = useAuthStore()
const toast = useToast()
const { timeframe, sidebarCollapsed, mobileMenuOpen } = storeToRefs(store)

/** Active asset derived from the URL parameter — single source of truth. */
const assetId = computed(() => route.params.id as string)

const { data: asset, isFetching } = useAssetById(assetId)
const { status, reconnectCount } = useWebSocketState()

const timeframes: Timeframe[] = ['1H', '24H', '7D', '30D']
const isUpdatingWatchlist = ref(false)

const isWatchlisted = computed(() => {
  if (!authStore.user) return false
  return authStore.user.watchlist.includes(assetId.value)
})

/**
 * Returns the brand hex colour for the active asset.
 * Falls back to the primary indigo if the asset isn't yet loaded.
 */
const assetBrandColor = computed(() => {
  if (!asset.value?.id) return '#6366f1'
  return getAssetBrandColor(asset.value.id as RouteAssetId)
})

/**
 * Toggles watchlist membership for the active asset with optimistic mutation
 * and automatic rollback on network failure.
 *
 * @throws Never — errors are caught, logged, and shown as toast notifications.
 */
async function handleWatchlistToggle(): Promise<void> {
  if (!authStore.isAuthenticated || !authStore.user) {
    toast.show({
      title: 'Authentication Required',
      message: 'Please sign in to add assets to your watchlist.',
      type: 'warning',
      durationMs: 4000,
    })
    return
  }

  const id = assetId.value
  const originalWatchlist = [...authStore.user.watchlist]
  const isCurrentlyFav = originalWatchlist.includes(id)
  const action = isCurrentlyFav ? 'remove' : 'add'

  // 1. Optimistic Mutation
  const updatedWatchlist = isCurrentlyFav
    ? originalWatchlist.filter(item => item !== id)
    : [...originalWatchlist, id]

  authStore.updateUser({ ...authStore.user, watchlist: updatedWatchlist })

  toast.show({
    title: isCurrentlyFav ? 'Removed from Watchlist' : 'Added to Watchlist',
    message: isCurrentlyFav
      ? `${id} was removed from your tracked assets.`
      : `${id} was added to your watchlist.`,
    type: 'success',
    durationMs: 3000,
  })

  try {
    isUpdatingWatchlist.value = true
    // 2. Network Synchronization
    const response = await authApi.updateWatchlist(id, action)
    authStore.updateUser(response)
  } catch (err) {
    console.error('[Header] Watchlist sync failed:', { assetId: id, action, err })

    // 3. Automatic Rollback
    authStore.updateUser({ ...authStore.user, watchlist: originalWatchlist })

    toast.show({
      title: 'Sync Failed',
      message: `Could not update watchlist for ${id}. Previous state restored.`,
      type: 'error',
      durationMs: 5000,
    })
  } finally {
    isUpdatingWatchlist.value = false
  }
}

/** On mobile, toggles the Drawer. On desktop, collapses/expands the sidebar. */
function handleMenuToggle(): void {
  if (window.innerWidth < 1024) {
    store.toggleMobileMenu()
  } else {
    store.toggleSidebar()
  }
}
</script>

<template>
  <header
    class="glass-panel border-b border-border/40 h-14 flex items-center justify-between px-4 sm:px-6 z-20 shrink-0"
    role="banner"
  >
    <!-- ── Left: Hamburger + Asset breadcrumb ─────────────────────── -->
    <div class="flex items-center gap-3 min-w-0">

      <!-- Sidebar / Hamburger Toggle -->
      <button
        id="sidebar-toggle-btn"
        @click="handleMenuToggle"
        aria-label="Toggle navigation menu"
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 hover:border-border transition-all shrink-0"
      >
        <X v-if="mobileMenuOpen" class="h-4 w-4 lg:hidden" aria-hidden="true" />
        <component v-else :is="sidebarCollapsed ? Menu : X" class="h-4 w-4 hidden lg:block" aria-hidden="true" />
        <Menu class="h-4 w-4 lg:hidden" :class="{ 'hidden': mobileMenuOpen }" aria-hidden="true" />
      </button>

      <!-- Asset breadcrumb -->
      <div v-if="asset" class="flex items-center gap-2 select-none min-w-0">
        <!-- Brand colour dot -->
        <span
          class="h-2 w-2 rounded-full shrink-0"
          :style="{ backgroundColor: assetBrandColor }"
          aria-hidden="true"
        />
        <span class="text-xs text-muted-foreground font-semibold uppercase tracking-wider hidden sm:block">Dashboard</span>
        <span class="text-xs text-muted-foreground/40 font-bold hidden sm:block">/</span>
        <span class="text-sm font-bold text-foreground truncate">{{ asset.name }}</span>
        <span class="text-xs bg-muted border border-border/60 px-1.5 py-0.5 rounded price-mono text-muted-foreground shrink-0">
          {{ asset.symbol }}/USD
        </span>

        <!-- Watchlist Star -->
        <button
          @click="handleWatchlistToggle"
          :disabled="isUpdatingWatchlist"
          class="p-1 rounded-lg border border-transparent hover:bg-white/5 transition-all duration-300 ml-1 flex items-center justify-center shrink-0 active:scale-90 cursor-pointer"
          :class="[isWatchlisted ? 'text-amber-400' : 'text-slate-500 hover:text-slate-300']"
          :aria-label="isWatchlisted ? 'Remove from watchlist' : 'Add to watchlist'"
          :aria-pressed="isWatchlisted"
        >
          <Star
            class="h-4 w-4 transition-all duration-300"
            :class="{
              'fill-amber-400 animate-glow-gold': isWatchlisted,
              'animate-pulse': isUpdatingWatchlist,
            }"
            aria-hidden="true"
          />
        </button>
      </div>

      <!-- Loading skeleton for asset name -->
      <div v-else class="h-5 w-32 bg-muted/30 border border-border/30 rounded animate-pulse" aria-hidden="true" />
    </div>

    <!-- ── Right: WS Status + Timeframe + Refresh ──────────────────── -->
    <div class="flex items-center gap-2 sm:gap-3 shrink-0">

      <!-- WebSocket Connection Status Pill -->
      <div class="hidden md:block">
        <StatusIndicator :status="status" :reconnect-count="reconnectCount" />
      </div>

      <!-- Timeframe Pill Selector -->
      <nav
        class="flex p-0.5 bg-muted/60 border border-border/60 rounded-xl"
        aria-label="Chart timeframe selector"
      >
        <button
          v-for="tf in timeframes"
          :key="tf"
          :id="`timeframe-${tf}`"
          @click="store.setTimeframe(tf)"
          class="px-2 sm:px-3 py-1 rounded-lg text-xs font-bold transition-all duration-200"
          :class="[
            timeframe === tf
              ? 'text-white shadow-md'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40',
          ]"
          :style="timeframe === tf
            ? { background: 'var(--active-brand-color, #f59e0b)', boxShadow: '0 0 12px var(--active-brand-color-glow, rgba(245,158,11,0.30))' }
            : {}"
          :aria-label="`Set timeframe to ${tf}`"
          :aria-pressed="timeframe === tf"
        >
          {{ tf }}
        </button>
      </nav>

      <!-- Fetch spinner -->
      <button
        aria-label="Data refresh indicator"
        class="p-2 rounded-lg border border-border/60 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all cursor-default shrink-0"
        :class="[isFetching ? 'animate-spin' : '']"
        :style="isFetching ? { color: '#f59e0b' } : {}"
        tabindex="-1"
      >
        <RefreshCw class="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  </header>
</template>
