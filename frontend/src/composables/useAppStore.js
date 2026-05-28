import { ref } from 'vue';
import { defineStore } from 'pinia';
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
    const timeframe = ref('24H');
    const sidebarCollapsed = ref(false);
    const mobileMenuOpen = ref(false);
    /** Sets the active chart timeframe. */
    const setTimeframe = (newTimeframe) => {
        timeframe.value = newTimeframe;
    };
    /** Toggles the desktop sidebar between collapsed and expanded states. */
    const toggleSidebar = () => {
        sidebarCollapsed.value = !sidebarCollapsed.value;
    };
    /** Opens the mobile navigation Drawer. */
    const openMobileMenu = () => {
        mobileMenuOpen.value = true;
    };
    /** Closes the mobile navigation Drawer. */
    const closeMobileMenu = () => {
        mobileMenuOpen.value = false;
    };
    /** Toggles the mobile navigation Drawer open/closed. */
    const toggleMobileMenu = () => {
        mobileMenuOpen.value = !mobileMenuOpen.value;
    };
    return {
        timeframe,
        sidebarCollapsed,
        mobileMenuOpen,
        setTimeframe,
        toggleSidebar,
        openMobileMenu,
        closeMobileMenu,
        toggleMobileMenu,
    };
});
