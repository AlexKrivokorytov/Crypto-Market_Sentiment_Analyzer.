import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { SentimentArticle } from '../types/market'
import { safeStorage } from '../utils/storage'

const NEWS_CACHE_KEY = 'sentiment_news_cache'
const MAX_CACHED_ITEMS = 50

/**
 * Pinia Store managing market news sentiment articles with offline hydration.
 * Allows instantaneous rendering on application boot while backend is starting.
 */
export const useNewsStore = defineStore('news', () => {
  const articles = ref<SentimentArticle[]>([])
  const isHydrated = ref(false)

  /** Hydrates the Pinia state from LocalStorage on initial load. */
  function hydrateStore(): void {
    if (isHydrated.value) return

    try {
      const cached = safeStorage.get(NEWS_CACHE_KEY)
      if (cached) {
        articles.value = JSON.parse(cached) as SentimentArticle[]
        console.log(`[NewsStore] Successfully hydrated ${articles.value.length} items from cache.`)
      }
    } catch (err) {
      console.error('[NewsStore] Failed to hydrate cache:', err)
      safeStorage.remove(NEWS_CACHE_KEY)
    } finally {
      isHydrated.value = true
    }
  }

  /**
   * Replaces the current articles and flushes the update to LocalStorage.
   * Capped to avoid bloating localized memory footprints.
   */
  function setArticles(newArticles: SentimentArticle[]): void {
    hydrateStore() // Secure safety check

    const limited = newArticles.slice(0, MAX_CACHED_ITEMS)
    articles.value = limited

    try {
      safeStorage.set(NEWS_CACHE_KEY, JSON.stringify(limited))
    } catch (err) {
      console.error('[NewsStore] Failed to write cache:', err)
    }
  }

  /**
   * Appends a newly scanned live article to the top of the feed reactively.
   */
  function prependArticle(article: SentimentArticle): void {
    hydrateStore()

    // Prevent duplicate entries
    if (articles.value.some((a) => a.id === article.id)) return

    const updated = [article, ...articles.value].slice(0, MAX_CACHED_ITEMS)
    articles.value = updated

    try {
      safeStorage.set(NEWS_CACHE_KEY, JSON.stringify(updated))
    } catch (err) {
      console.error('[NewsStore] Failed to prepend and cache:', err)
    }
  }

  /**
   * Updates an existing article in the store and local storage.
   */
  function updateArticle(updatedArticle: SentimentArticle): void {
    hydrateStore()
    const idx = articles.value.findIndex((a) => a.id === updatedArticle.id)
    if (idx !== -1) {
      articles.value[idx] = updatedArticle
      try {
        safeStorage.set(NEWS_CACHE_KEY, JSON.stringify(articles.value))
      } catch (err) {
        console.error('[NewsStore] Failed to write cache on update:', err)
      }
    }
  }

  const latestArticles = computed(() => {
    // Return items sorted by timestamp descending
    return [...articles.value].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
  })

  return {
    articles: latestArticles,
    isHydrated,
    hydrateStore,
    setArticles,
    prependArticle,
    updateArticle,
  }
})
