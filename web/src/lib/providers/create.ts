/**
 * Factory + singleton — kept separate from context to avoid circular imports.
 */

import { resolveDataMode } from "./mode";
import { mockProviders, type TitanProviders } from "./mock";
import { liveProviders } from "./live";
import type { DataMode } from "./types";

export type { TitanProviders };

export function createProviders(opts?: { mode?: DataMode }): TitanProviders {
  const mode = opts?.mode ?? resolveDataMode();
  return mode === "live" ? liveProviders : mockProviders;
}

let _providers: TitanProviders | null = null;
let _mode: DataMode | null = null;

export function getProviders(): TitanProviders {
  const mode = resolveDataMode();
  if (!_providers || _mode !== mode) {
    _providers = createProviders({ mode });
    _mode = mode;
  }
  return _providers;
}

export function resetProviders(): void {
  _providers = null;
  _mode = null;
}
