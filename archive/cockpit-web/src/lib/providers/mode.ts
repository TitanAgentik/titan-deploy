/**
 * Data mode resolution: env VITE_DATA_MODE + optional session override (Settings).
 * Default: mock — safe until real providers are wired.
 */

import type { DataMode } from "./types";

export const DATA_MODE_STORAGE_KEY = "titan.dataMode";

export function envDataMode(): DataMode {
  const raw = (import.meta.env.VITE_DATA_MODE as string | undefined)?.toLowerCase();
  if (raw === "live" || raw === "mock") return raw;
  return "mock";
}

export function readStoredDataMode(): DataMode | null {
  try {
    const v = sessionStorage.getItem(DATA_MODE_STORAGE_KEY);
    if (v === "live" || v === "mock") return v;
  } catch {
    /* ignore */
  }
  return null;
}

/** Effective mode: session override wins over env. */
export function resolveDataMode(): DataMode {
  return readStoredDataMode() ?? envDataMode();
}

export function setStoredDataMode(mode: DataMode | null): void {
  try {
    if (mode === null) {
      sessionStorage.removeItem(DATA_MODE_STORAGE_KEY);
    } else {
      sessionStorage.setItem(DATA_MODE_STORAGE_KEY, mode);
    }
  } catch {
    /* ignore */
  }
}

export function dataModeLabel(mode: DataMode): string {
  return mode === "live" ? "LIVE (API stubs)" : "MOCK (fixtures)";
}
