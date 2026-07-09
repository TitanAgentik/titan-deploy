/** Demo + live-ready data for TITAN Cockpit. Live endpoints proxied via Vite. */

export type LaneHealth = "HEALTHY" | "WATCH" | "BLEEDING";

export const portfolio = {
  equityUsd: 28450.32,
  availableUsd: 12120.5,
  depositedUsd: 25000,
  weeklyPnlUsd: 842.17,
  drawdownPct: 1.8,
  regime: "neutral" as const,
  capitalProfile: "paper" as const,
  killActive: false,
  evolutionFrozen: true,
  dmsHoursSinceHeartbeat: 2.4,
};

export const equitySeries = [
  { t: "Mon", equity: 25000 },
  { t: "Tue", equity: 25340 },
  { t: "Wed", equity: 26110 },
  { t: "Thu", equity: 26880 },
  { t: "Fri", equity: 27420 },
  { t: "Sat", equity: 27990 },
  { t: "Sun", equity: 28450 },
];

export const lanes = [
  { id: "P1", name: "CEX Spot Arb", allocation: 6200, netBps: 4.2, trades: 412, health: "HEALTHY" as LaneHealth },
  { id: "P5", name: "Funding Carry", allocation: 4800, netBps: 3.1, trades: 288, health: "HEALTHY" as LaneHealth },
  { id: "P12", name: "Intent Solver", allocation: 3100, netBps: 2.4, trades: 156, health: "WATCH" as LaneHealth },
  { id: "P29", name: "MEV Bundle", allocation: 0, netBps: -1.8, trades: 94, health: "BLEEDING" as LaneHealth },
];

export const agents = [
  { id: "ARCHON", role: "Orchestrator", tier: "T2 :30001", status: "online", load: 42 },
  { id: "GUARDIAN", role: "Risk / Kelly", tier: "T1 :30000", status: "online", load: 61 },
  { id: "CORTEX", role: "Meta / GEPA", tier: "T3a :30005", status: "standby", load: 8 },
  { id: "ORACLE", role: "Signals", tier: "T1 :30000", status: "online", load: 55 },
  { id: "PREDATOR", role: "Mempool", tier: "T1 :30000", status: "online", load: 48 },
  { id: "AUGUR", role: "Macro regime", tier: "T1 :30000", status: "online", load: 33 },
  { id: "TRENCH-OPS", role: "Execution", tier: "T1 :30000", status: "online", load: 71 },
  { id: "ATLAS", role: "Portfolio", tier: "U :30002", status: "online", load: 29 },
  { id: "HERALD", role: "Telegram", tier: "U :30002", status: "online", load: 12 },
  { id: "FORGE", role: "Infra health", tier: "U :30002", status: "online", load: 22 },
  { id: "ARBITER", role: "Backtest", tier: "U :30002", status: "online", load: 18 },
  { id: "QCC", role: "Quantum coord", tier: "DORMANT", status: "dormant", load: 0 },
];

export const services = [
  { name: "risk-kernel", port: 19001, ok: true },
  { name: "reconciliation", port: 19002, ok: true },
  { name: "status-agg", port: 19003, ok: true },
  { name: "portfolio-risk", port: 19004, ok: true },
  { name: "dead-mans", port: 19005, ok: true },
  { name: "allocator", port: 19006, ok: true },
  { name: "tca", port: 19007, ok: true },
  { name: "signing-node", port: 19010, ok: true },
];

export const promotions = [
  { id: "promo-041", strategy: "P34 CLMM 2.0", phase: 5, status: "PENDING_PROMOTION_APPROVAL", score: 0.86 },
  { id: "promo-038", strategy: "P16 RWA Basis", phase: 4, status: "SCORECARD", score: 0.79 },
  { id: "promo-033", strategy: "P11 Pred Arb", phase: 3, status: "MICRO_LIVE", score: 0.72 },
];

export const aiLog = [
  { ts: "2026-07-09T06:41:12Z", agent: "GUARDIAN", level: "info", msg: "Pre-trade DENY skipped — paper venue, notional $42 within Kelly" },
  { ts: "2026-07-09T06:38:01Z", agent: "AUGUR", level: "info", msg: "Regime reading: neutral (file feed stub)" },
  { ts: "2026-07-09T06:22:44Z", agent: "ARBITER", level: "warn", msg: "P29 TCA net_bps=-1.8 → profit_loop defund queued" },
  { ts: "2026-07-09T05:55:10Z", agent: "SENTINEL", level: "info", msg: "CodeQL scan clean — 0 high findings" },
  { ts: "2026-07-09T05:12:33Z", agent: "TRENCH-OPS", level: "info", msg: "Gate receipt issued GATE_ALLOW|t-9912… signing deferred (paper)" },
];

export const questions = [
  { id: "q-12", from: "operator", text: "Should we unfreeze evolution for shadow-only GEPA?", status: "open", priority: "medium" },
  { id: "q-11", from: "CORTEX", text: "P12 WATCH lane — extend sample or defund?", status: "escalated", priority: "high" },
  { id: "q-09", from: "ARBITER", text: "Phase 5 YES for P34 CLMM 2.0?", status: "awaiting_yes", priority: "critical" },
];

export const skills = [
  { name: "trench_ops_execution", version: "2.4.0", status: "live", owner: "TRENCH-OPS" },
  { name: "herald_notify", version: "1.2.1", status: "live", owner: "HERALD" },
  { name: "forge_infra", version: "1.0.4", status: "live", owner: "FORGE" },
  { name: "guardian_kelly", version: "0.9.0", status: "staging", owner: "GUARDIAN" },
  { name: "gepa_reflect", version: "0.3.2", status: "shadow", owner: "CORTEX" },
];

export const goals = [
  { id: "g1", title: "Reach $35K equity (sweep unlock)", progress: 81, target: "$35,000", eta: "3–5 weeks" },
  { id: "g2", title: "≥200 fills / funded lane", progress: 64, target: "200 fills", eta: "Phase 1 stretch" },
  { id: "g3", title: "Kill-switch drill monthly", progress: 100, target: "pass", eta: "done" },
  { id: "g4", title: "Wire live signer_module", progress: 20, target: "trezor", eta: "pre-live gate" },
];

export const automations = [
  { id: "a1", name: "TCA → allocator profit loop", schedule: "every fill batch", enabled: true },
  { id: "a2", name: "Weekly profit sweep (≥$35K)", schedule: "Sun 00:00 UTC", enabled: true },
  { id: "a3", name: "Dead-man's derisk / flatten", schedule: "48h / 72h", enabled: true },
  { id: "a4", name: "Evolution freeze while live", schedule: "on capital_profile=live", enabled: true },
  { id: "a5", name: "Shadow GEPA nightly", schedule: "02:00 UTC", enabled: false },
];

export const workspaceFiles = [
  { path: "AGENTS.md", bytes: 19896, role: "bootstrap" },
  { path: "SOUL.md", bytes: 3253, role: "bootstrap" },
  { path: "TOOLS.md", bytes: 19917, role: "bootstrap" },
  { path: "IDENTITY.md", bytes: 7939, role: "bootstrap" },
  { path: "MEMORY.md", bytes: 2334, role: "bootstrap" },
  { path: "refs/TITAN.digest.md", bytes: 16305, role: "reference" },
  { path: "refs/CONFIGS_detail.md", bytes: 33044, role: "reference" },
];

export const autonomyMatrix = [
  { action: "Routine trade <1% equity", auto: true },
  { action: "Trade >1% equity", auto: false },
  { action: "New pipeline activation", auto: false },
  { action: "Model/skill promotion to live", auto: false },
  { action: "Evolution deploy", auto: false },
  { action: "Leverage change", auto: false },
  { action: "Flash-loan live", auto: false },
  { action: "CB tier response", auto: true },
  { action: "TIMEOUT on promotion", auto: false, note: "HOLD/de-risk" },
];

export async function probeHealth(path: string): Promise<boolean> {
  try {
    const r = await fetch(path, { signal: AbortSignal.timeout(1500) });
    return r.ok;
  } catch {
    return false;
  }
}
