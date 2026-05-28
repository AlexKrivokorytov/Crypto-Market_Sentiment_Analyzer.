/// <reference types="../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { onErrorCaptured } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import Sidebar from '@/components/layout/Sidebar.vue';
import Header from '@/components/layout/Header.vue';
import { useAppStore } from '@/composables/useAppStore';
import { storeToRefs } from 'pinia';
const store = useAppStore();
const { mobileMenuOpen } = storeToRefs(store);
const route = useRoute();
/**
 * Auth and portfolio routes use a full-page layout without the sidebar and header.
 * Login and Register routes have requiresGuest meta; portfolio has requiresAuth meta.
 */
const isFullPage = computed(() => !!(route.meta.requiresGuest || route.name === 'portfolio'));
/**
 * Global error boundary. Catches any unhandled render errors from child
 * components, logs them with context, and returns false to prevent Vue
 * from propagating the error up and crashing the entire tree.
 */
onErrorCaptured((error, instance, info) => {
    console.error('[App] Unhandled render error:', { message: error.message, info, instance });
    return false;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
if (__VLS_ctx.isFullPage) {
    const __VLS_0 = {}.RouterView;
    /** @type {[typeof __VLS_components.RouterView, ]} */ ;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({}));
    const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex h-screen w-screen overflow-hidden bg-[#05070f] text-slate-100 font-sans" },
    });
    /** @type {[typeof Sidebar, ]} */ ;
    // @ts-ignore
    const __VLS_4 = __VLS_asFunctionalComponent(Sidebar, new Sidebar({}));
    const __VLS_5 = __VLS_4({}, ...__VLS_functionalComponentArgsRest(__VLS_4));
    const __VLS_7 = {}.Transition;
    /** @type {[typeof __VLS_components.Transition, typeof __VLS_components.Transition, ]} */ ;
    // @ts-ignore
    const __VLS_8 = __VLS_asFunctionalComponent(__VLS_7, new __VLS_7({
        name: "fade",
    }));
    const __VLS_9 = __VLS_8({
        name: "fade",
    }, ...__VLS_functionalComponentArgsRest(__VLS_8));
    __VLS_10.slots.default;
    if (__VLS_ctx.mobileMenuOpen) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
            ...{ onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.isFullPage))
                        return;
                    if (!(__VLS_ctx.mobileMenuOpen))
                        return;
                    __VLS_ctx.store.closeMobileMenu();
                } },
            ...{ class: "fixed inset-0 bg-black/60 z-30 lg:hidden" },
            'aria-hidden': "true",
        });
    }
    var __VLS_10;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "flex-1 flex flex-col min-w-0 h-full relative" },
    });
    /** @type {[typeof Header, ]} */ ;
    // @ts-ignore
    const __VLS_11 = __VLS_asFunctionalComponent(Header, new Header({}));
    const __VLS_12 = __VLS_11({}, ...__VLS_functionalComponentArgsRest(__VLS_11));
    const __VLS_14 = {}.RouterView;
    /** @type {[typeof __VLS_components.RouterView, ]} */ ;
    // @ts-ignore
    const __VLS_15 = __VLS_asFunctionalComponent(__VLS_14, new __VLS_14({}));
    const __VLS_16 = __VLS_15({}, ...__VLS_functionalComponentArgsRest(__VLS_15));
}
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['h-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['w-screen']} */ ;
/** @type {__VLS_StyleScopedClasses['overflow-hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-[#05070f]']} */ ;
/** @type {__VLS_StyleScopedClasses['text-slate-100']} */ ;
/** @type {__VLS_StyleScopedClasses['font-sans']} */ ;
/** @type {__VLS_StyleScopedClasses['fixed']} */ ;
/** @type {__VLS_StyleScopedClasses['inset-0']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-black/60']} */ ;
/** @type {__VLS_StyleScopedClasses['z-30']} */ ;
/** @type {__VLS_StyleScopedClasses['lg:hidden']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-1']} */ ;
/** @type {__VLS_StyleScopedClasses['flex']} */ ;
/** @type {__VLS_StyleScopedClasses['flex-col']} */ ;
/** @type {__VLS_StyleScopedClasses['min-w-0']} */ ;
/** @type {__VLS_StyleScopedClasses['h-full']} */ ;
/** @type {__VLS_StyleScopedClasses['relative']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            RouterView: RouterView,
            Sidebar: Sidebar,
            Header: Header,
            store: store,
            mobileMenuOpen: mobileMenuOpen,
            isFullPage: isFullPage,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
