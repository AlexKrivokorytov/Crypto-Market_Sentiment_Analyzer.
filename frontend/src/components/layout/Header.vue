<script setup lang="ts">
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

/** Toggles favorite status for the active asset optimistically. */
async function handleWatchlistToggle() {
  if (!authStore.isAuthenticated || !authStore.user) {
    toast.show({
      title: 'Требуется авторизация',
      message: 'Пожалуйста, войдите в аккаунт, чтобы добавить ассет в отслеживаемые.',
      type: 'warning',
      durationMs: 4000
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

  authStore.updateUser({
    ...authStore.user,
    watchlist: updatedWatchlist
  })

  // Show visual feedback instantly
  toast.show({
    title: isCurrentlyFav ? 'Удалено из избранного' : 'Добавлено в избранное',
    message: isCurrentlyFav 
      ? `Ассет ${id} успешно удален из вашего списка.` 
      : `Ассет ${id} добавлен в ваш список отслеживания.`,
    type: 'success',
    durationMs: 3000
  })

  try {
    isUpdatingWatchlist.value = true
    // 2. Perform Network Synchronization
    const response = await authApi.updateWatchlist(id, action)
    authStore.updateUser(response)
  } catch (err) {
    console.error('[Header] Failed to synchronize watchlist with backend:', err)

    // 3. Automatic Rollback on Error
    authStore.updateUser({
      ...authStore.user,
      watchlist: originalWatchlist
    })

    // Notify user of rollback state
    toast.show({
      title: 'Ошибка синхронизации',
      message: `Не удалось изменить статус избранного для ${id}. Восстановлено предыдущее состояние.`,
      type: 'error',
      durationMs: 5000
    })
  } finally {
    isUpdatingWatchlist.value = false
  }
}

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

        <!-- Watchlist Star Button -->
        <button
          @click="handleWatchlistToggle"
          :disabled="isUpdatingWatchlist"
          class="p-1 rounded-lg border border-transparent hover:bg-white/5 transition-all duration-300 ml-1.5 flex items-center justify-center shrink-0 active:scale-90 cursor-pointer"
          :class="[isWatchlisted ? 'text-amber-400' : 'text-slate-500 hover:text-slate-300']"
          :aria-label="isWatchlisted ? 'Remove from watchlist' : 'Add to watchlist'"
        >
          <Star class="h-4.5 w-4.5" :class="{ 'fill-amber-400': isWatchlisted, 'animate-pulse': isUpdatingWatchlist }" />
        </button>
      </div>
      <div v-else class="h-5 w-32 bg-muted/30 border border-border/30 rounded animate-pulse" />
    </div>

    <!-- Right Controls -->
    <div class="flex items-center gap-2 sm:gap-4">
      <!-- Connection Status Pill -->
      <div class="hidden md:block">
        <StatusIndicator :status="status" :reconnect-count="reconnectCount" />
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

