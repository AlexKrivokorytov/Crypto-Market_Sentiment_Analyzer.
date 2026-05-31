<script setup lang="ts">
/**
 * PortfolioView — Live portfolio tracker with P&L cards and position management.
 *
 * Uses usePortfolio (local storage) and useAssets for live prices.
 * Pinia auth store provides the current user context.
 */

import { computed, ref } from 'vue'
import { useAuthStore } from '@/composables/useAuthStore'
import { usePortfolio } from '@/composables/usePortfolio'
import { useAssets } from '@/composables/useMarketData'
import type { RouteAssetId } from '@/types/market'
import {
  formatPrice,
  getAssetBrandColor,
} from '@/composables/useCryptoFormatters'
import { Plus, Trash2, TrendingUp, TrendingDown, Minus, Briefcase, PlusCircle, AlertCircle, X } from '@lucide/vue'

const authStore = useAuthStore()

// ── Queries ─────────────────────────────────────────────────────────────────

const { positions, upsertPosition, deletePosition } = usePortfolio()
const { data: assets } = useAssets()

// ── Portfolio summary ────────────────────────────────────────────────────────

// Map to fast lookup
const assetPriceMap = computed(() => {
  const map: Record<string, number> = {}
  if (assets.value) {
    for (const a of assets.value) {
      map[a.id] = a.price
    }
  }
  return map
})

const enrichedPositions = computed(() => {
  return positions.value.map(p => {
    const current_price = assetPriceMap.value[p.asset_id] || 0
    const value = p.quantity * current_price
    const cost = p.quantity * p.avg_buy_price
    const pnl_usd = value - cost
    const pnl_pct = cost > 0 ? (pnl_usd / cost) * 100 : 0
    return {
      ...p,
      current_price,
      value,
      pnl_usd,
      pnl_pct
    }
  })
})

const totalValue = computed<number>(() =>
  enrichedPositions.value.reduce((sum, p) => sum + p.value, 0)
)

const totalPnlUsd = computed<number>(() =>
  enrichedPositions.value.reduce((sum, p) => sum + p.pnl_usd, 0)
)

const totalPnlPct = computed<number>(() => {
  const costBasis = enrichedPositions.value.reduce(
    (sum, p) => sum + p.avg_buy_price * p.quantity,
    0
  )
  return costBasis > 0 ? (totalPnlUsd.value / costBasis) * 100 : 0
})

// ── Add position modal ───────────────────────────────────────────────────────

const showAddModal = ref(false)
const newAssetId = ref<RouteAssetId>('BTC')
const newQuantity = ref<string>('')
const newAvgBuy = ref<string>('')
const addError = ref<string | null>(null)

const ASSET_OPTIONS: RouteAssetId[] = ['BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA', 'AAPL']

function handleAddPosition(): void {
  addError.value = null
  const qty = parseFloat(newQuantity.value)
  const price = parseFloat(newAvgBuy.value)
  if (!newAssetId.value || isNaN(qty) || qty <= 0 || isNaN(price) || price <= 0) {
    addError.value = 'Please enter valid quantity and price.'
    return
  }
  upsertPosition(newAssetId.value, qty, price)
  showAddModal.value = false
  newQuantity.value = ''
  newAvgBuy.value = ''
  addError.value = null
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value)
}

function pnlClass(value: number): string {
  if (value > 0) return 'text-signal price-flash-up'
  if (value < 0) return 'text-alarm price-flash-down'
  return 'text-slate-400'
}

function pnlIcon(value: number) {
  if (value > 0) return TrendingUp
  if (value < 0) return TrendingDown
  return Minus
}
</script>

<template>
  <main class="flex-1 overflow-y-auto w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 font-mono">
    <!-- Header -->
    <header class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-signal/20 pb-6">
      <div class="flex flex-col gap-1.5">
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight font-display text-signal flex items-center gap-2">
          <Briefcase class="h-6 w-6" />
          [SYS_PORTFOLIO]
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 font-medium">
          LOCAL_TRACKER_MODE_ACTIVE // <strong class="text-slate-200">{{ authStore.user?.display_name || 'GUEST' }}</strong>
        </p>
      </div>
      <button
        @click="showAddModal = true"
        class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded text-xs font-bold text-black bg-signal hover:bg-signal/90 transition-all shrink-0"
      >
        <Plus class="h-4 w-4" />
        ADD_POSITION
      </button>
    </header>

    <!-- Summary KPI Cards -->
    <section class="grid grid-cols-2 lg:grid-cols-4 gap-4" aria-label="Portfolio Summary">
      <div class="glass-card-signal scanline-overlay p-5 rounded flex flex-col gap-2 relative overflow-hidden group">
        <span class="text-[10px] font-bold text-signal uppercase tracking-wider relative z-10">> NET_VALUE</span>
        <span class="text-2xl sm:text-3xl font-bold text-white price-mono tracking-tight relative z-10">{{ formatCurrency(totalValue) }}</span>
      </div>
      
      <div class="glass-card scanline-overlay p-5 rounded flex flex-col gap-2 relative overflow-hidden group border border-white/5">
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider relative z-10">> PNL_USD</span>
        <div class="flex items-center gap-1.5 relative z-10">
          <span class="text-xl sm:text-2xl font-bold price-mono tracking-tight" :class="pnlClass(totalPnlUsd)">
            {{ totalPnlUsd >= 0 ? '+' : '' }}{{ formatCurrency(totalPnlUsd) }}
          </span>
        </div>
      </div>
      
      <div class="glass-card scanline-overlay p-5 rounded flex flex-col gap-2 relative overflow-hidden group border border-white/5">
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider relative z-10">> PNL_PCT</span>
        <div class="flex items-center gap-1.5 relative z-10">
          <component :is="pnlIcon(totalPnlPct)" class="h-5 w-5 shrink-0" :class="pnlClass(totalPnlPct)" />
          <span class="text-xl sm:text-2xl font-bold price-mono tracking-tight" :class="pnlClass(totalPnlPct)">
            {{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%
          </span>
        </div>
      </div>
      
      <div class="glass-card scanline-overlay p-5 rounded flex flex-col gap-2 relative overflow-hidden group border border-white/5">
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider relative z-10">> OPEN_POSITIONS</span>
        <span class="text-2xl sm:text-3xl font-bold text-slate-100 price-mono tracking-tight relative z-10">{{ enrichedPositions.length }}</span>
      </div>
    </section>

    <!-- Empty State -->
    <div v-if="!enrichedPositions.length" class="glass-card flex flex-col items-center justify-center text-center p-12 sm:p-20 rounded border-dashed border-white/20">
      <div class="h-16 w-16 bg-slate-900/50 flex items-center justify-center mb-6 border border-white/10">
        <Briefcase class="h-8 w-8 text-slate-500" />
      </div>
      <h2 class="text-xl font-bold text-signal mb-2">NO_POSITIONS_DETECTED</h2>
      <p class="text-sm text-slate-400 max-w-md mb-8">
        Portfolio registry is empty. Add tracked assets to monitor local P&L.
      </p>
      <button 
        @click="showAddModal = true"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded text-sm font-bold text-black bg-signal hover:bg-signal/90 transition-colors"
      >
        <PlusCircle class="h-4 w-4" />
        INITIALIZE_POSITION
      </button>
    </div>

    <!-- Positions List (Desktop + Mobile responsive) -->
    <section v-else aria-label="Portfolio positions" class="space-y-4">
      <!-- Desktop List Header (hidden on mobile) -->
      <div class="hidden sm:grid grid-cols-12 gap-4 px-6 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/10 mb-2 bg-white/[0.02]">
        <div class="col-span-3">ASSET_TICKER</div>
        <div class="col-span-2 text-right">SIZE</div>
        <div class="col-span-2 text-right">ENTRY_PRICE</div>
        <div class="col-span-2 text-right">MARK_VALUE</div>
        <div class="col-span-2 text-right">PNL_DATA</div>
        <div class="col-span-1 text-center">CMD</div>
      </div>

      <!-- Position Rows -->
      <TransitionGroup name="list" tag="div" class="flex flex-col gap-3">
        <div 
          v-for="pos in enrichedPositions" 
          :key="pos.asset_id"
          class="glass-card hover:bg-white/[0.04] p-4 sm:p-0 sm:px-6 sm:py-4 rounded flex flex-col sm:grid sm:grid-cols-12 sm:items-center gap-4 transition-all duration-300 relative group overflow-hidden border border-white/5"
        >
          <!-- Asset Info -->
          <div class="col-span-3 flex items-center gap-3 relative z-10">
            <span class="h-2.5 w-2.5 shadow-sm" :style="{ backgroundColor: getAssetBrandColor(pos.asset_id) }" />
            <div>
              <div class="font-bold text-slate-100 font-display text-base">{{ pos.asset_id }}</div>
            </div>
            <!-- Mobile current price badge (hidden on desktop) -->
            <div class="sm:hidden ml-auto px-2 py-1 bg-slate-900/50 rounded text-xs font-bold price-mono text-slate-300 border border-white/10">
              {{ formatPrice(pos.current_price, pos.asset_id) }}
            </div>
          </div>

          <!-- Quantity -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">SIZE</span>
            <div class="font-bold price-mono text-slate-200 text-sm">
              {{ pos.quantity }}
            </div>
          </div>

          <!-- Avg Buy -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">ENTRY</span>
            <div class="font-semibold price-mono text-slate-400 text-sm">
              {{ formatPrice(pos.avg_buy_price, pos.asset_id) }}
            </div>
          </div>

          <!-- Current Value -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">MARK</span>
            <div class="font-bold price-mono text-slate-100 text-sm sm:text-base">
              {{ formatCurrency(pos.value) }}
            </div>
          </div>

          <!-- P&L -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">PNL</span>
            <div class="flex flex-col items-end">
              <span class="font-bold price-mono text-sm" :class="pnlClass(pos.pnl_usd)">
                {{ pos.pnl_usd >= 0 ? '+' : '' }}{{ formatCurrency(pos.pnl_usd) }}
              </span>
              <span class="text-[10px] font-bold price-mono bg-white/5 px-1.5 py-0.5 mt-0.5 border border-white/10" :class="pnlClass(pos.pnl_pct)">
                {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="col-span-1 flex justify-end sm:justify-center mt-2 sm:mt-0 border-t border-white/10 pt-3 sm:border-0 sm:pt-0 relative z-10">
            <button
              class="p-2 rounded bg-alarm/10 hover:bg-alarm/20 text-alarm border border-alarm/20 transition-colors"
              @click="deletePosition(pos.asset_id)"
              aria-label="Remove Position"
            >
              <Trash2 class="h-4 w-4" />
            </button>
          </div>
        </div>
      </TransitionGroup>
    </section>

    <!-- Add Position Modal -->
    <Teleport to="body">
      <Transition name="fade-modal">
        <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/80 backdrop-blur-sm transition-opacity" @click="showAddModal = false" />
          
          <!-- Modal Content -->
          <div class="glass-card relative w-full max-w-md rounded p-6 sm:p-8 shadow-2xl border border-signal/40 transform transition-all font-mono">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-bold text-signal font-display flex items-center gap-2">
                <div class="p-1.5 rounded bg-signal/10 text-signal">
                  <Plus class="h-5 w-5" />
                </div>
                NEW_RECORD
              </h2>
              <button @click="showAddModal = false" class="p-1.5 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
                <X class="h-5 w-5" />
              </button>
            </div>

            <form @submit.prevent="handleAddPosition" class="space-y-4" novalidate>
              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">> ASSET_TICKER</label>
                <div class="relative">
                  <select v-model="newAssetId" class="w-full appearance-none bg-black/50 border border-white/20 rounded px-4 py-3 text-sm font-bold text-white focus:outline-none focus:border-signal transition-all cursor-pointer">
                    <option v-for="a in ASSET_OPTIONS" :key="a" :value="a">{{ a }}</option>
                  </select>
                </div>
              </div>

              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">> QUANTITY</label>
                <input
                  v-model="newQuantity"
                  type="number"
                  placeholder="0.0"
                  step="any"
                  min="0"
                  required
                  class="w-full bg-black/50 border border-white/20 rounded px-4 py-3 text-sm font-bold price-mono text-white placeholder-slate-600 focus:outline-none focus:border-signal transition-all"
                />
              </div>

              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">> ENTRY_PRICE_USD</label>
                <input
                  v-model="newAvgBuy"
                  type="number"
                  placeholder="0.00"
                  step="any"
                  min="0"
                  required
                  class="w-full bg-black/50 border border-white/20 rounded px-4 py-3 text-sm font-bold price-mono text-white placeholder-slate-600 focus:outline-none focus:border-signal transition-all"
                />
              </div>

              <div v-if="addError" class="p-3 rounded bg-alarm/10 border border-alarm/20 flex items-start gap-2">
                <AlertCircle class="h-4 w-4 text-alarm shrink-0 mt-0.5" />
                <p class="text-xs font-semibold text-alarm">{{ addError }}</p>
              </div>

              <div class="pt-2 flex gap-3">
                <button type="button" @click="showAddModal = false" class="flex-1 px-4 py-3 rounded border border-white/20 text-sm font-bold text-slate-300 hover:bg-white/10 transition-colors">
                  ABORT
                </button>
                <button 
                  type="submit" 
                  class="flex-1 px-4 py-3 rounded bg-signal hover:bg-signal/90 text-sm font-bold text-black transition-colors flex items-center justify-center gap-2"
                >
                  COMMIT_WRITE
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </main>
</template>

<style scoped>
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.list-leave-active {
  position: absolute;
  width: 100%;
}

.fade-modal-enter-active,
.fade-modal-leave-active {
  transition: opacity 0.2s ease;
}
.fade-modal-enter-from,
.fade-modal-leave-to {
  opacity: 0;
}
.fade-modal-enter-active .glass-card {
  animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slide-up {
  0% { opacity: 0; transform: translateY(10px) scale(0.97); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
