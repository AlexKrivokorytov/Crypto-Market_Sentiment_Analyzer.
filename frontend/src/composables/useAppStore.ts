import { ref } from 'vue'
import { defineStore } from 'pinia'

export type Timeframe = '1H' | '24H' | '7D' | '30D'

/**
 * Global UI state store.
 *
 * Responsibilities:
 *  - `timeframe` — active chart timeframe selected by the user.
 *  - `sidebarCollapsed` — desktop sidebar collapsed/expanded toggle.
 *  - `mobileMenuOpen` — mobile Drawer open/close state.
 *
 * The active asset ID is **not** stored here; it lives in the URL as
 * `useRoute().params.id` so the URL always reflects the application state.
 */
export const useAppStore = defineStore('app', () => {
  const timeframe = ref<Timeframe>('24H')
  const sidebarCollapsed = ref<boolean>(false)
  const mobileMenuOpen = ref<boolean>(false)

  /** Sets the active chart timeframe. */
  const setTimeframe = (newTimeframe: Timeframe): void => {
    timeframe.value = newTimeframe
  }

  /** Toggles the desktop sidebar between collapsed and expanded states. */
  const toggleSidebar = (): void => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /** Opens the mobile navigation Drawer. */
  const openMobileMenu = (): void => {
    mobileMenuOpen.value = true
  }

  /** Closes the mobile navigation Drawer. */
  const closeMobileMenu = (): void => {
    mobileMenuOpen.value = false
  }

  /** Toggles the mobile navigation Drawer open/closed. */
  const toggleMobileMenu = (): void => {
    mobileMenuOpen.value = !mobileMenuOpen.value
  }

  return {
    timeframe,
    sidebarCollapsed,
    mobileMenuOpen,
    setTimeframe,
    toggleSidebar,
    openMobileMenu,
    closeMobileMenu,
    toggleMobileMenu,
  }
})

