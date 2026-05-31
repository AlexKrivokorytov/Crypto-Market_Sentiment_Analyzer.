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
    class="bento-card scanline-overlay rounded-lg border border-border/40 flex flex-col transition-all duration-300 relative group select-none h-full overflow-hidden"
    :class="[
      collapsed ? 'h-10 sm:h-10 lg:h-10 shadow-none bg-slate-950/40' : 'shadow-xl',
      hasError ? 'border-alarm/40 bg-alarm-soft' : ''
    ]"
  >
    <!-- Widget Control Header -->
    <header 
      class="h-10 flex items-center justify-between px-3 sm:px-4 border-b border-white/5 shrink-0 select-none bg-white/[0.02]"
    >
      <div class="flex items-center gap-2 min-w-0 z-10">
        <!-- Drag Handle Affordance -->
        <div class="drag-handle text-slate-600 hover:text-slate-400 cursor-grab active:cursor-grabbing p-1 rounded hover:bg-white/5 transition-colors hidden sm:block shrink-0">
          <GripVertical class="h-4 w-4 pointer-events-none" />
        </div>
        
        <!-- Live Glowing Status Dot -->
        <span 
          class="h-1.5 w-1.5 rounded-full shrink-0 transition-all duration-500" 
          :class="[hasError ? 'bg-alarm shadow-[0_0_8px_rgba(255,62,108,0.8)]' : 'bg-signal shadow-[0_0_8px_rgba(0,217,126,0.5)] animate-pulse']"
        ></span>

        <h3 class="text-[11px] sm:text-xs font-bold tracking-widest uppercase font-display text-slate-300 truncate">
          {{ title }}
        </h3>
      </div>

      <!-- Controls Block -->
      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <!-- Collapse Toggle -->
        <button 
          v-if="collapsible"
          @click.stop="handleCollapseToggle"
          class="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-slate-300 transition-colors"
          :title="collapsed ? 'Expand widget' : 'Collapse widget'"
        >
          <ChevronDown v-if="collapsed" class="h-3.5 w-3.5" />
          <ChevronUp v-else class="h-3.5 w-3.5" />
        </button>
        
        <!-- Hide Toggle -->
        <button 
          v-if="hideable"
          @click.stop="$emit('hide')"
          class="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-slate-300 transition-colors"
          title="Hide widget from dashboard"
        >
          <EyeOff class="h-3.5 w-3.5" />
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
