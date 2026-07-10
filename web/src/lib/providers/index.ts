/**
 * Titan cockpit data providers.
 *
 * createProviders({ mode }) returns the active adapter set.
 * Pages should use DataProvider / hooks (useFleet, useHealth, …)
 * so swapping mock → live is one place — not a page rewrite.
 */

export type { TitanProviders } from "./create";
export type {
  DataMode,
  ProviderResult,
  ProviderSource,
  HealthSnapshot,
  FleetSnapshot,
  SigningSnapshot,
  SecuritySnapshot,
  PortfolioSnapshot,
  PipelinesSnapshot,
  ManualControlSnapshot,
  ServiceRow,
  AgentDto,
} from "./types";

export {
  resolveDataMode,
  envDataMode,
  setStoredDataMode,
  readStoredDataMode,
  dataModeLabel,
  DATA_MODE_STORAGE_KEY,
} from "./mode";

export { createProviders, getProviders, resetProviders } from "./create";

export {
  DataProvider,
  useDataMode,
  useHealth,
  useFleet,
  useSigning,
  useSecurityProvider,
  usePortfolioProvider,
  usePipelinesProvider,
  useManualControlProvider,
  advisoryLabel,
} from "./context";
