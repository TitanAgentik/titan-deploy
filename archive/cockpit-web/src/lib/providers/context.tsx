/**
 * React context + hooks for cockpit data providers.
 */

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createProviders, resetProviders } from "./create";
import {
  resolveDataMode,
  setStoredDataMode,
} from "./mode";
import type { DataMode } from "./types";
import type { TitanProviders } from "./mock";
import type {
  FleetSnapshot,
  HealthSnapshot,
  ManualControlSnapshot,
  PipelinesSnapshot,
  PortfolioSnapshot,
  ProviderResult,
  SecuritySnapshot,
  SigningSnapshot,
} from "./types";

type ProviderContextValue = {
  mode: DataMode;
  setMode: (mode: DataMode) => void;
  providers: TitanProviders;
};

const ProviderContext = createContext<ProviderContextValue | null>(null);

export function DataProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<DataMode>(() => resolveDataMode());

  const setMode = useCallback((next: DataMode) => {
    setStoredDataMode(next);
    resetProviders();
    setModeState(next);
  }, []);

  const providers = useMemo(() => createProviders({ mode }), [mode]);

  const value = useMemo(
    () => ({ mode, setMode, providers }),
    [mode, setMode, providers],
  );

  return createElement(ProviderContext.Provider, { value }, children);
}

export function useDataMode(): ProviderContextValue {
  const ctx = useContext(ProviderContext);
  if (!ctx) {
    throw new Error("useDataMode requires <DataProvider>");
  }
  return ctx;
}

function useProviderQuery<T>(
  loader: (p: TitanProviders) => Promise<ProviderResult<T>>,
): {
  result: ProviderResult<T> | null;
  loading: boolean;
  refresh: () => Promise<ProviderResult<T>>;
} {
  const { providers, mode } = useDataMode();
  const [result, setResult] = useState<ProviderResult<T> | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await loader(providers);
      setResult(r);
      return r;
    } finally {
      setLoading(false);
    }
  }, [providers, loader]);

  useEffect(() => {
    void refresh();
  }, [refresh, mode]);

  return { result, loading, refresh };
}

export function useHealth() {
  const loader = useCallback((p: TitanProviders) => p.getHealth(), []);
  return useProviderQuery<HealthSnapshot>(loader);
}

export function useFleet() {
  const loader = useCallback((p: TitanProviders) => p.getFleet(), []);
  return useProviderQuery<FleetSnapshot>(loader);
}

export function useSigning() {
  const loader = useCallback((p: TitanProviders) => p.getSigning(), []);
  return useProviderQuery<SigningSnapshot>(loader);
}

export function useSecurityProvider() {
  const loader = useCallback((p: TitanProviders) => p.getSecurity(), []);
  return useProviderQuery<SecuritySnapshot>(loader);
}

export function usePortfolioProvider() {
  const loader = useCallback((p: TitanProviders) => p.getPortfolio(), []);
  return useProviderQuery<PortfolioSnapshot>(loader);
}

export function usePipelinesProvider() {
  const loader = useCallback((p: TitanProviders) => p.getPipelines(), []);
  return useProviderQuery<PipelinesSnapshot>(loader);
}

export function useManualControlProvider() {
  const loader = useCallback((p: TitanProviders) => p.getManualControl(), []);
  return useProviderQuery<ManualControlSnapshot>(loader);
}

/** Small advisory chip for pages still on fixtures. */
export function advisoryLabel(result: ProviderResult<unknown> | null): string {
  if (!result) return "…";
  if (result.error) return `ADVISORY · ${result.source} fallback`;
  if (result.advisory || result.source === "mock") return "ADVISORY · mock";
  return "LIVE";
}
