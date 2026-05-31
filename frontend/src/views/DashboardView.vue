<script setup lang="ts">
import { defineAsyncComponent, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/composables/useAppStore'
import { storeToRefs } from 'pinia'
import WidgetWrapper from '@/components/dashboard/WidgetWrapper.vue'
import CryptoTickerBar from '@/components/dashboard/CryptoTickerBar.vue'
import { Sliders, Eye, EyeOff, RotateCcw, LayoutGrid, Search } from '@lucide/vue'
import { GridLayout, GridItem } from 'grid-layout-plus'
import type { RouteAssetId } from '@/types/market'

// Lazy-load heavy widgets to split chunks and speed up TTI
const SentimentHeatmap    = defineAsyncComponent(() => import('@/components/dashboard/SentimentHeatmap.vue'))
const MetricsPanel        = defineAsyncComponent(() => import('@/components/dashboard/MetricsPanel.vue'))
const SentimentChart      = defineAsyncComponent(() => import('@/components/dashboard/SentimentChart.vue'))
const LiveFeed            = defineAsyncComponent(() => import('@/components/dashboard/LiveFeed.vue'))
const MarketOverviewGrid  = defineAsyncComponent(() => import('@/components/dashboard/MarketOverviewGrid.vue'))
const NewsCorrelationPanel = defineAsyncComponent(() => import('@/components/dashboard/NewsCorrelationPanel.vue'))
const FearGreedGauge      = defineAsyncComponent(() => import('@/components/dashboard/FearGreedGauge.vue'))

const route = useRoute()
const store = useAppStore()
const { timeframe } = storeToRefs(store)

/** The active asset ID is authoritative from the URL parameter. */
const assetId = computed(() => route.params.id as RouteAssetId)

// ──────────────────────────────────────────────────────────────────────────────
// Grid Layout Types
// ──────────────────────────────────────────────────────────────────────────────

interface GridWidget {
  /** Unique widget identifier — must match componentMap keys. */
  i: 'overview' | 'heatmap' | 'metrics' | 'chart' | 'feed' | 'feargreed'
  title: string
  visible: boolean
  collapsed: boolean
  /** Grid position and size (12-column base). */
  x: number
  y: number
  w: number
  h: number
  /** Minimum height in grid rows. */
  minH?: number
  /** Whether the user can resize this widget. */
  isResizable?: boolean
}

const LAYOUT_CACHE_KEY = 'dashboard_grid_layout_v4'

/** Default 12-column bento grid — mirrors the plan table. */
const defaultGrid: GridWidget[] = [
  { i: 'overview',  title: 'Market Overview',          visible: true, collapsed: false, x: 0, y: 0,  w: 12, h: 8,  minH: 6, isResizable: true },
  { i: 'heatmap',   title: 'Sentiment Heatmap',        visible: true, collapsed: false, x: 0, y: 8,  w: 8,  h: 6,  minH: 4, isResizable: true  },
  { i: 'feargreed', title: 'Fear & Greed Index',       visible: true, collapsed: false, x: 8, y: 8,  w: 4,  h: 6,  minH: 5, isResizable: true },
  { i: 'metrics',   title: 'Price Metrics',            visible: true, collapsed: false, x: 0, y: 14, w: 12, h: 4,  minH: 3, isResizable: true },
  { i: 'chart',     title: 'Interactive Overlay Chart', visible: true, collapsed: false, x: 0, y: 18, w: 8,  h: 9,  minH: 6, isResizable: true  },
  { i: 'feed',      title: 'Live Sentiment Feed',       visible: true, collapsed: false, x: 8, y: 18, w: 4,  h: 9,  minH: 6, isResizable: true  },
]

const gridWidgets = ref<GridWidget[]>([])
const showSettings = ref(false)
const searchQuery = ref('')

/** Map widget IDs to async components. */
const componentMap: Record<string, ReturnType<typeof defineAsyncComponent>> = {
  overview:  MarketOverviewGrid,
  heatmap:   SentimentHeatmap,
  feargreed: FearGreedGauge,
  metrics:   MetricsPanel,
  chart:     SentimentChart,
  feed:      LiveFeed,
}

// ──────────────────────────────────────────────────────────────────────────────
// Layout Persistence
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Hydrates grid layout from localStorage, falling back to defaults.
 * Validates that all required widget IDs are present in the cached schema.
 */
function getInitialLayout(): GridWidget[] {
  try {
    const cached = localStorage.getItem(LAYOUT_CACHE_KEY)
    if (cached) {
      const parsed = JSON.parse(cached) as GridWidget[]
      const isValid = defaultGrid.every(def => parsed.some(p => p.i === def.i))
      if (isValid) {
        return parsed
      }
    }
  } catch {
    // Silently fall back to defaults on parse error
  }
  return JSON.parse(JSON.stringify(defaultGrid))
}

gridWidgets.value = getInitialLayout()

/** Persists current grid layout to localStorage. */
function saveLayout(): void {
  try {
    localStorage.setItem(LAYOUT_CACHE_KEY, JSON.stringify(gridWidgets.value))
  } catch {
    // Ignore storage quota errors
  }
}

// Layout is hydrated synchronously, no need to wait for onMounted

/** Toggles a widget's visibility and persists the change. */
function toggleWidgetVisibility(id: GridWidget['i']): void {
  const widget = gridWidgets.value.find(w => w.i === id)
  if (widget) {
    widget.visible = !widget.visible
    saveLayout()
  }
}

/** Resets dashboard layout to factory defaults. */
function handleResetLayout(): void {
  gridWidgets.value = JSON.parse(JSON.stringify(defaultGrid))
  saveLayout()
  showSettings.value = false
}

/**
 * Returns grid items formatted for `grid-layout-plus` (excluding hidden widgets).
 * Hidden widgets are removed from the layout array so the grid
 * collapses the gap they would otherwise leave.
 */
const visibleGridLayout = computed(() =>
  gridWidgets.value
    .filter(w => w.visible)
    .map(w => ({
      i: w.i,
      x: w.x,
      y: w.y,
      w: w.w,
      h: w.h,
      minH: w.minH,
      isResizable: w.isResizable ?? true,
    }))
)

/**
 * Syncs position changes from the grid engine back into our reactive state
 * and persists the new layout. Called on `@layout-updated` events.
 */
function onLayoutUpdated(updatedLayout: Array<{ i: string; x: number; y: number; w: number; h: number }>): void {
  for (const item of updatedLayout) {
    const widget = gridWidgets.value.find(w => w.i === item.i)
    if (widget) {
      widget.x = item.x
      widget.y = item.y
      widget.w = item.w
      widget.h = item.h
    }
  }
  saveLayout()
}
</script>

<template>
  <main class="flex-1 overflow-y-auto">
    <!-- Sticky ticker strip -->
    <div class="sticky top-0 z-30">
      <CryptoTickerBar />
    </div>

    <!-- Padded page body -->
    <div class="px-3 sm:px-4 lg:px-6 pb-8">

      <!-- Page Header & Toolbar -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 select-none shrink-0 border-b border-border/10 py-4 mb-2">
        <div class="flex flex-col gap-1">
          <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight font-display text-gradient-crypto">
            Market Intelligence Center
          </h1>
          <p class="text-xs text-slate-400 font-medium leading-relaxed">
            Real-time AI-powered sentiment analysis across crypto &amp; equity markets.
          </p>
        </div>

        <!-- Toolbar: Search + Config -->
        <div class="relative flex items-center gap-2 shrink-0 self-start sm:self-center">
          <!-- Search bar -->
          <div class="flex items-center bg-slate-900/40 border border-border/60 rounded-xl px-3 py-1.5">
            <Search class="h-3.5 w-3.5 text-slate-400 mr-2 shrink-0" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search assets…"
              class="bg-transparent border-none outline-none text-xs text-slate-200 placeholder-slate-500 w-24 sm:w-32 lg:w-40"
            />
          </div>

          <!-- Layout config toggle -->
          <button
            id="layout-config-btn"
            @click="showSettings = !showSettings"
            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border/60 bg-slate-900/40 hover:bg-slate-900 text-xs font-semibold text-slate-300 hover:text-slate-100 transition-all shadow-md cursor-pointer select-none"
          >
            <Sliders class="h-4 w-4" />
            <span class="hidden sm:inline">Layout</span>
          </button>

          <!-- Config dropdown -->
          <Transition name="fade">
            <div
              v-if="showSettings"
              class="absolute right-0 top-full mt-2 w-72 rounded-2xl border border-border/40 p-4 shadow-2xl z-40 glass-panel flex flex-col gap-4"
            >
              <div class="flex items-center justify-between border-b border-white/5 pb-2">
                <span class="text-xs font-bold text-slate-200 flex items-center gap-1.5 uppercase tracking-wider">
                  <LayoutGrid class="h-4 w-4 text-indigo-400" />
                  Dashboard Widgets
                </span>
                <button
                  @click="handleResetLayout"
                  class="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors cursor-pointer"
                  title="Reset to defaults"
                >
                  <RotateCcw class="h-3 w-3" />
                  Reset
                </button>
              </div>

              <div class="space-y-2">
                <div
                  v-for="widget in gridWidgets"
                  :key="widget.i"
                  class="flex items-center justify-between p-2 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <button
                      :id="`toggle-${widget.i}`"
                      @click="toggleWidgetVisibility(widget.i)"
                      class="p-1 rounded hover:bg-white/5 transition-colors cursor-pointer shrink-0"
                      :class="widget.visible ? 'text-indigo-400' : 'text-slate-600'"
                    >
                      <Eye v-if="widget.visible" class="h-4 w-4" />
                      <EyeOff v-else class="h-4 w-4" />
                    </button>
                    <span class="text-xs font-semibold text-slate-300 truncate">{{ widget.title }}</span>
                  </div>
                  <span class="text-[10px] text-slate-600 font-mono shrink-0">
                    {{ widget.w }}×{{ widget.h }}
                  </span>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <!-- ──────────────────────────────────────────────────────────────────
           2D Draggable & Resizable Grid (grid-layout-plus)
           Widgets shift fluidly as you drag. Resize via the ↗ handle.
           Layout auto-persists to localStorage.
           ────────────────────────────────────────────────────────────────── -->
      <GridLayout
        v-model:layout="visibleGridLayout"
        :col-num="12"
        :row-height="54"
        :is-draggable="true"
        :is-resizable="true"
        :margin="[12, 12]"
        :use-css-transforms="true"
        :responsive="true"
        @layout-updated="onLayoutUpdated"
        class="grid-canvas"
      >
        <GridItem
          v-for="item in visibleGridLayout"
          :key="item.i"
          :i="item.i"
          :x="item.x"
          :y="item.y"
          :w="item.w"
          :h="item.h"
          :min-h="item.minH ?? 3"
          :is-resizable="item.isResizable ?? true"
          drag-allow-from=".drag-handle"
          class="grid-widget"
        >
          <WidgetWrapper
            :title="gridWidgets.find(w => w.i === item.i)?.title ?? ''"
            :widget-id="item.i"
            v-model:collapsed="gridWidgets.find(w => w.i === item.i)!.collapsed"
            @hide="toggleWidgetVisibility(item.i as GridWidget['i'])"
            class="h-full"
          >
            <Suspense>
              <component
                :is="componentMap[item.i]"
                :asset-id="assetId"
                :timeframe="timeframe"
                :search-query="searchQuery"
                class="h-full"
              />
              <template #fallback>
                <div class="h-full min-h-[200px] rounded-2xl animate-pulse bg-white/[0.02]" />
              </template>
            </Suspense>

            <!-- News Correlation stacked below Live Feed -->
            <template v-if="item.i === 'feed'">
              <Suspense>
                <NewsCorrelationPanel :asset-id="assetId" class="mt-3" />
                <template #fallback>
                  <div class="mt-3 h-32 rounded-2xl animate-pulse bg-white/[0.02]" />
                </template>
              </Suspense>
            </template>
          </WidgetWrapper>
        </GridItem>
      </GridLayout>

    </div><!-- end padded body -->
  </main>
</template>

<style scoped>
/* Smooth widget movement during drag via CSS transforms (GPU-composited) */
.grid-widget {
  transition: box-shadow 0.2s ease;
}

.grid-widget:hover {
  z-index: 5;
}

/* Shadow lift while actively dragging */
:global(.vue-grid-item.vue-draggable-dragging) {
  box-shadow: 0 24px 60px -12px rgba(0, 0, 0, 0.8), 0 0 0 2px rgba(139, 92, 246, 0.4);
  z-index: 100 !important;
  opacity: 0.95;
  transform: scale(1.01);
}

/* Smooth neighbouring widget repositioning */
:global(.vue-grid-item:not(.vue-draggable-dragging)) {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Resize handle style */
:global(.vue-resizable-handle) {
  width: 20px;
  height: 20px;
  border-right: 2px solid rgba(139, 92, 246, 0.4);
  border-bottom: 2px solid rgba(139, 92, 246, 0.4);
  border-radius: 0 0 4px 0;
  bottom: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

:global(.vue-grid-item:hover .vue-resizable-handle) {
  opacity: 1;
}

/* Config dropdown fade */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
