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
