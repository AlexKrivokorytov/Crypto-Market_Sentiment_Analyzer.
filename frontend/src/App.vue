<script setup lang="ts">
import { onErrorCaptured } from 'vue'
import { RouterView } from 'vue-router'
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import { useAppStore } from '@/composables/useAppStore'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { mobileMenuOpen } = storeToRefs(store)

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
  <div class="flex h-screen w-screen overflow-hidden bg-[#05070f] text-slate-100 font-sans">
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
      <!-- Routed page content (DashboardView or NotFoundView) -->
      <RouterView />
    </div>
  </div>
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

