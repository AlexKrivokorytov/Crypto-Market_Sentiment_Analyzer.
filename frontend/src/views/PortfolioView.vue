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
import type { PortfolioPosition } from '@/types/market'

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

const ASSET_OPTIONS = ['BTC', 'ETH', 'SOL', 'AAPL'] as const

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
</script>

<template>
  <main class="portfolio-page">
    <!-- Page header -->
    <header class="portfolio-header">
      <div class="portfolio-header__left">
        <h1 class="portfolio-title">Portfolio</h1>
        <p class="portfolio-subtitle">
          Welcome back, <strong>{{ authStore.user?.display_name }}</strong>
        </p>
      </div>
      <button
        id="portfolio-add-btn"
        class="btn-add"
        @click="showAddModal = true"
        aria-label="Add a new portfolio position"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
        </svg>
        Add Position
      </button>
    </header>

    <!-- Summary cards -->
    <section class="summary-grid" aria-label="Portfolio summary">
      <article class="summary-card">
        <span class="summary-card__label">Total Value</span>
        <span class="summary-card__value">{{ formatCurrency(totalValue) }}</span>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">Total P&amp;L</span>
        <span
          class="summary-card__value"
          :class="totalPnlUsd >= 0 ? 'pnl--positive' : 'pnl--negative'"
        >
          {{ totalPnlUsd >= 0 ? '+' : '' }}{{ formatCurrency(totalPnlUsd) }}
        </span>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">Return</span>
        <span
          class="summary-card__value"
          :class="totalPnlPct >= 0 ? 'pnl--positive' : 'pnl--negative'"
        >
          {{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%
        </span>
      </article>
      <article class="summary-card">
        <span class="summary-card__label">Positions</span>
        <span class="summary-card__value">{{ (positions ?? []).length }}</span>
      </article>
    </section>

    <!-- Loading / error states -->
    <div v-if="isLoading" class="state-message" role="status" aria-live="polite">
      <span class="spinner" />
      <span>Loading portfolio…</span>
    </div>
    <div v-else-if="isError" class="state-message state-message--error" role="alert">
      Failed to load portfolio data. Please refresh.
    </div>

    <!-- Empty state -->
    <div v-else-if="!positions?.length" class="empty-state">
      <div class="empty-state__icon" aria-hidden="true">📈</div>
      <h2 class="empty-state__title">No positions yet</h2>
      <p class="empty-state__desc">Add your first position to start tracking P&amp;L.</p>
      <button id="portfolio-empty-add-btn" class="btn-add" @click="showAddModal = true">
        Add First Position
      </button>
    </div>

    <!-- Positions table -->
    <section v-else class="positions-section" aria-label="Portfolio positions">
      <table class="positions-table">
        <thead>
          <tr>
            <th scope="col">Asset</th>
            <th scope="col">Quantity</th>
            <th scope="col">Avg Buy</th>
            <th scope="col">Current</th>
            <th scope="col">Value</th>
            <th scope="col">P&amp;L</th>
            <th scope="col">Return</th>
            <th scope="col" class="col-actions"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="pos in positions"
            :key="pos.asset_id"
            class="position-row"
          >
            <td class="col-asset">
              <span class="asset-symbol">{{ pos.asset_id }}</span>
              <span class="asset-name">{{ pos.asset_name }}</span>
            </td>
            <td>{{ pos.quantity }}</td>
            <td>{{ formatCurrency(pos.avg_buy_price) }}</td>
            <td>{{ formatCurrency(pos.current_price) }}</td>
            <td>{{ formatCurrency(pos.current_price * pos.quantity) }}</td>
            <td :class="pos.pnl_usd >= 0 ? 'pnl--positive' : 'pnl--negative'">
              {{ pos.pnl_usd >= 0 ? '+' : '' }}{{ formatCurrency(pos.pnl_usd) }}
            </td>
            <td :class="pos.pnl_pct >= 0 ? 'pnl--positive' : 'pnl--negative'">
              {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
            </td>
            <td class="col-actions">
              <button
                :id="`portfolio-delete-${pos.asset_id}`"
                class="btn-delete"
                :aria-label="`Remove ${pos.asset_id} position`"
                :disabled="deleteMutation.isPending.value"
                @click="deleteMutation.mutate(pos.asset_id)"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M2 3.5h10M5.5 3.5V2.5a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1m1.5 0-.5 7.5a1 1 0 0 1-1 .96H4.5a1 1 0 0 1-1-.96L3 3.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Add position modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showAddModal" class="modal-backdrop" @click.self="showAddModal = false" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div class="modal-card">
            <h2 id="modal-title" class="modal-title">Add Position</h2>

            <form id="portfolio-add-form" class="modal-form" @submit.prevent="handleAddPosition" novalidate>
              <div class="field-group">
                <label for="modal-asset" class="field-label">Asset</label>
                <select id="modal-asset" v-model="newAssetId" class="field-input field-select">
                  <option v-for="a in ASSET_OPTIONS" :key="a" :value="a">{{ a }}</option>
                </select>
              </div>

              <div class="field-group">
                <label for="modal-qty" class="field-label">Quantity</label>
                <input
                  id="modal-qty"
                  v-model="newQuantity"
                  type="number"
                  class="field-input"
                  placeholder="0.5"
                  step="any"
                  min="0"
                  required
                />
              </div>

              <div class="field-group">
                <label for="modal-price" class="field-label">Avg Buy Price (USD)</label>
                <input
                  id="modal-price"
                  v-model="newAvgBuy"
                  type="number"
                  class="field-input"
                  placeholder="68000"
                  step="any"
                  min="0"
                  required
                />
              </div>

              <Transition name="fade">
                <p v-if="addError" class="auth-error" role="alert">{{ addError }}</p>
              </Transition>

              <div class="modal-actions">
                <button
                  id="portfolio-modal-cancel"
                  type="button"
                  class="btn-secondary"
                  @click="showAddModal = false"
                >
                  Cancel
                </button>
                <button
                  id="portfolio-modal-submit"
                  type="submit"
                  class="btn-primary"
                  :disabled="upsertMutation.isPending.value"
                >
                  <span v-if="!upsertMutation.isPending.value">Save Position</span>
                  <span v-else class="spinner spinner--sm" aria-label="Saving…" />
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
/* ── Page ───────────────────────────────────────────────────────── */
.portfolio-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

/* ── Header ─────────────────────────────────────────────────────── */
.portfolio-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 2rem;
  gap: 1rem;
  flex-wrap: wrap;
}
.portfolio-title {
  font-size: 2rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0;
  letter-spacing: -0.03em;
}
.portfolio-subtitle {
  font-size: 0.9375rem;
  color: #64748b;
  margin: 0.25rem 0 0;
}
.portfolio-subtitle strong { color: #94a3b8; }

/* ── Summary grid ───────────────────────────────────────────────── */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}
.summary-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  transition: border-color 0.2s;
}
.summary-card:hover { border-color: rgba(255,255,255,0.15); }
.summary-card__label {
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.summary-card__value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.02em;
}

/* ── P&L colors ─────────────────────────────────────────────────── */
.pnl--positive { color: #34d399; }
.pnl--negative { color: #f87171; }

/* ── State messages ─────────────────────────────────────────────── */
.state-message {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem;
  color: #64748b;
  font-size: 0.9375rem;
}
.state-message--error { color: #f87171; }

/* ── Empty state ────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}
.empty-state__icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-state__title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f8fafc;
  margin: 0 0 0.5rem;
}
.empty-state__desc { color: #64748b; margin: 0 0 1.5rem; }

/* ── Positions table ────────────────────────────────────────────── */
.positions-section { overflow-x: auto; }
.positions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.positions-table th {
  text-align: left;
  padding: 0.75rem 1rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.position-row td {
  padding: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  color: #cbd5e1;
  vertical-align: middle;
}
.position-row:hover td { background: rgba(255,255,255,0.02); }
.col-asset {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.asset-symbol { font-weight: 600; color: #f8fafc; }
.asset-name { font-size: 0.75rem; color: #475569; }
.col-actions { text-align: right; }

/* ── Buttons ────────────────────────────────────────────────────── */
.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border-radius: 0.75rem;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 4px 14px rgba(99,102,241,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}
.btn-add:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
.btn-delete {
  background: rgba(248,113,113,0.12);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 0.5rem;
  color: #f87171;
  padding: 0.375rem;
  cursor: pointer;
  transition: background 0.15s;
  line-height: 0;
}
.btn-delete:hover { background: rgba(248,113,113,0.22); }
.btn-delete:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Modal ──────────────────────────────────────────────────────── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  padding: 1rem;
  z-index: 100;
}
.modal-card {
  width: 100%;
  max-width: 440px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 1.25rem;
  padding: 2rem;
  box-shadow: 0 32px 80px rgba(0,0,0,0.6);
}
.modal-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 1.5rem;
  letter-spacing: -0.02em;
}
.modal-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.field-group { display: flex; flex-direction: column; gap: 0.375rem; }
.field-label { font-size: 0.8125rem; font-weight: 500; color: #94a3b8; }
.field-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 0.625rem;
  color: #f8fafc;
  font-size: 0.9375rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.field-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.2);
}
.field-select { cursor: pointer; }
.modal-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.btn-secondary {
  flex: 1;
  padding: 0.75rem;
  border-radius: 0.625rem;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.05);
  color: #94a3b8;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-secondary:hover { background: rgba(255,255,255,0.09); }
.btn-primary {
  flex: 2;
  padding: 0.75rem;
  border-radius: 0.625rem;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.15s;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.auth-error {
  font-size: 0.8125rem;
  color: #f87171;
  background: rgba(248,113,113,0.1);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 0.5rem;
  padding: 0.625rem 0.875rem;
  margin: 0;
}

/* ── Spinners ───────────────────────────────────────────────────── */
.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
.spinner--sm { width: 16px; height: 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }

/* ── Transitions ────────────────────────────────────────────────── */
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-active .modal-card { transition: transform 0.25s cubic-bezier(0.22,1,0.36,1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card { transform: scale(0.95) translateY(8px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
