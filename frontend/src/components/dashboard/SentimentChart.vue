<script setup lang="ts">
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { computed } from 'vue'
import { useHistoricalData } from '@/composables/useMarketData'
import { BarChart2 } from '@lucide/vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import type { RouteAssetId } from '@/types/market'
import type { Timeframe } from '@/composables/useAppStore'

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
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
])

const props = defineProps<{
  /** The asset ticker ID derived from the current route parameter. */
  assetId: RouteAssetId
  /** The active chart timeframe selector. */
  timeframe: Timeframe
}>()

const { data: chartData, isLoading, isError, refetch } = useHistoricalData(
  computed(() => props.assetId),
  computed(() => props.timeframe),
)



const chartOption = computed(() => {
  if (!chartData.value || chartData.value.length === 0) return {}

  const timestamps = chartData.value.map(d => d.timestamp)
  
  // Candlestick data format: [open, close, low, high]
  const prices = chartData.value.map(d => [d.open, d.close, d.low, d.high])
  const sentiments = chartData.value.map(d => d.sentimentScore)

  return {
    backgroundColor: 'transparent',
    grid: {
      left: '4%',
      right: '4%',
      bottom: '12%',
      top: '12%',
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#1e293b'
        }
      },
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.08)',
      textStyle: {
        color: '#f1f5f9',
        fontSize: 12
      },
      formatter: (params: TooltipParam | TooltipParam[]) => {
        const paramList = Array.isArray(params) ? params : [params]
        let content = `<div class="font-sans p-1">
          <div class="font-bold text-slate-400 mb-1.5">${paramList[0]?.axisValue ?? ''}</div>`
        
        paramList.forEach((param: TooltipParam) => {
          if (param.seriesName === 'Price') {
            const [, open = 0, close = 0, low = 0, high = 0] = param.data
            content += `<div class="flex justify-between items-center gap-6 mb-1">
              <span class="text-slate-400 flex items-center gap-1.5">
                <span class="h-2 w-2 rounded-full" style="background-color: ${close >= open ? '#10b981' : '#f43f5e'}"></span>
                Price:
              </span>
              <span class="font-mono font-bold">$${close.toLocaleString()}</span>
            </div>
            <div class="text-[10px] text-slate-500 font-mono pl-3.5 mb-1.5">
              O: $${open} &nbsp; H: $${high} &nbsp; L: $${low} &nbsp; C: $${close}
            </div>`
          } else if (param.seriesName === 'LLM Sentiment') {
            const color = param.value >= 60 ? '#10b981' : param.value <= 40 ? '#f43f5e' : '#94a3b8';
            content += `<div class="flex justify-between items-center gap-6 border-t border-slate-800 pt-1.5 mt-1.5">
              <span class="text-slate-400">LLM Sentiment:</span>
              <span class="font-mono font-bold" style="color: ${color}">${param.value}/100</span>
            </div>`
          }
        })
        
        content += '</div>'
        return content
      }
    },
    legend: {
      data: ['Price', 'LLM Sentiment'],
      textStyle: {
        color: '#94a3b8',
        fontWeight: 'bold',
        fontSize: 11
      },
      top: 0,
      right: '4%'
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.08)'
        }
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace'
      },
      splitLine: {
        show: false
      }
    },
    yAxis: [
      {
        type: 'value',
        scale: true,
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontFamily: 'monospace',
          formatter: (value: number) => `$${value.toLocaleString()}`
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.08)'
          }
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.03)'
          }
        }
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        position: 'right',
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontFamily: 'monospace',
          formatter: '{value}%'
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 255, 255, 0.08)'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 40,
        end: 100
      },
      {
        show: true,
        type: 'slider',
        bottom: 0,
        borderColor: 'transparent',
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        fillerColor: 'rgba(99, 102, 241, 0.1)',
        dataBackground: {
          lineStyle: {
            color: '#6366f1',
            width: 1
          },
          areaStyle: {
            color: 'rgba(99, 102, 241, 0.03)'
          }
        },
        selectedDataBackground: {
          lineStyle: {
            color: '#6366f1',
            width: 1.5
          },
          areaStyle: {
            color: 'rgba(99, 102, 241, 0.1)'
          }
        },
        handleStyle: {
          color: '#4f46e5',
          borderColor: 'rgba(255, 255, 255, 0.1)'
        },
        textStyle: {
          color: '#64748b',
          fontFamily: 'monospace'
        }
      }
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
          borderColor0: '#f43f5e'
        }
      },
      {
        name: 'LLM Sentiment',
        type: 'line',
        yAxisIndex: 1,
        data: sentiments,
        smooth: true,
        showSymbol: false,
        lineStyle: {
          color: '#6366f1',
          width: 2,
          type: 'dashed'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.25)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.0)' }
            ]
          }
        }
      }
    ]
  }
})
</script>

<template>
  <div class="glass-card p-6 rounded-3xl border border-border/40 flex flex-col h-[320px] sm:h-[400px] lg:h-[480px]">
    <div class="flex items-center justify-between mb-4 shrink-0">
      <div class="flex items-center gap-2 select-none">
        <div class="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <BarChart2 class="h-4.5 w-4.5" />
        </div>
        <div>
          <h2 class="text-sm font-bold text-foreground">Interactive Overlay Chart</h2>
          <p class="text-[10px] text-muted-foreground font-semibold">Candlestick Price overlaid with LLM Sentiment Score</p>
        </div>
      </div>

      <!-- Mini Chart Indicators -->
      <div class="hidden sm:flex items-center gap-4 text-xs font-semibold">
        <span class="flex items-center gap-1 text-muted-foreground">
          <span class="h-2 w-2 rounded bg-bullish"></span> Up Price
        </span>
        <span class="flex items-center gap-1 text-muted-foreground">
          <span class="h-2 w-2 rounded bg-bearish"></span> Down Price
        </span>
        <span class="flex items-center gap-1 text-muted-foreground">
          <span class="h-0.5 w-4 bg-primary border-t border-dashed border-primary"></span> LLM Index
        </span>
      </div>
    </div>

    <!-- Chart Wrapper -->
    <div class="flex-1 min-h-0 relative">
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-background/20 rounded-2xl animate-pulse">
        <div class="flex flex-col items-center gap-2">
          <div class="h-10 w-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span class="text-xs font-semibold text-muted-foreground">Loading overlay datasets...</span>
        </div>
      </div>

      <ErrorState
        v-else-if="isError"
        title="Failed to load chart data"
        description="Historical price data is temporarily unavailable."
        :on-retry="() => refetch()"
      />

      <v-chart v-else :option="chartOption" class="w-full h-full" autoresize />
    </div>
  </div>
</template>

