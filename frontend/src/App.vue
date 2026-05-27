<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import MetricsPanel from '@/components/dashboard/MetricsPanel.vue'
import SentimentChart from '@/components/dashboard/SentimentChart.vue'
import LiveFeed from '@/components/dashboard/LiveFeed.vue'
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#05070f] text-slate-100 font-sans">
    <!-- Sidebar Left -->
    <Sidebar />

    <!-- Main Content Right -->
    <div class="flex-1 flex flex-col min-w-0 h-full relative">
      <!-- Header Top -->
      <Header />

      <!-- Scrollable Workspace -->
      <main class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Banner Title Info -->
        <div class="flex flex-col gap-1 select-none">
          <h1 class="text-xl sm:text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
            Market Intelligence Center
          </h1>
          <p class="text-xs text-slate-400 font-medium">
            Aggregated orderbook quotes overlaid with real-time LLM-processed sentiment metrics.
          </p>
        </div>

        <!-- Metrics Grid (Row 1) -->
        <MetricsPanel />

        <!-- Chart and Live Feed Grid (Row 2) -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          <!-- Interactive ECharts Overlay (2/3 width) -->
          <div class="lg:col-span-2 flex flex-col">
            <SentimentChart />
          </div>

          <!-- Live Sentiment Feed (1/3 width) -->
          <div class="lg:col-span-1 flex flex-col h-[550px] lg:h-[480px]">
            <LiveFeed />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
