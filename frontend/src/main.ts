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
      title: 'Сессия завершена',
      message: detail || 'Токен авторизации недействителен или истек. Пожалуйста, войдите в аккаунт заново.',
      type: 'warning',
      durationMs: 5000
    })
    router.push('/login')
  } else if (status === 429) {
    toast.show({
      title: 'Превышен лимит запросов',
      message: detail || 'Вы отправляете слишком много запросов. Пожалуйста, подождите некоторое время.',
      type: 'warning',
      durationMs: 4000
    })
  } else if (status >= 500) {
    toast.show({
      title: 'Сервер недоступен или просыпается',
      message: detail || 'Бэкенд на Render просыпается после паузы (холодный старт) или временно перегружен.',
      type: 'error',
      durationMs: 0, // Keep pinned until dismissed or retried
      action: {
        label: 'Повторить запрос',
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
