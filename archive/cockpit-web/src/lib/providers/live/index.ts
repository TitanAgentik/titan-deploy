/**
 * Live adapters — call Vite-proxied /api/* surfaces.
 * Soft-fail: on error, fall back to mock fixtures with advisory=true + error string.
 *
 * TODO when wiring real providers:
 * - Map status-agg /health JSON → HealthSnapshot
 * - Map agent registry / fleet endpoint → FleetSnapshot (20 classical agents)
 * - Map signing status from titan-safety control plane (in-process; NOT :19010)
 * - Prefer VITE_API_BASE if set (absolute origin); else relative /api/*
 */

import { fetchSecurityPosture } from "@/lib/securityApi";
import { fetchJson, nowIso } from "../http";
import { mockProviders } from "../mock";
import type {
  FleetSnapshot,
  HealthSnapshot,
  ManualControlSnapshot,
  PipelinesSnapshot,
  PortfolioSnapshot,
  ProviderResult,
  SecuritySnapshot,
  ServiceRow,
  SigningSnapshot,
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

function api(path: string): string {
  return `${API_BASE}${path}`;
}

function softFail<T>(
  fallback: ProviderResult<T>,
  error: string,
): ProviderResult<T> {
  return {
    ...fallback,
    source: "live",
    advisory: true,
    error,
    fetchedAt: nowIso(),
  };
}

const SERVICE_PORT: Record<string, number> = {
  risk_kernel: 19001,
  reconciliation: 19002,
  status_agg: 19003,
  "status-agg": 19003,
  portfolio_risk: 19004,
  dead_mans_switch: 19005,
  allocator: 19006,
  tca: 19007,
  security_ops: 19008,
};

export const liveProviders = {
  async getHealth(): Promise<ProviderResult<HealthSnapshot>> {
    const mock = await mockProviders.getHealth();
    const r = await fetchJson<{
      status?: string;
      services?: Record<string, { status?: string }>;
    }>(api("/api/status/health"));

    if (!r.ok) {
      return softFail(mock, r.error);
    }

    const raw = (r.data.status ?? "ok").toLowerCase();
    const overall =
      raw === "ok" || raw === "degraded" || raw === "halted"
        ? raw
        : ("degraded" as const);

    const services: ServiceRow[] = r.data.services
      ? Object.entries(r.data.services).map(([key, h]) => {
          const st = String(h?.status ?? "unknown").toLowerCase();
          const ok = !["unreachable", "halted", "flatten", "derisk", "down"].includes(st);
          return {
            name: key.replace(/_/g, "-"),
            port: SERVICE_PORT[key] ?? null,
            ok,
            kind: "safety_unit" as const,
          };
        })
      : mock.data.services;

    return {
      data: {
        overall,
        reachable: true,
        services,
        inProcessSigning: mock.data.inProcessSigning,
        optionalLegacySigning: {
          ...mock.data.optionalLegacySigning,
          note: "Optional legacy HTTP :19010 — probe skipped (not required)",
        },
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  /**
   * TODO: GET /api/status/v1/fleet (or agent registry) when available.
   * Until then, soft-fail to mock roster (20 classical agents).
   */
  async getFleet(): Promise<ProviderResult<FleetSnapshot>> {
    const mock = await mockProviders.getFleet();
    const r = await fetchJson<{ agents?: FleetSnapshot["agents"]; total?: number }>(
      api("/api/status/v1/fleet"),
    );
    if (!r.ok) {
      return softFail(mock, `fleet endpoint: ${r.error}`);
    }
    const agents = r.data.agents ?? mock.data.agents;
    const total = r.data.total ?? agents.length;
    if (total !== 20) {
      return softFail(
        mock,
        `fleet total=${total} (expected 20 classical; ignoring live payload)`,
      );
    }
    return {
      data: { ...mock.data, agents, total: 20 },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  /**
   * Signing is in-process titan-safety. Live path uses control-plane halt status
   * via /api/signing (proxied to status-agg), NOT mandatory :19010.
   */
  async getSigning(): Promise<ProviderResult<SigningSnapshot>> {
    const mock = await mockProviders.getSigning();
    const r = await fetchJson<{
      halted?: boolean;
      mode?: string;
      audit?: SigningSnapshot["audit"];
    }>(api("/api/signing/v1/status"));
    if (!r.ok) {
      return softFail(mock, r.error);
    }
    return {
      data: {
        ...mock.data,
        mode: "in_process",
        daemonRequired: false,
        halted: Boolean(r.data.halted),
        audit: r.data.audit ?? mock.data.audit,
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  async getSecurity(): Promise<ProviderResult<SecuritySnapshot>> {
    const mock = await mockProviders.getSecurity();
    const live = await fetchSecurityPosture();
    if (!live.live) {
      return softFail(mock, live.error ?? "security unreachable");
    }
    return {
      data: {
        overall: live.overall ?? live.status ?? mock.data.overall,
        threatLevel: live.threat_level ?? mock.data.threatLevel,
        live: true,
        huntMode: live.hunt_mode,
        honeypotArmed: live.honeypot_armed,
        pcrDrift: live.pcr_drift,
        signingHalted: live.signing_halted,
        killActive: live.kill_active,
        evolutionFrozen: live.evolution_frozen,
        pillars: live.pillars,
        layers: live.layers,
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  /** TODO: wire portfolio equity from :19004 / reconciliation. */
  async getPortfolio(): Promise<ProviderResult<PortfolioSnapshot>> {
    const mock = await mockProviders.getPortfolio();
    const r = await fetchJson<{
      equity_usd?: number;
      available_usd?: number;
      drawdown_pct?: number;
      capital_profile?: string;
      kill_active?: boolean;
    }>(api("/api/portfolio/v1/summary"));
    if (!r.ok) {
      return softFail(mock, r.error);
    }
    return {
      data: {
        equityUsd: r.data.equity_usd ?? mock.data.equityUsd,
        availableUsd: r.data.available_usd ?? mock.data.availableUsd,
        drawdownPct: r.data.drawdown_pct ?? mock.data.drawdownPct,
        capitalProfile: r.data.capital_profile ?? mock.data.capitalProfile,
        killActive: r.data.kill_active ?? mock.data.killActive,
        evolutionFrozen: mock.data.evolutionFrozen,
        dmsHoursSinceHeartbeat: mock.data.dmsHoursSinceHeartbeat,
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  /** TODO: wire pipeline catalog from allocator / status. */
  async getPipelines(): Promise<ProviderResult<PipelinesSnapshot>> {
    const mock = await mockProviders.getPipelines();
    const r = await fetchJson<{ pipelines?: PipelinesSnapshot["catalog"] }>(
      api("/api/allocator/v1/pipelines"),
    );
    if (!r.ok) {
      return softFail(mock, r.error);
    }
    return {
      data: {
        ...mock.data,
        catalog: r.data.pipelines ?? mock.data.catalog,
        dexOnly: true,
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },

  async getManualControl(): Promise<ProviderResult<ManualControlSnapshot>> {
    const mock = await mockProviders.getManualControl();
    const r = await fetchJson<{
      trading_halted?: boolean;
      kill_active?: boolean;
      signing_halted?: boolean;
      capital_profile?: string;
    }>(api("/api/status/v1/control"));
    if (!r.ok) {
      return softFail(mock, r.error);
    }
    return {
      data: {
        ...mock.data,
        tradingHalted: r.data.trading_halted ?? mock.data.tradingHalted,
        killActive: r.data.kill_active ?? mock.data.killActive,
        signingHalted: r.data.signing_halted ?? mock.data.signingHalted,
        capitalProfile: r.data.capital_profile ?? mock.data.capitalProfile,
        quantumEnabled: false,
        quantumAgentsRemoved: true,
        agentCount: 20,
      },
      source: "live",
      advisory: false,
      fetchedAt: nowIso(),
    };
  },
};
