<script setup lang="ts">
import { useToast } from '../../composables/useToast'
import { 
  X as XIcon, 
  CheckCircle as CheckCircleIcon, 
  AlertTriangle as AlertTriangleIcon, 
  AlertOctagon as AlertOctagonIcon, 
  Info as InfoIcon,
  RotateCw as RotateCwIcon
} from '@lucide/vue'

const { toasts, dismiss } = useToast()

const getToastClasses = (type?: string) => {
  switch (type) {
    case 'success':
      return {
        border: 'border-emerald-500/25 bg-emerald-950/20 text-emerald-300',
        icon: 'text-emerald-400 bg-emerald-500/10',
        progress: 'bg-emerald-500',
        glow: 'shadow-emerald-950/50'
      }
    case 'error':
      return {
        border: 'border-rose-500/25 bg-rose-950/20 text-rose-300',
        icon: 'text-rose-400 bg-rose-500/10',
        progress: 'bg-rose-500',
        glow: 'shadow-rose-950/50'
      }
    case 'warning':
      return {
        border: 'border-amber-500/25 bg-amber-950/20 text-amber-300',
        icon: 'text-amber-400 bg-amber-500/10',
        progress: 'bg-amber-500',
        glow: 'shadow-amber-950/50'
      }
    case 'info':
    default:
      return {
        border: 'border-indigo-500/25 bg-indigo-950/20 text-indigo-300',
        icon: 'text-indigo-400 bg-indigo-500/10',
        progress: 'bg-indigo-500',
        glow: 'shadow-indigo-950/50'
      }
  }
}
</script>

<template>
  <div
    class="fixed bottom-4 right-4 z-50 flex flex-col gap-3 w-full max-w-sm pointer-events-none"
    role="alert"
    aria-live="polite"
  >
    <TransitionGroup name="toast-list">
      <div
        v-for="toast in toasts"
        v-show="toast.visible"
        :key="toast.id"
        class="pointer-events-auto relative overflow-hidden rounded-2xl border p-4 shadow-xl backdrop-blur-xl transition-all duration-300 ease-out glass-panel flex flex-col gap-3"
        :class="[getToastClasses(toast.type).border, getToastClasses(toast.type).glow]"
      >
        <!-- Card Core Layout -->
        <div class="flex items-start gap-3">
          <!-- Type Specific Icon -->
          <div class="flex-shrink-0 p-1.5 rounded-lg" :class="getToastClasses(toast.type).icon">
            <CheckCircleIcon v-if="toast.type === 'success'" class="w-5 h-5" />
            <AlertOctagonIcon v-else-if="toast.type === 'error'" class="w-5 h-5" />
            <AlertTriangleIcon v-else-if="toast.type === 'warning'" class="w-5 h-5" />
            <InfoIcon v-else class="w-5 h-5" />
          </div>

          <!-- Text Block -->
          <div class="flex-grow min-w-0 select-none">
            <h3 class="text-sm font-semibold leading-5 text-slate-100">
              {{ toast.title }}
            </h3>
            <p class="mt-1 text-xs leading-relaxed text-slate-300">
              {{ toast.message }}
            </p>
          </div>

          <!-- Close Action -->
          <button
            class="flex-shrink-0 text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-md hover:bg-white/5"
            @click="dismiss(toast.id)"
          >
            <XIcon class="w-4 h-4" />
          </button>
        </div>

        <!-- Custom Action Hook Button (e.g. Retry) -->
        <div v-if="toast.action" class="flex justify-end gap-2 border-t border-white/5 pt-3">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-900/30 transition-all active:scale-95"
            @click="toast.action.onClick(); dismiss(toast.id)"
          >
            <RotateCwIcon class="w-3.5 h-3.5" />
            <span>{{ toast.action.label }}</span>
          </button>
        </div>

        <!-- Shimmer Timeout Line Indicator -->
        <div
          v-if="toast.durationMs && toast.durationMs > 0"
          class="absolute bottom-0 left-0 h-0.5 w-full bg-slate-700/20"
        >
          <div
            class="h-full rounded-r transition-all duration-[5000ms] linear"
            :class="getToastClasses(toast.type).progress"
            :style="{
              animation: `toast-progress ${toast.durationMs}ms linear forwards`
            }"
          ></div>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style>
/* Toast List Transitions */
.toast-list-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.toast-list-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}

@keyframes toast-progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}
</style>
