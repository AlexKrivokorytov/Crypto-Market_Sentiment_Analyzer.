/**
 * Single source of truth for all environment-derived constants.
 * Import from here — never access import.meta.env directly in components.
 */
export const API_HTTP_BASE = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1`
export const API_WS_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws')
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 15_000)
