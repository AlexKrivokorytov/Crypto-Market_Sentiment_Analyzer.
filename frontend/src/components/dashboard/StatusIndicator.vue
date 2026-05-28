<script setup lang="ts">
import { computed } from 'vue'
import type { ConnectionStatus } from '../../composables/useWebSocketManager'

const props = defineProps<{
  status: ConnectionStatus
  reconnectCount: number
}>()

const statusClasses = computed(() => {
  switch (props.status) {
    case 'CONNECTED':
      return {
        bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        dot: 'bg-emerald-500 shadow-emerald-500/50 animate-pulse',
        label: 'Live Stream'
      }
    case 'CONNECTING':
      return {
        bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        dot: 'bg-amber-500 shadow-amber-500/50 animate-ping',
        label: 'Connecting'
      }
    case 'RECONNECTING':
      return {
        bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
        dot: 'bg-rose-500 shadow-rose-500/50 animate-ping',
        label: `Reconnecting (${props.reconnectCount})`
      }
    case 'DISCONNECTED':
    default:
      return {
        bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        dot: 'bg-slate-500 shadow-slate-500/20',
        label: 'Offline'
      }
  }
})
</script>

<template>
  <div
    class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold backdrop-blur-md transition-all duration-300 select-none"
    :class="statusClasses.bg"
  >
    <span class="relative flex h-2 w-2">
      <span
        class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
        :class="statusClasses.dot"
      ></span>
      <span
        class="relative inline-flex rounded-full h-2 w-2"
        :class="statusClasses.dot.replace('animate-ping', '').replace('animate-pulse', '')"
      ></span>
    </span>
    <span>{{ statusClasses.label }}</span>
  </div>
</template>
