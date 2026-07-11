/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** mock (default) | live — live uses /api/* stubs with soft-fail to fixtures */
  readonly VITE_DATA_MODE?: "mock" | "live" | string;
  /** Optional absolute API origin; empty = same-origin Vite proxy */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
