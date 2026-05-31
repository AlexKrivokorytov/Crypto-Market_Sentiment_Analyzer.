import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router/index'
import './index.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(VueQueryPlugin)
app.use(router)

/**
 * Restore auth session from localStorage on every page load before mounting.
 * Calls /auth/me with the stored JWT — clears the token silently on failure.
 */
import { useAuthStore } from '@/composables/useAuthStore'
import { apiClient } from '@/services/api'
import { useToast } from '@/composables/useToast'

const authStore = useAuthStore()
const toast = useToast()

// Register global, decoupled API error interceptor
apiClient.onError((status, detail, retry) => {
  if (status === 401) {
    authStore.logout()
    toast.show({
      title: 'Session Expired',
      message: detail || 'Your authorization token is invalid or expired. Please sign in again.',
      type: 'warning',
      durationMs: 5000
    })
    router.push('/login')
  } else if (status === 429) {
    toast.show({
      title: 'Rate Limit Exceeded',
      message: detail || 'You are sending too many requests. Please slow down and try again shortly.',
      type: 'warning',
      durationMs: 4000
    })
  } else if (status >= 500) {
    toast.show({
      title: 'Service Unavailable (Spinning Up)',
      message: detail || 'The backend is waking up (Render cold-start) or temporarily busy. Please stand by.',
      type: 'error',
      durationMs: 0, // Keep pinned until dismissed or retried
      action: {
        label: 'Retry Request',
        onClick: () => {
          retry().catch((err) => console.log('[GlobalErrorInterceptor] Manual retry failed:', err))
        }
      }
    })
  }
})

authStore.restoreSession().finally(() => {
  /**
   * Updates the browser tab title after each navigation.
   * Asset routes produce titles like "BTC · SentimentAI".
   * Other routes fall back to the route meta title or the app name.
   */
  router.afterEach((to) => {
    const assetId = to.params.id as string | undefined
    const base = 'SentimentAI'
    if (assetId) {
      document.title = `${assetId} · ${base}`
    } else {
      const metaTitle = to.meta.title as string | undefined
      document.title = metaTitle ? `${metaTitle} · ${base}` : base
    }
  })

  app.mount('#app')
})

// Unregister any rogue service workers causing "old interface" caching
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const registration of registrations) {
      registration.unregister()
    }
  })
}
