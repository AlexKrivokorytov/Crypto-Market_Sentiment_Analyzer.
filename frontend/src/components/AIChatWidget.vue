<script setup lang="ts">
/**
 * AIChatWidget — Floating AI market assistant chat bubble.
 *
 * Architecture:
 *   - Floating action button (bottom-right, always visible)
 *   - Sends one POST /api/v1/chat request with the user message
 *   - Client-side rate limit: 1 message per 30s (localStorage timer)
 *   - Quick-question chips for zero-typing UX
 *   - Typewriter effect on AI response for premium feel
 */

import { ref, nextTick } from 'vue'
import { MessageCircle, X, Send, Loader2, Bot, User } from '@lucide/vue'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  fallback?: boolean
}

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const RATE_LIMIT_KEY = 'ai_chat_last_send'
const RATE_LIMIT_MS = 30_000 // 30 seconds between requests

const isOpen = ref(false)
const isLoading = ref(false)
const inputText = ref('')
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    text: 'Hello! Ask me anything about current crypto market sentiment. I have access to live news and prices.',
  },
])
const messagesEndRef = ref<HTMLDivElement | null>(null)

const QUICK_QUESTIONS = [
  'What\'s happening with BTC?',
  'Which asset is most bearish right now?',
  'Summarize today\'s crypto news',
  'What does the current sentiment suggest?',
]

/**
 * Checks if the user is within the client-side rate limit.
 * Returns the remaining cooldown ms, or 0 if allowed.
 */
function getRateLimitRemaining(): number {
  try {
    const last = parseInt(localStorage.getItem(RATE_LIMIT_KEY) ?? '0', 10)
    const elapsed = Date.now() - last
    return elapsed < RATE_LIMIT_MS ? RATE_LIMIT_MS - elapsed : 0
  } catch {
    return 0
  }
}

function setRateLimitTimestamp(): void {
  try {
    localStorage.setItem(RATE_LIMIT_KEY, String(Date.now()))
  } catch {
    // ignore storage errors
  }
}

/** Scrolls the messages container to the latest message. */
async function scrollToBottom(): Promise<void> {
  await nextTick()
  messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
}

/** Types out a string character by character into the last assistant message. */
async function typewriterEffect(fullText: string): Promise<void> {
  const lastMsg = messages.value[messages.value.length - 1]
  if (!lastMsg || lastMsg.role !== 'assistant') return

  lastMsg.text = ''
  for (const char of fullText) {
    lastMsg.text += char
    await new Promise<void>(resolve => setTimeout(resolve, 14))
    await scrollToBottom()
  }
}

/**
 * Sends the user message to the backend /api/v1/chat endpoint.
 * Enforces client-side rate limiting and shows a typewriter reply.
 *
 * @param text - The message text to send.
 */
async function sendMessage(text: string): Promise<void> {
  const msg = text.trim()
  if (!msg || isLoading.value) return

  const cooldown = getRateLimitRemaining()
  if (cooldown > 0) {
    messages.value.push({
      role: 'assistant',
      text: `⏱ Please wait ${Math.ceil(cooldown / 1000)}s before sending another message.`,
    })
    await scrollToBottom()
    return
  }

  inputText.value = ''
  messages.value.push({ role: 'user', text: msg })
  await scrollToBottom()

  // Placeholder while loading
  messages.value.push({ role: 'assistant', text: '' })
  isLoading.value = true
  setRateLimitTimestamp()

  try {
    const resp = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    })

    const data = (await resp.json()) as { reply: string; fallback?: boolean }
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.fallback = data.fallback ?? false

    await typewriterEffect(data.reply)
  } catch {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.text = 'Network error — check your connection.'
  } finally {
    isLoading.value = false
  }
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage(inputText.value)
  }
}
</script>

<template>
  <!-- Floating trigger button -->
  <div class="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">

    <!-- Chat panel -->
    <Transition name="chat-slide">
      <div
        v-if="isOpen"
        class="w-80 sm:w-96 rounded-2xl border border-border/50 shadow-2xl glass-panel flex flex-col overflow-hidden"
        style="height: 480px; max-height: calc(100dvh - 100px);"
        role="dialog"
        aria-label="AI Market Assistant"
      >
        <!-- Header -->
        <header class="flex items-center gap-2 px-4 py-3 border-b border-border/20 bg-white/[0.02] shrink-0">
          <div class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.7)]" />
          <Bot class="h-4 w-4 text-indigo-400" />
          <span class="text-xs font-bold text-slate-200 tracking-tight">AI Market Assistant</span>
          <span class="text-[9px] text-slate-600 ml-auto font-mono">openrouter/free</span>
          <button
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
            <div class="shrink-0 h-6 w-6 rounded-full flex items-center justify-center mt-0.5"
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
                msg.fallback ? 'border-amber-500/20' : ''
              ]"
            >
              <!-- Loading dots -->
              <span v-if="msg.role === 'assistant' && !msg.text && isLoading" class="flex gap-1 py-1">
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:0ms" />
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:150ms" />
                <span class="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:300ms" />
              </span>
              <span v-else>{{ msg.text }}</span>
              <span
                v-if="msg.fallback"
                class="block text-[9px] text-amber-500/70 mt-1"
              >⚠ VADER fallback</span>
            </div>
          </div>
          <div ref="messagesEndRef" />
        </div>

        <!-- Quick questions (shown when no user messages yet) -->
        <div
          v-if="messages.filter(m => m.role === 'user').length === 0"
          class="px-3 pb-2 flex flex-wrap gap-1.5 shrink-0"
        >
          <button
            v-for="q in QUICK_QUESTIONS"
            :key="q"
            @click="sendMessage(q)"
            :disabled="isLoading"
            class="text-[10px] px-2 py-1 rounded-lg border border-border/40 bg-white/[0.02] text-slate-400 hover:text-slate-200 hover:border-indigo-500/30 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ q }}
          </button>
        </div>

        <!-- Input -->
        <div class="shrink-0 flex items-center gap-2 px-3 py-3 border-t border-border/20 bg-white/[0.01]">
          <input
            v-model="inputText"
            @keydown="handleKeydown"
            :disabled="isLoading"
            type="text"
            placeholder="Ask about market sentiment…"
            maxlength="280"
            class="flex-1 min-w-0 bg-transparent border-none outline-none text-xs text-slate-200 placeholder-slate-600 disabled:opacity-50"
          />
          <button
            @click="sendMessage(inputText)"
            :disabled="isLoading || !inputText.trim()"
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
      :class="isOpen ? 'rotate-0' : 'hover:scale-110'"
      aria-label="Open AI Market Assistant"
    >
      <Transition name="icon-flip" mode="out-in">
        <X v-if="isOpen" class="h-5 w-5 text-white" key="close" />
        <MessageCircle v-else class="h-5 w-5 text-white" key="open" />
      </Transition>
    </button>

  </div>
</template>

<style scoped>
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

.icon-flip-enter-active,
.icon-flip-leave-active {
  transition: all 0.15s ease;
}
.icon-flip-enter-from,
.icon-flip-leave-to {
  opacity: 0;
  transform: scale(0.6) rotate(90deg);
}
</style>
