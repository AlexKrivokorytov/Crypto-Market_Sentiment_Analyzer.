import { ref } from 'vue';
import { defineStore } from 'pinia';
export const useAppStore = defineStore('app', () => {
    const selectedAssetId = ref('BTC');
    const timeframe = ref('24H');
    const sidebarCollapsed = ref(false);
    const setAsset = (assetId) => {
        selectedAssetId.value = assetId;
    };
    const setTimeframe = (newTimeframe) => {
        timeframe.value = newTimeframe;
    };
    const toggleSidebar = () => {
        sidebarCollapsed.value = !sidebarCollapsed.value;
    };
    return {
        selectedAssetId,
        timeframe,
        sidebarCollapsed,
        setAsset,
        setTimeframe,
        toggleSidebar
    };
});
