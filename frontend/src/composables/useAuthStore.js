/**
 * Pinia store for client-side authentication state.
 *
 * Manages:
 *  - The current user public profile (null when unauthenticated).
 *  - JWT token persistence in localStorage.
 *  - Login, register, logout, and session-restore actions.
 *
 * State management boundary:
 *  - This store holds ONLY client-side auth state (user, token).
 *  - Server data (assets, articles) remains in TanStack Query.
 */
import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { authApi } from '@/services/api';
const TOKEN_KEY = 'access_token';
export const useAuthStore = defineStore('auth', () => {
    // ── State ────────────────────────────────────────────────────────────────
    const user = ref(null);
    const isLoading = ref(false);
    const error = ref(null);
    // ── Computed ─────────────────────────────────────────────────────────────
    /** True when the user is logged in and their profile has been fetched. */
    const isAuthenticated = computed(() => user.value !== null);
    /** The raw JWT string from localStorage, or null if not present. */
    const token = computed(() => localStorage.getItem(TOKEN_KEY));
    // ── Actions ──────────────────────────────────────────────────────────────
    /**
     * Attempts to restore an existing session on page reload.
     *
     * Reads the token from localStorage and fetches /auth/me. On failure
     * (expired/invalid token) clears the token silently — no redirect.
     */
    async function restoreSession() {
        if (!localStorage.getItem(TOKEN_KEY))
            return;
        try {
            isLoading.value = true;
            user.value = await authApi.getMe();
        }
        catch {
            localStorage.removeItem(TOKEN_KEY);
            user.value = null;
        }
        finally {
            isLoading.value = false;
        }
    }
    /**
     * Logs the user in with email and password credentials.
     *
     * Stores the returned JWT in localStorage and sets user state.
     *
     * @param email - User email address.
     * @param password - Plain-text password.
     * @throws Error with the server error message on failure.
     */
    async function login(email, password) {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await authApi.login(email, password);
            localStorage.setItem(TOKEN_KEY, response.access_token);
            user.value = response.user;
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Login failed.';
            throw err;
        }
        finally {
            isLoading.value = false;
        }
    }
    /**
     * Registers a new user account and automatically logs them in.
     *
     * @param email - User email address.
     * @param password - Plain-text password (min 8 chars).
     * @param displayName - Public display name.
     * @throws Error with the server error message on failure.
     */
    async function register(email, password, displayName) {
        isLoading.value = true;
        error.value = null;
        try {
            await authApi.register(email, password, displayName);
            // Auto-login after registration
            await login(email, password);
        }
        catch (err) {
            error.value = err instanceof Error ? err.message : 'Registration failed.';
            throw err;
        }
        finally {
            isLoading.value = false;
        }
    }
    /**
     * Logs the user out by clearing the JWT token and user state.
     * Does not call a server-side logout endpoint (tokens are stateless).
     */
    function logout() {
        localStorage.removeItem(TOKEN_KEY);
        user.value = null;
        error.value = null;
    }
    /**
     * Updates the local user state after a watchlist change.
     *
     * @param updatedUser - The fresh UserPublic returned by the watchlist API.
     */
    function updateUser(updatedUser) {
        user.value = updatedUser;
    }
    return {
        user,
        isLoading,
        error,
        isAuthenticated,
        token,
        restoreSession,
        login,
        register,
        logout,
        updateUser,
    };
});
