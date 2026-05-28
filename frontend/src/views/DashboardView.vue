<script setup lang="ts">
import { defineAsyncComponent, computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/composables/useAppStore'
import { storeToRefs } from 'pinia'
import WidgetWrapper from '@/components/dashboard/WidgetWrapper.vue'
import { Sliders, Eye, EyeOff, RotateCcw, LayoutGrid } from '@lucide/vue'
import type { RouteAssetId } from '@/types/market'

// Lazy-load heavy widgets to divide chunks and speed up TTI
const MetricsPanel = defineAsyncComponent(() => import('@/components/dashboard/MetricsPanel.vue'))
const SentimentChart = defineAsyncComponent(() => import('@/components/dashboard/SentimentChart.vue'))
const LiveFeed = defineAsyncComponent(() => import('@/components/dashboard/LiveFeed.vue'))

const route = useRoute()
const store = useAppStore()
const { timeframe } = storeToRefs(store)

/** The active asset ID is authoritative from URL parameter */
const assetId = computed(() => route.params.id as RouteAssetId)

// Define Layout Types and Defaults
export interface WidgetLayout {
  id: 'metrics' | 'chart' | 'feed'
  title: string
  visible: boolean
  collapsed: boolean
  order: number // Higher order values render lower
}

const LAYOUT_CACHE_KEY = 'dashboard_widgets_layout_v1'

const defaultLayout: WidgetLayout[] = [
  { id: 'metrics', title: 'Market Price Metrics', visible: true, collapsed: false, order: 1 },
  { id: 'chart', title: 'Interactive Overlay Chart', visible: true, collapsed: false, order: 2 },
  { id: 'feed', title: 'Live Sentiment Feed', visible: true, collapsed: false, order: 3 }
]

const layouts = ref<WidgetLayout[]>([])
const showSettings = ref(false)

/**
 * Hydrates widget configuration settings from LocalStorage,
 * falling back to initial presets.
 */
function hydrateLayout(): void {
  try {
    const cached = localStorage.getItem(LAYOUT_CACHE_KEY)
    if (cached) {
      const parsed = JSON.parse(cached) as WidgetLayout[]
      // Ensure all required default widgets are present in the cached schema
      const isValid = defaultLayout.every(def => parsed.some(p => p.id === def.id))
      if (isValid) {
        layouts.value = parsed.sort((a, b) => a.order - b.order)
        console.log('[DashboardView] Hydrated customized layout schema.')
        return
      }
    }
  } catch (err) {
    console.error('[DashboardView] Cache hydration error:', err)
  }
  layouts.value = JSON.parse(JSON.stringify(defaultLayout))
}

onMounted(() => {
  hydrateLayout()
})

/**
 * Persists current widget layout configurations to LocalStorage.
 */
function saveLayout(): void {
  try {
    localStorage.setItem(LAYOUT_CACHE_KEY, JSON.stringify(layouts.value))
  } catch (err) {
    console.error('[DashboardView] Failed to persist layout cache:', err)
  }
}

/** Toggles the visibility of a widget. */
function toggleWidgetVisibility(id: 'metrics' | 'chart' | 'feed'): void {
  const widget = layouts.value.find(w => w.id === id)
  if (widget) {
    widget.visible = !widget.visible
    saveLayout()
  }
}

/** Moves a widget up in the rendering order. */
function moveWidgetUp(index: number): void {
  if (index <= 0) return
  const current = layouts.value[index]
  const previous = layouts.value[index - 1]
  if (current && previous) {
    // Swap positions
    layouts.value[index] = previous
    layouts.value[index - 1] = current
    
    // Recalculate order indices
    layouts.value.forEach((w, idx) => {
      w.order = idx + 1
    })
    saveLayout()
  }
}

/** Moves a widget down in the rendering order. */
function moveWidgetDown(index: number): void {
  if (index >= layouts.value.length - 1) return
  const current = layouts.value[index]
  const next = layouts.value[index + 1]
  if (current && next) {
    // Swap positions
    layouts.value[index] = next
    layouts.value[index + 1] = current
    
    // Recalculate order indices
    layouts.value.forEach((w, idx) => {
      w.order = idx + 1
    })
    saveLayout()
  }
}

/** Resets dashboard widgets layout settings to defaults. */
function handleResetLayout(): void {
  layouts.value = JSON.parse(JSON.stringify(defaultLayout))
  saveLayout()
  showSettings.value = false
}

// Compute dynamic rendering segments
const chartWidget = computed(() => layouts.value.find(w => w.id === 'chart'))
const feedWidget = computed(() => layouts.value.find(w => w.id === 'feed'))

/** Sorts and filters the main lower row widgets (chart & feed) if visible. */
const visibleMainWidgets = computed(() => {
  return [chartWidget.value, feedWidget.value]
    .filter((w): w is WidgetLayout => !!w && w.visible)
    .sort((a, b) => a.order - b.order)
})

/** Computes structural CSS grids for the main body rows based on visibility configurations. */
const mainRowGridClass = computed(() => {
  const chartVisible = chartWidget.value?.visible
  const feedVisible = feedWidget.value?.visible

  if (chartVisible && feedVisible) {
    return 'grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6 items-stretch'
  }
  return 'grid grid-cols-1 gap-4 lg:gap-6 items-stretch'
})
</script>

<template>
  <main class="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 space-y-4 lg:space-y-6">
    <!-- Page Header & Layout Customizer Toolbar -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 select-none shrink-0 border-b border-border/10 pb-4">
      <div class="flex flex-col gap-1">
        <h1
          class="text-xl sm:text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent"
        >
          Market Intelligence Center
        </h1>
        <p class="text-xs text-slate-400 font-medium leading-relaxed">
          Aggregated orderbook quotes overlaid with real-time LLM-processed sentiment metrics.
        </p>
      </div>

      <!-- Controls Popover Trigger -->
      <div class="relative shrink-0 self-start sm:self-center">
        <button
          @click="showSettings = !showSettings"
          class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border/60 bg-slate-900/40 hover:bg-slate-900 text-xs font-semibold text-slate-300 hover:text-slate-100 transition-all shadow-md select-none cursor-pointer"
        >
          <Sliders class="h-4 w-4" />
          <span>Настроить сетку</span>
        </button>

        <!-- Customization Glass Panel dropdown -->
        <Transition name="fade">
          <div
            v-if="showSettings"
            class="absolute right-0 mt-2 w-72 rounded-2xl border border-border/40 p-4 shadow-2xl z-20 glass-panel flex flex-col gap-4 animate-fade-in"
          >
            <div class="flex items-center justify-between border-b border-white/5 pb-2">
              <span class="text-xs font-bold text-slate-200 flex items-center gap-1.5 uppercase tracking-wider">
                <LayoutGrid class="h-4 w-4 text-indigo-400" />
                Виджеты дашборда
              </span>
              <button 
                @click="handleResetLayout"
                class="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors cursor-pointer"
                title="Сбросить к значениям по умолчанию"
              >
                <RotateCcw class="h-3 w-3" />
                Сброс
              </button>
            </div>

            <!-- List of Widgets under customization -->
            <div class="space-y-3">
              <div 
                v-for="(widget, idx) in layouts" 
                :key="widget.id"
                class="flex items-center justify-between p-2 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors"
              >
                <div class="flex items-center gap-2 min-w-0">
                  <!-- Checkbox toggle visibility -->
                  <button
                    @click="toggleWidgetVisibility(widget.id)"
                    class="p-1 rounded hover:bg-white/5 transition-colors cursor-pointer shrink-0"
                    :class="[widget.visible ? 'text-indigo-400' : 'text-slate-600']"
                  >
                    <Eye v-if="widget.visible" class="h-4 w-4" />
                    <EyeOff v-else class="h-4 w-4" />
                  </button>

                  <span class="text-xs font-semibold text-slate-300 truncate">
                    {{ widget.title }}
                  </span>
                </div>

                <!-- Re-order buttons -->
                <div class="flex items-center gap-0.5 shrink-0">
                  <button
                    @click="moveWidgetUp(idx)"
                    :disabled="idx === 0"
                    class="p-1 rounded hover:bg-white/5 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                    title="Вверх"
                  >
                    ▲
                  </button>
                  <button
                    @click="moveWidgetDown(idx)"
                    :disabled="idx === layouts.length - 1"
                    class="p-1 rounded hover:bg-white/5 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                    title="Вниз"
                  >
                    ▼
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Active dynamic Grid Canvas -->
    <div class="flex flex-col gap-4 lg:gap-6 min-w-0">
      
      <!-- Loop widgets matching their User Sorted Order configurations -->
      <template v-for="widget in layouts" :key="widget.id">
        
        <!-- SECTION 1: Metrics panel (renders if ordered before or after chart/feed, full width) -->
        <div 
          v-if="widget.id === 'metrics' && widget.visible"
          class="w-full transition-all duration-300"
          :style="{ order: widget.order }"
        >
          <WidgetWrapper
            :title="widget.title"
            :widget-id="widget.id"
            v-model:collapsed="widget.collapsed"
            @hide="toggleWidgetVisibility(widget.id)"
          >
            <Suspense>
              <MetricsPanel :asset-id="assetId" />
              <template #fallback>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div v-for="i in 4" :key="i" class="h-28 bg-card border border-border/30 rounded-2xl animate-pulse" />
                </div>
              </template>
            </Suspense>
          </WidgetWrapper>
        </div>

      </template>

      <!-- SECTION 2: Dynamic Row (renders interactive chart and feeds as configured) -->
      <div 
        v-if="visibleMainWidgets.length > 0"
        class="transition-all duration-300 min-w-0"
        :class="mainRowGridClass"
        :style="{ 
          order: Math.min(
            chartWidget?.visible ? chartWidget.order : Infinity, 
            feedWidget?.visible ? feedWidget.order : Infinity
          ) 
        }"
      >
        <!-- Render ordered elements dynamically in the main row row column templates -->
        <div
          v-for="widget in visibleMainWidgets"
          :key="widget.id"
          class="flex flex-col transition-all duration-300 min-w-0"
          :class="[
            widget.id === 'chart' && visibleMainWidgets.length > 1 ? 'lg:col-span-2' : '',
            widget.id === 'feed' && visibleMainWidgets.length > 1 ? 'lg:col-span-1' : '',
            visibleMainWidgets.length === 1 ? 'w-full lg:col-span-1' : ''
          ]"
        >
          <!-- Candlestick Chart -->
          <WidgetWrapper
            v-if="widget.id === 'chart'"
            :title="widget.title"
            :widget-id="widget.id"
            v-model:collapsed="widget.collapsed"
            @hide="toggleWidgetVisibility(widget.id)"
          >
            <Suspense>
              <SentimentChart :asset-id="assetId" :timeframe="timeframe" />
              <template #fallback>
                <div class="glass-card rounded-3xl border border-border/40 h-[320px] sm:h-[400px] lg:h-[480px] animate-pulse" />
              </template>
            </Suspense>
          </WidgetWrapper>

          <!-- Live Sentiment RSS Feed -->
          <WidgetWrapper
            v-else-if="widget.id === 'feed'"
            :title="widget.title"
            :widget-id="widget.id"
            v-model:collapsed="widget.collapsed"
            @hide="toggleWidgetVisibility(widget.id)"
          >
            <Suspense>
              <LiveFeed :asset-id="assetId" />
              <template #fallback>
                <div class="glass-card rounded-3xl border border-border/40 h-[450px] sm:h-[550px] lg:h-full animate-pulse" />
              </template>
            </Suspense>
          </WidgetWrapper>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
