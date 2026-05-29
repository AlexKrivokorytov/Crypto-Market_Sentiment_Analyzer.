import { ref } from 'vue'

export interface ToastAction {
  label: string
  onClick: () => void
}

export interface ToastOptions {
  title: string
  message: string
  type?: 'success' | 'warning' | 'error' | 'info'
  durationMs?: number
  action?: ToastAction
}

export interface ToastState extends ToastOptions {
  id: string
  visible: boolean
}

const activeToasts = ref<ToastState[]>([])

/**
 * Lightweight, high-performance Toast notification system.
 * Designed to show micro-feedback and critical connection alerts with CTAs.
 */
export function useToast() {
  /**
   * Triggers a new toast alert on the screen.
   */
  function show(options: ToastOptions): string {
    const id = Math.random().toString(36).substring(2, 9)
    const { type = 'info', durationMs = 5000, action } = options

    const toastItem: ToastState = {
      id,
      visible: true,
      title: options.title,
      message: options.message,
      type,
      durationMs,
      action,
    }

    activeToasts.value.push(toastItem)

    // Auto-dismiss after duration, unless set to 0 (which keeps it pinned)
    if (durationMs > 0) {
      window.setTimeout(() => {
        dismiss(id)
      }, durationMs)
    }

    return id
  }

  /**
   * Dismisses a specific toast alert by its identifier.
   */
  function dismiss(id: string): void {
    const idx = activeToasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) {
      const toast = activeToasts.value[idx]
      if (toast) {
        toast.visible = false
      }
      // Let transition finish before removing
      window.setTimeout(() => {
        activeToasts.value = activeToasts.value.filter((t) => t.id !== id)
      }, 300)
    }
  }

  /**
   * Triggers a standardized critical connection error toast with a Retry action.
   * 
   * @param onRetry Callback triggered when user clicks the retry button
   */
  function showConnectionFailedToast(onRetry: () => void): string {
    return show({
      title: 'Connection Offline',
      message: 'Maximum reconnection attempts exceeded. The backend host might be restarting (Render cold-start).',
      type: 'error',
      durationMs: 0, // Pin to screen until dismissed or retried
      action: {
        label: 'Retry Connection',
        onClick: () => {
          onRetry()
        },
      },
    })
  }

  return {
    toasts: activeToasts,
    show,
    dismiss,
    showConnectionFailedToast,
  }
}
