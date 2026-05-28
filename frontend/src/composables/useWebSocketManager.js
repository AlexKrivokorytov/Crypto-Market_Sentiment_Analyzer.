import { ref, watch, onScopeDispose } from 'vue';
/**
 * High-performance WebSocket connection manager.
 *
 * Features:
 *   - Auto-reconnect with exponential backoff capped at a maximum delay.
 *   - Keeping-alive heartbeats (ping/pong) to prevent Render's idle timeout.
 *   - requestAnimationFrame throttled message processing to prevent UI lags during high tick volumes.
 *   - Triggers an error callback once maximum reconnect attempts are exhausted.
 *
 * @param streamId Reactive reference to the stream ticker ID (e.g., 'BTC')
 * @param onMessageReceived Callback triggered on throttled message payloads
 * @param onReconnectFailed Callback triggered when all reconnect attempts are exhausted
 * @param config Optional configuration parameters
 */
export function useWebSocketManager(streamId, onMessageReceived, onReconnectFailed, config = {}) {
    const { pingIntervalMs = 20000, maxReconnectAttempts = 5, reconnectBaseDelayMs = 1000, reconnectMaxDelayMs = 30000, } = config;
    const socket = ref(null);
    const connectionStatus = ref('DISCONNECTED');
    const reconnectCount = ref(0);
    const isManuallyClosed = ref(false);
    let pingIntervalId = null;
    let reconnectTimeoutId = null;
    let throttleFrameId = null;
    let pendingUpdate = null;
    /**
     * Clears active timers (heartbeat ping and reconnect timeouts).
     */
    function clearTimers() {
        if (pingIntervalId !== null) {
            window.clearInterval(pingIntervalId);
            pingIntervalId = null;
        }
        if (reconnectTimeoutId !== null) {
            window.clearTimeout(reconnectTimeoutId);
            reconnectTimeoutId = null;
        }
    }
    /**
     * Closes the active socket connection and cleans up buffers and timers.
     */
    function disconnect() {
        isManuallyClosed.value = true;
        connectionStatus.value = 'DISCONNECTED';
        clearTimers();
        if (throttleFrameId !== null) {
            cancelAnimationFrame(throttleFrameId);
            throttleFrameId = null;
        }
        pendingUpdate = null;
        if (socket.value) {
            // Clear event listeners before closing to avoid trigger loop
            socket.value.onclose = null;
            socket.value.onerror = null;
            socket.value.onmessage = null;
            socket.value.onopen = null;
            if (socket.value.readyState === WebSocket.OPEN || socket.value.readyState === WebSocket.CONNECTING) {
                socket.value.close(1000, 'Normal Closure');
            }
            socket.value = null;
        }
    }
    /**
     * Establishes a WebSocket connection to the backend for the specific stream ID.
     */
    function connect(id) {
        if (!id)
            return;
        isManuallyClosed.value = false;
        clearTimers();
        if (socket.value) {
            socket.value.close();
            socket.value = null;
        }
        connectionStatus.value = reconnectCount.value > 0 ? 'RECONNECTING' : 'CONNECTING';
        // Retrieve and compute the WebSocket protocol from environment configurations
        const rawApiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
        const wsHost = rawApiUrl.replace(/^http/, 'ws');
        const wsUrl = `${wsHost}/api/v1/ws/${id}`;
        try {
            const ws = new WebSocket(wsUrl);
            socket.value = ws;
            ws.onopen = () => {
                connectionStatus.value = 'CONNECTED';
                reconnectCount.value = 0;
                console.log(`[WebSocketManager] Stream active: ${id}`);
                // Register heartbeat interval to prevent Render idle teardown
                pingIntervalId = window.setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send('ping');
                    }
                }, pingIntervalMs);
            };
            ws.onmessage = (event) => {
                if (event.data === 'pong')
                    return;
                try {
                    const payload = JSON.parse(event.data);
                    pendingUpdate = payload;
                    // Throttle state changes to paint cycles via requestAnimationFrame
                    if (throttleFrameId === null) {
                        throttleFrameId = requestAnimationFrame(() => {
                            if (pendingUpdate !== null) {
                                onMessageReceived(pendingUpdate);
                                pendingUpdate = null;
                            }
                            throttleFrameId = null;
                        });
                    }
                }
                catch (err) {
                    console.error('[WebSocketManager] Failed to parse message packet:', err);
                }
            };
            ws.onerror = (err) => {
                console.error(`[WebSocketManager] Stream encountered an error for ${id}:`, err);
            };
            ws.onclose = (event) => {
                socket.value = null;
                clearTimers();
                if (isManuallyClosed.value) {
                    connectionStatus.value = 'DISCONNECTED';
                    return;
                }
                connectionStatus.value = 'DISCONNECTED';
                console.warn(`[WebSocketManager] Socket closed: code=${event.code} reason=${event.reason}`);
                // Trigger exponential backoff reconnect sequence
                if (reconnectCount.value < maxReconnectAttempts) {
                    const delay = Math.min(reconnectMaxDelayMs, Math.pow(2, reconnectCount.value) * reconnectBaseDelayMs);
                    reconnectCount.value++;
                    console.log(`[WebSocketManager] Reconnecting stream ${id} in ${delay}ms (${reconnectCount.value}/${maxReconnectAttempts})`);
                    reconnectTimeoutId = window.setTimeout(() => {
                        connect(id);
                    }, delay);
                }
                else {
                    console.error('[WebSocketManager] Maximum reconnect attempts exceeded.');
                    if (onReconnectFailed) {
                        onReconnectFailed();
                    }
                }
            };
        }
        catch (err) {
            connectionStatus.value = 'DISCONNECTED';
            console.error('[WebSocketManager] WebSocket instantiation failed:', err);
        }
    }
    // Reactively rebuild connection rooms upon ticker identification changes
    watch(() => streamId.value, (newVal) => {
        if (newVal) {
            connect(newVal);
        }
    }, { immediate: true });
    onScopeDispose(() => {
        disconnect();
    });
    return {
        connectionStatus,
        reconnectCount,
        disconnect,
        reconnect: () => streamId.value && connect(streamId.value),
    };
}
