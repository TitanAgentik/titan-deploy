/**
 * Mock adapters — wrap existing data.ts fixtures.
 * Keep data.ts as the fixture source of truth until live backends exist.
 */

import {
  agentBftStatus,
  agentFleetSummary,
  agents,
  manualControl,
  pipelinesCatalog,
  portfolio,
  probeHealth,
  securityPosture,
  services,
  signingAudit,
  type AgentRecord,
} from "@/lib/data";
import { nowIso } from "../http";
import type {
  AgentDto,
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

function wrap<T>(data: T): ProviderResult<T> {
  return {
    data,
    source: "mock",
    advisory: true,
    fetchedAt: nowIso(),
  };
}

const SAFETY_SERVICES: ServiceRow[] = services.map((s) => ({
  name: s.name,
  port: s.port,
  ok: s.ok,
  kind: "safety_unit" as const,
}));

const IN_PROCESS_SIGNING: ServiceRow = {
  name: "signing-in-process",
  port: null,
  ok: true,
  kind: "in_process",
  note: "titan-safety SigningNode · no :19010 required",
};

const OPTIONAL_LEGACY: ServiceRow = {
  name: "signing-node-http",
  port: 19010,
  ok: true,
  kind: "optional_legacy",
  note: "Optional legacy HTTP only — not on hot path",
};

function toAgentDto(a: AgentRecord): AgentDto {
  return { ...a };
}

export const mockProviders = {
  async getHealth(): Promise<ProviderResult<HealthSnapshot>> {
    const probe = await probeHealth();
    const rows: ServiceRow[] =
      probe.reachable && probe.services.length > 0
        ? probe.services.map((s) => ({
            name: s.name,
            port: s.port || null,
            ok: s.ok,
            kind: "safety_unit" as const,
          }))
        : SAFETY_SERVICES;
    return wrap({
      overall: probe.reachable ? probe.overall : "ok",
      reachable: probe.reachable,
      services: rows,
      inProcessSigning: IN_PROCESS_SIGNING,
      optionalLegacySigning: OPTIONAL_LEGACY,
    });
  },

  async getFleet(): Promise<ProviderResult<FleetSnapshot>> {
    const summary = agentFleetSummary(agents);
    return wrap({
      total: 20,
      agents: agents.map(toAgentDto),
      byStatus: summary.byStatus,
      byTier: summary.byTier,
      tradeVoters: agentBftStatus.tradeVoters.map((v) => ({
        id: v.id,
        vote: v.vote,
        signed: v.signed,
        note: v.note,
      })),
      bftThreshold: agentBftStatus.threshold,
      authoritativeGate: agentBftStatus.authoritativeGate,
    });
  },

  async getSigning(): Promise<ProviderResult<SigningSnapshot>> {
    return wrap({
      mode: "in_process",
      daemonRequired: false,
      optionalLegacyPort: 19010,
      receiptTtlSec: 30,
      blindSign: "REJECTED",
      liveSignerRequired: true,
      halted: manualControl.signingHalted,
      audit: signingAudit.map((r) => ({ ...r })),
    });
  },

  async getSecurity(): Promise<ProviderResult<SecuritySnapshot>> {
    return wrap({
      overall: securityPosture.overall,
      threatLevel: securityPosture.threatLevel,
      live: false,
      huntMode: true,
      honeypotArmed: true,
      pcrDrift: securityPosture.pcrDrift,
      signingHalted: false,
      killActive: portfolio.killActive,
      evolutionFrozen: portfolio.evolutionFrozen,
    });
  },

  async getPortfolio(): Promise<ProviderResult<PortfolioSnapshot>> {
    return wrap({
      equityUsd: portfolio.equityUsd,
      availableUsd: portfolio.availableUsd,
      drawdownPct: portfolio.drawdownPct,
      capitalProfile: portfolio.capitalProfile,
      killActive: portfolio.killActive,
      evolutionFrozen: portfolio.evolutionFrozen,
      dmsHoursSinceHeartbeat: portfolio.dmsHoursSinceHeartbeat,
    });
  },

  async getPipelines(): Promise<ProviderResult<PipelinesSnapshot>> {
    return wrap({
      catalog: pipelinesCatalog.map((p) => ({
        id: p.id,
        name: p.name,
        phase: p.phase,
        edge: p.edge,
        memecoin: "memecoin" in p ? Boolean(p.memecoin) : undefined,
        flash: "flash" in p ? Boolean(p.flash) : undefined,
      })),
      maxFundedHealthy: 4,
      dexOnly: true as const,
    });
  },

  async getManualControl(): Promise<ProviderResult<ManualControlSnapshot>> {
    return wrap({
      overallPosture: manualControl.overallPosture,
      tradingHalted: manualControl.tradingHalted,
      killActive: manualControl.killActive,
      signingHalted: manualControl.signingHalted,
      capitalProfile: manualControl.capitalProfile,
      equityUsd: manualControl.equityUsd,
      availableUsd: manualControl.availableUsd,
      drawdownPct: manualControl.drawdownPct,
      quantumEnabled: false as const,
      quantumAgentsRemoved: true as const,
      agentCount: 20 as const,
      honeypotArmed: manualControl.honeypotArmed,
      huntMode: manualControl.huntMode,
      promotionHold: manualControl.promotionHold,
      bftPosture: manualControl.bftPosture,
      controlPlaneServices: SAFETY_SERVICES,
    });
  },
};

export type TitanProviders = typeof mockProviders;
