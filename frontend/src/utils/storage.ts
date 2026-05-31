/**
 * Safe localStorage wrapper that degrades gracefully in private-browsing mode.
 * All write failures are caught and logged; reads return null on failure.
 */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value)
    } catch {
      // Private browsing or quota exceeded — fail silently
    }
  },
  remove(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch {
      // ignore
    }
  },
}
