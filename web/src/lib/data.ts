/** Demo + live-ready data for Titan Agentik. Live endpoints proxied via Vite. */

export type LaneHealth = "HEALTHY" | "WATCH" | "BLEEDING";

export const portfolio = {
  equityUsd: 28450.32,
  availableUsd: 12120.5,
  depositedUsd: 25000,
  weeklyPnlUsd: 842.17,
  drawdownPct: 1.8,
  drawdownNotifyOnly: true,
  edgeMeshMode: "full_mesh" as const,
  paperLatencyFaithful: true,
  regime: "neutral" as const,
  capitalProfile: "live" as const,
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
  { id: "ALCHEMY", role: "DeFi / flash compose", tier: "U :30002", status: "online", load: 24 },
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
  { name: "security-ops", port: 19008, ok: true },
  { name: "signing-node", port: 19010, ok: true },
];

export const promotions = [
  { id: "promo-041", strategy: "P34 CLMM 2.0", phase: 5, status: "PENDING_PROMOTION_APPROVAL", score: 0.86 },
  { id: "promo-p22", strategy: "P22 Memecoin Trench", phase: 5, status: "PENDING_PROMOTION_APPROVAL", score: 0.74 },
  { id: "fl-promo-01", strategy: "flash_loan_live (global)", phase: 5, status: "PENDING_PROMOTION_APPROVAL", score: 0.81 },
  { id: "promo-038", strategy: "P16 RWA Basis", phase: 4, status: "SCORECARD", score: 0.79 },
  { id: "promo-033", strategy: "P11 Pred Arb", phase: 3, status: "MICRO_LIVE", score: 0.72 },
];

export const aiLog = [
  { ts: "2026-07-09T06:41:12Z", agent: "GUARDIAN", level: "info", msg: "Pre-trade DENY — recon not configured; fill ~/.openclaw/.env" },
  { ts: "2026-07-09T06:38:01Z", agent: "AUGUR", level: "info", msg: "Regime reading: neutral (file feed stub)" },
  { ts: "2026-07-09T06:22:44Z", agent: "ARBITER", level: "warn", msg: "P29 TCA net_bps=-1.8 → profit_loop defund queued" },
  { ts: "2026-07-09T05:55:10Z", agent: "SENTINEL", level: "info", msg: "CodeQL scan clean — 0 high findings" },
  { ts: "2026-07-09T05:12:33Z", agent: "TRENCH-OPS", level: "info", msg: "Gate receipt issued GATE_ALLOW|t-9912… signing deferred (live, credentials pending)" },
];

export const questions = [
  { id: "q-12", from: "operator", text: "Should we unfreeze evolution for shadow-only GEPA?", status: "open", priority: "medium" },
  { id: "q-11", from: "CORTEX", text: "P12 WATCH lane — extend sample or defund?", status: "escalated", priority: "high" },
  { id: "q-09", from: "ARBITER", text: "Phase 5 YES for P34 CLMM 2.0?", status: "awaiting_yes", priority: "critical" },
];

export const activityFeed = [
  {
    id: "act-mc",
    title: "P22 memecoin paper: 12 filters passed",
    detail: "68% sim pass · 0.85/2 SOL daily cap · EDGE-FRA Jito path",
    ts: "2026-07-09T11:45:00Z",
    tsLabel: "5m ago",
    tone: "ok" as const,
  },
  {
    id: "act-0",
    title: "Flash-loan paper sim complete",
    detail: "72% pass rate · 100 routes — awaiting flash_loan_live YES",
    ts: "2026-07-09T11:15:00Z",
    tsLabel: "12m ago",
    tone: "info" as const,
  },
  {
    id: "act-0b",
    title: "Security stalk: sandwich cluster",
    detail: "PREDATOR re-tagged adversarial flow on EDGE-FRA — hunting",
    ts: "2026-07-09T06:48:11Z",
    tsLabel: "4h ago",
    tone: "warn" as const,
  },
  {
    id: "act-1",
    title: "Phase 5 promotion pending",
    detail: "P34 CLMM 2.0 awaiting operator YES — score 0.86",
    ts: "2026-07-09T06:45:00Z",
    tsLabel: "6m ago",
    tone: "warn" as const,
  },
  {
    id: "act-2",
    title: "DMS heartbeat acknowledged",
    detail: "Dead man's switch reset — 2.4h since last pulse",
    ts: "2026-07-09T06:30:00Z",
    tsLabel: "21m ago",
    tone: "ok" as const,
  },
  {
    id: "act-3",
    title: "P29 TCA defund queued",
    detail: "ARBITER flagged net_bps −1.8 on MEV Bundle lane",
    ts: "2026-07-09T06:22:44Z",
    tsLabel: "29m ago",
    tone: "danger" as const,
  },
  {
    id: "act-4",
    title: "Risk kernel healthy",
    detail: "Pre-trade gate :19001 responding · live profile",
    ts: "2026-07-09T06:00:00Z",
    tsLabel: "52m ago",
    tone: "info" as const,
  },
  {
    id: "act-5",
    title: "Evolution freeze active",
    detail: "Shadow-only deploys — live promotion blocked",
    ts: "2026-07-09T05:00:00Z",
    tsLabel: "1h ago",
    tone: "warn" as const,
  },
];

export const skills = [
  { name: "trench_ops_execution", version: "2.5.0", status: "live", owner: "TRENCH-OPS" },
  { name: "flash_loan_router", version: "1.0.0", status: "catalog", owner: "ALCHEMY" },
  { name: "memecoin_trench", version: "1.0.0", status: "paper", owner: "PREDATOR" },
  { name: "herald_notify", version: "1.2.1", status: "live", owner: "HERALD" },
  { name: "forge_infra", version: "1.1.0", status: "live", owner: "FORGE" },
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

/** Capital ledger ≠ trading PnL. Deposits credit equity/available. */
export const capitalLedger = {
  equityUsd: portfolio.equityUsd,
  availableUsd: portfolio.availableUsd,
  depositedUsd: portfolio.depositedUsd,
  withdrawnUsd: 0,
  weeklyProfitUsd: portfolio.weeklyPnlUsd,
  sweepThresholdUsd: 35000,
  sweepPct: 20,
  sweepDayUtc: "Sunday",
  growthPhase: true, // equity < $35K → 100% reinvest, no sweep
  withdrawalAdapter: "trezor_signing" as "mock" | "trezor_signing",
  maxSingleWithdrawalPct: 20,
};

export const wallets = [
  {
    id: "hot-ops",
    label: "Hot ops (signing_node)",
    kind: "hot" as const,
    chain: "multi",
    address: "0x7a…c4e2",
    balanceUsd: 12120.5,
    role: "Execution / TRENCH-OPS",
  },
  {
    id: "edge-fra",
    label: "EDGE-FRA working",
    kind: "hot" as const,
    chain: "solana+evm",
    address: "So1…9kQm",
    balanceUsd: 2100,
    role: "EU broadcast float",
  },
  {
    id: "trezor-safe-7",
    label: "Trezor Safe 7",
    kind: "cold" as const,
    chain: "multi",
    address: "trezor:safe-7",
    balanceUsd: 0,
    role: "Weekly profit sweep vault · Mac Mini ceremony",
  },
  {
    id: "macmini-meta",
    label: "Mac Mini vault metadata",
    kind: "cold" as const,
    chain: "—",
    address: "vault://macmini",
    balanceUsd: 0,
    role: "Key metadata only — no live signing",
  },
];

export const capitalTxns = [
  { ts: "2026-07-01T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Biweekly injection", status: "cleared" },
  { ts: "2026-06-15T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Biweekly injection", status: "cleared" },
  { ts: "2026-06-01T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Starting capital tranche", status: "cleared" },
  { ts: "2026-05-18T00:00:00Z", type: "sweep", amount: 0, asset: "USDC", note: "Skipped — equity <$35K growth phase", status: "skipped" },
];

export const circuitBreakers = [
  { pct: 2, action: "HERALD notify · MEDIUM", state: "notify-only" },
  { pct: 5, action: "HERALD notify · HIGH", state: "notify-only" },
  { pct: 8, action: "HERALD notify · HIGH", state: "notify-only" },
  { pct: 10, action: "HERALD CRITICAL · trading continues", state: "notify-only" },
  { pct: 12, action: "HERALD CRITICAL · trading continues", state: "notify-only" },
];

export const drawdownPolicy = {
  notifyOnly: true,
  velocityHalt60s: 150,
  velocityHalt15m: 400,
  volatileExemptPipelines: ["P22", "P29", "P30", "P12"],
  note: "Portfolio drawdown tiers never block trades — velocity breakers still fail-closed",
};

export const latencyBudget = {
  hotPathGateP95Ms: 15,
  hotPathSubmitP95Ms: 50,
  homeToEdgeP95Ms: 25,
  edgeToExchangeP95Ms: 1,
  nostrDispatchMs: 3,
  warmPathGateP95Ms: 150,
  hotPipelines: ["P22", "P29", "P12", "P30"],
};

export const pipelinesCatalog = [
  { id: "P1", name: "CEX Spot Arb", phase: "funded", edge: "EDGE-TKY" },
  { id: "P3", name: "Cross-Rollup Arb", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P5", name: "Funding Carry", phase: "funded", edge: "EDGE-TKY", flash: true },
  { id: "P6", name: "Liquidation Hunter", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P10", name: "Restaking / AVS", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P11", name: "Prediction Arb", phase: "micro_live", edge: "EDGE-USE" },
  { id: "P12", name: "Intent Solver", phase: "funded", edge: "EDGE-FRA", flash: true },
  { id: "P16", name: "RWA Basis", phase: "scorecard", edge: "EDGE-FRA", flash: true },
  { id: "P22", name: "Memecoin Trench", phase: "paper", edge: "EDGE-FRA", memecoin: true },
  { id: "P29", name: "MEV Bundle", phase: "defunded", edge: "EDGE-TKY" },
  { id: "P32", name: "Bridge Security", phase: "shadow", edge: "EDGE-FRA" },
  { id: "P34", name: "CLMM 2.0", phase: "pending_yes", edge: "EDGE-FRA" },
];

export const edgeMesh = {
  mode: "full_mesh",
  routingPolicy: "lowest_live_p50_rtt",
  paperLatencyFaithful: true,
  activePops: 5,
  defaultPop: "EDGE-FRA",
};

export const edgeStrategyRouting = [
  { strategy: "P22", primary: "EDGE-FRA", fallback: "EDGE-AMS", note: "Jito FRA · memecoin" },
  { strategy: "P29", primary: "EDGE-TKY", fallback: "EDGE-FRA", note: "MEV colo" },
  { strategy: "P30", primary: "EDGE-TKY", fallback: "EDGE-SIN", note: "Cross-chain MEV" },
  { strategy: "P12", primary: "EDGE-FRA", fallback: "EDGE-USE", note: "Intent solver EU/US" },
  { strategy: "P3", primary: "EDGE-FRA", fallback: "EDGE-TKY", note: "Flash-loan arb" },
  { strategy: "P8", primary: "EDGE-TKY", fallback: "EDGE-SIN", note: "APAC CEX-adjacent" },
];

export const edgePops = [
  { id: "EDGE-FRA", region: "Frankfurt DE-CIX", targets: "Jito FRA, Erigon, EU DEX", rtt: "≤5ms", status: "healthy", wg: "10.0.10.100" },
  { id: "EDGE-TKY", region: "ap-northeast-1", targets: "Binance, OKX, Hyperliquid", rtt: "<1ms", status: "healthy", wg: "10.0.10.101" },
  { id: "EDGE-SIN", region: "ap-southeast-1", targets: "Bybit, BSC, Sui", rtt: "<1ms", status: "healthy", wg: "10.0.10.102" },
  { id: "EDGE-USE", region: "us-east-1", targets: "Coinbase, L2 seq, Flashbots", rtt: "≤3ms", status: "healthy", wg: "10.0.10.103" },
  { id: "EDGE-AMS", region: "Amsterdam AMS-IX", targets: "Solana gRPC, Nostr", rtt: "≤5ms", status: "healthy", wg: "10.0.10.104" },
];

export const flashLoanRouter = {
  enabled: false,
  promotionApproved: false,
  skill: "flash_loan_router",
  composeAgent: "ALCHEMY",
  executeAgent: "TRENCH-OPS",
  maxAmountUsd: 500_000,
  paperSimPassRate: 0.72,
  paperSimCount: 100,
  sourcePriority: {
    ethereum: ["balancer", "morpho", "uniswap_v4", "aave_v3"],
    arbitrum: ["balancer", "morpho", "aave_v3"],
    base: ["morpho", "balancer", "aave_v3"],
  },
  pipelines: ["P1", "P2", "P3", "P5", "P6", "P7", "P8", "P12", "P15", "P16", "P17"],
  recentComposes: [
    { ts: "2026-07-09T11:10:00Z", chain: "ethereum", source: "balancer", amountUsd: 4200, profitUsd: 14.2, strategy: "P3" },
    { ts: "2026-07-09T10:55:00Z", chain: "arbitrum", source: "morpho", amountUsd: 2800, profitUsd: 9.1, strategy: "P12" },
    { ts: "2026-07-09T10:40:00Z", chain: "base", source: "morpho", amountUsd: 1500, profitUsd: 4.8, strategy: "P6" },
  ],
};

export const memecoinTrench = {
  pipelineId: "P22",
  enabled: false,
  promotionApproved: false,
  mode: "paper" as const,
  skill: "memecoin_trench",
  scanAgent: "PREDATOR",
  executeAgent: "TRENCH-OPS",
  feedsAgent: "NEXUS",
  sizeAgent: "GUARDIAN",
  edgePop: "EDGE-FRA",
  jitoBlockEngine: "frankfurt.mainnet.block-engine.jito.wtf",
  pumpFunProgram: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
  geyserConfigured: false,
  dailySolCap: 2.0,
  dailySolUsed: 0.85,
  maxSnipePctEquity: 0.5,
  maxTop10HolderPct: 30,
  maxInsiderPct: 15,
  graduationTargetUsd: 69000,
  paperSimPassRate: 0.68,
  paperSimCount: 100,
  filtersPassed24h: 12,
  filtersRejected24h: 88,
  drawdownExempt: true,
  hotPathMs: 15,
  sixGates: [
    { id: "G1", name: "Mint authority revoked", key: "G1_mint_authority" },
    { id: "G2", name: "Freeze authority revoked", key: "G2_freeze_authority" },
    { id: "G3", name: "Holder concentration", key: "G3_holder_concentration" },
    { id: "G4", name: "No cabal preload", key: "G4_preload_cabal" },
    { id: "G5", name: "Curve liquidity alive", key: "G5_curve_liquidity" },
    { id: "G6", name: "Sell simulation OK", key: "G6_sellability" },
  ],
  strategies: [
    { id: "first_block_snipe", when: "G1–G6 pass at create", maxPctEquity: 0.5, phase: "A" },
    { id: "curve_climb", when: "15–85% curve, no cabal", maxPctEquity: 0.5, phase: "B" },
    { id: "graduation", when: "~$69k migration approach", maxPctEquity: 0.5, phase: "C" },
    { id: "post_grad_pullback", when: "After PumpSwap migration", maxPctEquity: 1.0, phase: "D" },
    { id: "smart_money_mirror", when: "Tracked wallet entry", maxPctEquity: 0.5, phase: "D" },
  ],
  circuitBreakers: [
    { id: "CB_MEMECOIN_DAILY_SOL_CAP", action: "halt P22 until UTC reset" },
    { id: "CB_MEMECOIN_FILTER_BYPASS", action: "DENY fail-closed" },
    { id: "CB_MEMECOIN_HONEYPOT", action: "DENY + HERALD alert" },
    { id: "CB_MEMECOIN_GRAD_FAIL", action: "halt lane P22" },
    { id: "CB_MEMECOIN_TIP_BLEED", action: "reduce size P22" },
  ],
  exits: {
    stopLossPct: 40,
    trailingStopPct: 25,
    takeProfitLadder: [0.25, 0.25, 0.5],
    timeExitMinutes: 15,
  },
  recentCandidates: [
    {
      ts: "2026-07-09T11:42:00Z",
      mint: "7xKX…9pQm",
      passed: true,
      strategy: "curve_climb",
      gates: { G1_mint_authority: "PASS", G2_freeze_authority: "PASS", G3_holder_concentration: "PASS", G4_preload_cabal: "PASS", G5_curve_liquidity: "PASS", G6_sellability: "PASS" },
      notionalUsd: 142,
      confidence: 0.58,
    },
    {
      ts: "2026-07-09T11:38:00Z",
      mint: "4nWp…k2Rs",
      passed: false,
      strategy: "—",
      gates: { G1_mint_authority: "PASS", G2_freeze_authority: "FAIL", G3_holder_concentration: "—", G4_preload_cabal: "—", G5_curve_liquidity: "—", G6_sellability: "—" },
      rejectReason: "freeze authority active (honeypot risk)",
      notionalUsd: 0,
      confidence: 0,
    },
    {
      ts: "2026-07-09T11:35:00Z",
      mint: "9mTy…3vLk",
      passed: true,
      strategy: "first_block_snipe",
      gates: { G1_mint_authority: "PASS", G2_freeze_authority: "PASS", G3_holder_concentration: "PASS", G4_preload_cabal: "PASS", G5_curve_liquidity: "PASS", G6_sellability: "PASS" },
      notionalUsd: 71,
      confidence: 0.52,
    },
  ],
  paperTrades: [
    { ts: "2026-07-09T11:42:05Z", mint: "7xKX…9pQm", side: "buy", notionalUsd: 142, strategy: "curve_climb", pnlUsd: null, status: "open" },
    { ts: "2026-07-09T11:35:08Z", mint: "9mTy…3vLk", side: "buy", notionalUsd: 71, strategy: "first_block_snipe", pnlUsd: 18.4, status: "closed" },
    { ts: "2026-07-09T11:20:00Z", mint: "2pQr…8nWf", side: "buy", notionalUsd: 95, strategy: "graduation", pnlUsd: -38.2, status: "stopped" },
  ],
};

export const modelTiers = [
  { tier: "1", port: ":30000", model: "Qwen3-30B-A3B FP8", role: "Signals, risk, TRENCH-OPS", live: true },
  { tier: "2", port: ":30001", model: "Qwen3-Coder-Next-80B", role: "ARCHON, SENTINEL, LAMARCK", live: true },
  { tier: "E", port: ":30004", model: "Qwen3-Embedding-0.6B", role: "Embedder ride-along", live: true },
  { tier: "3a", port: ":30005", model: "DeepSeek V4 Pro", role: "R&D / CORTEX deep votes", live: false },
  { tier: "3b", port: ":30003", model: "GLM-5.2 Q4_K_M", role: "Secondary R&D only", live: false },
  { tier: "U", port: ":30002", model: "Qwen3-30B (TITANSPARK)", role: "Utility agents · ALCHEMY", live: true },
];

export const signingAudit = [
  { ts: "2026-07-09T06:12:01Z", action: "deny", code: "GATE_RECEIPT_INVALID", trade: "—" },
  { ts: "2026-07-09T05:12:33Z", action: "allow", code: "OK", trade: "t-9912" },
  { ts: "2026-07-08T22:01:00Z", action: "halt", code: "SIGNING_HALTED", trade: "—" },
];

/** Security Ops — impenetrable / evasion / stalking / predatory posture */
export const securityPosture = {
  overall: "HARDENED" as const,
  threatLevel: "ELEVATED" as const,
  lastRedTeam: "2026-07-02T00:00:00Z",
  pcrDrift: false,
  netnsIsolated: true,
  signingIsolated: true,
  cloudModelsBanned: true,
  mewShieldActive: true,
};

export const impenetrableLayers = [
  {
    id: "L1",
    name: "Out-of-process risk kernel",
    port: ":19001",
    status: "armed" as const,
    detail: "Pre-trade DENY authoritative — agents cannot bypass",
  },
  {
    id: "L2",
    name: "Signing node isolation",
    port: ":19010",
    status: "armed" as const,
    detail: "Minimal OS · no evolution workloads · UPS · TPM-SPI PCR",
  },
  {
    id: "L3",
    name: "Network namespace / policy engine",
    port: "netns",
    status: "armed" as const,
    detail: "Every action validated out-of-process before egress",
  },
  {
    id: "L4",
    name: "SENTINEL CodeQL + PCR drift",
    port: "T2",
    status: "armed" as const,
    detail: "Continuous audit · TPM PCR drift → alert + hold",
  },
  {
    id: "L5",
    name: "Dead-man's switch",
    port: ":19005",
    status: "armed" as const,
    detail: "48h derisk · 72h flatten if heartbeat lost",
  },
  {
    id: "L6",
    name: "Closed-model ban (live path)",
    port: "policy",
    status: "armed" as const,
    detail: "No Claude/GPT/Gemini on TRENCH-OPS / GUARDIAN / EXECUTOR",
  },
];

export const evasionControls = [
  {
    id: "ev-1",
    name: "MEV-shielded intent solvers",
    mode: "active",
    detail: "Declarative intents · no public RPC pool for DEX swaps",
  },
  {
    id: "ev-2",
    name: "Edge RTT routing",
    mode: "active",
    detail: "Lowest live p50 RTT PoP — same-AZ as exchange matching engines",
  },
  {
    id: "ev-3",
    name: "Nostr NIP-44 edge dispatch",
    mode: "active",
    detail: "Kind 1059 encrypted pub/sub · ≤3ms broadcast to workers",
  },
  {
    id: "ev-4",
    name: "Wallet / fingerprint rotation",
    mode: "scheduled",
    detail: "Hot ops address rotation · sessionStorage tokens only",
  },
  {
    id: "ev-5",
    name: "Traffic pattern obfuscation",
    mode: "active",
    detail: "Jittered heartbeats · decoy probes · no predictable cron egress",
  },
  {
    id: "ev-6",
    name: "Signing ceremony air-gap",
    mode: "active",
    detail: "Mac Mini metadata only · Trezor Safe 7 never on live path",
  },
];

export const stalkTargets = [
  {
    id: "st-1",
    label: "Mempool predator cluster",
    source: "PREDATOR",
    severity: "high" as const,
    lastSeen: "2m ago",
    status: "tracking",
    note: "Sandwich pattern on EDGE-FRA Solana shreds — tagged, not engaged",
  },
  {
    id: "st-2",
    label: "RPC fingerprint probe",
    source: "SENTINEL",
    severity: "medium" as const,
    lastSeen: "18m ago",
    status: "watching",
    note: "Repeated eth_call from unknown ASN against signing health endpoint",
  },
  {
    id: "st-3",
    label: "Competitor copy-trade wallet",
    source: "WRAITH",
    severity: "medium" as const,
    lastSeen: "41m ago",
    status: "tracking",
    note: "Mirrors P1 fills with 180–400ms lag — feed poisoned via decoy size",
  },
  {
    id: "st-4",
    label: "PCR anomaly candidate",
    source: "SENTINEL",
    severity: "low" as const,
    lastSeen: "3h ago",
    status: "cleared",
    note: "Kernel module load matched allowlist after operator confirm",
  },
  {
    id: "st-5",
    label: "Telegram phishing lure",
    source: "HERALD",
    severity: "high" as const,
    lastSeen: "6h ago",
    status: "quarantined",
    note: "Impersonation of operator channel — blocked at HERALD ingress",
  },
];

export const predatoryModules = [
  {
    id: "pr-1",
    name: "PREDATOR sniper / mempool",
    agent: "PREDATOR",
    posture: "hunt",
    detail: "Scan + classify adversarial flow · feed BFT vote as safety signal",
  },
  {
    id: "pr-2",
    name: "Honeypot wallet lattice",
    agent: "SENTINEL",
    posture: "lure",
    detail: "Decoy hot wallets with tripwire balances · alert on touch",
  },
  {
    id: "pr-3",
    name: "Red Team gauntlet",
    agent: "ARBITER",
    posture: "simulate",
    detail: "Adversarial strategy stress before Phase 5 promotion",
  },
  {
    id: "pr-4",
    name: "Graph-R1 fraud hypergraph",
    agent: "GUARDIAN",
    posture: "isolate",
    detail: "Recursive Neo4j queries for contract / counterparty fraud rings",
  },
  {
    id: "pr-5",
    name: "Counter-copy poison",
    agent: "TRENCH-OPS",
    posture: "disrupt",
    detail: "Sized decoy fills to burn lagging copy-traders without PnL hit",
  },
  {
    id: "pr-6",
    name: "Kill-chain auto-response",
    agent: "ARCHON",
    posture: "contain",
    detail: "CB tier + kill switch + signing halt sequenced on confirmed breach",
  },
];

export const securityEvents = [
  {
    ts: "2026-07-09T06:48:11Z",
    pillar: "stalk",
    level: "warn",
    msg: "PREDATOR: sandwich cluster re-tagged on EDGE-FRA shred stream",
  },
  {
    ts: "2026-07-09T06:22:00Z",
    pillar: "evasion",
    level: "info",
    msg: "Intent solver path selected — public RPC pool bypassed for P12",
  },
  {
    ts: "2026-07-09T05:55:10Z",
    pillar: "impenetrable",
    level: "info",
    msg: "SENTINEL CodeQL clean — 0 high findings",
  },
  {
    ts: "2026-07-09T04:10:44Z",
    pillar: "predatory",
    level: "info",
    msg: "Honeypot tripwire idle — 0 touches in 24h",
  },
  {
    ts: "2026-07-08T21:03:00Z",
    pillar: "predatory",
    level: "warn",
    msg: "ARBITER Red Team: P29 failed gauntlet → defund confirmed",
  },
];

export type HealthOverall = "ok" | "degraded" | "halted" | "unreachable";

export type HealthServiceRow = {
  name: string;
  port: number;
  ok: boolean;
  status: string;
};

export type HealthProbeResult = {
  reachable: boolean;
  overall: HealthOverall;
  services: HealthServiceRow[];
};

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
  signing_node: 19010,
};

function displayName(apiKey: string): string {
  return apiKey.replace(/_/g, "-");
}

/** Probe status aggregator (`/api/status/health` → :19003). */
export async function probeHealth(
  path = "/api/status/health",
): Promise<HealthProbeResult> {
  try {
    const r = await fetch(path, { signal: AbortSignal.timeout(2000) });
    if (!r.ok) {
      return { reachable: false, overall: "unreachable", services: [] };
    }
    const data = (await r.json()) as {
      status?: string;
      services?: Record<string, { status?: string; error?: string }>;
    };
    const raw = (data.status ?? "ok").toLowerCase();
    const overall: HealthOverall =
      raw === "ok" || raw === "degraded" || raw === "halted"
        ? raw
        : "degraded";

    const services: HealthServiceRow[] = data.services
      ? Object.entries(data.services).map(([key, h]) => {
          const st = String(h?.status ?? "unknown").toLowerCase();
          const ok = !["unreachable", "halted", "flatten", "derisk", "down"].includes(st);
          return {
            name: displayName(key),
            port: SERVICE_PORT[key] ?? 0,
            ok,
            status: st,
          };
        })
      : [];

    return { reachable: true, overall, services };
  } catch {
    return { reachable: false, overall: "unreachable", services: [] };
  }
}
