import { ref } from 'vue';
const activeToasts = ref([]);
/**
 * Lightweight, high-performance Toast notification system.
 * Designed to show micro-feedback and critical connection alerts with CTAs.
 */
export function useToast() {
    /**
     * Triggers a new toast alert on the screen.
     */
    function show(options) {
        const id = Math.random().toString(36).substring(2, 9);
        const { type = 'info', durationMs = 5000, action } = options;
        const toastItem = {
            id,
            visible: true,
            title: options.title,
            message: options.message,
            type,
            durationMs,
            action,
        };
        activeToasts.value.push(toastItem);
        // Auto-dismiss after duration, unless set to 0 (which keeps it pinned)
        if (durationMs > 0) {
            window.setTimeout(() => {
                dismiss(id);
            }, durationMs);
        }
        return id;
    }
    /**
     * Dismisses a specific toast alert by its identifier.
     */
    function dismiss(id) {
        const idx = activeToasts.value.findIndex((t) => t.id === id);
        if (idx !== -1) {
            const toast = activeToasts.value[idx];
            if (toast) {
                toast.visible = false;
            }
            // Let transition finish before removing
            window.setTimeout(() => {
                activeToasts.value = activeToasts.value.filter((t) => t.id !== id);
            }, 300);
        }
    }
    /**
     * Triggers a standardized critical connection error toast with a Retry action.
     *
     * @param onRetry Callback triggered when user clicks the retry button
     */
    function showConnectionFailedToast(onRetry) {
        return show({
            title: 'Сбой соединения с сервером',
            message: 'Превышено число попыток переподключения. Бэкенд на Render, возможно, «уснул» или перезагружается.',
            type: 'error',
            durationMs: 0, // Pin to screen until dismissed or retried
            action: {
                label: 'Повторить попытку',
                onClick: () => {
                    onRetry();
                },
            },
        });
    }
    return {
        toasts: activeToasts,
        show,
        dismiss,
        showConnectionFailedToast,
    };
}
