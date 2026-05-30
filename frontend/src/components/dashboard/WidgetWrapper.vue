<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { 
  ChevronDown, 
  ChevronUp, 
  EyeOff, 
  AlertTriangle, 
  RefreshCw, 
  GripVertical
} from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    title: string
    widgetId: string
    collapsible?: boolean
    collapsed?: boolean
    hideable?: boolean
  }>(),
  {
    collapsible: true,
    collapsed: false,
    hideable: true
  }
)

const emit = defineEmits<{
  (e: 'update:collapsed', value: boolean): void
  (e: 'hide'): void
}>()

const hasError = ref(false)
const errorMessage = ref('')
const errorStack = ref('')
const refreshKey = ref(0)

/**
 * Capture error from child components.
 * This isolates crashes inside the slot content, preventing the entire
 * application or other dashboard widgets from failing simultaneously.
 */
onErrorCaptured((error: Error, instance, info) => {
  console.error(`[WidgetWrapper][${props.widgetId}] Caught unhandled crash:`, {
    message: error.message,
    info,
    instance
  })
  
  hasError.value = true
  errorMessage.value = error.message
  errorStack.value = error.stack || 'No stack trace available.'
  
  // Return false to stop error propagation to App global boundary
  return false
})

/**
 * Re-mounts the slot component from scratch by incrementing the Vue render key,
 * clearing the error states and triggering fresh API calls.
 */
function handleResetError() {
  hasError.value = false
  errorMessage.value = ''
  errorStack.value = ''
  refreshKey.value++
}

function handleCollapseToggle() {
  emit('update:collapsed', !props.collapsed)
}
</script>

<template>
  <div
    class="glass-panel rounded-3xl border border-border/40 flex flex-col transition-all duration-300 relative group select-none h-full"
    :class="[
      collapsed ? 'h-14 sm:h-14 lg:h-14 shadow-none bg-slate-950/20 overflow-hidden' : 'shadow-xl',
      hasError ? 'border-rose-500/20 bg-rose-950/5' : ''
    ]"
  >
    <!-- Widget Control Header -->
    <header 
      class="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-border/20 shrink-0 select-none bg-white/[0.01]"
    >
      <div class="flex items-center gap-2 min-w-0">
        <!-- Drag Handle Affordance -->
        <div class="text-slate-600 hover:text-slate-400 cursor-grab active:cursor-grabbing p-1 rounded hover:bg-white/5 transition-colors hidden sm:block shrink-0">
          <GripVertical class="h-4 w-4" />
        </div>
        
        <!-- Live Glowing Status Dot -->
        <span 
          class="h-1.5 w-1.5 rounded-full shrink-0 transition-all duration-500" 
          :class="[hasError ? 'bg-rose-500 shadow-rose-500/50' : 'animate-pulse']"
          :style="!hasError ? { backgroundColor: 'var(--active-brand-color)', boxShadow: '0 0 8px var(--active-brand-color)' } : {}"
        ></span>

        <h3 class="text-xs sm:text-sm font-bold tracking-tight text-slate-200 truncate">
          {{ title }}
        </h3>
      </div>

      <!-- Controls Block -->
      <div class="flex items-center gap-1.5">
        <!-- Collapse Trigger -->
        <button
          v-if="collapsible && !hasError"
          @click="handleCollapseToggle"
          class="p-1.5 rounded-xl hover:bg-white/5 text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
          :aria-label="collapsed ? 'Expand widget' : 'Collapse widget'"
        >
          <ChevronUp v-if="!collapsed" class="h-4 w-4" />
          <ChevronDown v-else class="h-4 w-4" />
        </button>

        <!-- Hide Trigger -->
        <button
          v-if="hideable"
          @click="emit('hide')"
          class="p-1.5 rounded-xl hover:bg-white/5 text-slate-400 hover:text-red-400 transition-all cursor-pointer"
          aria-label="Hide widget"
        >
          <EyeOff class="h-4 w-4" />
        </button>
      </div>
    </header>

    <!-- Widget Body Context Grid -->
    <div 
      class="flex-1 min-h-0 relative transition-all duration-300"
      :class="[collapsed ? 'h-0 opacity-0 scale-95 pointer-events-none overflow-hidden' : 'h-auto opacity-100 scale-100']"
    >
      <!-- Isolated Crash Recovery Overlay Screen -->
      <Transition name="fade">
        <div
          v-if="hasError"
          class="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 bg-slate-950/85 backdrop-blur-md text-center select-none"
        >
          <div class="p-3 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 mb-3 animate-bounce">
            <AlertTriangle class="h-6 w-6" />
          </div>

          <h4 class="text-sm font-bold text-slate-100">Widget Temporarily Offline</h4>
          <p class="text-xs text-slate-400 mt-1 max-w-sm leading-relaxed">
            A critical rendering error occurred inside this component block.
          </p>

          <!-- Raw Debug Details -->
          <div class="mt-3 max-w-sm w-full bg-slate-900 border border-border/60 rounded-xl p-2.5 text-left overflow-x-auto text-[9px] font-mono text-rose-300">
            <span class="font-bold block text-slate-400 uppercase tracking-wider mb-1 text-[8px]">Logs:</span>
            {{ errorMessage }}
          </div>

          <!-- Recovery Action Button -->
          <button
            @click="handleResetError"
            class="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-900/30 transition-all active:scale-95 cursor-pointer"
          >
            <RefreshCw class="h-3.5 w-3.5" />
            <span>Reinitialize Widget</span>
          </button>
        </div>
      </Transition>

      <!-- Slot Mounting Area -->
      <div v-show="!collapsed" class="w-full h-full p-4 sm:p-5 lg:p-6">
        <!-- The key bind allows a clean mount upon crash retry resets -->
        <slot :key="refreshKey" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
