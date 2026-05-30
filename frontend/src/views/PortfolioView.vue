<script setup lang="ts">
/**
 * PortfolioView — Live portfolio tracker with P&L cards and position management.
 *
 * Uses TanStack Query (useQuery / useMutation) for server state.
 * Pinia auth store provides the current user context.
 */

import { computed, ref } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { useAuthStore } from '@/composables/useAuthStore'
import { portfolioApi } from '@/services/api'
import type { PortfolioPosition, RouteAssetId } from '@/types/market'
import {
  formatPrice,
  getAssetBrandColor,
} from '@/composables/useCryptoFormatters'
import { Plus, Trash2, TrendingUp, TrendingDown, Minus, Briefcase, PlusCircle, AlertCircle, X } from '@lucide/vue'

const authStore = useAuthStore()
const queryClient = useQueryClient()

// ── Queries ─────────────────────────────────────────────────────────────────

const {
  data: positions,
  isLoading,
  isError,
} = useQuery<PortfolioPosition[]>({
  queryKey: ['portfolio'],
  queryFn: () => portfolioApi.getPortfolio(),
  refetchInterval: 60_000,
})

// ── Portfolio summary ────────────────────────────────────────────────────────

const totalValue = computed<number>(() =>
  (positions.value ?? []).reduce((sum, p) => sum + p.current_price * p.quantity, 0)
)

const totalPnlUsd = computed<number>(() =>
  (positions.value ?? []).reduce((sum, p) => sum + p.pnl_usd, 0)
)

const totalPnlPct = computed<number>(() => {
  const costBasis = (positions.value ?? []).reduce(
    (sum, p) => sum + p.avg_buy_price * p.quantity,
    0
  )
  return costBasis > 0 ? (totalPnlUsd.value / costBasis) * 100 : 0
})

// ── Add position modal ───────────────────────────────────────────────────────

const showAddModal = ref(false)
const newAssetId = ref('BTC')
const newQuantity = ref<string>('')
const newAvgBuy = ref<string>('')
const addError = ref<string | null>(null)

const ASSET_OPTIONS = ['BTC', 'ETH', 'SOL', 'TON', 'XRP', 'ADA', 'AAPL'] as const

const upsertMutation = useMutation({
  mutationFn: ({ assetId, qty, price }: { assetId: string; qty: number; price: number }) =>
    portfolioApi.upsertPosition(assetId, qty, price),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['portfolio'] })
    showAddModal.value = false
    newQuantity.value = ''
    newAvgBuy.value = ''
    addError.value = null
  },
  onError: (err) => {
    addError.value = err instanceof Error ? err.message : 'Failed to add position.'
  },
})

const deleteMutation = useMutation({
  mutationFn: (assetId: string) => portfolioApi.deletePosition(assetId),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['portfolio'] }),
})

function handleAddPosition(): void {
  addError.value = null
  const qty = parseFloat(newQuantity.value)
  const price = parseFloat(newAvgBuy.value)
  if (!newAssetId.value || isNaN(qty) || qty <= 0 || isNaN(price) || price <= 0) {
    addError.value = 'Please enter valid quantity and price.'
    return
  }
  upsertMutation.mutate({ assetId: newAssetId.value, qty, price })
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value)
}

function pnlClass(value: number): string {
  if (value > 0) return 'text-emerald-400'
  if (value < 0) return 'text-rose-400'
  return 'text-slate-400'
}

function pnlIcon(value: number) {
  if (value > 0) return TrendingUp
  if (value < 0) return TrendingDown
  return Minus
}
</script>

<template>
  <main class="flex-1 overflow-y-auto w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
    <!-- Header -->
    <header class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border/10 pb-6">
      <div class="flex flex-col gap-1.5">
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight font-display text-gradient-crypto flex items-center gap-2">
          <Briefcase class="h-6 w-6 text-indigo-400" />
          My Portfolio
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 font-medium">
          Welcome back, <strong class="text-slate-200">{{ authStore.user?.display_name }}</strong>. Track your live asset performance.
        </p>
      </div>
      <button
        @click="showAddModal = true"
        class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-[0_0_16px_-4px_rgba(99,102,241,0.5)] transition-all hover-scale-premium shrink-0"
      >
        <Plus class="h-4 w-4" />
        Add Position
      </button>
    </header>

    <!-- Summary KPI Cards -->
    <section class="grid grid-cols-2 lg:grid-cols-4 gap-4" aria-label="Portfolio Summary">
      <div class="glass-card p-5 rounded-2xl flex flex-col gap-2 relative overflow-hidden group">
        <div class="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent pointer-events-none" />
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">Total Value</span>
        <span class="text-2xl sm:text-3xl font-bold text-slate-100 price-mono tracking-tight relative z-10">{{ formatCurrency(totalValue) }}</span>
      </div>
      
      <div class="glass-card p-5 rounded-2xl flex flex-col gap-2 relative overflow-hidden group">
        <div class="absolute inset-0 bg-gradient-to-br pointer-events-none transition-colors" 
             :class="totalPnlUsd > 0 ? 'from-emerald-500/5' : totalPnlUsd < 0 ? 'from-rose-500/5' : 'from-slate-500/5'" />
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">Total P&L (USD)</span>
        <div class="flex items-center gap-1.5 relative z-10">
          <span class="text-xl sm:text-2xl font-bold price-mono tracking-tight" :class="pnlClass(totalPnlUsd)">
            {{ totalPnlUsd >= 0 ? '+' : '' }}{{ formatCurrency(totalPnlUsd) }}
          </span>
        </div>
      </div>
      
      <div class="glass-card p-5 rounded-2xl flex flex-col gap-2 relative overflow-hidden group">
        <div class="absolute inset-0 bg-gradient-to-br pointer-events-none transition-colors" 
             :class="totalPnlPct > 0 ? 'from-emerald-500/5' : totalPnlPct < 0 ? 'from-rose-500/5' : 'from-slate-500/5'" />
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">Return (%)</span>
        <div class="flex items-center gap-1.5 relative z-10">
          <component :is="pnlIcon(totalPnlPct)" class="h-5 w-5 shrink-0" :class="pnlClass(totalPnlPct)" />
          <span class="text-xl sm:text-2xl font-bold price-mono tracking-tight" :class="pnlClass(totalPnlPct)">
            {{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%
          </span>
        </div>
      </div>
      
      <div class="glass-card p-5 rounded-2xl flex flex-col gap-2 relative overflow-hidden group">
        <div class="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent pointer-events-none" />
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider relative z-10">Active Positions</span>
        <span class="text-2xl sm:text-3xl font-bold text-slate-100 price-mono tracking-tight relative z-10">{{ (positions ?? []).length }}</span>
      </div>
    </section>

    <!-- State Handling -->
    <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 gap-4 text-slate-400">
      <div class="h-8 w-8 rounded-full border-2 border-indigo-500/30 border-t-indigo-500 animate-spin" />
      <span class="text-xs font-bold uppercase tracking-wider">Syncing Portfolio...</span>
    </div>

    <div v-else-if="isError" class="glass-card bg-rose-500/5 border-rose-500/20 p-6 rounded-2xl flex items-center justify-center gap-3 text-rose-400">
      <AlertCircle class="h-5 w-5" />
      <span class="text-sm font-semibold">Failed to load portfolio data. Please try refreshing the page.</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="!positions?.length" class="glass-card flex flex-col items-center justify-center text-center p-12 sm:p-20 rounded-3xl border-dashed border-border/50">
      <div class="h-16 w-16 rounded-full bg-slate-900/50 flex items-center justify-center mb-6 border border-border/50 shadow-inner">
        <Briefcase class="h-8 w-8 text-slate-500" />
      </div>
      <h2 class="text-xl font-bold text-slate-200 mb-2">No positions yet</h2>
      <p class="text-sm text-slate-400 max-w-md mb-8">
        Your portfolio is currently empty. Add your first asset to start tracking real-time performance and P&L.
      </p>
      <button 
        @click="showAddModal = true"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-500/20 hover-scale-premium"
      >
        <PlusCircle class="h-4 w-4" />
        Add First Position
      </button>
    </div>

    <!-- Positions List (Desktop + Mobile responsive) -->
    <section v-else aria-label="Portfolio positions" class="space-y-4">
      <!-- Desktop List Header (hidden on mobile) -->
      <div class="hidden sm:grid grid-cols-12 gap-4 px-6 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-border/10 mb-2">
        <div class="col-span-3">Asset</div>
        <div class="col-span-2 text-right">Holdings</div>
        <div class="col-span-2 text-right">Avg Buy</div>
        <div class="col-span-2 text-right">Total Value</div>
        <div class="col-span-2 text-right">Total P&L</div>
        <div class="col-span-1 text-center">Act</div>
      </div>

      <!-- Position Rows -->
      <TransitionGroup name="list" tag="div" class="flex flex-col gap-3">
        <div 
          v-for="pos in positions" 
          :key="pos.asset_id"
          class="glass-card hover-scale-premium p-4 sm:p-0 sm:px-6 sm:py-4 rounded-2xl flex flex-col sm:grid sm:grid-cols-12 sm:items-center gap-4 transition-all duration-300 relative group overflow-hidden"
        >
          <!-- Subtle background hover gradient -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.02] to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />

          <!-- Asset Info -->
          <div class="col-span-3 flex items-center gap-3 relative z-10">
            <span class="h-2.5 w-2.5 rounded-full shrink-0 shadow-sm" :style="{ backgroundColor: getAssetBrandColor(pos.asset_id as RouteAssetId) }" />
            <div>
              <div class="font-bold text-slate-100 font-display text-base">{{ pos.asset_id }}</div>
              <div class="text-[10px] text-slate-400 font-medium">{{ pos.asset_name }}</div>
            </div>
            <!-- Mobile current price badge (hidden on desktop) -->
            <div class="sm:hidden ml-auto px-2 py-1 bg-slate-900/50 rounded-lg text-xs font-bold price-mono text-slate-300">
              {{ formatPrice(pos.current_price, pos.asset_id as RouteAssetId) }}
            </div>
          </div>

          <!-- Quantity -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">Holdings</span>
            <div class="font-bold price-mono text-slate-200 text-sm">
              {{ pos.quantity }} <span class="text-xs text-slate-500 ml-1">{{ pos.asset_id }}</span>
            </div>
          </div>

          <!-- Avg Buy -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">Avg Buy</span>
            <div class="font-semibold price-mono text-slate-400 text-sm">
              {{ formatPrice(pos.avg_buy_price, pos.asset_id as RouteAssetId) }}
            </div>
          </div>

          <!-- Current Value -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 sm:gap-0 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">Total Value</span>
            <div class="font-bold price-mono text-slate-100 text-sm sm:text-base">
              {{ formatCurrency(pos.current_price * pos.quantity) }}
            </div>
          </div>

          <!-- P&L -->
          <div class="col-span-2 flex flex-row sm:flex-col justify-between sm:justify-end items-center sm:items-end gap-1 relative z-10">
            <span class="sm:hidden text-[10px] font-bold text-slate-500 uppercase">Total P&L</span>
            <div class="flex flex-col items-end">
              <span class="font-bold price-mono text-sm" :class="pnlClass(pos.pnl_usd)">
                {{ pos.pnl_usd >= 0 ? '+' : '' }}{{ formatCurrency(pos.pnl_usd) }}
              </span>
              <span class="text-[10px] font-bold price-mono bg-slate-900/40 px-1.5 py-0.5 rounded-md mt-0.5" :class="pnlClass(pos.pnl_pct)">
                {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="col-span-1 flex justify-end sm:justify-center mt-2 sm:mt-0 border-t border-border/10 pt-3 sm:border-0 sm:pt-0 relative z-10">
            <button
              class="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 transition-colors disabled:opacity-50"
              :disabled="deleteMutation.isPending.value"
              @click="deleteMutation.mutate(pos.asset_id)"
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
          <div class="absolute inset-0 bg-background/80 backdrop-blur-sm transition-opacity" @click="showAddModal = false" />
          
          <!-- Modal Content -->
          <div class="glass-panel relative w-full max-w-md rounded-3xl p-6 sm:p-8 shadow-2xl border border-border/40 transform transition-all">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-bold text-slate-100 font-display flex items-center gap-2">
                <div class="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <Plus class="h-5 w-5" />
                </div>
                Add Position
              </h2>
              <button @click="showAddModal = false" class="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
                <X class="h-5 w-5" />
              </button>
            </div>

            <form @submit.prevent="handleAddPosition" class="space-y-4" novalidate>
              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">Asset Ticker</label>
                <div class="relative">
                  <select v-model="newAssetId" class="w-full appearance-none bg-slate-900/50 border border-border/50 rounded-xl px-4 py-3 text-sm font-bold text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all cursor-pointer">
                    <option v-for="a in ASSET_OPTIONS" :key="a" :value="a">{{ a }}</option>
                  </select>
                  <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-slate-400">
                    <svg class="h-4 w-4 fill-current" viewBox="0 0 20 20"><path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/></svg>
                  </div>
                </div>
              </div>

              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">Quantity</label>
                <input
                  v-model="newQuantity"
                  type="number"
                  placeholder="0.0"
                  step="any"
                  min="0"
                  required
                  class="w-full bg-slate-900/50 border border-border/50 rounded-xl px-4 py-3 text-sm font-bold price-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                />
              </div>

              <div class="space-y-1.5">
                <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pl-1">Avg Buy Price (USD)</label>
                <input
                  v-model="newAvgBuy"
                  type="number"
                  placeholder="0.00"
                  step="any"
                  min="0"
                  required
                  class="w-full bg-slate-900/50 border border-border/50 rounded-xl px-4 py-3 text-sm font-bold price-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                />
              </div>

              <div v-if="addError" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2">
                <AlertCircle class="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <p class="text-xs font-semibold text-rose-400">{{ addError }}</p>
              </div>

              <div class="pt-2 flex gap-3">
                <button type="button" @click="showAddModal = false" class="flex-1 px-4 py-3 rounded-xl border border-border/50 text-sm font-bold text-slate-300 hover:bg-slate-800 transition-colors">
                  Cancel
                </button>
                <button 
                  type="submit" 
                  :disabled="upsertMutation.isPending.value"
                  class="flex-1 px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-bold text-white shadow-lg shadow-indigo-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <span v-if="upsertMutation.isPending.value" class="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Save Position</span>
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
.fade-modal-enter-active .glass-panel {
  animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slide-up {
  0% { opacity: 0; transform: translateY(10px) scale(0.97); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
