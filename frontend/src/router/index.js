/**
 * Application router configuration.
 *
 * Routes:
 *   /             → redirect to /asset/BTC
 *   /asset/:id    → DashboardView (lazy-loaded)
 *   *             → NotFoundView
 *
 * The `beforeEach` guard validates the `:id` parameter against the set of
 * known asset tickers. Invalid tickers are silently redirected to the default
 * asset (/asset/BTC) instead of rendering a broken dashboard.
 */
import { createRouter, createWebHistory } from 'vue-router';
const VALID_ASSET_IDS = new Set(['BTC', 'ETH', 'SOL', 'AAPL']);
const DEFAULT_ASSET = 'BTC';
const routes = [
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
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/views/NotFoundView.vue'),
        meta: { title: 'Page Not Found' },
    },
];
const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior: () => ({ top: 0 }),
});
/**
 * Navigation guard that validates the asset `:id` route parameter.
 * Redirects to the default asset if an unknown ticker is supplied.
 */
router.beforeEach((to) => {
    if (to.name === 'dashboard') {
        const id = to.params.id;
        if (!VALID_ASSET_IDS.has(id)) {
            return { name: 'dashboard', params: { id: DEFAULT_ASSET }, replace: true };
        }
    }
    return true;
});
export { DEFAULT_ASSET, VALID_ASSET_IDS };
export default router;
