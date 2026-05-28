/**
 * Centralized API client for the Market Sentiment Analyzer backend.
 *
 * Exports:
 *   - `marketApi` — public market data endpoints (no auth required)
 *   - `authApi`   — registration, login, and authenticated user routes
 *   - `portfolioApi` — portfolio and alert CRUD (requires auth)
 */

import type {
  AlertCondition,
  AssetMetrics,
  HistoricalDataPoint,
  PortfolioPosition,
  SentimentArticle,
  TokenResponse,
  UserPublic,
} from '../types/market'

const BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`

// ─────────────────────────────────────────────────────────────────────────────
// Core fetch helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Issues an unauthenticated GET request and parses the JSON body.
 *
 * @param url - Absolute URL to request.
 * @returns Parsed JSON body typed as T.
 * @throws Error with status code and URL on any non-2xx response.
 */
async function apiFetch<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`API request failed: status=${response.status} url=${url}`)
  }
  return response.json() as Promise<T>
}

/**
 * Issues an authenticated request using the stored Bearer token.
 *
 * Reads the token from localStorage key `access_token`. On 401 the stored token
 * is cleared (the user is considered logged out — no silent refresh implemented).
 *
 * @param url - Absolute URL to request.
 * @param options - Fetch RequestInit options (method, body, etc.).
 * @returns Parsed JSON body typed as T, or void for 204 responses.
 * @throws Error on network failure or non-2xx response.
 */
async function authFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    localStorage.removeItem('access_token')
    throw new Error(`Unauthorized: status=401 url=${url}`)
  }

  if (response.status === 204) {
    return undefined as unknown as T
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail ?? body.message ?? detail
    } catch {
      // Non-JSON error body — use statusText
    }
    throw new Error(`API request failed: status=${response.status} url=${url} detail=${detail}`)
  }

  return response.json() as Promise<T>
}

// ─────────────────────────────────────────────────────────────────────────────
// Market data API (public)
// ─────────────────────────────────────────────────────────────────────────────

export const marketApi = {
  /**
   * Fetches the list of all supported assets with their current price and sentiment metrics.
   *
   * @returns A promise resolving to an array of AssetMetrics.
   * @throws Error if the network request fails or the server returns a non-2xx status.
   */
  getAssets(): Promise<AssetMetrics[]> {
    return apiFetch<AssetMetrics[]>(`${BASE_URL}/assets`)
  },

  /**
   * Fetches current price and sentiment metrics for a single asset by its ticker ID.
   * Returns null when the backend responds with 404 (asset not found).
   *
   * @param id - Ticker symbol of the asset (e.g. 'BTC', 'ETH').
   * @returns A promise resolving to AssetMetrics or null if the asset is not found.
   * @throws Error if the network request fails or the server returns a non-2xx, non-404 status.
   */
  async getAssetById(id: string): Promise<AssetMetrics | null> {
    const response = await fetch(`${BASE_URL}/assets/${id}/metrics`)
    if (response.status === 404) return null
    if (!response.ok) {
      throw new Error(
        `API request failed: status=${response.status} url=${BASE_URL}/assets/${id}/metrics`
      )
    }
    return response.json() as Promise<AssetMetrics>
  },

  /**
   * Fetches historical OHLCV candlestick data overlaid with LLM sentiment score for
   * the given asset and timeframe.
   *
   * @param assetId - Ticker symbol of the asset (e.g. 'BTC').
   * @param timeframe - Chart timeframe selector ('1H' | '24H' | '7D' | '30D').
   * @returns A promise resolving to an array of HistoricalDataPoint objects.
   * @throws Error if the network request fails or the server returns a non-2xx status.
   */
  getHistoricalData(assetId: string, timeframe: string): Promise<HistoricalDataPoint[]> {
    return apiFetch<HistoricalDataPoint[]>(
      `${BASE_URL}/assets/${assetId}/historical?timeframe=${timeframe}`
    )
  },

  /**
   * Fetches the most recent news articles processed by the LLM sentiment engine
   * for a given asset.
   *
   * @param assetId - Ticker symbol of the asset (e.g. 'BTC').
   * @returns A promise resolving to an array of SentimentArticle objects.
   * @throws Error if the network request fails or the server returns a non-2xx status.
   */
  getArticles(assetId: string): Promise<SentimentArticle[]> {
    return apiFetch<SentimentArticle[]>(`${BASE_URL}/assets/${assetId}/sentiment`)
  },

  /**
   * Fetches backend runtime configuration: active LLM model name and whether a live
   * LLM API endpoint is configured. Result is meant to be cached indefinitely (no polling).
   *
   * @returns A promise resolving to the LLM configuration object.
   * @throws Error if the network request fails or the server returns a non-2xx status.
   */
  getConfig(): Promise<{ llm_configured: boolean; llm_model: string }> {
    return apiFetch<{ llm_configured: boolean; llm_model: string }>(`${BASE_URL}/config`)
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────────────────────────────────────

export const authApi = {
  /**
   * Registers a new user account.
   *
   * @param email - User email address.
   * @param password - Plain-text password (min 8 chars).
   * @param displayName - Public display name.
   * @returns The created UserPublic profile.
   * @throws Error on conflict (409) or validation failure.
   */
  register(email: string, password: string, displayName: string): Promise<UserPublic> {
    return authFetch<UserPublic>(`${BASE_URL}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
  },

  /**
   * Authenticates a user and returns a signed JWT token.
   *
   * @param email - User email address.
   * @param password - Plain-text password.
   * @returns TokenResponse with access_token and user profile.
   * @throws Error on 401 (invalid credentials).
   */
  login(email: string, password: string): Promise<TokenResponse> {
    return authFetch<TokenResponse>(`${BASE_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  /**
   * Fetches the current authenticated user's public profile.
   *
   * @returns UserPublic profile.
   * @throws Error on 401 (expired or missing token).
   */
  getMe(): Promise<UserPublic> {
    return authFetch<UserPublic>(`${BASE_URL}/auth/me`)
  },

  /**
   * Adds or removes an asset from the authenticated user's watchlist.
   *
   * @param assetId - Ticker symbol to add or remove.
   * @param action - 'add' or 'remove'.
   * @returns Updated UserPublic profile.
   * @throws Error on auth or validation failure.
   */
  updateWatchlist(assetId: string, action: 'add' | 'remove'): Promise<UserPublic> {
    return authFetch<UserPublic>(`${BASE_URL}/watchlist`, {
      method: 'PUT',
      body: JSON.stringify({ asset_id: assetId, action }),
    })
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Portfolio + Alerts API
// ─────────────────────────────────────────────────────────────────────────────

export const portfolioApi = {
  /**
   * Fetches the authenticated user's portfolio with live P&L data.
   *
   * @returns Array of PortfolioPosition objects.
   * @throws Error on auth failure.
   */
  getPortfolio(): Promise<PortfolioPosition[]> {
    return authFetch<PortfolioPosition[]>(`${BASE_URL}/portfolio`)
  },

  /**
   * Creates or updates a portfolio position for the authenticated user.
   *
   * @param assetId - Ticker symbol.
   * @param quantity - Number of units held.
   * @param avgBuyPrice - Average buy price in USD.
   * @returns The created/updated PortfolioPosition with live P&L.
   * @throws Error on auth or validation failure.
   */
  upsertPosition(assetId: string, quantity: number, avgBuyPrice: number): Promise<PortfolioPosition> {
    return authFetch<PortfolioPosition>(`${BASE_URL}/portfolio`, {
      method: 'PUT',
      body: JSON.stringify({ asset_id: assetId, quantity, avg_buy_price: avgBuyPrice }),
    })
  },

  /**
   * Deletes a portfolio position by asset ID.
   *
   * @param assetId - Ticker symbol of the position to remove.
   * @throws Error on auth failure or if position is not found.
   */
  deletePosition(assetId: string): Promise<void> {
    return authFetch<void>(`${BASE_URL}/portfolio/${assetId}`, { method: 'DELETE' })
  },

  /**
   * Fetches all alerts (triggered and untriggered) for the authenticated user.
   *
   * @returns Array of AlertCondition objects.
   * @throws Error on auth failure.
   */
  getAlerts(): Promise<AlertCondition[]> {
    return authFetch<AlertCondition[]>(`${BASE_URL}/alerts`)
  },

  /**
   * Creates a new price or sentiment alert.
   *
   * @param assetId - Ticker symbol to watch.
   * @param condition - Trigger condition type.
   * @param targetValue - Numeric threshold.
   * @returns The created AlertCondition.
   * @throws Error on auth or validation failure.
   */
  createAlert(
    assetId: string,
    condition: 'PRICE_ABOVE' | 'PRICE_BELOW' | 'SENTIMENT_CHANGE',
    targetValue: number
  ): Promise<AlertCondition> {
    return authFetch<AlertCondition>(`${BASE_URL}/alerts`, {
      method: 'POST',
      body: JSON.stringify({ asset_id: assetId, condition, target_value: targetValue }),
    })
  },

  /**
   * Deletes an alert by its UUID.
   *
   * @param alertId - UUID of the alert to delete.
   * @throws Error on auth failure or if alert is not found.
   */
  deleteAlert(alertId: string): Promise<void> {
    return authFetch<void>(`${BASE_URL}/alerts/${alertId}`, { method: 'DELETE' })
  },
}
