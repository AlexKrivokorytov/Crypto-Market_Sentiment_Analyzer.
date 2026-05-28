<script setup lang="ts">
/**
 * RegisterView — Animated glassmorphism account creation page.
 *
 * On successful registration auto-logs in and redirects to the dashboard.
 */

import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/composables/useAuthStore'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const displayName = ref('')
const submitting = ref(false)
const localError = ref<string | null>(null)

async function handleSubmit(): Promise<void> {
  localError.value = null

  if (!email.value.trim() || !password.value || !displayName.value.trim()) {
    localError.value = 'Please fill in all fields.'
    return
  }
  if (password.value !== confirmPassword.value) {
    localError.value = 'Passwords do not match.'
    return
  }
  if (password.value.length < 8) {
    localError.value = 'Password must be at least 8 characters.'
    return
  }

  submitting.value = true
  try {
    await authStore.register(email.value.trim(), password.value, displayName.value.trim())
    await router.push('/asset/BTC')
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Registration failed.'
    localError.value = msg.includes('409') || msg.includes('already registered')
      ? 'This email is already registered.'
      : 'Registration failed. Please try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <div class="orb orb--blue" />
    <div class="orb orb--violet" />
    <div class="orb orb--cyan" />

    <section class="auth-card" aria-label="Create a SentimentAI account">
      <div class="auth-logo">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden="true">
          <rect width="40" height="40" rx="12" fill="url(#logoGradR)" />
          <path d="M10 28L20 12l10 16" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="20" cy="12" r="2.5" fill="white" />
          <defs>
            <linearGradient id="logoGradR" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
              <stop stop-color="#6366f1" />
              <stop offset="1" stop-color="#8b5cf6" />
            </linearGradient>
          </defs>
        </svg>
        <span class="auth-logo__name">SentimentAI</span>
      </div>

      <h1 class="auth-title">Create account</h1>
      <p class="auth-subtitle">Start tracking markets and building your portfolio today.</p>

      <form id="register-form" class="auth-form" @submit.prevent="handleSubmit" novalidate>
        <div class="field-group">
          <label for="register-name" class="field-label">Display Name</label>
          <input
            id="register-name"
            v-model="displayName"
            type="text"
            class="field-input"
            placeholder="Alex Krivokorytov"
            autocomplete="name"
            :disabled="submitting"
            required
          />
        </div>

        <div class="field-group">
          <label for="register-email" class="field-label">Email</label>
          <input
            id="register-email"
            v-model="email"
            type="email"
            class="field-input"
            placeholder="you@example.com"
            autocomplete="email"
            :disabled="submitting"
            required
          />
        </div>

        <div class="field-group">
          <label for="register-password" class="field-label">Password</label>
          <input
            id="register-password"
            v-model="password"
            type="password"
            class="field-input"
            placeholder="Min. 8 characters"
            autocomplete="new-password"
            :disabled="submitting"
            required
          />
        </div>

        <div class="field-group">
          <label for="register-confirm-password" class="field-label">Confirm Password</label>
          <input
            id="register-confirm-password"
            v-model="confirmPassword"
            type="password"
            class="field-input"
            placeholder="••••••••"
            autocomplete="new-password"
            :disabled="submitting"
            required
          />
        </div>

        <Transition name="fade">
          <p v-if="localError" class="auth-error" role="alert" aria-live="polite">
            {{ localError }}
          </p>
        </Transition>

        <button
          id="register-submit-btn"
          type="submit"
          class="btn-primary"
          :disabled="submitting"
          :aria-busy="submitting"
        >
          <span v-if="!submitting">Create Account</span>
          <span v-else class="spinner" aria-label="Creating account…" />
        </button>
      </form>

      <p class="auth-footer">
        Already have an account?&nbsp;
        <RouterLink id="register-login-link" to="/login" class="auth-link">Sign in</RouterLink>
      </p>
    </section>
  </main>
</template>

<style scoped>
/* ── Shared styles with LoginView ───────────────────────────────── */
.auth-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem 1rem;
  background: #050810;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  animation: drift 8s ease-in-out infinite alternate;
  pointer-events: none;
}
.orb--blue   { width: 480px; height: 480px; background: #6366f1; top: -140px; left: -120px; animation-delay: 0s; }
.orb--violet { width: 400px; height: 400px; background: #8b5cf6; bottom: -100px; right: -80px; animation-delay: -3s; }
.orb--cyan   { width: 300px; height: 300px; background: #06b6d4; top: 40%; left: 55%; animation-delay: -6s; }

@keyframes drift {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(40px, -30px) scale(1.08); }
}

.auth-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  padding: 2.5rem 2rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1.5rem;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.08);
  animation: slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(32px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.auth-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}
.auth-logo__name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.02em;
}
.auth-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 0.5rem;
  letter-spacing: -0.03em;
}
.auth-subtitle {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 0 0 2rem;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.field-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.02em;
}
.field-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  color: #f8fafc;
  font-size: 0.9375rem;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  outline: none;
  box-sizing: border-box;
}
.field-input::placeholder { color: #475569; }
.field-input:focus {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}
.field-input:disabled { opacity: 0.5; cursor: not-allowed; }
.auth-error {
  font-size: 0.8125rem;
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 0.5rem;
  padding: 0.625rem 0.875rem;
  margin: 0;
}
.btn-primary {
  width: 100%;
  padding: 0.875rem;
  border-radius: 0.75rem;
  border: none;
  cursor: pointer;
  font-size: 0.9375rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
  margin-top: 0.25rem;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.45);
}
.btn-primary:active:not(:disabled) { transform: translateY(0); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.auth-footer {
  margin-top: 1.75rem;
  text-align: center;
  font-size: 0.875rem;
  color: #64748b;
}
.auth-link {
  color: #818cf8;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.15s;
}
.auth-link:hover { color: #a5b4fc; text-decoration: underline; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
