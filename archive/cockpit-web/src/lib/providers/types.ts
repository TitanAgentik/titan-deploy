/**
 * Shared DTOs for the cockpit data-provider seam.
 * Mock adapters return these from fixtures; live adapters map /api/* JSON into the same shapes.
 */

export type DataMode = "mock" | "live";

export type ProviderSource = "mock" | "live";

/** Soft-fail envelope — live stubs never throw into the UI. */
export type ProviderResult<T> = {
  data: T;
  source: ProviderSource;
  /** True when data is fixture / advisory (not authoritative live capital). */
  advisory: boolean;
  error?: string;
  fetchedAt: string;
};

export type ServiceRow = {
  name: string;
  port: number | null;
  ok: boolean;
  /** in_process | http_daemon | safety_unit */
  kind?: "safety_unit" | "in_process" | "optional_legacy";
  note?: string;
};

export type HealthOverall = "ok" | "degraded" | "halted" | "unreachable";

export type HealthSnapshot = {
  overall: HealthOverall;
  reachable: boolean;
  services: ServiceRow[];
  /** Optional legacy HTTP signing_node — never required for health PASS. */
  optionalLegacySigning: ServiceRow;
  inProcessSigning: ServiceRow;
};

export type AgentRunStatus = "UP" | "DOWN" | "DORMANT" | "IDLE";
export type AgentTierKey = "1" | "2" | "3a" | "U";
export type AgentRoleFamily =
  | "orch"
  | "risk"
  | "signal"
  | "exec"
  | "research"
  | "utility"
  | "operator";

export type AgentDto = {
  id: string;
  role: string;
  tier: string;
  tierKey: AgentTierKey;
  port: string;
  model: string;
  roleFamily: AgentRoleFamily;
  status: string;
  runStatus: AgentRunStatus;
  load: number;
  priority: number;
  slotWeight: number;
  capabilities: string[];
  pipelines: string[];
  skills: string[];
  lastHeartbeatAt: string;
  lastActivity: string;
  confidence: number;
  bftRole?: "trade_voter" | "orch_voter" | "veto";
  notes?: string;
};

export type FleetSnapshot = {
  /** Classical fleet size — always 20 (no QCC/QSA/QRP). */
  total: number;
  agents: AgentDto[];
  byStatus: Record<AgentRunStatus, number>;
  byTier: { t1: number; t2: number; t3a: number; u: number };
  tradeVoters: { id: string; vote: string; signed: boolean; note: string }[];
  bftThreshold: string;
  authoritativeGate: string;
};

export type SigningSnapshot = {
  mode: "in_process";
  daemonRequired: false;
  optionalLegacyPort: 19010;
  receiptTtlSec: number;
  blindSign: "REJECTED";
  liveSignerRequired: boolean;
  halted: boolean;
  audit: { ts: string; action: string; code: string; trade: string }[];
};

export type SecuritySnapshot = {
  overall: string;
  threatLevel: string;
  live: boolean;
  huntMode?: boolean;
  honeypotArmed?: boolean;
  pcrDrift?: boolean;
  signingHalted?: boolean;
  killActive?: boolean;
  evolutionFrozen?: boolean;
  pillars?: Record<string, string>;
  layers?: { id: string; name: string; port: string; status: string }[];
  error?: string;
};

export type PortfolioSnapshot = {
  equityUsd: number;
  availableUsd: number;
  drawdownPct: number;
  capitalProfile: string;
  killActive: boolean;
  evolutionFrozen: boolean;
  dmsHoursSinceHeartbeat: number;
};

export type PipelineDto = {
  id: string;
  name: string;
  phase: string;
  edge: string;
  memecoin?: boolean;
  flash?: boolean;
};

export type PipelinesSnapshot = {
  catalog: PipelineDto[];
  maxFundedHealthy: number;
  dexOnly: true;
};

export type ManualControlSnapshot = {
  overallPosture: string;
  tradingHalted: boolean;
  killActive: boolean;
  signingHalted: boolean;
  capitalProfile: string;
  equityUsd: number;
  availableUsd: number;
  drawdownPct: number;
  quantumEnabled: false;
  quantumAgentsRemoved: true;
  agentCount: 20;
  honeypotArmed: boolean;
  huntMode: boolean;
  promotionHold: boolean;
  bftPosture: string;
  controlPlaneServices: ServiceRow[];
};
