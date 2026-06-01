/**
 * Single source of truth for all environment-derived constants.
 * Import from here — never access import.meta.env directly in components.
 */
export const API_HTTP_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`
export const API_WS_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/^http/, 'ws')
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 20_000)
