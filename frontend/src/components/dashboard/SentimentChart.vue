<script setup lang="ts">
/**
 * SentimentChart — Overlay chart: candlestick price (left Y) + VADER sentiment (right Y).
 *
 * Sprint 5 upgrades:
 * - VADER sentiment line colour changed from indigo to gold (#f59e0b) per design system.
 * - Asset brand colour used for candlestick border and dataZoom handle.
 * - Timeframe quick-select tabs rendered inside the chart header.
 * - Tooltip upgraded with JetBrains Mono font and OHLC formatted by formatPrice.
 * - dataZoom filler colour matches gold accent.
 * - Legend moved inline with header tabs to reduce vertical chrome.
 */

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { computed } from 'vue'
import { useHistoricalData } from '@/composables/useMarketData'
import { useAppStore, type Timeframe } from '@/composables/useAppStore'
import { BarChart2 } from '@lucide/vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import type { RouteAssetId } from '@/types/market'
import { formatPrice, getAssetBrandColor } from '@/composables/useCryptoFormatters'

interface TooltipParam {
  axisValue: string
  seriesName: string
  data: number[]
  value: number
}

// Register ECharts modules
use([
  CanvasRenderer,
  CandlestickChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
])

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
  /** The active chart timeframe selector. */
  timeframe: Timeframe
}>()

const store = useAppStore()

const { data: chartData, isLoading, isError, refetch } = useHistoricalData(
  computed(() => props.assetId),
  computed(() => props.timeframe),
)

const timeframes: Timeframe[] = ['1H', '24H', '7D', '30D']

/** Asset brand colour — used for dataZoom handle and OHLC borders. */
const brandColor = computed(() => getAssetBrandColor(props.assetId))

const chartOption = computed(() => {
  if (!chartData.value || chartData.value.length === 0) return {}

  const color      = brandColor.value
  const timestamps = chartData.value.map(d => d.timestamp)

  // Candlestick format: [open, close, low, high]
  const prices     = chartData.value.map(d => [d.open, d.close, d.low, d.high])
  // Normalise 0–100 to compound VADER scale [−1.0, +1.0]
  const sentiments = chartData.value.map(d => (d.sentimentScore - 50) / 50)

  return {
    backgroundColor: 'transparent',
    grid: {
      left: '4%',
      right: '4%',
      bottom: '14%',
      top: '10%',
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: { backgroundColor: '#1e293b' },
      },
      backgroundColor: 'rgba(10, 12, 24, 0.97)',
      borderColor: 'rgba(245, 158, 11, 0.25)',
      borderWidth: 1,
      textStyle: { color: '#f1f5f9', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' },
      formatter: (params: TooltipParam | TooltipParam[]) => {
        const paramList = Array.isArray(params) ? params : [params]
        let content = `<div style="font-family:'JetBrains Mono',monospace;padding:4px 2px;">
          <div style="font-size:10px;color:#64748b;margin-bottom:6px;">${paramList[0]?.axisValue ?? ''}</div>`

        paramList.forEach((param: TooltipParam) => {
          if (param.seriesName === 'Price') {
            const [, open = 0, close = 0, low = 0, high = 0] = param.data
            const isUp = close >= open
            content += `<div style="display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:4px;">
              <span style="color:#94a3b8;display:flex;align-items:center;gap:6px;">
                <span style="height:8px;width:8px;border-radius:50%;display:inline-block;background:${isUp ? '#10b981' : '#f43f5e'};"></span>
                Close
              </span>
              <span style="font-weight:700;color:${isUp ? '#10b981' : '#f43f5e'}">${formatPrice(close, props.assetId)}</span>
            </div>
            <div style="font-size:10px;color:#475569;margin-bottom:6px;padding-left:14px;">
              O:${formatPrice(open, props.assetId)}&nbsp;&nbsp;H:${formatPrice(high, props.assetId)}&nbsp;&nbsp;L:${formatPrice(low, props.assetId)}
            </div>`
          } else if (param.seriesName === 'VADER Sentiment') {
            const val = param.value
            const vcolor = val > 0 ? '#10b981' : val < 0 ? '#f43f5e' : '#94a3b8'
            const prefix = val > 0 ? '+' : ''
            content += `<div style="display:flex;justify-content:space-between;align-items:center;gap:24px;border-top:1px solid rgba(255,255,255,0.07);padding-top:6px;margin-top:4px;">
              <span style="color:#94a3b8;display:flex;align-items:center;gap:6px;">
                <span style="height:6px;width:12px;border-radius:2px;display:inline-block;background:#f59e0b;opacity:0.8;"></span>
                VADER
              </span>
              <span style="font-weight:700;color:${vcolor}">${prefix}${val.toFixed(2)}</span>
            </div>`
          }
        })

        content += '</div>'
        return content
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.07)' } },
      axisLabel: { color: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
      splitLine: { show: false },
    },
    yAxis: [
      {
        // Left axis: price
        type: 'value',
        scale: true,
        axisLabel: {
          color: '#475569',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          formatter: (value: number) => formatPrice(value, props.assetId),
        },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.07)' } },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
      },
      {
        // Right axis: VADER compound [−1, +1]
        type: 'value',
        min: -1.0,
        max: 1.0,
        position: 'right',
        axisLabel: {
          color: '#475569',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          formatter: (value: number) => {
            const prefix = value > 0 ? '+' : ''
            return `${prefix}${value.toFixed(1)}`
          },
        },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.07)' } },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'inside', start: 40, end: 100 },
      {
        show: true,
        type: 'slider',
        bottom: 0,
        height: 24,
        borderColor: 'transparent',
        backgroundColor: 'rgba(255,255,255,0.02)',
        fillerColor: 'rgba(245,158,11,0.08)',
        dataBackground: {
          lineStyle: { color: color, width: 1 },
          areaStyle: { color: `${color}08` },
        },
        selectedDataBackground: {
          lineStyle: { color: color, width: 1.5 },
          areaStyle: { color: `${color}14` },
        },
        handleStyle: { color, borderColor: 'rgba(255,255,255,0.12)' },
        textStyle: { color: '#475569', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
      },
    ],
    series: [
      {
        name: 'Price',
        type: 'candlestick',
        data: prices,
        itemStyle: {
          color: '#10b981',
          color0: '#f43f5e',
          borderColor: '#10b981',
          borderColor0: '#f43f5e',
        },
        large: true,
      },
      {
        name: 'VADER Sentiment',
        type: 'line',
        yAxisIndex: 1,
        data: sentiments,
        smooth: 0.4,
        showSymbol: false,
        lineStyle: {
          // Sprint 5: gold replaces indigo for VADER line
          color: '#f59e0b',
          width: 2,
        },
        markLine: {
          silent: true,
          symbol: 'none',
          label: { show: false },
          data: [
            {
              yAxis: 0,
              lineStyle: { color: 'rgba(255,255,255,0.12)', type: 'dashed', width: 1 },
            },
          ],
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245,158,11,0.20)' },
              { offset: 1, color: 'rgba(245,158,11,0.00)' },
            ],
          },
        },
      },
    ],
  }
})
</script>

<template>
  <div class="glass-card p-4 sm:p-5 rounded-3xl border border-border/40 flex flex-col h-full w-full relative overflow-hidden group">
    <!-- Abstract gradient mesh for modern 2026 aesthetic -->
    <div 
      class="absolute inset-0 opacity-[0.08] pointer-events-none transition-opacity duration-1000 group-hover:opacity-[0.15]"
      :style="`background: radial-gradient(circle at top right, ${brandColor}, transparent 60%); mix-blend-mode: screen;`"
      aria-hidden="true"
    />

    <!-- ── Header row: title + timeframe tabs ────────────────────────── -->
    <!-- ── Header row: title + timeframe tabs ────────────────────────── -->
    <div class="flex items-center justify-between mb-4 shrink-0 gap-3 relative z-10">
      <div class="flex items-center gap-2 select-none min-w-0">
        <div
          class="p-2 rounded-lg border shrink-0"
          :style="{
            background: `${brandColor}15`,
            borderColor: `${brandColor}30`,
          }"
          aria-hidden="true"
        >
          <BarChart2 class="h-4 w-4" :style="{ color: brandColor }" />
        </div>
        <div class="min-w-0">
          <h2 class="text-sm font-bold text-foreground font-display">Overlay Chart</h2>
          <p class="text-[10px] text-muted-foreground font-semibold hidden sm:block">
            Candlestick Price · VADER Sentiment [−1.0, +1.0]
          </p>
        </div>
      </div>

      <!-- Inline timeframe tabs (echo what Header does but scoped to chart) -->
      <nav
        class="flex p-0.5 bg-muted/60 border border-border/60 rounded-xl shrink-0"
        aria-label="Chart timeframe"
      >
        <button
          v-for="tf in timeframes"
          :key="tf"
          :id="`chart-timeframe-${tf}`"
          @click="store.setTimeframe(tf)"
          class="px-2 py-1 rounded-lg text-[10px] font-bold transition-all duration-200"
          :class="[
            props.timeframe === tf
              ? 'text-white shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/40',
          ]"
          :style="props.timeframe === tf
            ? { background: '#f59e0b', boxShadow: '0 0 10px rgba(245,158,11,0.28)' }
            : {}"
          :aria-pressed="props.timeframe === tf"
          :aria-label="`View ${tf} chart`"
        >
          {{ tf }}
        </button>
      </nav>
    </div>

    <!-- ── Mini indicator row ─────────────────────────────────────────── -->
    <!-- ── Mini indicator row ─────────────────────────────────────────── -->
    <div class="hidden sm:flex items-center gap-4 text-xs font-semibold mb-3 shrink-0 relative z-10">
      <span class="flex items-center gap-1.5 text-muted-foreground">
        <span class="h-2 w-2 rounded bg-bullish" aria-hidden="true" />
        Bullish candle
      </span>
      <span class="flex items-center gap-1.5 text-muted-foreground">
        <span class="h-2 w-2 rounded bg-bearish" aria-hidden="true" />
        Bearish candle
      </span>
      <span class="flex items-center gap-1.5 text-muted-foreground">
        <span class="h-0.5 w-5 rounded-full bg-gold" aria-hidden="true" />
        VADER line
      </span>
    </div>

    <!-- ── Chart canvas ──────────────────────────────────────────────── -->
    <!-- ── Chart canvas ──────────────────────────────────────────────── -->
    <div class="flex-1 min-h-0 relative z-10">
      <!-- Loading state -->
      <div
        v-if="isLoading"
        class="absolute inset-0 flex items-center justify-center bg-background/20 rounded-2xl"
        aria-live="polite"
        aria-label="Loading chart data"
      >
        <div class="flex flex-col items-center gap-2">
          <div
            class="h-10 w-10 border-4 border-t-transparent rounded-full animate-spin"
            :style="{ borderColor: `${brandColor}40`, borderTopColor: 'transparent' }"
            aria-hidden="true"
          />
          <span class="text-xs font-semibold text-muted-foreground">Loading datasets…</span>
        </div>
      </div>

      <ErrorState
        v-else-if="isError"
        title="Chart data unavailable"
        description="Historical price data is temporarily unavailable."
        :on-retry="() => refetch()"
      />

      <v-chart
        v-else
        :option="chartOption"
        class="w-full h-full"
        autoresize
        aria-label="Price and VADER sentiment overlay chart"
      />
    </div>
  </div>
</template>
