/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_API_TIMEOUT_MS?: string
  readonly VITE_LLM_MODEL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<
    Record<string, unknown>,
    Record<string, unknown>,
    unknown
  >
  export default component
}
