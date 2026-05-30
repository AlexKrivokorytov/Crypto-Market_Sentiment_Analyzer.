/**
 * Application router configuration.
 *
 * Routes:
 *   /             → redirect to /asset/BTC
 *   /asset/:id    → DashboardView (public)
 *   /login        → LoginView (guest only — redirects authenticated users)
 *   /register     → RegisterView (guest only — redirects authenticated users)
 *   /portfolio    → PortfolioView (requires auth)
 *   *             → NotFoundView
 *
 * Navigation guards:
 *   - Asset routes: validates `:id` against known tickers.
 *   - Auth routes (`requiresGuest`): redirects authenticated users to dashboard.
 *   - Protected routes (`requiresAuth`): redirects unauthenticated users to login.
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import type { RouteAssetId } from '@/types/market'
import { useAuthStore } from '@/composables/useAuthStore'

const VALID_ASSET_IDS = new Set<RouteAssetId>([
  'BTC', 'ETH', 'SOL', 'AAPL', 'TON', 'XRP', 'ADA',
  'DOGE', 'DOT', 'LINK', 'AVAX', 'MATIC', 'SHIB', 'LTC', 'UNI', 'NEAR', 'ATOM',
])

const DEFAULT_ASSET: RouteAssetId = 'BTC'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: `/asset/${DEFAULT_ASSET}`,
  },
  {
    path: '/asset/:id',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: 'Sign In', requiresGuest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: 'Create Account', requiresGuest: true },
  },
  {
    path: '/portfolio',
    name: 'portfolio',
    component: () => import('@/views/PortfolioView.vue'),
    meta: { title: 'Portfolio', requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Page Not Found' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

/**
 * Navigation guard that:
 *   1. Validates asset `:id` route parameters.
 *   2. Redirects authenticated users away from guest-only routes.
 *   3. Redirects unauthenticated users away from protected routes.
 */
router.beforeEach((to) => {
  // Asset ID validation guard
  if (to.name === 'dashboard') {
    const id = to.params.id as string
    if (!VALID_ASSET_IDS.has(id as RouteAssetId)) {
      return { name: 'dashboard', params: { id: DEFAULT_ASSET }, replace: true }
    }
  }

  const authStore = useAuthStore()

  // Guest-only routes: redirect to dashboard if already authenticated
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return { name: 'dashboard', params: { id: DEFAULT_ASSET }, replace: true }
  }

  // Protected routes: redirect to login if not authenticated
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath }, replace: true }
  }

  return true
})

export { DEFAULT_ASSET, VALID_ASSET_IDS }
export default router
