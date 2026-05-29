<script setup lang="ts">
/**
 * Sidebar — Left navigation rail with asset list, portfolio link, and footer status.
 *
 * Sprint 5 upgrades:
 * - Asset list split into two sections: CRYPTO (BTC, ETH, TON, SOL, XRP, ADA)
 *   and STOCKS (AAPL, …) with distinct section headers.
 * - Each asset icon square uses getAssetBrandColor as background tint (not flat indigo).
 * - Price labels routed through formatPrice (smart decimal precision per asset).
 * - formatChange used for 24h percentage display.
 * - Internal formatCurrency helper removed (DRY).
 * - Brand label updated from "SentimentAI" to "Cryptex" for consistency with Sprint 5.
 */

import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/composables/useAppStore'
import { useAuthStore } from '@/composables/useAuthStore'
import { useAssets, useBackendConfig } from '@/composables/useMarketData'
import { Activity, Cpu, TrendingDown, TrendingUp, Star, Bitcoin, Layers } from '@lucide/vue'
import { storeToRefs } from 'pinia'
import {
  formatPrice,
  formatChange,
  getAssetBrandColor,
} from '@/composables/useCryptoFormatters'
import type { RouteAssetId, AssetMetrics } from '@/types/market'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const authStore = useAuthStore()
const { sidebarCollapsed, mobileMenuOpen } = storeToRefs(store)

/** The currently active asset ticker, derived from the URL. */
const selectedAssetId = computed(() => route.params.id as string)

const { data: assets, isLoading } = useAssets()
const { data: config, isLoading: configLoading, isError: configError } = useBackendConfig()

/** Ordered crypto asset IDs — rendered in the CRYPTO section. */
const CRYPTO_IDS: RouteAssetId[] = [
  'BTC',
  'ETH',
  'TON',
  'SOL',
  'XRP',
  'ADA',
  'DOGE',
  'DOT',
  'LINK',
  'AVAX',
  'MATIC',
  'SHIB',
  'LTC',
  'UNI',
  'NEAR',
  'ATOM'
]

/** Crypto assets in canonical display order. */
const cryptoAssets = computed<AssetMetrics[]>(() => {
  if (!assets.value) return []
  return CRYPTO_IDS
    .map(id => assets.value!.find(a => a.id === id))
    .filter((a): a is AssetMetrics => a !== undefined)
})

/** Non-crypto assets (equities, etc.) for the STOCKS section. */
const stockAssets = computed<AssetMetrics[]>(() => {
  if (!assets.value) return []
  return assets.value.filter(a => !CRYPTO_IDS.includes(a.id as RouteAssetId))
})

/**
 * Returns the inline CSS style for an asset icon square.
 * Uses the brand colour as a tinted background.
 *
 * @param assetId  - Asset ticker.
 * @param isActive - Whether this is the currently selected asset.
 */
function iconStyle(assetId: RouteAssetId, isActive: boolean): Record<string, string> {
  const color = getAssetBrandColor(assetId)
  if (isActive) {
    return {
      background: `${color}28`,
      borderColor: `${color}55`,
      color,
      boxShadow: `0 0 10px ${color}25`,
    }
  }
  return {
    background: `${color}10`,
    borderColor: 'rgba(255,255,255,0.08)',
    color: `${color}aa`,
  }
}

/**
 * Returns the outer button Tailwind class for active vs inactive asset rows.
 *
 * @param assetId - Asset ticker.
 */
function rowClass(assetId: string): string {
  return selectedAssetId.value === assetId
    ? 'glass-card border-white/10 text-foreground'
    : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground'
}

/** Computes inline style for active sidebar button rows using their brand color. */
function rowStyle(assetId: RouteAssetId, isActive: boolean): Record<string, string> {
  if (isActive) {
    const color = getAssetBrandColor(assetId)
    return {
      borderColor: `${color}35`,
      boxShadow: `0 0 12px ${color}0d`,
    }
  }
  return {}
}

/** Navigates to the selected asset and closes the mobile drawer. */
function selectAsset(assetId: string): void {
  router.push(`/asset/${assetId}`)
  store.closeMobileMenu()
}

/** Logs out and redirects to the login page. */
function handleLogout(): void {
  authStore.logout()
  router.push('/login')
  store.closeMobileMenu()
}
</script>

<template>
  <aside
    class="sidebar-container glass-panel border-r border-border/40 h-screen transition-all duration-300 ease-in-out flex flex-col z-40
           fixed inset-y-0 left-0 lg:relative lg:z-20"
    :class="[
      sidebarCollapsed ? 'lg:w-20' : 'lg:w-72',
      mobileMenuOpen ? 'w-72 translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
    aria-label="Main navigation"
  >

    <!-- ── Logo & Brand ────────────────────────────────────────────── -->
    <div class="h-14 flex items-center px-4 sm:px-6 border-b border-border/40 gap-3 overflow-hidden select-none shrink-0">
      <div
        class="flex items-center justify-center p-2 rounded-xl shrink-0"
        style="background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.25); box-shadow: 0 0 14px rgba(245,158,11,0.12);"
        aria-hidden="true"
      >
        <Activity class="h-5 w-5 text-gold animate-pulse" />
      </div>
      <div
        class="flex flex-col transition-all duration-200 sidebar-hide-on-collapsed"
        :class="[sidebarCollapsed ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']"
      >
        <span class="font-extrabold text-sm tracking-wider uppercase text-gradient-gold font-display">
          CryptoSentiment
        </span>
        <span class="text-[10px] text-muted-foreground font-medium tracking-tight">Market Intelligence v2.0</span>
      </div>
    </div>

    <!-- ── Asset Sections ─────────────────────────────────────────── -->
    <div class="flex-1 px-3 overflow-y-auto space-y-1 py-2">

      <!-- Loading skeleton -->
      <div v-if="isLoading" class="space-y-2 p-2" aria-hidden="true">
        <div v-for="i in 7" :key="i" class="h-14 bg-muted/30 border border-border/30 rounded-xl animate-pulse" />
      </div>

      <template v-else>
        <!-- ── CRYPTO section ──────────────────────────────────────── -->
        <div class="mb-1 mt-1">
          <div
            class="px-2 py-1.5 flex items-center gap-1.5 text-[9px] font-extrabold uppercase tracking-widest text-muted-foreground select-none sidebar-center-on-collapsed"
            :class="[sidebarCollapsed ? 'justify-center' : '']"
          >
            <Bitcoin class="h-3 w-3 text-gold shrink-0" aria-hidden="true" />
            <span class="sidebar-hide-on-collapsed" :class="[sidebarCollapsed ? 'hidden' : '']">Crypto</span>
          </div>

          <button
            v-for="asset in cryptoAssets"
            :key="asset.id"
            @click="selectAsset(asset.id)"
            class="w-full text-left p-3 rounded-xl flex items-center border group hover-scale-premium"
            :class="rowClass(asset.id)"
            :style="rowStyle(asset.id as RouteAssetId, selectedAssetId === asset.id)"
            :aria-label="`View ${asset.name} dashboard`"
            :aria-pressed="selectedAssetId === asset.id"
          >
            <!-- Brand-coloured asset icon square -->
            <div
              class="h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 border transition-all duration-200 group-hover:scale-105"
              :style="iconStyle(asset.id as RouteAssetId, selectedAssetId === asset.id)"
            >
              {{ asset.symbol }}
            </div>

            <!-- Asset info (hidden when sidebar collapsed) -->
            <div
              class="ml-3 flex-1 flex justify-between items-center transition-all duration-200 overflow-hidden sidebar-hide-on-collapsed"
              :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']"
            >
              <div class="flex flex-col min-w-0">
                <span class="font-semibold text-sm truncate flex items-center gap-1.5 text-slate-200">
                  {{ asset.name }}
                  <Star
                    v-if="authStore.user?.watchlist.includes(asset.id)"
                    class="h-3 w-3 text-amber-400 fill-amber-400 shrink-0"
                    aria-hidden="true"
                  />
                </span>
                <!-- Smart-precision price (JetBrains Mono) -->
                <span class="text-xs text-muted-foreground truncate price-mono">
                  {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
                </span>
              </div>

              <!-- Sentiment badge + 24h change -->
              <div class="flex flex-col items-end shrink-0 gap-0.5">
                <span
                  class="text-[9px] font-bold px-1.5 py-0.5 rounded-full border price-mono"
                  :class="[
                    asset.sentimentLabel === 'Bullish'
                      ? 'bg-bullish/10 text-bullish border-bullish/30'
                      : asset.sentimentLabel === 'Bearish'
                      ? 'bg-bearish/10 text-bearish border-bearish/30'
                      : 'bg-slate-700/50 text-slate-400 border-slate-600/30',
                  ]"
                >
                  {{ asset.sentimentScore }}
                </span>
                <span
                  class="text-[10px] flex items-center font-semibold price-mono"
                  :class="[asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']"
                >
                  <component
                    :is="asset.change24h >= 0 ? TrendingUp : TrendingDown"
                    class="h-2.5 w-2.5 mr-0.5 shrink-0"
                    aria-hidden="true"
                  />
                  {{ formatChange(asset.change24h) }}
                </span>
              </div>
            </div>
          </button>
        </div>

        <!-- ── STOCKS section (rendered only if there are stock assets) ─ -->
        <div v-if="stockAssets.length > 0" class="mt-3">
          <div
            class="px-2 py-1.5 flex items-center gap-1.5 text-[9px] font-extrabold uppercase tracking-widest text-muted-foreground select-none sidebar-center-on-collapsed"
            :class="[sidebarCollapsed ? 'justify-center' : '']"
          >
            <Layers class="h-3 w-3 text-slate-400 shrink-0" aria-hidden="true" />
            <span class="sidebar-hide-on-collapsed" :class="[sidebarCollapsed ? 'hidden' : '']">Stocks</span>
          </div>

          <button
            v-for="asset in stockAssets"
            :key="asset.id"
            @click="selectAsset(asset.id)"
            class="w-full text-left p-3 rounded-xl flex items-center border group hover-scale-premium"
            :class="rowClass(asset.id)"
            :style="rowStyle(asset.id as RouteAssetId, selectedAssetId === asset.id)"
            :aria-label="`View ${asset.name} dashboard`"
            :aria-pressed="selectedAssetId === asset.id"
          >
            <div
              class="h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 border transition-all duration-200 group-hover:scale-105"
              :style="iconStyle(asset.id as RouteAssetId, selectedAssetId === asset.id)"
            >
              {{ asset.symbol }}
            </div>

            <div
              class="ml-3 flex-1 flex justify-between items-center transition-all duration-200 overflow-hidden sidebar-hide-on-collapsed"
              :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']"
            >
              <div class="flex flex-col min-w-0">
                <span class="font-semibold text-sm truncate flex items-center gap-1.5 text-slate-200">
                  {{ asset.name }}
                  <Star
                    v-if="authStore.user?.watchlist.includes(asset.id)"
                    class="h-3 w-3 text-amber-400 fill-amber-400 shrink-0"
                    aria-hidden="true"
                  />
                </span>
                <span class="text-xs text-muted-foreground truncate price-mono">
                  {{ formatPrice(asset.price, asset.id as RouteAssetId) }}
                </span>
              </div>

              <div class="flex flex-col items-end shrink-0 gap-0.5">
                <span
                  class="text-[9px] font-bold px-1.5 py-0.5 rounded-full border price-mono"
                  :class="[
                    asset.sentimentLabel === 'Bullish'
                      ? 'bg-bullish/10 text-bullish border-bullish/30'
                      : asset.sentimentLabel === 'Bearish'
                      ? 'bg-bearish/10 text-bearish border-bearish/30'
                      : 'bg-slate-700/50 text-slate-400 border-slate-600/30',
                  ]"
                >
                  {{ asset.sentimentScore }}
                </span>
                <span
                  class="text-[10px] flex items-center font-semibold price-mono"
                  :class="[asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']"
                >
                  <component
                    :is="asset.change24h >= 0 ? TrendingUp : TrendingDown"
                    class="h-2.5 w-2.5 mr-0.5 shrink-0"
                    aria-hidden="true"
                  />
                  {{ formatChange(asset.change24h) }}
                </span>
              </div>
            </div>
          </button>
        </div>
      </template>
    </div>

    <!-- ── Portfolio nav link ─────────────────────────────────────── -->
    <div class="px-3 pb-1">
      <button
        id="sidebar-portfolio-link"
        class="w-full text-left p-3 rounded-xl flex items-center gap-3 border group hover-scale-premium"
        :class="[
          route.name === 'portfolio'
            ? 'glass-card border-gold/25 text-foreground'
            : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground',
        ]"
        @click="router.push('/portfolio'); store.closeMobileMenu()"
        aria-label="Go to Portfolio"
      >
        <div
          class="h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 border"
          :class="route.name === 'portfolio'
            ? 'bg-gold/15 text-gold border-gold/30'
            : 'bg-muted/50 border border-border/40 text-muted-foreground'"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M2 5.5h12M2 5.5v7a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-7M2 5.5V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
            <path d="M6 3V2.5a2 2 0 0 1 4 0V3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
          </svg>
        </div>
        <span
          class="font-semibold text-sm transition-all duration-200 sidebar-hide-on-collapsed"
          :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']"
        >
          Portfolio
        </span>
      </button>
    </div>

    <!-- ── Footer: Engine status + auth ──────────────────────────── -->
    <div class="p-4 border-t border-border/40 flex flex-col gap-2 overflow-hidden shrink-0">

      <!-- Backend / Engine status -->
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
              : 'bg-amber-500/10 border-amber-500/20 text-amber-400',
          ]"
          aria-hidden="true"
        >
          <Cpu class="h-4 w-4" :class="[!configError ? 'animate-pulse' : '']" />
        </div>

        <div
          class="flex flex-col min-w-0 transition-all duration-200 sidebar-hide-on-collapsed"
          :class="[sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']"
        >
          <span class="text-xs font-semibold text-foreground truncate">
            {{ configError
              ? 'Server Offline'
              : configLoading
              ? 'Connecting…'
              : (config?.llm_model || 'VADER Engine') }}
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
                : 'text-amber-400',
            ]"
          >
            <span
              class="h-1.5 w-1.5 rounded-full animate-ping"
              :class="[
                configError ? 'bg-rose-400'
                : configLoading ? 'bg-blue-400'
                : config?.llm_configured ? 'bg-emerald-400'
                : 'bg-amber-400',
              ]"
              aria-hidden="true"
            />
            {{ configError
              ? 'Backend Unreachable'
              : configLoading
              ? 'Checking API…'
              : config?.llm_configured
              ? 'Live AI Active'
              : 'Simulation Mode' }}
          </span>
        </div>
      </div>

      <!-- Auth: Sign in / Sign out -->
      <div class="sidebar-hide-on-collapsed" :class="[sidebarCollapsed ? 'hidden' : 'block']">
        <button
          v-if="authStore.isAuthenticated"
          id="sidebar-logout-btn"
          class="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-150 cursor-pointer"
          @click="handleLogout"
          aria-label="Sign out"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M5.5 2H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h2.5M9.5 10l2.5-3-2.5-3M12 7H5.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Sign out ({{ authStore.user?.display_name }})
        </button>
        <button
          v-else
          id="sidebar-login-btn"
          class="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-gold hover:bg-gold/10 transition-all duration-150 cursor-pointer"
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

<style scoped>
.sidebar-container {
  container-type: inline-size;
  container-name: sidebar;
}

@container sidebar (max-width: 240px) {
  .sidebar-hide-on-collapsed {
    display: none !important;
  }
  .sidebar-center-on-collapsed {
    justify-content: center !important;
  }
}
</style>
