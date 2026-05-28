import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { VueQueryPlugin } from '@tanstack/vue-query';
import App from './App.vue';
import router from './router/index';
import './index.css';
const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(VueQueryPlugin);
app.use(router);
/**
 * Restore auth session from localStorage on every page load before mounting.
 * Calls /auth/me with the stored JWT — clears the token silently on failure.
 */
import { useAuthStore } from '@/composables/useAuthStore';
const authStore = useAuthStore();
authStore.restoreSession().finally(() => {
    /**
     * Updates the browser tab title after each navigation.
     * Asset routes produce titles like "BTC · SentimentAI".
     * Other routes fall back to the route meta title or the app name.
     */
    router.afterEach((to) => {
        const assetId = to.params.id;
        const base = 'SentimentAI';
        if (assetId) {
            document.title = `${assetId} · ${base}`;
        }
        else {
            const metaTitle = to.meta.title;
            document.title = metaTitle ? `${metaTitle} · ${base}` : base;
        }
    });
    app.mount('#app');
});
