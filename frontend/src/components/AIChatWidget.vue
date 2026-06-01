<script setup lang="ts">
/**
 * AIChatWidget — Floating AI market assistant chat bubble.
 *
 * Architecture:
 *   - Floating action button (bottom-right, always visible, iOS-safe inset)
 *   - Routes through the centralized `marketApi.sendChatMessage()` — no raw fetch()
 *   - Client-side rate limit: 30s cooldown with live countdown in the placeholder
 *   - Quick-question chips in a single-row horizontal scroll (no height jump)
 *   - Human-readable fallback state: hides cryptic "VADER fallback" label
 *   - Typewriter effect on AI response for a premium feel
 *   - Fully responsive: min 320px height, max 100dvh-120px, no overflow on mobile
 */

import { ref, computed, onUnmounted, nextTick } from 'vue'
import { MessageCircle, X, Send, Loader2, Bot, User, WifiOff, AlertTriangle } from '@lucide/vue'
import { marketApi, type ChatResponse } from '@/services/api'
import { safeStorage } from '@/utils/storage'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  /** True when the backend returned a fallback (LLM unavailable). */
  fallback?: boolean
  /** True when the reply is a hard config-error (LLM not set up). */
  configError?: boolean
  /** True when the HTTP call itself failed (network / CORS / timeout). */
  networkError?: boolean
}

const RATE_LIMIT_KEY = 'ai_chat_last_send'
const RATE_LIMIT_MS = 30_000 // 30 seconds

// ── Reactive state ──────────────────────────────────────────────────────────

const isOpen = ref(false)
const isLoading = ref(false)
const inputText = ref('')
const cooldownSeconds = ref(0)
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    text: 'Hello! Ask me anything about current crypto market sentiment. I have access to live news and prices.',
  },
])
const messagesEndRef = ref<HTMLDivElement | null>(null)

let cooldownTimer: ReturnType<typeof setInterval> | null = null

// ── Computed ────────────────────────────────────────────────────────────────

const hasUserMessages = computed(() =>
  messages.value.some((m) => m.role === 'user'),
)

const inputPlaceholder = computed<string>(() => {
  if (cooldownSeconds.value > 0) return `⏳ Wait ${cooldownSeconds.value}s…`
  if (isLoading.value) return 'Analyzing market…'
  return 'Ask about market sentiment…'
})

const canSend = computed<boolean>(
  () => !isLoading.value && !cooldownSeconds.value && inputText.value.trim().length > 0,
)

// ── Quick questions ─────────────────────────────────────────────────────────

const QUICK_QUESTIONS: readonly string[] = [
  "What's happening with BTC?",
  'Which asset is most bearish?',
  "Summarize today's crypto news",
  'What does current sentiment suggest?',
]

// ── Rate limit helpers ──────────────────────────────────────────────────────

/**
 * Returns the remaining cooldown in milliseconds, or 0 when the user may send.
 */
function getRateLimitRemaining(): number {
  const last = parseInt(safeStorage.get(RATE_LIMIT_KEY) ?? '0', 10)
  const elapsed = Date.now() - last
  return elapsed < RATE_LIMIT_MS ? RATE_LIMIT_MS - elapsed : 0
}

function startCooldown(remainingMs: number): void {
  cooldownSeconds.value = Math.ceil(remainingMs / 1000)
  cooldownTimer = setInterval(() => {
    cooldownSeconds.value -= 1
    if (cooldownSeconds.value <= 0) {
      cooldownSeconds.value = 0
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }
  }, 1000)
}

function setRateLimitTimestamp(): void {
  safeStorage.set(RATE_LIMIT_KEY, String(Date.now()))
  const remaining = getRateLimitRemaining()
  if (remaining > 0) startCooldown(remaining)
}

// ── Scroll helper ───────────────────────────────────────────────────────────

/** Scrolls the messages container to the latest message. */
async function scrollToBottom(): Promise<void> {
  await nextTick()
  messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// ── Typewriter effect ───────────────────────────────────────────────────────

/** Types out a string character by character into the last assistant message. */
async function typewriterEffect(fullText: string): Promise<void> {
  const lastMsg = messages.value[messages.value.length - 1]
  if (!lastMsg || lastMsg.role !== 'assistant') return

  lastMsg.text = ''
  for (const char of fullText) {
    lastMsg.text += char
    await new Promise<void>((resolve) => setTimeout(resolve, 14))
    await scrollToBottom()
  }
}

// ── Send message ────────────────────────────────────────────────────────────

/**
 * Sends the user message via the centralized `marketApi.sendChatMessage()`.
 *
 * Enforces the 30-second client-side rate limit and shows a live countdown.
 * Handles three distinct failure states with distinct UI feedback:
 *   - configError: LLM_API_URL/KEY not configured on the backend
 *   - networkError: Request failed (CORS, timeout, server down)
 *   - fallback:     LLM returned a fallback due to rate limit or model failure
 *
 * @param text - The message text to send.
 */
async function sendMessage(text: string): Promise<void> {
  const msg = text.trim()
  if (!msg || isLoading.value || cooldownSeconds.value > 0) return

  const remaining = getRateLimitRemaining()
  if (remaining > 0) {
    startCooldown(remaining)
    return
  }

  inputText.value = ''
  messages.value.push({ role: 'user', text: msg })
  await scrollToBottom()

  // Placeholder bubble while waiting for LLM response
  messages.value.push({ role: 'assistant', text: '' })
  isLoading.value = true
  setRateLimitTimestamp()

  try {
    const data: ChatResponse = await marketApi.sendChatMessage(msg)
    const lastMsg = messages.value[messages.value.length - 1]

    const isConfigError =
      data.fallback &&
      (data.reply.toLowerCase().includes('not configured') ||
        data.reply.toLowerCase().includes('ask the site administrator'))

    if (lastMsg) {
      lastMsg.fallback = data.fallback && !isConfigError
      lastMsg.configError = isConfigError
    }

    await typewriterEffect(data.reply)
  } catch {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) {
      lastMsg.text = 'Connection failed — check your network or try again later.'
      lastMsg.networkError = true
    }
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage(inputText.value)
  }
}

// ── Cleanup ─────────────────────────────────────────────────────────────────

onUnmounted(() => {
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
})
</script>

<template>
  <!--
    Outer container: fixed to the viewport bottom-right.
    Uses env(safe-area-inset-bottom) so the FAB is not hidden behind the
    iOS Safari home indicator bar on notch devices.
  -->
  <div
    class="fixed right-4 z-50 flex flex-col items-end gap-3"
    style="bottom: max(3rem, calc(env(safe-area-inset-bottom, 0px) + 3rem));"
  >

    <!-- Chat panel -->
    <Transition name="chat-slide">
      <div
        v-if="isOpen"
        class="w-80 sm:w-96 rounded-2xl border border-border/50 shadow-2xl glass-panel flex flex-col overflow-hidden"
        style="height: min(480px, calc(100dvh - 120px)); min-height: 320px;"
        role="dialog"
        aria-label="AI Market Assistant"
        aria-modal="true"
      >
        <!-- Header -->
        <header class="flex items-center gap-2 px-4 py-3 border-b border-border/20 bg-white/[0.02] shrink-0">
          <div class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.7)]" />
          <Bot class="h-4 w-4 text-indigo-400" />
          <span class="text-xs font-bold text-slate-200 tracking-tight">AI Market Assistant</span>
          <span class="text-[9px] text-slate-600 ml-auto font-mono">openrouter/free</span>
          <button
            id="ai-chat-close"
            @click="isOpen = false"
            class="ml-1 p-1 rounded hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
            aria-label="Close chat"
          >
            <X class="h-3.5 w-3.5" />
          </button>
        </header>

        <!-- Messages -->
        <div class="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="flex gap-2"
            :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
          >
            <!-- Avatar -->
            <div
              class="shrink-0 h-6 w-6 rounded-full flex items-center justify-center mt-0.5"
              :class="msg.role === 'user' ? 'bg-indigo-500/20' : 'bg-slate-700/50'"
            >
              <User v-if="msg.role === 'user'" class="h-3 w-3 text-indigo-400" />
              <Bot v-else class="h-3 w-3 text-slate-400" />
            </div>

            <!-- Bubble -->
            <div
              class="max-w-[78%] rounded-2xl px-3 py-2 text-xs leading-relaxed"
              :class="[
                msg.role === 'user'
                  ? 'bg-indigo-600/20 border border-indigo-500/20 text-slate-200 rounded-tr-sm'
                  : 'bg-white/[0.03] border border-white/5 text-slate-300 rounded-tl-sm',
                msg.networkError ? 'border-red-500/20' : '',
                msg.configError ? 'border-amber-600/25' : '',
              ]"
            >
              <!-- Loading dots -->
              <span
                v-if="msg.role === 'assistant' && !msg.text && isLoading"
                class="flex gap-1 py-1"
                aria-label="AI is thinking"
              >
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:0ms" />
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:150ms" />
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:300ms" />
              </span>

              <span v-else>{{ msg.text }}</span>

              <!-- Network error badge -->
              <span
                v-if="msg.networkError"
                class="flex items-center gap-1 mt-1 text-[9px] text-red-400/80"
              >
                <WifiOff class="h-2.5 w-2.5" />
                Connection error
              </span>

              <!-- Config error badge (LLM not set up) -->
              <span
                v-else-if="msg.configError"
                class="flex items-center gap-1 mt-1 text-[9px] text-amber-500/80"
              >
                <AlertTriangle class="h-2.5 w-2.5" />
                AI not configured
              </span>

              <!-- Fallback badge (model unavailable, not a config error) -->
              <span
                v-else-if="msg.fallback"
                class="flex items-center gap-1 mt-1 text-[9px] text-amber-400/70"
              >
                <AlertTriangle class="h-2.5 w-2.5" />
                Limited mode — AI unavailable
              </span>
            </div>
          </div>
          <div ref="messagesEndRef" />
        </div>

        <!-- Quick questions — single-row horizontal scroll, no height jump -->
        <div
          v-if="!hasUserMessages"
          class="px-3 pb-2 overflow-x-auto flex gap-1.5 shrink-0 scrollbar-none"
          style="-webkit-overflow-scrolling: touch;"
        >
          <button
            v-for="q in QUICK_QUESTIONS"
            :key="q"
            @click="sendMessage(q)"
            :disabled="isLoading || cooldownSeconds > 0"
            class="whitespace-nowrap flex-none text-[10px] px-2.5 py-1.5 rounded-lg border border-border/40 bg-white/[0.02] text-slate-400 hover:text-slate-200 hover:border-indigo-500/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ q }}
          </button>
        </div>

        <!-- Input row -->
        <div class="shrink-0 flex items-center gap-2 px-3 py-3 border-t border-border/20 bg-white/[0.01]">
          <!-- Cooldown progress bar -->
          <div
            v-if="cooldownSeconds > 0"
            class="absolute bottom-[52px] left-3 right-3 h-0.5 bg-white/5 rounded-full overflow-hidden"
          >
            <div
              class="h-full bg-indigo-500/50 rounded-full transition-none"
              :style="`width: ${(cooldownSeconds / 30) * 100}%`"
            />
          </div>

          <input
            id="ai-chat-input"
            v-model="inputText"
            @keydown="handleKeydown"
            :disabled="isLoading || cooldownSeconds > 0"
            type="text"
            :placeholder="inputPlaceholder"
            maxlength="500"
            autocomplete="off"
            class="flex-1 min-w-0 bg-transparent border-none outline-none text-xs text-slate-200 placeholder-slate-600 disabled:opacity-50 transition-opacity"
          />

          <button
            id="ai-chat-send"
            @click="sendMessage(inputText)"
            :disabled="!canSend"
            class="shrink-0 p-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer"
            aria-label="Send message"
          >
            <Loader2 v-if="isLoading" class="h-3.5 w-3.5 animate-spin" />
            <Send v-else class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- FAB trigger -->
    <button
      id="ai-chat-trigger"
      @click="isOpen = !isOpen"
      class="h-12 w-12 rounded-2xl bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-900/50 flex items-center justify-center transition-all duration-200 active:scale-95 cursor-pointer"
      :class="isOpen ? '' : 'hover:scale-110'"
      :aria-label="isOpen ? 'Close AI Market Assistant' : 'Open AI Market Assistant'"
      :aria-expanded="isOpen"
    >
      <Transition name="icon-flip" mode="out-in">
        <X v-if="isOpen" class="h-5 w-5 text-white" key="close" />
        <MessageCircle v-else class="h-5 w-5 text-white" key="open" />
      </Transition>
    </button>

  </div>
</template>

<style scoped>
/* ── Chat panel slide-up animation ─────────────────────────────────────────── */
.chat-slide-enter-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.chat-slide-leave-active {
  transition: all 0.18s ease-in;
}
.chat-slide-enter-from,
.chat-slide-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.97);
}

/* ── FAB icon swap animation ───────────────────────────────────────────────── */
.icon-flip-enter-active,
.icon-flip-leave-active {
  transition: all 0.15s ease;
}
.icon-flip-enter-from,
.icon-flip-leave-to {
  opacity: 0;
  transform: scale(0.6) rotate(90deg);
}

/* ── Hide scrollbar on the chips row (all browsers) ──────────────────────── */
.scrollbar-none {
  scrollbar-width: none;
}
.scrollbar-none::-webkit-scrollbar {
  display: none;
}
</style>
