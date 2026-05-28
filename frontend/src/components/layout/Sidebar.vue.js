/// <reference types="../../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAppStore } from '@/composables/useAppStore';
import { useAuthStore } from '@/composables/useAuthStore';
import { useAssets, useBackendConfig } from '@/composables/useMarketData';
import { Activity, Cpu, TrendingDown, TrendingUp } from '@lucide/vue';
import { storeToRefs } from 'pinia';
const router = useRouter();
const route = useRoute();
const store = useAppStore();
const authStore = useAuthStore();
const { sidebarCollapsed, mobileMenuOpen } = storeToRefs(store);
/** The currently active asset ticker, derived from the URL. */
const selectedAssetId = computed(() => route.params.id);
const { data: assets, isLoading } = useAssets();
const { data: config, isLoading: configLoading, isError: configError } = useBackendConfig();
const formatCurrency = (val, symbol) => {
    const options = symbol === 'AAPL'
        ? { minimumFractionDigits: 2, maximumFractionDigits: 2 }
        : { minimumFractionDigits: 0, maximumFractionDigits: 2 };
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', ...options }).format(val);
};
/** Navigates to the selected asset route and closes the mobile Drawer. */
const selectAsset = (assetId) => {
    router.push(`/asset/${assetId}`);
    store.closeMobileMenu();
};
/** Logs out and navigates to the login page. */
function handleLogout() {
    authStore.logout();
    router.push('/login');
    store.closeMobileMenu();
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
    ...{ class: "\u0067\u006c\u0061\u0073\u0073\u002d\u0070\u0061\u006e\u0065\u006c\u0020\u0062\u006f\u0072\u0064\u0065\u0072\u002d\u0072\u0020\u0062\u006f\u0072\u0064\u0065\u0072\u002d\u0062\u006f\u0072\u0064\u0065\u0072\u002f\u0034\u0030\u0020\u0068\u002d\u0073\u0063\u0072\u0065\u0065\u006e\u0020\u0074\u0072\u0061\u006e\u0073\u0069\u0074\u0069\u006f\u006e\u002d\u0061\u006c\u006c\u0020\u0064\u0075\u0072\u0061\u0074\u0069\u006f\u006e\u002d\u0033\u0030\u0030\u0020\u0065\u0061\u0073\u0065\u002d\u0069\u006e\u002d\u006f\u0075\u0074\u0020\u0066\u006c\u0065\u0078\u0020\u0066\u006c\u0065\u0078\u002d\u0063\u006f\u006c\u0020\u007a\u002d\u0034\u0030\u000a\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0066\u0069\u0078\u0065\u0064\u0020\u0069\u006e\u0073\u0065\u0074\u002d\u0079\u002d\u0030\u0020\u006c\u0065\u0066\u0074\u002d\u0030\u0020\u006c\u0067\u003a\u0072\u0065\u006c\u0061\u0074\u0069\u0076\u0065\u0020\u006c\u0067\u003a\u007a\u002d\u0032\u0030" },
    ...{ class: ([
            __VLS_ctx.sidebarCollapsed ? 'lg:w-20' : 'lg:w-72',
            __VLS_ctx.mobileMenuOpen ? 'w-72 translate-x-0' : '-translate-x-full lg:translate-x-0'
        ]) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "h-16 flex items-center px-6 border-b border-border/40 gap-3 overflow-hidden select-none" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center justify-center p-2 rounded-xl bg-primary/10 border border-primary/20 shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.15)]" },
});
const __VLS_0 = {}.Activity;
/** @type {[typeof __VLS_components.Activity, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "h-5 w-5 text-primary animate-pulse" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "h-5 w-5 text-primary animate-pulse" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col transition-all duration-200" },
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "font-extrabold text-sm tracking-wider uppercase bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "text-[10px] text-muted-foreground font-medium tracking-tight" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "px-4 py-3 flex items-center text-xs font-semibold text-muted-foreground tracking-wider uppercase overflow-hidden" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'mx-auto' : 'pl-2']) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex-1 px-3 overflow-y-auto space-y-1" },
});
if (__VLS_ctx.isLoading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "space-y-2 p-2" },
    });
    for (const [i] of __VLS_getVForSourceType((4))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            key: (i),
            ...{ class: "h-14 bg-muted/30 border border-border/30 rounded-xl animate-pulse" },
        });
    }
}
else {
    for (const [asset] of __VLS_getVForSourceType((__VLS_ctx.assets))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isLoading))
                        return;
                    __VLS_ctx.selectAsset(asset.id);
                } },
            key: (asset.id),
            ...{ class: "w-full text-left p-3 rounded-xl flex items-center transition-all duration-200 border group" },
            ...{ class: ([
                    __VLS_ctx.selectedAssetId === asset.id
                        ? 'glass-card border-primary/30 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_0_20px_-5px_rgba(99,102,241,0.15)] text-foreground'
                        : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground'
                ]) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-transform duration-200 group-hover:scale-105" },
            ...{ class: ([
                    __VLS_ctx.selectedAssetId === asset.id
                        ? 'bg-primary/20 text-white border border-primary/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]'
                        : 'bg-muted/50 border border-border/40 text-muted-foreground group-hover:border-border/80'
                ]) },
        });
        (asset.symbol);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "ml-3 flex-1 flex justify-between items-center transition-all duration-200 overflow-hidden" },
            ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex flex-col min-w-0" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "font-semibold text-sm truncate" },
        });
        (asset.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-xs text-muted-foreground truncate" },
        });
        (__VLS_ctx.formatCurrency(asset.price, asset.symbol));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "flex flex-col items-end shrink-0" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[10px] font-bold px-2 py-0.5 rounded-full border shadow-sm transition-all" },
            ...{ class: ([
                    asset.sentimentLabel === 'Bullish'
                        ? 'bg-bullish/10 text-bullish border-bullish/30 shadow-bullish/5'
                        : asset.sentimentLabel === 'Bearish'
                            ? 'bg-bearish/10 text-bearish border-bearish/30 shadow-bearish/5'
                            : 'bg-neutral/10 text-neutral border-neutral/30'
                ]) },
        });
        (asset.sentimentScore);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-[10px] flex items-center font-semibold mt-1" },
            ...{ class: ([asset.change24h >= 0 ? 'text-bullish' : 'text-bearish']) },
        });
        const __VLS_4 = ((asset.change24h >= 0 ? __VLS_ctx.TrendingUp : __VLS_ctx.TrendingDown));
        // @ts-ignore
        const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
            ...{ class: "h-3 w-3 mr-0.5 shrink-0" },
        }));
        const __VLS_6 = __VLS_5({
            ...{ class: "h-3 w-3 mr-0.5 shrink-0" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_5));
        (asset.change24h >= 0 ? '+' : '');
        (asset.change24h);
    }
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "px-3 pb-1" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.router.push('/portfolio');
            __VLS_ctx.store.closeMobileMenu();
        } },
    id: "sidebar-portfolio-link",
    ...{ class: "w-full text-left p-3 rounded-xl flex items-center gap-3 transition-all duration-200 border group" },
    ...{ class: ([
            __VLS_ctx.route.name === 'portfolio'
                ? 'glass-card border-primary/30 text-foreground'
                : 'border-transparent text-muted-foreground hover:bg-muted/30 hover:text-foreground'
        ]) },
    'aria-label': "Go to Portfolio",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "h-9 w-9 rounded-lg flex items-center justify-center font-bold text-xs shrink-0" },
    ...{ class: (__VLS_ctx.route.name === 'portfolio' ? 'bg-primary/20 text-white border border-primary/30' : 'bg-muted/50 border border-border/40 text-muted-foreground') },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
    width: "16",
    height: "16",
    viewBox: "0 0 16 16",
    fill: "none",
    'aria-hidden': "true",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
    d: "M2 5.5h12M2 5.5v7a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-7M2 5.5V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1.5",
    stroke: "currentColor",
    'stroke-width': "1.25",
    'stroke-linecap': "round",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
    d: "M6 3V2.5a2 2 0 0 1 4 0V3",
    stroke: "currentColor",
    'stroke-width': "1.25",
    'stroke-linecap': "round",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "font-semibold text-sm transition-all duration-200" },
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 scale-100']) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "p-4 border-t border-border/40 flex flex-col gap-2 overflow-hidden" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex items-center gap-3" },
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'justify-center' : '']) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border" },
    ...{ class: ([
            __VLS_ctx.configError
                ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                : __VLS_ctx.configLoading
                    ? 'bg-blue-500/10 border-blue-500/20 text-blue-400 animate-pulse'
                    : __VLS_ctx.config?.llm_configured
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
        ]) },
});
const __VLS_8 = {}.Cpu;
/** @type {[typeof __VLS_components.Cpu, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    ...{ class: "h-4 w-4" },
    ...{ class: ([!__VLS_ctx.configError ? 'animate-pulse' : '']) },
}));
const __VLS_10 = __VLS_9({
    ...{ class: "h-4 w-4" },
    ...{ class: ([!__VLS_ctx.configError ? 'animate-pulse' : '']) },
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "flex flex-col min-w-0 transition-all duration-200" },
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'opacity-0 w-0 scale-95 pointer-events-none' : 'opacity-100 w-auto scale-100']) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "text-xs font-semibold text-foreground truncate" },
});
(__VLS_ctx.configError ? 'Server Offline' : __VLS_ctx.configLoading ? 'Connecting...' : (__VLS_ctx.config?.llm_model || 'Simulated Model'));
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "text-[10px] font-medium flex items-center gap-1" },
    ...{ class: ([
            __VLS_ctx.configError
                ? 'text-rose-400'
                : __VLS_ctx.configLoading
                    ? 'text-blue-400'
                    : __VLS_ctx.config?.llm_configured
                        ? 'text-emerald-400'
                        : 'text-amber-400'
        ]) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "h-1.5 w-1.5 rounded-full animate-ping" },
    ...{ class: ([
            __VLS_ctx.configError
                ? 'bg-rose-400'
                : __VLS_ctx.configLoading
                    ? 'bg-blue-400'
                    : __VLS_ctx.config?.llm_configured
                        ? 'bg-emerald-400'
                        : 'bg-amber-400'
        ]) },
});
(__VLS_ctx.configError ? 'Backend Unreachable' : __VLS_ctx.configLoading ? 'Checking API...' : (__VLS_ctx.config?.llm_configured ? 'Live AI Active' : 'Simulation Mode'));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: ([__VLS_ctx.sidebarCollapsed ? 'hidden' : 'block']) },
});
if (__VLS_ctx.authStore.isAuthenticated) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.handleLogout) },
        id: "sidebar-logout-btn",
        ...{ class: "w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-all duration-150" },
        'aria-label': "Log out",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
        width: "14",
        height: "14",
        viewBox: "0 0 14 14",
        fill: "none",
        'aria-hidden': "true",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
        d: "M5.5 2H3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h2.5M9.5 10l2.5-3-2.5-3M12 7H5.5",
        stroke: "currentColor",
        'stroke-width': "1.25",
        'stroke-linecap': "round",
        'stroke-linejoin': "round",
    });
    (__VLS_ctx.authStore.user?.display_name);
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(__VLS_ctx.authStore.isAuthenticated))
                    return;
                __VLS_ctx.router.push('/login');
            } },
        id: "sidebar-login-btn",
        ...{ class: "w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-indigo-400 hover:bg-indigo-500/10 transition-all duration-150" },
        'aria-label': "Sign in",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
        width: "14",
        height: "14",
        viewBox: "0 0 14 14",
        fill: "none",
        'aria-hidden': "true",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
        d: "M8.5 2H11a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H8.5M4.5 10l-2.5-3 2.5-3M2 7h6.5",
        stroke: "currentColor",
        'stroke-width': "1.25",
        'stroke-linecap': "round",
        'stroke-linejoin': "round",
    });
}
/** @type {__VLS_StyleScopedClasses['glass-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['border-r']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border/40']} */ ;
/** @type {__VLS_StyleScopedClasses['h-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-300']} */ ;
/** @type {__VLS_StyleScopedClasses['ease-in-out']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['z-40']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-y-0']} */ ;
/** @type {__VLS_StyleScopedClasses['left-0']} */ ;
/** @type {__VLS_StyleScopedClasses['lg:relative']} */ ;
/** @type {__VLS_StyleScopedClasses['lg:z-20']} */ ;
/** @type {__VLS_StyleScopedClasses['h-16']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['px-6']} */ ;
/** @type {__VLS_StyleScopedClasses['border-b']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border/40']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['select-none']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-primary/10']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-primary/20']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-[0_0_15px_rgba(99,102,241,0.15)]']} */ ;
/** @type {__VLS_StyleScopedClasses['h-5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-5']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['font-extrabold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-wider']} */ ;
/** @type {__VLS_StyleScopedClasses['uppercase']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-gradient-to-r']} */ ;
/** @type {__VLS_StyleScopedClasses['from-white']} */ ;
/** @type {__VLS_StyleScopedClasses['via-slate-200']} */ ;
/** @type {__VLS_StyleScopedClasses['to-indigo-400']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-clip-text']} */ ;
/** @type {__VLS_StyleScopedClasses['text-transparent']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-tight']} */ ;
/** @type {__VLS_StyleScopedClasses['px-4']} */ ;
/** @type {__VLS_StyleScopedClasses['py-3']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['tracking-wider']} */ ;
/** @type {__VLS_StyleScopedClasses['uppercase']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-y-auto']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-1']} */ ;
/** @type {__VLS_StyleScopedClasses['space-y-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['h-14']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-muted/30']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border/30']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-pulse']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['text-left']} */ ;
/** @type {__VLS_StyleScopedClasses['p-3']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['group']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-transform']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['group-hover:scale-105']} */ ;
/** @type {__VLS_StyleScopedClasses['ml-3']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-between']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['items-end']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['px-2']} */ ;
/** @type {__VLS_StyleScopedClasses['py-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['shadow-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['mt-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-3']} */ ;
/** @type {__VLS_StyleScopedClasses['w-3']} */ ;
/** @type {__VLS_StyleScopedClasses['mr-0.5']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['px-3']} */ ;
/** @type {__VLS_StyleScopedClasses['pb-1']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['text-left']} */ ;
/** @type {__VLS_StyleScopedClasses['p-3']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-xl']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['group']} */ ;
/** @type {__VLS_StyleScopedClasses['h-9']} */ ;
/** @type {__VLS_StyleScopedClasses['w-9']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['font-bold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-sm']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['p-4']} */ ;
/** @type {__VLS_StyleScopedClasses['border-t']} */ ;
/** @type {__VLS_StyleScopedClasses['border-border/40']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-3']} */ ;
/** @type {__VLS_StyleScopedClasses['h-8']} */ ;
/** @type {__VLS_StyleScopedClasses['w-8']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['justify-center']} */ ;
/** @type {__VLS_StyleScopedClasses['shrink-0']} */ ;
/** @type {__VLS_StyleScopedClasses['border']} */ ;
/** @type {__VLS_StyleScopedClasses['h-4']} */ ;
/** @type {__VLS_StyleScopedClasses['w-4']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-200']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-semibold']} */ ;
/** @type {__VLS_StyleScopedClasses['text-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['truncate']} */ ;
/** @type {__VLS_StyleScopedClasses['text-[10px]']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-1']} */ ;
/** @type {__VLS_StyleScopedClasses['h-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['w-1.5']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-full']} */ ;
/** @type {__VLS_StyleScopedClasses['animate-ping']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-red-400']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-red-500/10']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-150']} */ ;
/** @type {__VLS_StyleScopedClasses['w-full']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['items-center']} */ ;
/** @type {__VLS_StyleScopedClasses['gap-2']} */ ;
/** @type {__VLS_StyleScopedClasses['p-2']} */ ;
/** @type {__VLS_StyleScopedClasses['rounded-lg']} */ ;
/** @type {__VLS_StyleScopedClasses['text-xs']} */ ;
/** @type {__VLS_StyleScopedClasses['font-medium']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted-foreground']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:text-indigo-400']} */ ;
/** @type {__VLS_StyleScopedClasses['hover:bg-indigo-500/10']} */ ;
/** @type {__VLS_StyleScopedClasses['transition-all']} */ ;
/** @type {__VLS_StyleScopedClasses['duration-150']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Activity: Activity,
            Cpu: Cpu,
            TrendingDown: TrendingDown,
            TrendingUp: TrendingUp,
            router: router,
            route: route,
            store: store,
            authStore: authStore,
            sidebarCollapsed: sidebarCollapsed,
            mobileMenuOpen: mobileMenuOpen,
            selectedAssetId: selectedAssetId,
            assets: assets,
            isLoading: isLoading,
            config: config,
            configLoading: configLoading,
            configError: configError,
            formatCurrency: formatCurrency,
            selectAsset: selectAsset,
            handleLogout: handleLogout,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
