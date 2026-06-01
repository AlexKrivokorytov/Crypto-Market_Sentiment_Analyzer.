/**
 * Single source of truth for all environment-derived constants.
 * Import from here — never access import.meta.env directly in components.
 */
export const API_HTTP_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`
export const API_WS_BASE = (() => {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) {
    return envUrl.replace(/^http/, 'ws') + '/api/v1'
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1`
})()
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 20_000)
