/**
 * Centralized, decoupled API client for the Market Sentiment Analyzer backend.
 *
 * Exports:
 *   - `apiClient`    — core client instance supporting interceptor registries
 *   - `marketApi`    — public market data endpoints
 *   - `authApi`      — authentication and user watchlist endpoints
 *   - `portfolioApi` — portfolio assets and alerts CRUD endpoints
 */
const BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`;
/**
 * Highly decoupled, type-safe HTTP client wrapped around native fetch.
 * Uses a registry-based callback pattern for global error interceptors,
 * completely avoiding circular dependencies between services, Pinia stores, and Toasts.
 */
class ApiClient {
    baseUrl;
    errorCallbacks = [];
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    /**
     * Registers a global error interceptor callback.
     * Useful to trigger toast notifications or clear user sessions.
     */
    onError(callback) {
        this.errorCallbacks.push(callback);
    }
    /** Triggers all registered error interceptors. */
    triggerError(status, detail, retry) {
        this.errorCallbacks.forEach((cb) => {
            try {
                cb(status, detail, retry);
            }
            catch (err) {
                console.error('[ApiClient] Error callback failed:', err);
            }
        });
    }
    /**
     * Issues an HTTP request, injects active tokens, and processes responses.
     */
    async request(path, options = {}) {
        const token = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const url = `${this.baseUrl}${path}`;
        const fetchOptions = {
            ...options,
            headers,
        };
        try {
            const response = await fetch(url, fetchOptions);
            if (response.status === 204) {
                return undefined;
            }
            if (!response.ok) {
                let detail = response.statusText;
                try {
                    const body = await response.json();
                    detail = body.detail ?? body.message ?? detail;
                }
                catch {
                    // Fallback to response.statusText if body is not JSON
                }
                // Trigger the decoupled error callbacks, providing a lazy retry function
                this.triggerError(response.status, detail, () => this.request(path, options));
                throw new Error(`API client request failed: status=${response.status} url=${url} detail=${detail}`);
            }
            return response.json();
        }
        catch (err) {
            // Net connection / DNS failure (e.g. Server asleep or down)
            if (!(err instanceof Error) || !err.message.includes('API client request failed')) {
                this.triggerError(504, 'Север недоступен. Проверьте соединение с сетью или подождите запуска бэкенда на Render.', () => this.request(path, options));
            }
            throw err;
        }
    }
}
// Instantiate the single, shared core client
export const apiClient = new ApiClient(BASE_URL);
// ─────────────────────────────────────────────────────────────────────────────
// Market data API (public)
// ─────────────────────────────────────────────────────────────────────────────
export const marketApi = {
    getAssets() {
        return apiClient.request('/assets');
    },
    async getAssetById(id) {
        try {
            return await apiClient.request(`/assets/${id}/metrics`);
        }
        catch (err) {
            // Gracefully handle 404
            if (err instanceof Error && err.message.includes('status=404')) {
                return null;
            }
            throw err;
        }
    },
    getHistoricalData(assetId, timeframe) {
        return apiClient.request(`/assets/${assetId}/historical?timeframe=${timeframe}`);
    },
    getArticles(assetId) {
        return apiClient.request(`/assets/${assetId}/sentiment`);
    },
    getConfig() {
        return apiClient.request('/config');
    },
};
// ─────────────────────────────────────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────────────────────────────────────
export const authApi = {
    register(email, password, displayName) {
        return apiClient.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, display_name: displayName }),
        });
    },
    login(email, password) {
        return apiClient.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },
    getMe() {
        return apiClient.request('/auth/me');
    },
    updateWatchlist(assetId, action) {
        return apiClient.request('/watchlist', {
            method: 'PUT',
            body: JSON.stringify({ asset_id: assetId, action }),
        });
    },
};
// ─────────────────────────────────────────────────────────────────────────────
// Portfolio + Alerts API
// ─────────────────────────────────────────────────────────────────────────────
export const portfolioApi = {
    getPortfolio() {
        return apiClient.request('/portfolio');
    },
    upsertPosition(assetId, quantity, avgBuyPrice) {
        return apiClient.request('/portfolio', {
            method: 'PUT',
            body: JSON.stringify({ asset_id: assetId, quantity, avg_buy_price: avgBuyPrice }),
        });
    },
    deletePosition(assetId) {
        return apiClient.request(`/portfolio/${assetId}`, { method: 'DELETE' });
    },
    getAlerts() {
        return apiClient.request('/alerts');
    },
    createAlert(assetId, condition, targetValue) {
        return apiClient.request('/alerts', {
            method: 'POST',
            body: JSON.stringify({ asset_id: assetId, condition, target_value: targetValue }),
        });
    },
    deleteAlert(alertId) {
        return apiClient.request(`/alerts/${alertId}`, { method: 'DELETE' });
    },
};
