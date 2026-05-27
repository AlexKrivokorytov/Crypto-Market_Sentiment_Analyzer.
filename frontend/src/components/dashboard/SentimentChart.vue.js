/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components';
import VChart from 'vue-echarts';
import { computed } from 'vue';
import { useAppStore } from '@/composables/useAppStore';
import { useHistoricalData } from '@/composables/useMarketData';
import { storeToRefs } from 'pinia';
import { BarChart2 } from '@lucide/vue';
// Register ECharts modules
use([
    CanvasRenderer,
    CandlestickChart,
    BarChart,
    LineChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    DataZoomComponent
]);
const store = useAppStore();
const { selectedAssetId, timeframe } = storeToRefs(store);
const { data: chartData, isLoading } = useHistoricalData(selectedAssetId, timeframe);
const chartOption = computed(() => {
    if (!chartData.value || chartData.value.length === 0)
        return {};
    const timestamps = chartData.value.map(d => d.timestamp);
    // Candlestick data format: [open, close, low, high]
    const prices = chartData.value.map(d => [d.open, d.close, d.low, d.high]);
    const sentiments = chartData.value.map(d => d.sentimentScore);
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
            formatter: (params) => {
                let content = `<div class="font-sans p-1">
          <div class="font-bold text-slate-400 mb-1.5">${params[0].axisValue}</div>`;
                params.forEach((param) => {
                    if (param.seriesName === 'Price') {
                        const data = param.data; // [index, open, close, low, high]
                        content += `<div class="flex justify-between items-center gap-6 mb-1">
              <span class="text-slate-400 flex items-center gap-1.5">
                <span class="h-2 w-2 rounded-full" style="background-color: ${data[2] >= data[1] ? '#10b981' : '#f43f5e'}"></span>
                Price:
              </span>
              <span class="font-mono font-bold">$${data[2].toLocaleString()}</span>
            </div>
            <div class="text-[10px] text-slate-500 font-mono pl-3.5 mb-1.5">
              O: $${data[1]} &nbsp; H: $${data[4]} &nbsp; L: $${data[3]} &nbsp; C: $${data[2]}
            </div>`;
                    }
                    else if (param.seriesName === 'LLM Sentiment') {
                        const color = param.value >= 60 ? '#10b981' : param.value <= 40 ? '#f43f5e' : '#94a3b8';
                        content += `<div class="flex justify-between items-center gap-6 border-t border-slate-800 pt-1.5 mt-1.5">
              <span class="text-slate-400">LLM Sentiment:</span>
              <span class="font-mono font-bold" style="color: ${color}">${param.value}/100</span>
            </div>`;
                    }
                });
                content += '</div>';
                return content;
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
                    formatter: (value) => `$${value.toLocaleString()}`
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
    };
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "glass-card p-6 rounded-3xl border border-border/40 flex flex-col h-[480px]" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center justify-between mb-4 shrink-0" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-2 select-none" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400" },
});
const __VLS_0 = {}.BarChart2;
/** @type {[typeof __VLS_components.BarChart2, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "h-4.5 w-4.5" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "h-4.5 w-4.5" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
    ...{ class: "text-sm font-bold text-foreground" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "text-[10px] text-muted-foreground font-semibold" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-4 text-xs font-semibold" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "flex items-center gap-1 text-muted-foreground" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "h-2 w-2 rounded bg-bullish" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "flex items-center gap-1 text-muted-foreground" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "h-2 w-2 rounded bg-bearish" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "flex items-center gap-1 text-muted-foreground" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "h-0.5 w-4 bg-primary border-t border-dashed border-primary" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex-1 min-h-0 relative" },
});
if (__VLS_ctx.isLoading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "absolute inset-0 flex items-center justify-center bg-background/20 rounded-2xl animate-pulse" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex flex-col items-center gap-2" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "h-10 w-10 border-4 border-primary border-t-transparent rounded-full animate-spin" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "text-xs font-semibold text-muted-foreground" },
    });
}
else {
    const __VLS_4 = {}.VChart;
    /** @type {[typeof __VLS_components.VChart, typeof __VLS_components.vChart, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        option: (__VLS_ctx.chartOption),
        ...{ class: "w-full h-full" },
        autoresize: true,
    }));
    const __VLS_6 = __VLS_5({
        option: (__VLS_ctx.chartOption),
        ...{ class: "w-full h-full" },
        autoresize: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
}
/** @type {__VLS_StyleScopedClasses['glass-card']} */ ;
/** @type {__VLS_StyleScopedClasses['p-6']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-3xl']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border/40']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['h-[480px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-between']} */ ;
/** @type {__VLS_StyleScopedClasses['mb-4']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-indigo-500/10']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-indigo-500/20']} */ ;
/** @type {__VLS_StyleScopedClasses['text-indigo-400']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4.5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-4.5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-4']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-bullish']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['h-2']} */ ;
/** @type {__VLS_StyleScopedClasses['w-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-bearish']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['h-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-4']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-dashed']} */ ;
/** @type {__VLS_StyleScopedClasses['border-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['min-h-0']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
/** @type {__VLS_StyleScopedClasses['absolute']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-background/20']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-2xl']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['h-10']} */ ;
/** @type {__VLS_StyleScopedClasses['w-10']} */ ;
/** @type {__VLS_StyleScopedClasses['border-4']} */ ;
/** @type {__VLS_StyleScopedClasses['border-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-spin']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            VChart: VChart,
            BarChart2: BarChart2,
            isLoading: isLoading,
            chartOption: chartOption,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
