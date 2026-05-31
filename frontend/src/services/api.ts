/**
 * Centralized, decoupled API client for the Market Sentiment Analyzer backend.
 * 
 * Exports:
 *   - `apiClient`    — core client instance supporting interceptor registries
 *   - `marketApi`    — public market data endpoints
 *   - `authApi`      — authentication and user watchlist endpoints
 *   - `portfolioApi` — portfolio assets and alerts CRUD endpoints
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

export interface FearGreedData {
  value: number
  classification: string
  timestamp: string
  history: Array<{
    value: number
    classification: string
    timestamp: string
  }>
}

const BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`

export type ErrorCallback = (status: number, detail: string, retry: () => Promise<any>) => void

/**
 * Highly decoupled, type-safe HTTP client wrapped around native fetch.
 * Uses a registry-based callback pattern for global error interceptors,
 * completely avoiding circular dependencies between services, Pinia stores, and Toasts.
 */
class ApiClient {
  private baseUrl: string
  private errorCallbacks: ErrorCallback[] = []

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  /**
   * Registers a global error interceptor callback.
   * Useful to trigger toast notifications or clear user sessions.
   */
  public onError(callback: ErrorCallback): void {
    this.errorCallbacks.push(callback)
  }

  /** Triggers all registered error interceptors. */
  private triggerError(status: number, detail: string, retry: () => Promise<any>): void {
    this.errorCallbacks.forEach((cb) => {
      try {
        cb(status, detail, retry)
      } catch (err) {
        console.error('[ApiClient] Error callback failed:', err)
      }
    })
  }

  /**
   * Issues an HTTP request, injects active tokens, and processes responses.
   */
  public async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = localStorage.getItem('access_token')

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const url = `${this.baseUrl}${path}`
    const fetchOptions: RequestInit = {
      ...options,
      headers,
    }

    try {
      const response = await fetch(url, fetchOptions)

      if (response.status === 204) {
        return undefined as unknown as T
      }

      if (!response.ok) {
        let detail = response.statusText
        try {
          const body = await response.json()
          if (body.detail) {
            if (Array.isArray(body.detail)) {
              // Handle FastAPI Pydantic v2 validation error array [{loc, msg, type}]
              interface PydanticValidationError {
                loc: (string | number)[]
                msg: string
                type: string
              }
              detail = body.detail.map((err: PydanticValidationError) => {
                const field = err.loc ? err.loc.filter((l) => l !== 'body').join('.') : ''
                return field ? `${field}: ${err.msg}` : err.msg
              }).join('; ')
            } else {
              detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
            }
          } else {
            detail = body.message ?? detail
          }
        } catch {
          // Fallback to response.statusText if body is not JSON
        }

        // Trigger the decoupled error callbacks, providing a lazy retry function
        this.triggerError(response.status, detail, () => this.request<T>(path, options))

        throw new Error(`API client request failed: status=${response.status} url=${url} detail=${detail}`)
      }

      return response.json() as Promise<T>
    } catch (err) {
      // Net connection / DNS failure (e.g. Server asleep or down)
      if (!(err instanceof Error) || !err.message.includes('API client request failed')) {
        this.triggerError(504, 'Server unreachable. Please check your connection or wait for the Render backend to finish spinning up.', () => this.request<T>(path, options))
      }
      throw err
    }
  }
}

// Instantiate the single, shared core client
export const apiClient = new ApiClient(BASE_URL)

// ─────────────────────────────────────────────────────────────────────────────
// Market data API (public)
// ─────────────────────────────────────────────────────────────────────────────

export const marketApi = {
  getAssets(): Promise<AssetMetrics[]> {
    return apiClient.request<AssetMetrics[]>('/assets')
  },

  async getAssetById(id: string): Promise<AssetMetrics | null> {
    try {
      return await apiClient.request<AssetMetrics>(`/assets/${id}/metrics`)
    } catch (err) {
      // Gracefully handle 404
      if (err instanceof Error && err.message.includes('status=404')) {
        return null
      }
      throw err
    }
  },

  getFearGreedIndex(): Promise<FearGreedData> {
    return apiClient.request<FearGreedData>('/fear-greed')
  },

  getHistoricalData(assetId: string, timeframe: string): Promise<HistoricalDataPoint[]> {
    return apiClient.request<HistoricalDataPoint[]>(`/assets/${assetId}/historical?timeframe=${timeframe}`)
  },

  getArticles(assetId: string): Promise<SentimentArticle[]> {
    return apiClient.request<SentimentArticle[]>(`/assets/${assetId}/sentiment`)
  },

  getConfig(): Promise<{ llm_configured: boolean; llm_model: string }> {
    return apiClient.request<{ llm_configured: boolean; llm_model: string }>('/config')
  },

  analyzeArticle(articleId: string): Promise<SentimentArticle> {
    return apiClient.request<SentimentArticle>(`/articles/${articleId}/analyze`, {
      method: 'POST',
    })
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────────────────────────────────────

export const authApi = {
  register(email: string, password: string, displayName: string): Promise<UserPublic> {
    return apiClient.request<UserPublic>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
  },

  login(email: string, password: string): Promise<TokenResponse> {
    return apiClient.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  getMe(): Promise<UserPublic> {
    return apiClient.request<UserPublic>('/auth/me')
  },

  updateWatchlist(assetId: string, action: 'add' | 'remove'): Promise<UserPublic> {
    return apiClient.request<UserPublic>('/watchlist', {
      method: 'PUT',
      body: JSON.stringify({ asset_id: assetId, action }),
    })
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Portfolio + Alerts API
// ─────────────────────────────────────────────────────────────────────────────

export const portfolioApi = {
  getPortfolio(): Promise<PortfolioPosition[]> {
    return apiClient.request<PortfolioPosition[]>('/portfolio')
  },

  upsertPosition(assetId: string, quantity: number, avgBuyPrice: number): Promise<PortfolioPosition> {
    return apiClient.request<PortfolioPosition>('/portfolio', {
      method: 'PUT',
      body: JSON.stringify({ asset_id: assetId, quantity, avg_buy_price: avgBuyPrice }),
    })
  },

  deletePosition(assetId: string): Promise<void> {
    return apiClient.request<void>(`/portfolio/${assetId}`, { method: 'DELETE' })
  },

  getAlerts(): Promise<AlertCondition[]> {
    return apiClient.request<AlertCondition[]>('/alerts')
  },

  createAlert(
    assetId: string,
    condition: 'PRICE_ABOVE' | 'PRICE_BELOW' | 'SENTIMENT_CHANGE',
    targetValue: number
  ): Promise<AlertCondition> {
    return apiClient.request<AlertCondition>('/alerts', {
      method: 'POST',
      body: JSON.stringify({ asset_id: assetId, condition, target_value: targetValue }),
    })
  },

  deleteAlert(alertId: string): Promise<void> {
    return apiClient.request<void>(`/alerts/${alertId}`, { method: 'DELETE' })
  },
}
