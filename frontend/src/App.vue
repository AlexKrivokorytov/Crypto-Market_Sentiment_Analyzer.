<script setup lang="ts">
import { computed } from 'vue'
import { onErrorCaptured } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import { useAppStore } from '@/composables/useAppStore'
import { storeToRefs } from 'pinia'
import { getAssetBrandColor } from '@/composables/useCryptoFormatters'
import type { RouteAssetId } from '@/types/market'
import { useAssetWebSocket } from '@/composables/useAssetWebSocket'

const store = useAppStore()
const { mobileMenuOpen } = storeToRefs(store)
const route = useRoute()

// Establish WebSocket connection room reactively linked to current active asset route parameter
const activeAssetIdStr = computed<string>(() => (route.params.id as string) || '')
useAssetWebSocket(activeAssetIdStr)

/**
 * Compute active brand color dynamically based on current selected asset ticker
 */
const activeAssetId = computed<RouteAssetId | undefined>(
  () => route.params.id as RouteAssetId | undefined
)

const activeBrandColor = computed<string>(() => {
  if (activeAssetId.value) {
    try {
      const color = getAssetBrandColor(activeAssetId.value)
      if (color) return color
    } catch {
      // Fallback if asset is invalid or not in registry
    }
  }
  return '#8b5cf6' // default premium violet
})

const activeBrandColorGlow = computed<string>(() => {
  return `${activeBrandColor.value}1d`
})

/**
 * Guest-only auth routes (Login/Register) use a full-page layout without the sidebar and header.
 * They have the requiresGuest meta flag.
 */
const isFullPage = computed<boolean>(
  () => !!route.meta.requiresGuest
)

/**
 * Global error boundary. Catches any unhandled render errors from child
 * components, logs them with context, and returns false to prevent Vue
 * from propagating the error up and crashing the entire tree.
 */
onErrorCaptured((error: Error, instance, info: string) => {
  console.error('[App] Unhandled render error:', { message: error.message, info, instance })
  return false
})
</script>

<template>
  <!-- Auth pages: full-page glass layout, no sidebar -->
  <RouterView v-if="isFullPage" />

  <!-- Authenticated app shell: sidebar + header + routed content -->
  <div v-else class="flex h-screen w-screen overflow-hidden bg-[#05070f] text-slate-100 font-sans" :style="{ '--active-brand-color': activeBrandColor, '--active-brand-color-glow': activeBrandColorGlow }">
    <!-- Sidebar (desktop: static, mobile: Drawer overlay) -->
    <Sidebar />

    <!-- Mobile backdrop — closes the Drawer when clicked -->
    <Transition name="fade">
      <div
        v-if="mobileMenuOpen"
        class="fixed inset-0 bg-black/60 z-30 lg:hidden"
        aria-hidden="true"
        @click="store.closeMobileMenu()"
      />
    </Transition>

    <!-- Main Content Column -->
    <div class="flex-1 flex flex-col min-w-0 h-full relative">
      <Header />
      <!-- Routed page content (DashboardView, PortfolioView, NotFoundView…) -->
      <RouterView />
    </div>
  </div>
  <ToastContainer />
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

