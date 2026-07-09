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

/** Trading PnL only — excludes deposit ledger credits. */
export const pnl = {
  tradingPnlUsd: 3450.32,
  realizedUsd: 3231.87,
  unrealizedUsd: 218.45,
  dailyUsd: 127,
  weeklyUsd: 842.17,
  mtdUsd: 2104.88,
  ytdUsd: 3450.32,
  allTimeUsd: 3450.32,
  winRatePct: 61.2,
  tradesClosed24h: 47,
  avgWinUsd: 28.4,
  avgLossUsd: -19.1,
  feesUsd24h: 84.2,
  netBpsWtd: 3.4,
};

export const pnlSeries = [
  { t: "Mon", daily: 98, cumulative: 98 },
  { t: "Tue", daily: 112, cumulative: 210 },
  { t: "Wed", daily: 145, cumulative: 355 },
  { t: "Thu", daily: 118, cumulative: 473 },
  { t: "Fri", daily: 94, cumulative: 567 },
  { t: "Sat", daily: 148, cumulative: 715 },
  { t: "Sun", daily: 127, cumulative: 842 },
];

export type StrategyCategory =
  | "dex"
  | "funding"
  | "defi"
  | "flash"
  | "memecoin"
  | "mev"
  | "prediction";

export const strategyCategoryLabels: Record<StrategyCategory, string> = {
  dex: "DEX / AMM",
  funding: "DEX Perp Funding",
  defi: "DeFi / Intent",
  flash: "Flash-loan composed",
  memecoin: "Memecoin Trench",
  mev: "MEV / Bundle",
  prediction: "Prediction markets",
};

/** Strategy-level PnL + capital attribution — sums to portfolio WTD PnL. DEX-only (R02 / R46). */
export const pnlByStrategy = [
  {
    id: "P1",
    name: "DEX Cross-Venue Arb",
    category: "dex" as StrategyCategory,
    phase: "funded",
    allocationUsd: 6200,
    dailyUsd: 62,
    wtdUsd: 412.8,
    mtdUsd: 980.2,
    trades24h: 18,
    netBps: 4.2,
    health: "HEALTHY" as LaneHealth,
    revenueSource: "Uniswap ↔ Curve ↔ Balancer spot spreads",
    edge: "EDGE-FRA",
  },
  {
    id: "P5",
    name: "DEX Funding Carry",
    category: "funding" as StrategyCategory,
    phase: "funded",
    allocationUsd: 4800,
    dailyUsd: 38,
    wtdUsd: 318.4,
    mtdUsd: 742.1,
    trades24h: 11,
    netBps: 3.1,
    health: "HEALTHY" as LaneHealth,
    revenueSource: "Hyperliquid DEX perp funding",
    edge: "EDGE-TKY",
  },
  {
    id: "P12",
    name: "Intent Solver",
    category: "defi" as StrategyCategory,
    phase: "funded",
    allocationUsd: 3100,
    dailyUsd: 14,
    wtdUsd: 94.2,
    mtdUsd: 210.5,
    trades24h: 6,
    netBps: 2.4,
    health: "WATCH" as LaneHealth,
    revenueSource: "MEV-shielded solver fills · EU/US",
    edge: "EDGE-FRA",
  },
  {
    id: "P22",
    name: "Memecoin Trench",
    category: "memecoin" as StrategyCategory,
    phase: "paper",
    allocationUsd: 420,
    dailyUsd: 22,
    wtdUsd: 86.2,
    mtdUsd: 142.8,
    trades24h: 9,
    netBps: 8.6,
    health: "HEALTHY" as LaneHealth,
    revenueSource: "Solana pump.fun / Raydium snipes",
    edge: "EDGE-FRA",
  },
  {
    id: "P6",
    name: "Liquidation Hunter",
    category: "flash" as StrategyCategory,
    phase: "paper",
    allocationUsd: 800,
    dailyUsd: 8,
    wtdUsd: 28.4,
    mtdUsd: 61.2,
    trades24h: 3,
    netBps: 3.2,
    health: "HEALTHY" as LaneHealth,
    revenueSource: "Morpho / Aave liquidations + flash close",
    edge: "EDGE-FRA",
  },
  {
    id: "P3",
    name: "Cross-Rollup Arb",
    category: "flash" as StrategyCategory,
    phase: "paper",
    allocationUsd: 600,
    dailyUsd: -4,
    wtdUsd: -9.43,
    mtdUsd: 18.6,
    trades24h: 2,
    netBps: -1.2,
    health: "WATCH" as LaneHealth,
    revenueSource: "L2 bridge latency arb · Balancer flash",
    edge: "EDGE-FRA",
  },
  {
    id: "P29",
    name: "MEV Bundle",
    category: "mev" as StrategyCategory,
    phase: "defunded",
    allocationUsd: 0,
    dailyUsd: -18,
    wtdUsd: -88.6,
    mtdUsd: -142.3,
    trades24h: 4,
    netBps: -1.8,
    health: "BLEEDING" as LaneHealth,
    revenueSource: "Flashbots bundle backrun (defunded)",
    edge: "EDGE-TKY",
  },
];

export const pnlBySubStrategy = [
  { parent: "P22", id: "curve_climb", name: "Curve climb", wtdUsd: 52.1, trades24h: 5 },
  { parent: "P22", id: "first_block_snipe", name: "First-block snipe", wtdUsd: 28.4, trades24h: 3 },
  { parent: "P22", id: "graduation", name: "Graduation play", wtdUsd: 5.7, trades24h: 1 },
];

export function pnlShareOfWtd(wtdUsd: number, totalWtd = pnl.weeklyUsd): number {
  if (totalWtd === 0) return 0;
  return (wtdUsd / totalWtd) * 100;
}

export function strategyDisplay(id: string): string {
  const s = pnlByStrategy.find((x) => x.id === id);
  return s ? `${s.id} · ${s.name}` : id;
}

export const recentTradesPnl = [
  {
    ts: "2026-07-09T11:42:05Z",
    lane: "P1",
    strategyName: "DEX Cross-Venue Arb",
    subStrategy: null as string | null,
    category: "dex" as StrategyCategory,
    asset: "WETH/USDC",
    side: "sell",
    notionalUsd: 4200,
    pnlUsd: 18.6,
    feesUsd: 2.1,
    netBps: 4.4,
    revenueSource: "Uniswap v4 vs Curve TriCrypto",
  },
  {
    ts: "2026-07-09T11:38:22Z",
    lane: "P5",
    strategyName: "DEX Funding Carry",
    subStrategy: null,
    category: "funding" as StrategyCategory,
    asset: "BTC-PERP",
    side: "close",
    notionalUsd: 8900,
    pnlUsd: 31.2,
    feesUsd: 4.8,
    netBps: 3.5,
    revenueSource: "Hyperliquid DEX funding receipt",
  },
  {
    ts: "2026-07-09T11:22:11Z",
    lane: "P12",
    strategyName: "Intent Solver",
    subStrategy: null,
    category: "defi" as StrategyCategory,
    asset: "ARB/USDC",
    side: "buy",
    notionalUsd: 2100,
    pnlUsd: -12.4,
    feesUsd: 1.9,
    netBps: -5.9,
    revenueSource: "Solver slippage miss",
  },
  {
    ts: "2026-07-09T10:55:00Z",
    lane: "P6",
    strategyName: "Liquidation Hunter",
    subStrategy: "flash-close",
    category: "flash" as StrategyCategory,
    asset: "WETH",
    side: "flash-close",
    notionalUsd: 1500,
    pnlUsd: 4.8,
    feesUsd: 0.6,
    netBps: 3.2,
    revenueSource: "Morpho liquidation + Balancer flash",
  },
  {
    ts: "2026-07-09T10:41:33Z",
    lane: "P29",
    strategyName: "MEV Bundle",
    subStrategy: "backrun",
    category: "mev" as StrategyCategory,
    asset: "ETH",
    side: "bundle",
    notionalUsd: 3200,
    pnlUsd: -22.1,
    feesUsd: 8.4,
    netBps: -6.9,
    revenueSource: "Bundle lost to competitor",
  },
  {
    ts: "2026-07-09T10:18:07Z",
    lane: "P22",
    strategyName: "Memecoin Trench",
    subStrategy: "first_block_snipe",
    category: "memecoin" as StrategyCategory,
    asset: "7xKX…9pQm",
    side: "sell",
    notionalUsd: 142,
    pnlUsd: 18.4,
    feesUsd: 0.9,
    netBps: 12.9,
    revenueSource: "Jito-FRA snipe exit",
  },
];

export function formatPnl(usd: number, signed = true): string {
  const abs = Math.abs(usd).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (!signed) return `$${abs}`;
  return `${usd >= 0 ? "+" : "−"}$${abs}`;
}

export function pnlDeltaDir(usd: number): "up" | "down" | undefined {
  if (usd > 0) return "up";
  if (usd < 0) return "down";
  return undefined;
}

export const equitySeries = [
  { t: "Mon", equity: 25000 },
  { t: "Tue", equity: 25340 },
  { t: "Wed", equity: 26110 },
  { t: "Thu", equity: 26880 },
  { t: "Fri", equity: 27420 },
  { t: "Sat", equity: 27990 },
  { t: "Sun", equity: 28450 },
];

/** Funded + active lanes — derived from strategy attribution for dashboard tables. */
export const lanes = pnlByStrategy.map((s) => ({
  id: s.id,
  name: s.name,
  allocation: s.allocationUsd,
  netBps: s.netBps,
  trades: s.trades24h * 30,
  health: s.health,
  pnlWtdUsd: s.wtdUsd,
  pnlMtdUsd: s.mtdUsd,
  category: s.category,
  revenueSource: s.revenueSource,
  phase: s.phase,
}));

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
    id: "act-ct",
    title: "Crypto Twitter: macro bearish tilt easing",
    detail: "NARRATIVE aggregate +0.24 · 842 posts/h · P22 memecoin velocity up",
    ts: "2026-07-09T12:48:00Z",
    tsLabel: "2m ago",
    tone: "info" as const,
  },
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

/** Crypto Twitter / X feed — NARRATIVE ingestion → ORACLE sentiment analyst. */
export const cryptoTwitter = {
  agent: "NARRATIVE",
  tier: "T1 :30000",
  feedStatus: "demo" as const,
  lastIngestTs: "2026-07-09T12:48:00Z",
  postsPerHour: 842,
  trackedAccounts: 156,
  aggregateSentiment: 0.24,
  sentimentConfidence: 0.71,
  lists: [
    { id: "all", label: "All", count: 156 },
    { id: "whales", label: "Whales & funds", count: 42 },
    { id: "kol", label: "KOL / alpha", count: 68 },
    { id: "protocols", label: "Protocols", count: 31 },
    { id: "macro", label: "Macro / policy", count: 18 },
    { id: "memecoin", label: "Memecoin / CT degen", count: 47 },
  ],
  topAccounts: [
    { handle: "lookonchain", followers: "2.1M", list: "whales", posts24h: 18 },
    { handle: "tier10k", followers: "890K", list: "kol", posts24h: 24 },
    { handle: "solana", followers: "3.4M", list: "protocols", posts24h: 6 },
    { handle: "unusual_whales", followers: "1.8M", list: "macro", posts24h: 42 },
    { handle: "aixbt_agent", followers: "420K", list: "kol", posts24h: 31 },
  ],
  posts: [
    {
      id: "ct-001",
      ts: "2026-07-09T12:47:22Z",
      handle: "lookonchain",
      displayName: "Lookonchain",
      verified: true,
      list: "whales" as const,
      text: "A whale bridged 12,400 $ETH ($24.8M) from a cold vault and deposited into Aave in the last 30 minutes. Health factor still >2.1 on linked Morpho position.",
      sentiment: "neutral" as const,
      sentimentScore: 0.05,
      assets: ["ETH", "AAVE"],
      catalyst: { type: "whale_flow", direction: "mixed", magnitude: "high", novelty: 0.82 },
      metrics: { likes: 2840, reposts: 612, replies: 189, views: 420000 },
      url: "https://x.com/lookonchain/status/demo-001",
    },
    {
      id: "ct-002",
      ts: "2026-07-09T12:44:10Z",
      handle: "tier10k",
      displayName: "Tier10k",
      verified: true,
      list: "kol" as const,
      text: "SOL memecoin rotation accelerating again. New Pump.fun launches with >$500K curve in first hour up 3× vs yesterday. Jito tips on FRA path spiking — watch P22 filter pass rate.",
      sentiment: "bullish" as const,
      sentimentScore: 0.62,
      assets: ["SOL"],
      catalyst: { type: "memecoin_velocity", direction: "bullish", magnitude: "medium", novelty: 0.71 },
      metrics: { likes: 1204, reposts: 388, replies: 96, views: 98000 },
      url: "https://x.com/tier10k/status/demo-002",
      pipelines: ["P22"],
    },
    {
      id: "ct-003",
      ts: "2026-07-09T12:41:55Z",
      handle: "unusual_whales",
      displayName: "Unusual Whales",
      verified: true,
      list: "macro" as const,
      text: "Fed speaker hinting at delayed cuts — crypto beta equities soft in pre-market. BTC funding flat but ETH perp OI +4% in 4h. Macro desk watching 2pm ET remarks.",
      sentiment: "bearish" as const,
      sentimentScore: -0.38,
      assets: ["BTC", "ETH"],
      catalyst: { type: "macro_policy", direction: "bearish", magnitude: "medium", novelty: 0.55 },
      metrics: { likes: 3420, reposts: 890, replies: 412, views: 610000 },
      url: "https://x.com/unusual_whales/status/demo-003",
      pipelines: ["P5", "P18"],
    },
    {
      id: "ct-004",
      ts: "2026-07-09T12:38:30Z",
      handle: "solana",
      displayName: "Solana",
      verified: true,
      list: "protocols" as const,
      text: "Mainnet upgrade window confirmed for next epoch boundary. Validators: please review release notes — no breaking RPC changes for Geyser subscribers.",
      sentiment: "neutral" as const,
      sentimentScore: 0.12,
      assets: ["SOL"],
      catalyst: { type: "protocol_upgrade", direction: "neutral", magnitude: "low", novelty: 0.44 },
      metrics: { likes: 8900, reposts: 2100, replies: 340, views: 1200000 },
      url: "https://x.com/solana/status/demo-004",
    },
    {
      id: "ct-005",
      ts: "2026-07-09T12:35:18Z",
      handle: "aixbt_agent",
      displayName: "aixbt",
      verified: true,
      list: "kol" as const,
      text: "Base L2 DEX volume overtook Arbitrum for 6h window — mostly memecoin flow. Base sequencer healthy; watch bridge latency on large exits.",
      sentiment: "bullish" as const,
      sentimentScore: 0.41,
      assets: ["BASE", "ARB"],
      catalyst: { type: "chain_activity", direction: "bullish", magnitude: "medium", novelty: 0.67 },
      metrics: { likes: 620, reposts: 142, replies: 88, views: 54000 },
      url: "https://x.com/aixbt_agent/status/demo-005",
    },
    {
      id: "ct-006",
      ts: "2026-07-09T12:32:04Z",
      handle: "DeFiIgnas",
      displayName: "Ignas | DeFi",
      verified: true,
      list: "kol" as const,
      text: "Morpho Blue USDC vault on Base crossed $400M TVL. Yield compressing but borrow demand from perp hedgers still strong — funding arb desks paying up.",
      sentiment: "bullish" as const,
      sentimentScore: 0.35,
      assets: ["USDC", "MORPHO"],
      catalyst: { type: "defi_tvl", direction: "bullish", magnitude: "low", novelty: 0.48 },
      metrics: { likes: 890, reposts: 210, replies: 64, views: 72000 },
      url: "https://x.com/DeFiIgnas/status/demo-006",
      pipelines: ["P5", "P6"],
    },
    {
      id: "ct-007",
      ts: "2026-07-09T12:28:41Z",
      handle: "wublockchain",
      displayName: "Wu Blockchain",
      verified: true,
      list: "whales" as const,
      text: "Hong Kong regulator approves expanded stablecoin sandbox — HKD-linked pilot with 3 banks. Asia session liquidity narrative improving for BTC pairs on local venues.",
      sentiment: "bullish" as const,
      sentimentScore: 0.48,
      assets: ["BTC", "USDC"],
      catalyst: { type: "regulatory", direction: "bullish", magnitude: "medium", novelty: 0.76 },
      metrics: { likes: 1560, reposts: 420, replies: 98, views: 180000 },
      url: "https://x.com/wublockchain/status/demo-007",
    },
    {
      id: "ct-008",
      ts: "2026-07-09T12:25:12Z",
      handle: "0xMert_",
      displayName: "mert | helius.dev",
      verified: true,
      list: "memecoin" as const,
      text: "If you're sniping Pump.fun without simulating sell path first you're donating. G6 sellability gate exists for a reason — seen 4 honeypots in the last hour on FRA Geyser alone.",
      sentiment: "bearish" as const,
      sentimentScore: -0.22,
      assets: ["SOL"],
      catalyst: { type: "security_warning", direction: "bearish", magnitude: "medium", novelty: 0.59 },
      metrics: { likes: 2100, reposts: 480, replies: 220, views: 145000 },
      url: "https://x.com/0xMert_/status/demo-008",
      pipelines: ["P22"],
    },
    {
      id: "ct-009",
      ts: "2026-07-09T12:21:33Z",
      handle: "VitalikButerin",
      displayName: "vitalik.eth",
      verified: true,
      list: "protocols" as const,
      text: "Quick thread on L2 data availability tradeoffs — not financial advice, but the security margin matters more than raw TPS for most use cases.",
      sentiment: "neutral" as const,
      sentimentScore: 0.08,
      assets: ["ETH"],
      catalyst: { type: "education", direction: "neutral", magnitude: "low", novelty: 0.31 },
      metrics: { likes: 12400, reposts: 2800, replies: 890, views: 890000 },
      url: "https://x.com/VitalikButerin/status/demo-009",
    },
    {
      id: "ct-010",
      ts: "2026-07-09T12:18:00Z",
      handle: "CryptoHayes",
      displayName: "Arthur Hayes",
      verified: true,
      list: "macro" as const,
      text: "Dollar liquidity pulse improving — watch TGA refill cadence. Still constructive BTC into Q3 unless real yields spike another 20bps.",
      sentiment: "bullish" as const,
      sentimentScore: 0.52,
      assets: ["BTC", "USD"],
      catalyst: { type: "macro_liquidity", direction: "bullish", magnitude: "medium", novelty: 0.63 },
      metrics: { likes: 8900, reposts: 1900, replies: 640, views: 520000 },
      url: "https://x.com/CryptoHayes/status/demo-010",
      pipelines: ["P18", "AUGUR"],
    },
  ],
};

export type NewsCategory =
  | "breaking"
  | "macro"
  | "regulation"
  | "markets"
  | "defi"
  | "layer2"
  | "security"
  | "protocol"
  | "etf";

export type NewsImpact = "bullish" | "bearish" | "neutral";
export type NewsSourceTier = "wire" | "tier1" | "tier2";

export const newsCategoryLabels: Record<NewsCategory, string> = {
  breaking: "Breaking",
  macro: "Macro",
  regulation: "Regulation",
  markets: "Markets",
  defi: "DeFi",
  layer2: "Layer 2",
  security: "Security",
  protocol: "Protocol",
  etf: "ETF / TradFi",
};

/** Crypto news wires — NARRATIVE News Analyst → ORACLE NewsReport (TradingAgents schema). */
export const cryptoNews = {
  agent: "NARRATIVE",
  subRole: "News Analyst",
  feedStatus: "demo" as const,
  lastIngestTs: "2026-07-09T13:18:00Z",
  articlesPerHour: 47,
  tier1Sources: 12,
  crossValidated24h: 8,
  aggregateImpact: 0.18 as number,

  marketPulse: {
    btc24hPct: 2.41,
    eth24hPct: 1.86,
    sol24hPct: 4.12,
    fearGreedIndex: 58,
    dominantNarrative: "Spot ETF inflows + delayed-cut Fed speak",
    vix: 14.2,
    dxy24hPct: -0.31,
  },

  calendar: [
    { ts: "2026-07-09T14:00:00Z", event: "US initial jobless claims", impact: "high" as const },
    { ts: "2026-07-09T18:00:00Z", event: "Fed speaker · Waller", impact: "high" as const },
    { ts: "2026-07-10T12:30:00Z", event: "US PPI", impact: "medium" as const },
    { ts: "2026-07-11T08:00:00Z", event: "Solana epoch boundary upgrade window", impact: "medium" as const },
  ],

  sources: [
    { id: "reuters", name: "Reuters", tier: "wire" as NewsSourceTier, reliability: 0.96, articles24h: 14 },
    { id: "bloomberg", name: "Bloomberg Crypto", tier: "wire" as NewsSourceTier, reliability: 0.95, articles24h: 11 },
    { id: "theblock", name: "The Block", tier: "tier1" as NewsSourceTier, reliability: 0.91, articles24h: 22 },
    { id: "coindesk", name: "CoinDesk", tier: "tier1" as NewsSourceTier, reliability: 0.89, articles24h: 28 },
    { id: "blockworks", name: "Blockworks", tier: "tier1" as NewsSourceTier, reliability: 0.87, articles24h: 16 },
    { id: "decrypt", name: "Decrypt", tier: "tier2" as NewsSourceTier, reliability: 0.82, articles24h: 19 },
  ],

  featuredIds: ["news-001", "news-002"],

  articles: [
    {
      id: "news-001",
      ts: "2026-07-09T13:12:00Z",
      headline: "Spot Bitcoin ETFs record $412M net inflow — fourth-largest daily since launch",
      dek: "BlackRock IBIT leads with $280M; ETH ETFs see parallel $98M day as rate-cut odds firm.",
      summary:
        "U.S. spot Bitcoin ETFs posted their strongest inflow day in six weeks, led by BlackRock's IBIT. Analysts tie the move to softer Fed rhetoric and declining real yields rather than a single headline catalyst.",
      bullets: [
        "IBIT +$280M, FBTC +$74M, ARKB +$41M — outflows zero across major issuers",
        "ETH spot products net +$98M; Grayscale ETHE flip continues",
        "CME BTC futures basis widened 8bps — arb desks report fuller books on APAC open",
      ],
      source: { name: "The Block", tier: "tier1" as NewsSourceTier, url: "https://www.theblock.co/post/demo-001" },
      category: "etf" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.68,
      confidence: 0.92,
      assets: ["BTC", "ETH"],
      regions: ["US"],
      pipelines: ["P5", "P18"],
      breaking: true,
      featured: true,
      readMin: 4,
      crossValidated: true,
      corroborationCount: 4,
      corroborationSources: ["Bloomberg Crypto", "CoinDesk", "Reuters", "Blockworks"],
      quote: {
        text: "Flows are tracking macro liquidity again — this looks like allocation, not short-covering.",
        attribution: "ETF desk head, unnamed bulge bracket",
      },
      marketReaction: "BTC +1.8% · ETH +1.2% in 30m post headline cluster",
    },
    {
      id: "news-002",
      ts: "2026-07-09T12:58:00Z",
      headline: "SEC staff issues updated guidance on staking-as-a-service for broker-dealers",
      dek: "Non-custodial delegation paths clarified; registered venues get 90-day compliance runway.",
      summary:
        "SEC Division of Trading and Markets released staff guidance distinguishing custodial staking from pure delegation models. Industry lawyers say the text is narrower than feared but still excludes certain restaking loops without disclosure.",
      bullets: [
        "Broker-dealers may facilitate delegation if client retains on-chain control",
        "Restaking points / airdrop rights require enhanced risk disclosure",
        "90-day comment window before enforcement discretion narrows",
      ],
      source: { name: "CoinDesk", tier: "tier1" as NewsSourceTier, url: "https://www.coindesk.com/policy/demo-002" },
      category: "regulation" as NewsCategory,
      impact: "neutral" as NewsImpact,
      impactScore: 0.12,
      confidence: 0.88,
      assets: ["ETH", "SOL"],
      regions: ["US"],
      pipelines: ["P10", "P16"],
      breaking: true,
      featured: true,
      readMin: 5,
      crossValidated: true,
      corroborationCount: 3,
      corroborationSources: ["Reuters", "The Block"],
      quote: {
        text: "This is a carve-out, not a green light for every yield product wearing a staking badge.",
        attribution: "Katten Muchin partner briefing note",
      },
      marketReaction: "LST tokens flat; RPL −2.1% on disclosure uncertainty",
    },
    {
      id: "news-003",
      ts: "2026-07-09T12:41:00Z",
      headline: "Hyperliquid perp OI hits ATH as Korean venue routing volume spikes",
      dek: "HL daily volume $8.2B; funding neutral despite long skew in top accounts.",
      summary:
        "Hyperliquid open interest crossed $4.1B for the first time as APAC session traders routed flow through AWS Tokyo-adjacent infrastructure. Funding rates stayed near flat, suggesting spot-hedged positioning rather than directional leverage.",
      bullets: [
        "Top 100 accounts net long BTC perp +12% vs 24h ago",
        "Jito-adjacent arb desks report sub-ms path stable on EDGE-TKY",
        "No governance token announcement — move purely flow-driven",
      ],
      source: { name: "Blockworks", tier: "tier1" as NewsSourceTier, url: "https://blockworks.co/news/demo-003" },
      category: "markets" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.44,
      confidence: 0.79,
      assets: ["BTC", "HYPE"],
      regions: ["APAC", "US"],
      pipelines: ["P5", "P8"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: true,
      corroborationCount: 2,
      corroborationSources: ["The Block"],
      marketReaction: "HYPE +6.4% · BTC funding flat",
    },
    {
      id: "news-004",
      ts: "2026-07-09T12:22:00Z",
      headline: "Morpho Blue exploit attempt on Base fails — $0 loss, whitehat tip paid",
      dek: "Oracle manipulation path blocked by guardian module; similar pattern flagged on Arbitrum fork.",
      summary:
        "A planned oracle push attack against a Morpho Blue USDC market on Base was aborted when guardian permissions paused borrows. Morpho Labs confirmed no funds at risk and paid a disclosed whitehat bounty.",
      bullets: [
        "Attack used thin DEX pool as price reference — guardian tripped in same block",
        "Arbitrum clone market put in borrow-only mode pending review",
        "Flash-loan compose simulations updated in ALCHEMY skill catalog",
      ],
      source: { name: "The Block", tier: "tier1" as NewsSourceTier, url: "https://www.theblock.co/post/demo-004" },
      category: "security" as NewsCategory,
      impact: "bearish" as NewsImpact,
      impactScore: -0.28,
      confidence: 0.94,
      assets: ["MORPHO", "USDC", "BASE"],
      regions: ["Global"],
      pipelines: ["P6", "P12"],
      breaking: false,
      featured: false,
      readMin: 4,
      crossValidated: true,
      corroborationCount: 3,
      corroborationSources: ["Decrypt", "CoinDesk"],
      marketReaction: "MORPHO −3.2% · DeFi index −0.4%",
    },
    {
      id: "news-005",
      ts: "2026-07-09T11:55:00Z",
      headline: "Ethereum Fusaka upgrade timeline confirmed for Q4 testnet",
      dek: "PeerDAS + blob throughput target 2× on Hoodi; mainnet date still TBD.",
      summary:
        "Ethereum Foundation published an updated Fusaka roadmap with Hoodi testnet fork in October. Developers emphasized PeerDAS as the gating item for blob capacity expansion, with L2 fee markets expected to compress post-ship.",
      bullets: [
        "Blob target increase from 3 to 6 per block on testnet config",
        "Major L2 sequencers commit to Hoodi participation",
        "No change to mainnet Dencun assumptions for H2 budgeting",
      ],
      source: { name: "CoinDesk", tier: "tier1" as NewsSourceTier, url: "https://www.coindesk.com/tech/demo-005" },
      category: "protocol" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.36,
      confidence: 0.85,
      assets: ["ETH", "ARB", "OP"],
      regions: ["Global"],
      pipelines: ["P12", "P3"],
      breaking: false,
      featured: false,
      readMin: 5,
      crossValidated: true,
      corroborationCount: 3,
      corroborationSources: ["Blockworks", "Decrypt"],
      marketReaction: "ETH L2 tokens mixed · ARB +0.8%",
    },
    {
      id: "news-006",
      ts: "2026-07-09T11:38:00Z",
      headline: "Hong Kong expands stablecoin sandbox — three banks join HKD pilot",
      dek: "Regulator signals path to retail redemption rails by 2027.",
      summary:
        "Hong Kong Monetary Authority added HSBC, Standard Chartered, and a local fintech to its stablecoin sandbox, expanding beyond last year's institutional-only scope. BTC/USDT premium on local OTC desks narrowed 15bps on the headline.",
      bullets: [
        "Pilot covers HKD-linked token with 1:1 reserve attestation monthly",
        "Retail touchpoints remain off-limits until phase 2 review",
        "Mainland China policy unchanged — HK treated as separate experiment",
      ],
      source: { name: "Reuters", tier: "wire" as NewsSourceTier, url: "https://www.reuters.com/technology/demo-006" },
      category: "regulation" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.52,
      confidence: 0.9,
      assets: ["BTC", "USDT", "USDC"],
      regions: ["APAC"],
      pipelines: ["P18", "P1"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: true,
      corroborationCount: 4,
      corroborationSources: ["Bloomberg Crypto", "The Block", "CoinDesk"],
      marketReaction: "Asia session BTC +0.6% · USDT HK premium −15bps",
    },
    {
      id: "news-007",
      ts: "2026-07-09T11:12:00Z",
      headline: "Solana validator vote passes on SIMD-032 — fee market retune for next epoch",
      dek: "Priority fee burn split adjusted; Geyser subscribers get 48h migration notice.",
      summary:
        "Solana validators approved SIMD-032 with 78% stake weight, adjusting local fee market parameters ahead of the scheduled epoch boundary. Infrastructure providers confirmed no breaking changes for Geyser streaming clients.",
      bullets: [
        "Priority fee burn ratio shifts 50/50 → 60/40 validator/burn",
        "No RPC breaking changes for standard JSON-RPC users",
        "Memecoin launch velocity unchanged in first 2h post vote",
      ],
      source: { name: "Blockworks", tier: "tier1" as NewsSourceTier, url: "https://blockworks.co/news/demo-007" },
      category: "protocol" as NewsCategory,
      impact: "neutral" as NewsImpact,
      impactScore: 0.08,
      confidence: 0.87,
      assets: ["SOL"],
      regions: ["Global"],
      pipelines: ["P22"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: true,
      corroborationCount: 2,
      corroborationSources: ["Decrypt"],
      marketReaction: "SOL +0.3% · Jito tips stable",
    },
    {
      id: "news-008",
      ts: "2026-07-09T10:48:00Z",
      headline: "Fed's Waller: 'Several cuts possible in 2026 if inflation cooperates'",
      dek: "Markets price +18bps easing by December; crypto beta equities rip in pre-market.",
      summary:
        "Fed Governor Christopher Waller said disinflation could allow multiple rate cuts this year if labor market cooling continues. Crypto-correlated equities led pre-market gains; BTC moved in lockstep with NASDAQ futures.",
      bullets: [
        "2Y yield −6bps immediate reaction · DXY soft",
        "BTC correlation to QQQ 0.82 on 30d rolling window",
        "Perp funding unchanged — move led by spot and ETF flows",
      ],
      source: { name: "Bloomberg Crypto", tier: "wire" as NewsSourceTier, url: "https://www.bloomberg.com/crypto/demo-008" },
      category: "macro" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.61,
      confidence: 0.93,
      assets: ["BTC", "ETH", "USD"],
      regions: ["US", "Global"],
      pipelines: ["P5", "P18", "AUGUR"],
      breaking: false,
      featured: false,
      readMin: 4,
      crossValidated: true,
      corroborationCount: 5,
      corroborationSources: ["Reuters", "CoinDesk", "The Block", "Blockworks"],
      quote: {
        text: "Several cuts are possible in 2026 if we continue to see the inflation progress we've had.",
        attribution: "Fed Governor Christopher Waller",
      },
      marketReaction: "BTC +2.1% · ETH +1.7% · QQQ futures +0.9%",
    },
    {
      id: "news-009",
      ts: "2026-07-09T10:22:00Z",
      headline: "Uniswap v4 hook volume crosses $2B cumulative on Base and Arbitrum",
      dek: "Custom AMM hooks drive 34% of DEX share on Base in 24h window.",
      summary:
        "Uniswap Labs reported v4 hook-enabled pools surpassed $2B cumulative volume since launch, with Base capturing the majority of incremental flow. Intent solver desks report tighter spreads on routed size >$50K.",
      bullets: [
        "Top hook: dynamic-fee market maker representing 41% of v4 volume",
        "Flash-loan arb routes updated in P12 intent catalog",
        "No governance proposal active on fee switch",
      ],
      source: { name: "The Block", tier: "tier1" as NewsSourceTier, url: "https://www.theblock.co/post/demo-009" },
      category: "defi" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.38,
      confidence: 0.81,
      assets: ["UNI", "ETH", "BASE"],
      regions: ["Global"],
      pipelines: ["P12", "P3"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: false,
      corroborationCount: 1,
      corroborationSources: [],
      marketReaction: "UNI +2.4%",
    },
    {
      id: "news-010",
      ts: "2026-07-09T09:58:00Z",
      headline: "Base sequencer incident post-mortem — 14-minute partial outage",
      dek: "Block production stalled; no reorg; user txs replayed successfully.",
      summary:
        "Base published a post-mortem on a 14-minute sequencer stall caused by a failed state sync on a redundant node. No funds lost; large bridge exits experienced delay but eventual inclusion.",
      bullets: [
        "Root cause: corrupted snapshot on hot standby — failover logic patched",
        "Bridge watchers flagged 22 delayed L1→L2 deposits >10 min",
        "P3 cross-rollup arb paused automatically via CB_BRIDGE_LATENCY",
      ],
      source: { name: "Decrypt", tier: "tier2" as NewsSourceTier, url: "https://decrypt.co/demo-010" },
      category: "layer2" as NewsCategory,
      impact: "bearish" as NewsImpact,
      impactScore: -0.22,
      confidence: 0.86,
      assets: ["BASE", "ETH"],
      regions: ["US"],
      pipelines: ["P3", "P12"],
      breaking: false,
      featured: false,
      readMin: 4,
      crossValidated: true,
      corroborationCount: 2,
      corroborationSources: ["The Block", "CoinDesk"],
      marketReaction: "BASE ecosystem tokens −1.1%",
    },
    {
      id: "news-011",
      ts: "2026-07-09T09:30:00Z",
      headline: "CME crypto options open interest record — institutions hedge ETF basis",
      dek: "BTC options OI $42B notional; put/call skew flattens.",
      summary:
        "CME Group crypto derivatives open interest hit a record as ETF market makers increased options hedges ahead of macro data. Skew normalization suggests less demand for crash protection vs last month.",
      bullets: [
        "Weekly BTC options +18% OI · ETH +12%",
        "Large block trades flagged in 0DTE products",
        "Correlated with IBIT options market making expansion",
      ],
      source: { name: "Bloomberg Crypto", tier: "wire" as NewsSourceTier, url: "https://www.bloomberg.com/crypto/demo-011" },
      category: "markets" as NewsCategory,
      impact: "neutral" as NewsImpact,
      impactScore: 0.05,
      confidence: 0.84,
      assets: ["BTC", "ETH"],
      regions: ["US"],
      pipelines: ["P5", "P1"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: true,
      corroborationCount: 2,
      corroborationSources: ["Reuters"],
      marketReaction: "Implied vol −1.2 vol points",
    },
    {
      id: "news-012",
      ts: "2026-07-09T08:45:00Z",
      headline: "Pump.fun daily launches down 28% WoW as Solana memecoin fatigue sets in",
      dek: "Graduation rate unchanged — quality filter narrative vs raw launch count.",
      summary:
        "On-chain data shows Pump.fun token creations fell 28% week-over-week while graduation-to-Raydium rate held steady. Traders debate whether lower launch volume reflects healthier market or reduced retail appetite.",
      bullets: [
        "Median curve peak $18K vs $14K prior week — higher quality launches",
        "Jito tips on FRA path −12% — aligns with P22 filter pass rate data",
        "Smart money mirror wallets still active — 41 tracked entries 24h",
      ],
      source: { name: "Blockworks", tier: "tier1" as NewsSourceTier, url: "https://blockworks.co/news/demo-012" },
      category: "markets" as NewsCategory,
      impact: "neutral" as NewsImpact,
      impactScore: -0.08,
      confidence: 0.76,
      assets: ["SOL"],
      regions: ["Global"],
      pipelines: ["P22"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: false,
      corroborationCount: 1,
      corroborationSources: [],
      marketReaction: "SOL flat · memecoin index −2.3%",
    },
    {
      id: "news-013",
      ts: "2026-07-09T08:10:00Z",
      headline: "EU MiCA stablecoin cap report due next week — USDC issuer prepares disclosure",
      dek: "Circle says reserves already MiCA-aligned; Tether EU routing unchanged.",
      summary:
        "European Banking Authority previewed next week's MiCA stablecoin market report. Circle confirmed reserve composition documentation ready; industry expects caps discussion but no immediate trading halts.",
      bullets: [
        "EBA report covers June 30 AUM snapshot across EEA issuers",
        "No new enforcement actions expected in July window",
        "EURC volume +22% on compliant venues month-to-date",
      ],
      source: { name: "Reuters", tier: "wire" as NewsSourceTier, url: "https://www.reuters.com/technology/demo-013" },
      category: "regulation" as NewsCategory,
      impact: "neutral" as NewsImpact,
      impactScore: 0.1,
      confidence: 0.89,
      assets: ["USDC", "USDT", "EUR"],
      regions: ["EU"],
      pipelines: ["P16", "P18"],
      breaking: false,
      featured: false,
      readMin: 4,
      crossValidated: true,
      corroborationCount: 3,
      corroborationSources: ["CoinDesk", "The Block"],
      marketReaction: "USDC flat · EUR stable pairs unchanged",
    },
    {
      id: "news-014",
      ts: "2026-07-09T07:52:00Z",
      headline: "Flashbots Protect expands L2 coverage — Base and Arbitrum bundles live",
      dek: "Private tx flow +19% on Arbitrum in beta week; MEV refund stats published.",
      summary:
        "Flashbots announced Protect coverage for Base and Arbitrum sequencers, publishing first-week stats on private transaction inclusion and MEV refunds. Intent solver operators report lower failed bundle rate on large swaps.",
      bullets: [
        "Arbitrum private flow +19% vs prior 7d baseline",
        "Base coverage limited to select RPC partners in beta",
        "P29 MEV bundle lane monitoring for overlap — still defunded",
      ],
      source: { name: "CoinDesk", tier: "tier1" as NewsSourceTier, url: "https://www.coindesk.com/tech/demo-014" },
      category: "layer2" as NewsCategory,
      impact: "bullish" as NewsImpact,
      impactScore: 0.29,
      confidence: 0.83,
      assets: ["ETH", "ARB", "BASE"],
      regions: ["Global"],
      pipelines: ["P12", "P29"],
      breaking: false,
      featured: false,
      readMin: 3,
      crossValidated: true,
      corroborationCount: 2,
      corroborationSources: ["The Block"],
      marketReaction: "ARB +0.5% · MEV share metrics pending",
    },
  ],

  categories: [
    { id: "all", label: "All", count: 14 },
    { id: "breaking", label: "Breaking", count: 2 },
    { id: "macro", label: "Macro", count: 1 },
    { id: "regulation", label: "Regulation", count: 3 },
    { id: "markets", label: "Markets", count: 3 },
    { id: "defi", label: "DeFi", count: 1 },
    { id: "layer2", label: "Layer 2", count: 2 },
    { id: "security", label: "Security", count: 1 },
    { id: "protocol", label: "Protocol", count: 2 },
    { id: "etf", label: "ETF / TradFi", count: 1 },
  ] as { id: NewsCategory | "all"; label: string; count: number }[],
};

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
  { id: "g1", title: "Harvest phase active (≥$15K)", progress: 100, target: "$15,000", eta: "unlocked" },
  { id: "g2", title: "≥200 fills / funded lane", progress: 64, target: "200 fills", eta: "Phase 1 stretch" },
  { id: "g3", title: "Kill-switch drill monthly", progress: 100, target: "pass", eta: "done" },
  { id: "g4", title: "Wire live signer_module", progress: 20, target: "trezor", eta: "pre-live gate" },
];

export const automations = [
  { id: "a1", name: "TCA → allocator profit loop", schedule: "every fill batch", enabled: true },
  { id: "a2", name: "Weekly profit sweep (≥$15K)", schedule: "Sun 00:00 UTC", enabled: true },
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
  sweepThresholdUsd: 15000,
  sweepPct: 20,
  sweepDayUtc: "Sunday",
  growthPhase: false, // equity < $15K → 100% reinvest, no sweep
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

/** Professional multi-chain wallet tracker (recon + on-chain aggregation). */
export const walletTracker = {
  lastSyncTs: "2026-07-09T12:40:00Z",
  reconLagSeconds: 12,
  sources: ["reconciliation :19002", "Erigon :8545", "Helius RPC", "DEX / on-chain balances"],
  totalAumUsd: 28450.32,
  hotAumUsd: 14220.5,
  coldAumUsd: 14229.82,
  change24hUsd: 412.8,
  change24hPct: 1.47,
  accounts: [
    {
      id: "hot-ops",
      label: "Hot ops · signing_node",
      group: "Trading",
      kind: "hot" as const,
      chains: ["ethereum", "arbitrum", "base"],
      address: "0x7a3F…c4e2",
      addressFull: "0x7a3F8b2c1d9e4A5f6B7c8D9e0F1a2B3c4D5e6F7c4e2",
      balanceUsd: 12120.5,
      change24hUsd: 286.4,
      change24hPct: 2.42,
      allocationPct: 42.6,
      status: "synced" as const,
      lastTxTs: "2026-07-09T12:38:11Z",
      role: "TRENCH-OPS execution · session keys only",
      signingPath: "127.0.0.1:19010",
      holdings: [
        { symbol: "USDC", name: "USD Coin", amount: 8420.12, usd: 8420.12, chain: "arbitrum", pct: 69.5 },
        { symbol: "ETH", name: "Ether", amount: 1.42, usd: 2840.0, chain: "ethereum", pct: 23.4 },
        { symbol: "USDC", name: "USD Coin", amount: 860.38, usd: 860.38, chain: "base", pct: 7.1 },
      ],
    },
    {
      id: "edge-fra-sol",
      label: "EDGE-FRA · Solana float",
      group: "Edge",
      kind: "edge" as const,
      chains: ["solana"],
      address: "So1aB…9kQm",
      addressFull: "So1aB2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9kQm",
      balanceUsd: 1420.0,
      change24hUsd: -18.2,
      change24hPct: -1.27,
      allocationPct: 5.0,
      status: "synced" as const,
      lastTxTs: "2026-07-09T12:35:44Z",
      role: "Jito tips + P22 broadcast float",
      edgePop: "EDGE-FRA",
      holdings: [
        { symbol: "SOL", name: "Solana", amount: 8.42, usd: 1180.0, chain: "solana", pct: 83.1 },
        { symbol: "USDC", name: "USD Coin", amount: 240.0, usd: 240.0, chain: "solana", pct: 16.9 },
      ],
    },
    {
      id: "edge-fra-evm",
      label: "EDGE-FRA · EVM relay",
      group: "Edge",
      kind: "edge" as const,
      chains: ["ethereum"],
      address: "0x9c2E…1aF0",
      addressFull: "0x9c2E4f5A6b7C8d9E0f1A2b3C4d5E6f7A8b9C0d1aF0",
      balanceUsd: 680.0,
      change24hUsd: 12.0,
      change24hPct: 1.79,
      allocationPct: 2.4,
      status: "synced" as const,
      lastTxTs: "2026-07-09T11:58:02Z",
      role: "Flashbots / builder relay gas",
      edgePop: "EDGE-FRA",
      holdings: [
        { symbol: "ETH", name: "Ether", amount: 0.34, usd: 680.0, chain: "ethereum", pct: 100 },
      ],
    },
    {
      id: "dex-uni-arb",
      label: "Uniswap / Curve arb float",
      group: "DEX",
      kind: "hot" as const,
      chains: ["ethereum", "arbitrum"],
      address: "0x4a1B…c8E2",
      addressFull: "0x4a1B7d9e2F3c4A5b6C7d8E9f0A1b2C3d4E5f6a7Bc8E2",
      balanceUsd: 6240.0,
      change24hUsd: 98.6,
      change24hPct: 1.6,
      allocationPct: 21.9,
      status: "synced" as const,
      lastTxTs: "2026-07-09T12:39:55Z",
      role: "P1 DEX cross-venue arb · Uniswap / Curve / Balancer",
      holdings: [
        { symbol: "USDC", name: "USD Coin", amount: 4100.0, usd: 4100.0, chain: "ethereum", pct: 65.7 },
        { symbol: "WETH", name: "Wrapped Ether", amount: 1.07, usd: 2140.0, chain: "ethereum", pct: 34.3 },
      ],
    },
    {
      id: "dex-hl-margin",
      label: "Hyperliquid DEX · margin",
      group: "DEX",
      kind: "hot" as const,
      chains: ["hyperliquid"],
      address: "hl:dex-margin-02",
      addressFull: "hl:dex-margin-02",
      balanceUsd: 3890.0,
      change24hUsd: 44.2,
      change24hPct: 1.15,
      allocationPct: 13.7,
      status: "lagging" as const,
      lastTxTs: "2026-07-09T12:22:18Z",
      role: "P5 DEX funding carry · hedge leg",
      holdings: [
        { symbol: "USDC", name: "USD Coin", amount: 3890.0, usd: 3890.0, chain: "hyperliquid", pct: 100 },
      ],
    },
    {
      id: "trezor-safe-7",
      label: "Trezor Safe 7 · cold vault",
      group: "Vault",
      kind: "cold" as const,
      chains: ["ethereum", "bitcoin"],
      address: "trezor:safe-7",
      addressFull: "bc1q…x7k9 · 0xCold…Vault",
      balanceUsd: 14229.82,
      change24hUsd: 0,
      change24hPct: 0,
      allocationPct: 50.0,
      status: "synced" as const,
      lastTxTs: "2026-06-01T14:00:00Z",
      role: "R23 weekly profit sweep · ceremony on Mac Mini",
      holdings: [
        { symbol: "USDC", name: "USD Coin", amount: 12000.0, usd: 12000.0, chain: "ethereum", pct: 84.3 },
        { symbol: "BTC", name: "Bitcoin", amount: 0.021, usd: 2229.82, chain: "bitcoin", pct: 15.7 },
      ],
    },
    {
      id: "deposit-inbound",
      label: "Deposit inbound · on-chain only",
      group: "Treasury",
      kind: "deposit" as const,
      chains: ["ethereum", "arbitrum", "base", "solana"],
      address: "0xDep0…tAddr",
      addressFull: "0xDep0s1tAddrRotatedNeverReuse0000000000001",
      balanceUsd: 0,
      change24hUsd: 0,
      change24hPct: 0,
      allocationPct: 0,
      status: "synced" as const,
      lastTxTs: "2026-07-01T14:00:00Z",
      role: "Rotating on-chain deposit address · never reused (CB_DEPOSIT_ADDR_REUSE) · DEX-only",
      holdings: [],
    },
    {
      id: "macmini-meta",
      label: "Mac Mini vault metadata",
      group: "Vault",
      kind: "cold" as const,
      chains: ["—"],
      address: "vault://macmini",
      addressFull: "vault://macmini",
      balanceUsd: 0,
      change24hUsd: 0,
      change24hPct: 0,
      allocationPct: 0,
      status: "synced" as const,
      lastTxTs: "—",
      role: "Key metadata only — no live signing",
      holdings: [],
    },
  ],
  chainAllocation: [
    { chain: "Ethereum", usd: 15250, pct: 53.6 },
    { chain: "Arbitrum", usd: 8420, pct: 29.6 },
    { chain: "Hyperliquid", usd: 3890, pct: 13.7 },
    { chain: "Solana", usd: 1420, pct: 5.0 },
    { chain: "Base", usd: 860, pct: 3.0 },
    { chain: "Bitcoin", usd: 2230, pct: 7.8 },
  ],
  recentFlows: [
    { ts: "2026-07-09T12:38:11Z", walletId: "hot-ops", direction: "out" as const, asset: "USDC", amount: 4200, amountUsd: 4200, txHash: "0xab12…9f0e", flowType: "trade_fill", status: "confirmed" },
    { ts: "2026-07-09T12:35:44Z", walletId: "edge-fra-sol", direction: "out" as const, asset: "SOL", amount: 0.05, amountUsd: 7.1, txHash: "5kQm…8nWp", flowType: "jito_tip", status: "confirmed" },
    { ts: "2026-07-09T12:22:18Z", walletId: "dex-hl-margin", direction: "in" as const, asset: "USDC", amount: 1200, amountUsd: 1200, txHash: "0xhl…fund", flowType: "rebalance", status: "confirmed" },
    { ts: "2026-07-09T11:10:00Z", walletId: "hot-ops", direction: "in" as const, asset: "ETH", amount: 0.12, amountUsd: 240, txHash: "0xcd34…1a2b", flowType: "arb_close", status: "confirmed" },
    { ts: "2026-07-01T14:00:00Z", walletId: "deposit-inbound", direction: "in" as const, asset: "USDC", amount: 2500, amountUsd: 2500, txHash: "0xdep…9912", flowType: "deposit", status: "cleared" },
    { ts: "2026-05-18T00:00:00Z", walletId: "trezor-safe-7", direction: "in" as const, asset: "USDC", amount: 0, amountUsd: 0, txHash: "—", flowType: "sweep_skipped", status: "skipped" },
  ],
  /** Preset external wallets — whales & smart money (PREDATOR / WRAITH feeds). */
  watchedPresets: [
    {
      id: "whale-jump-eth",
      label: "Jump Trading · ETH vault (tagged)",
      category: "whale" as const,
      chains: ["ethereum"],
      addressFull: "0x9b9eaa230E810C1730109fD2DD0410E644d27FBD",
      balanceUsd: 124_800_000,
      change24hUsd: 2_140_000,
      change24hPct: 1.74,
      lastTxTs: "2026-07-09T12:01:22Z",
      role: "Market maker · large DEX/router flow",
      tags: ["nansen", "mev-adjacent"],
      holdings: [
        { symbol: "ETH", name: "Ether", amount: 42000, usd: 84_000_000, chain: "ethereum", pct: 67.3 },
        { symbol: "USDC", name: "USD Coin", amount: 28_400_000, usd: 28_400_000, chain: "ethereum", pct: 22.8 },
        { symbol: "WBTC", name: "Wrapped Bitcoin", amount: 120, usd: 12_400_000, chain: "ethereum", pct: 9.9 },
      ],
    },
    {
      id: "whale-sol-sm",
      label: "Solana smart money · memecoin cluster",
      category: "smart_money" as const,
      chains: ["solana"],
      addressFull: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJos2Asq",
      balanceUsd: 4_820_000,
      change24hUsd: 890_000,
      change24hPct: 22.6,
      lastTxTs: "2026-07-09T11:55:00Z",
      role: "Early Pump.fun entries · P22 mirror candidate",
      tags: ["pump.fun", "geyser"],
      holdings: [
        { symbol: "SOL", name: "Solana", amount: 14200, usd: 1_980_000, chain: "solana", pct: 41.1 },
        { symbol: "BONK", name: "Bonk", amount: 88_000_000_000, usd: 1_420_000, chain: "solana", pct: 29.5 },
        { symbol: "USDC", name: "USD Coin", amount: 1_420_000, usd: 1_420_000, chain: "solana", pct: 29.4 },
      ],
    },
    {
      id: "whale-vitalik",
      label: "vitalik.eth (public)",
      category: "influencer" as const,
      chains: ["ethereum"],
      addressFull: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
      balanceUsd: 3_240_000,
      change24hUsd: -42_000,
      change24hPct: -1.28,
      lastTxTs: "2026-07-09T08:12:00Z",
      role: "High-signal macro wallet · news adjacency",
      tags: ["ens"],
      holdings: [
        { symbol: "ETH", name: "Ether", amount: 820, usd: 1_640_000, chain: "ethereum", pct: 50.6 },
        { symbol: "USDC", name: "USD Coin", amount: 980_000, usd: 980_000, chain: "ethereum", pct: 30.2 },
        { symbol: "KERMIT", name: "Kermit", amount: 420_000_000, usd: 620_000, chain: "ethereum", pct: 19.2 },
      ],
    },
    {
      id: "competitor-copy",
      label: "Copy-trader cluster · sandwich adj",
      category: "competitor" as const,
      chains: ["ethereum", "arbitrum"],
      addressFull: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      balanceUsd: 890_000,
      change24hUsd: 12_400,
      change24hPct: 1.41,
      lastTxTs: "2026-07-09T10:48:33Z",
      role: "PREDATOR stalk target · counter-copy poison eligible",
      tags: ["stalking", "reaper"],
      holdings: [
        { symbol: "USDC", name: "USD Coin", amount: 620_000, usd: 620_000, chain: "ethereum", pct: 69.7 },
        { symbol: "ETH", name: "Ether", amount: 135, usd: 270_000, chain: "ethereum", pct: 30.3 },
      ],
    },
  ],
  watchedFlows: [
    { ts: "2026-07-09T12:01:22Z", walletId: "whale-jump-eth", direction: "out" as const, asset: "USDC", amount: 8_400_000, amountUsd: 8_400_000, txHash: "0x88a1…3c2d", flowType: "whale_transfer", status: "confirmed" },
    { ts: "2026-07-09T11:55:00Z", walletId: "whale-sol-sm", direction: "in" as const, asset: "SOL", amount: 4200, amountUsd: 588_000, txHash: "4nWp…k9Qm", flowType: "pump_snipe", status: "confirmed" },
    { ts: "2026-07-09T11:42:00Z", walletId: "whale-sol-sm", direction: "out" as const, asset: "BONK", amount: 12_000_000_000, amountUsd: 194_000, txHash: "5mTy…3vLk", flowType: "take_profit", status: "confirmed" },
    { ts: "2026-07-09T10:48:33Z", walletId: "competitor-copy", direction: "in" as const, asset: "ETH", amount: 42, amountUsd: 84_000, txHash: "0x7f2b…9a1c", flowType: "copy_follow", status: "confirmed" },
    { ts: "2026-07-09T08:12:00Z", walletId: "whale-vitalik", direction: "out" as const, asset: "ETH", amount: 100, amountUsd: 200_000, txHash: "0x2c91…8e4f", flowType: "donation", status: "confirmed" },
  ],
};

export const capitalTxns = [
  { ts: "2026-07-01T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Biweekly injection", status: "cleared" },
  { ts: "2026-06-15T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Biweekly injection", status: "cleared" },
  { ts: "2026-06-01T14:00:00Z", type: "deposit", amount: 2500, asset: "USDC", note: "Starting capital tranche", status: "cleared" },
  { ts: "2026-07-07T00:00:00Z", type: "sweep", amount: 168.43, asset: "USDC", note: "R23 · 20% weekly profit → Trezor Safe 7", status: "cleared" },
  { ts: "2026-05-18T00:00:00Z", type: "sweep", amount: 0, asset: "USDC", note: "Skipped — equity <$15K growth phase", status: "skipped" },
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

export type LatencySegmentStatus = "ok" | "warn" | "breach";

export function latencySegmentStatus(liveP95Ms: number, budgetP95Ms: number): LatencySegmentStatus {
  if (liveP95Ms > budgetP95Ms) return "breach";
  if (liveP95Ms > budgetP95Ms * 0.85) return "warn";
  return "ok";
}

/** Comprehensive latency observatory — mirrors latency_budget.yaml + latency_fast_path.yaml */
export const latencyCenter = {
  version: "1.1",
  priority: "millisecond_first",
  overallStatus: "ok" as LatencySegmentStatus,
  lastProbeAt: "2026-07-09T13:04:22Z",
  probeAgent: "FORGE",
  paperLatencyFaithful: true,
  fullMeshFromPaper: true,

  hotPath: {
    gateTimeoutSec: 0.15,
    signingReceiptMaxAgeSec: 10,
    combinedValidate: true,
    segments: [
      { id: "gate_combined", label: "Gate · fast_validate", endpoint: "POST /v1/fast_validate", budgetP95Ms: 15, liveP50Ms: 8.2, liveP95Ms: 12.1, status: "ok" as LatencySegmentStatus },
      { id: "gate_receipt", label: "Gate receipt issue", endpoint: "localhost", budgetP95Ms: 2, liveP50Ms: 0.9, liveP95Ms: 1.4, status: "ok" as LatencySegmentStatus },
      { id: "signing_verify", label: "Signing verify", endpoint: ":19010 signing_node", budgetP95Ms: 5, liveP50Ms: 2.1, liveP95Ms: 3.8, status: "ok" as LatencySegmentStatus },
      { id: "nostr_dispatch", label: "Nostr dispatch", endpoint: "Kind 1059 → edge", budgetP95Ms: 3, liveP50Ms: 1.2, liveP95Ms: 2.4, status: "ok" as LatencySegmentStatus },
      { id: "home_to_edge", label: "Home → edge (WG)", endpoint: "TITANHOME → PoP", budgetP95Ms: 25, liveP50Ms: 16.4, liveP95Ms: 21.8, status: "ok" as LatencySegmentStatus },
      { id: "edge_to_jito", label: "Edge → Jito BE", endpoint: "EDGE-FRA colo", budgetP95Ms: 5, liveP50Ms: 1.8, liveP95Ms: 3.6, status: "ok" as LatencySegmentStatus },
      { id: "edge_to_rpc", label: "Edge → RPC", endpoint: "Erigon / gRPC", budgetP95Ms: 8, liveP50Ms: 2.9, liveP95Ms: 5.9, status: "ok" as LatencySegmentStatus },
      { id: "total_submit", label: "Total submit E2E", endpoint: "intent → ack", budgetP95Ms: 50, liveP50Ms: 28.4, liveP95Ms: 41.2, status: "ok" as LatencySegmentStatus },
    ],
  },

  warmPath: {
    segments: [
      { id: "execution_gate", label: "Execution gate total", budgetP95Ms: 150, liveP95Ms: 96.4, status: "ok" as LatencySegmentStatus },
      { id: "reconciliation", label: "Reconciliation", budgetP95Ms: 50, liveP95Ms: 30.8, endpoint: ":19002", status: "ok" as LatencySegmentStatus },
      { id: "risk_kernel", label: "Risk kernel", budgetP95Ms: 30, liveP95Ms: 17.6, endpoint: ":19001", status: "ok" as LatencySegmentStatus },
      { id: "tier1_ttft", label: "Tier 1 TTFT", budgetP95Ms: 300, liveP95Ms: 244.0, endpoint: ":30000", status: "ok" as LatencySegmentStatus },
      { id: "embedder", label: "Embedder", budgetP95Ms: 15, liveP95Ms: 8.7, endpoint: ":30004", status: "ok" as LatencySegmentStatus },
      { id: "mem0_recall", label: "Mem0 recall", budgetP95Ms: 20, liveP95Ms: 13.2, status: "ok" as LatencySegmentStatus },
    ],
  },

  inference: {
    tier1FirstTokenWarmP95Ms: 250,
    tier1FirstTokenColdP95Ms: 2000,
    tier2MustNotBlockTier1: true,
    liveTier1WarmP95Ms: 218,
    liveTier1ColdP95Ms: 1840,
    note: "Inference tiers off hot path for P22 / P29 / P12 / P30",
  },

  feeds: {
    nexusStalenessMaxSec: 5,
    rpcTimeoutSec: 1,
    websocketReconnectMs: 200,
    liveNexusStalenessSec: 2.1,
    liveRpcP95Ms: 780,
    status: "fresh" as const,
  },

  pipelineClasses: [
    { id: "P22", name: "Memecoin Trench", pathClass: "hot" as const, edgePop: "EDGE-FRA", skipDebate: true, liveGateP95Ms: 11.2 },
    { id: "P29", name: "MEV Bundle", pathClass: "hot" as const, edgePop: "EDGE-FRA", skipDebate: true, liveGateP95Ms: 13.8 },
    { id: "P12", name: "Intent Solver", pathClass: "hot" as const, edgePop: "EDGE-FRA", skipDebate: true, liveGateP95Ms: 12.4 },
    { id: "P30", name: "Cross-chain MEV", pathClass: "hot" as const, edgePop: "EDGE-TKY", skipDebate: true, liveGateP95Ms: 14.1 },
    { id: "P1", name: "DEX Cross-Venue Arb", pathClass: "warm" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: 88.2 },
    { id: "P3", name: "Cross-Rollup Arb", pathClass: "warm" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: 102.4 },
    { id: "P6", name: "Liquidation Hunter", pathClass: "warm" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: 94.1 },
    { id: "P7", name: "DEX Basis / Spread", pathClass: "warm" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: 91.0 },
    { id: "P8", name: "APAC DEX / AMM", pathClass: "warm" as const, edgePop: "EDGE-SIN", skipDebate: false, liveGateP95Ms: 79.6 },
    { id: "P11", name: "Prediction Arb", pathClass: "warm" as const, edgePop: "EDGE-USE", skipDebate: false, liveGateP95Ms: 112.8 },
    { id: "P18", name: "Macro Catalyst", pathClass: "warm" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: 118.4 },
    { id: "P34", name: "CLMM 2.0", pathClass: "cold" as const, edgePop: "EDGE-FRA", skipDebate: false, liveGateP95Ms: null },
    { id: "P40", name: "DGM-H Shadow", pathClass: "cold" as const, edgePop: "—", skipDebate: false, liveGateP95Ms: null },
    { id: "P41", name: "GEPA Promotion", pathClass: "cold" as const, edgePop: "—", skipDebate: false, liveGateP95Ms: null },
  ],

  venueRtt: [
    { venue: "Uniswap v4 router", protocol: "Uniswap", pop: "EDGE-FRA", region: "Frankfurt", p50Ms: 2.4, p95Ms: 4.1, targetMs: 8, status: "ok" as LatencySegmentStatus },
    { venue: "Curve TriCrypto", protocol: "Curve", pop: "EDGE-FRA", region: "Frankfurt", p50Ms: 2.8, p95Ms: 4.8, targetMs: 8, status: "ok" as LatencySegmentStatus },
    { venue: "Hyperliquid DEX (hl-visor)", protocol: "Hyperliquid", pop: "EDGE-TKY", region: "ap-northeast-1", p50Ms: 0.6, p95Ms: 1.1, targetMs: 1, status: "warn" as LatencySegmentStatus },
    { venue: "PancakeSwap / BSC RPC", protocol: "PancakeSwap", pop: "EDGE-SIN", region: "ap-southeast-1", p50Ms: 0.8, p95Ms: 1.4, targetMs: 3, status: "ok" as LatencySegmentStatus },
    { venue: "Jito block engine FRA", protocol: "Solana", pop: "EDGE-FRA", region: "Frankfurt", p50Ms: 2.1, p95Ms: 3.6, targetMs: 5, status: "ok" as LatencySegmentStatus },
    { venue: "Flashbots Protect", protocol: "Ethereum", pop: "EDGE-USE", region: "us-east-1", p50Ms: 1.8, p95Ms: 2.9, targetMs: 3, status: "ok" as LatencySegmentStatus },
    { venue: "Base / OP / ARB sequencers", protocol: "L2 DEX", pop: "EDGE-USE", region: "us-east-1", p50Ms: 1.2, p95Ms: 2.4, targetMs: 3, status: "ok" as LatencySegmentStatus },
    { venue: "Erigon archive RPC", protocol: "Ethereum", pop: "EDGE-FRA", region: "Frankfurt", p50Ms: 3.2, p95Ms: 5.9, targetMs: 8, status: "ok" as LatencySegmentStatus },
    { venue: "Solana gRPC (AMS)", protocol: "Solana", pop: "EDGE-AMS", region: "Amsterdam", p50Ms: 3.8, p95Ms: 4.9, targetMs: 5, status: "ok" as LatencySegmentStatus },
  ],

  popHealth: [
    { id: "EDGE-FRA", region: "Frankfurt DE-CIX", targets: "Jito FRA, Erigon, Uniswap/Curve/Balancer", rtt: "≤5ms", status: "healthy", wg: "10.0.10.100", liveP50Ms: 3.4, liveP95Ms: 4.8, wgLatencyP95Ms: 21.8, lastProbeAt: "2026-07-09T13:04:22Z" },
    { id: "EDGE-TKY", region: "ap-northeast-1", targets: "Hyperliquid DEX, Jito-TKY", rtt: "<1ms", status: "healthy", wg: "10.0.10.101", liveP50Ms: 0.6, liveP95Ms: 1.0, wgLatencyP95Ms: 38.2, lastProbeAt: "2026-07-09T13:04:22Z" },
    { id: "EDGE-SIN", region: "ap-southeast-1", targets: "BSC DEX, Sui, PancakeSwap", rtt: "<1ms", status: "healthy", wg: "10.0.10.102", liveP50Ms: 0.6, liveP95Ms: 1.0, wgLatencyP95Ms: 42.1, lastProbeAt: "2026-07-09T13:04:22Z" },
    { id: "EDGE-USE", region: "us-east-1", targets: "L2 sequencers, Flashbots, Base DEX", rtt: "≤3ms", status: "healthy", wg: "10.0.10.103", liveP50Ms: 2.1, liveP95Ms: 2.8, wgLatencyP95Ms: 48.6, lastProbeAt: "2026-07-09T13:04:22Z" },
    { id: "EDGE-AMS", region: "Amsterdam AMS-IX", targets: "Solana gRPC, Nostr", rtt: "≤5ms", status: "healthy", wg: "10.0.10.104", liveP50Ms: 3.4, liveP95Ms: 4.8, wgLatencyP95Ms: 44.0, lastProbeAt: "2026-07-09T13:04:22Z" },
  ],

  gateP95Series: [
    { t: "06:00", p95: 11.2 },
    { t: "07:00", p95: 10.8 },
    { t: "08:00", p95: 12.4 },
    { t: "09:00", p95: 13.1 },
    { t: "10:00", p95: 14.2 },
    { t: "11:00", p95: 12.8 },
    { t: "12:00", p95: 11.9 },
    { t: "13:00", p95: 12.1 },
  ],

  submitP95Series: [
    { t: "06:00", p95: 38.4 },
    { t: "07:00", p95: 36.2 },
    { t: "08:00", p95: 39.8 },
    { t: "09:00", p95: 42.1 },
    { t: "10:00", p95: 44.6 },
    { t: "11:00", p95: 41.2 },
    { t: "12:00", p95: 40.8 },
    { t: "13:00", p95: 41.2 },
  ],

  recentEvents: [
    { ts: "2026-07-09T10:14:02Z", severity: "warn", segment: "Hyperliquid RTT", detail: "p95 1.1ms — 10% above 1ms target; routing holds EDGE-TKY primary", resolved: false },
    { ts: "2026-07-09T08:22:18Z", severity: "info", segment: "Gate p95", detail: "Brief spike 14.2ms during Tier 1 prewarm — within 15ms budget", resolved: true },
    { ts: "2026-07-08T22:41:55Z", severity: "info", segment: "Home → EDGE-FRA", detail: "WG tune applied — p95 dropped 28ms → 22ms", resolved: true },
    { ts: "2026-07-08T16:03:11Z", severity: "warn", segment: "NEXUS feed", detail: "Staleness 4.8s on funding rates — ms lanes paused new entries 12s", resolved: true },
  ],

  enforcement: {
    agent: "FORGE",
    specs: [
      "~/.openclaw/infra/latency_budget.yaml",
      "~/.openclaw/infra/latency_fast_path.yaml",
      "~/.openclaw/infra/edge_hot_path.yaml",
    ],
    onBreach: ["herald_alert", "log_posture_jsonl"],
    hardHalts: [
      { rule: "hot_path_gate_p95 > 25ms sustained 2m", action: "HALT hot pipelines" },
      { rule: "home_to_edge_fra_p95 > 50ms sustained 5m", action: "Failover + HERALD CRITICAL" },
    ],
  },

  dispatchSteps: [
    { step: 1, hop: "PREDATOR / rules", latency: "0–2 ms", note: "Geyser / mempool signal (pre-validated)" },
    { step: 2, hop: "POST /v1/fast_validate", latency: "≤15 ms p95", note: "Recon + risk kernel single hop" },
    { step: 3, hop: "signing_node :19010", latency: "≤5 ms p95", note: "TPM-SPI session verify" },
    { step: 4, hop: "Nostr NIP-44 Kind 1059", latency: "≤3 ms", note: "TITANHOME → edge worker" },
    { step: 5, hop: "Edge PoP broadcast", latency: "≤1 ms", note: "Same-AZ to DEX / sequencer / builder" },
    { step: 6, hop: "DEX ack / bundle", latency: "≤50 ms E2E", note: "Excludes block inclusion time" },
  ],
};

export const pipelinesCatalog = [
  { id: "P1", name: "DEX Cross-Venue Arb", phase: "funded", edge: "EDGE-FRA" },
  { id: "P3", name: "Cross-Rollup Arb", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P5", name: "DEX Funding Carry", phase: "funded", edge: "EDGE-TKY", flash: true },
  { id: "P6", name: "Liquidation Hunter", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P10", name: "Restaking / AVS", phase: "paper", edge: "EDGE-FRA", flash: true },
  { id: "P11", name: "Prediction Arb", phase: "micro_live", edge: "EDGE-USE" },
  { id: "P12", name: "Intent Solver", phase: "funded", edge: "EDGE-FRA", flash: true },
  { id: "P16", name: "RWA Basis", phase: "scorecard", edge: "EDGE-FRA", flash: true },
  { id: "P22", name: "Memecoin Trench", phase: "paper", edge: "EDGE-FRA", memecoin: true },
  { id: "P29", name: "MEV Bundle", phase: "defunded", edge: "EDGE-FRA" },
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
  { strategy: "P29", primary: "EDGE-FRA", fallback: "EDGE-USE", note: "Flashbots / EU builders" },
  { strategy: "P30", primary: "EDGE-TKY", fallback: "EDGE-SIN", note: "Cross-chain MEV · DEX" },
  { strategy: "P12", primary: "EDGE-FRA", fallback: "EDGE-USE", note: "Intent solver EU/US" },
  { strategy: "P3", primary: "EDGE-FRA", fallback: "EDGE-USE", note: "Flash-loan arb" },
  { strategy: "P8", primary: "EDGE-SIN", fallback: "EDGE-TKY", note: "APAC DEX / AMM" },
];

export const edgePops = [
  { id: "EDGE-FRA", region: "Frankfurt DE-CIX", targets: "Jito FRA, Erigon, Uniswap/Curve/Balancer", rtt: "≤5ms", status: "healthy", wg: "10.0.10.100" },
  { id: "EDGE-TKY", region: "ap-northeast-1", targets: "Hyperliquid DEX, Jito-TKY", rtt: "<1ms", status: "healthy", wg: "10.0.10.101" },
  { id: "EDGE-SIN", region: "ap-southeast-1", targets: "BSC DEX, Sui, PancakeSwap", rtt: "<1ms", status: "healthy", wg: "10.0.10.102" },
  { id: "EDGE-USE", region: "us-east-1", targets: "L2 sequencers, Flashbots, Base DEX", rtt: "≤3ms", status: "healthy", wg: "10.0.10.103" },
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

/** Quantum-inspired lane optimizer — advisory demo (matches `titan-safety qi demo`). */
export type QiLaneEdge = {
  pipeline_id: string;
  net_bps: number;
  return_std: number;
  trade_count: number;
  capacity_usd: number;
  decaying: boolean;
  cluster: string;
};

export type QiKellyAllocation = {
  pipeline_id: string;
  target_notional_usd: number;
  weight: number;
  kelly_signal: number;
  cluster: string;
  capped_by: string;
};

export const quantumInspired = {
  advisoryOnly: true,
  livePath: false,
  backend: "classical_sa" as const,
  quantumEnabled: false,
  quantumAgentsRemoved: true,
  cli: "titan-safety qi demo --seed 42 --k 4 --compare-kelly",
  config: {
    k: 4,
    seed: 42,
    sweeps: 5000,
    risk_lambda: 1.0,
    cluster_penalty: 2.0,
    cardinality_lambda: 5.0,
    min_net_bps: 1.0,
    min_trades: 100,
  },
  equityUsd: 10000,
  regime: "neutral" as const,
  drawdownPct: 0,
  lanes: [
    { pipeline_id: "P1", net_bps: 12, return_std: 0.015, trade_count: 1500, capacity_usd: 0, decaying: false, cluster: "arb" },
    { pipeline_id: "P5", net_bps: 18, return_std: 0.012, trade_count: 900, capacity_usd: 0, decaying: false, cluster: "funding" },
    { pipeline_id: "P11", net_bps: 22, return_std: 0.025, trade_count: 600, capacity_usd: 0, decaying: false, cluster: "lp" },
    { pipeline_id: "P12", net_bps: 28, return_std: 0.02, trade_count: 1100, capacity_usd: 0, decaying: false, cluster: "mev_arb" },
    { pipeline_id: "P22", net_bps: 35, return_std: 0.04, trade_count: 400, capacity_usd: 0, decaying: false, cluster: "memecoin" },
    { pipeline_id: "P29", net_bps: 30, return_std: 0.03, trade_count: 1200, capacity_usd: 0, decaying: false, cluster: "mev_arb" },
  ] satisfies QiLaneEdge[],
  result: {
    selected_pipeline_ids: ["P1", "P5", "P11", "P12"],
    bitstring: "111100",
    energy: -82.266873,
    cardinality: 4,
    rewards: [5.333333, 12.5, 3.52, 7.0, 2.1875, 3.333333],
    excluded: {} as Record<string, string>,
  },
  kelly: {
    deployed_usd: 2092.54,
    utilization: 0.2093,
    allocations: [
      { pipeline_id: "P5", target_notional_usd: 922.53, weight: 0.369, kelly_signal: 12.5, cluster: "funding", capped_by: "" },
      { pipeline_id: "P12", target_notional_usd: 516.62, weight: 0.2066, kelly_signal: 7.0, cluster: "mev_arb", capped_by: "" },
      { pipeline_id: "P1", target_notional_usd: 393.61, weight: 0.1574, kelly_signal: 5.3333, cluster: "arb", capped_by: "" },
      { pipeline_id: "P11", target_notional_usd: 259.78, weight: 0.1039, kelly_signal: 3.52, cluster: "lp", capped_by: "" },
    ] satisfies QiKellyAllocation[],
    excluded: { P29: "max_active_pipelines=4", P22: "max_active_pipelines=4" },
    notes: [
      "ADVISORY — targets logged only; not enforced on execution",
      "capped to 4 active pipelines (of 6 eligible)",
    ],
  },
  comparison: {
    overlap: ["P1", "P11", "P12", "P5"],
    overlap_count: 4,
    qi_only: [] as string[],
    kelly_only: [] as string[],
    qi_cardinality: 4,
    kelly_active_count: 4,
    target_k: 4,
  },
  altScenarios: [
    {
      label: "k=3 · seed=7",
      seed: 7,
      k: 3,
      selected: ["P5", "P12", "P22"],
      energy: -61.42,
      overlap_count: 2,
      qi_only: ["P22"],
      kelly_only: ["P1", "P11"],
    },
    {
      label: "k=4 · seed=99",
      seed: 99,
      k: 4,
      selected: ["P1", "P5", "P12", "P29"],
      energy: -78.91,
      overlap_count: 3,
      qi_only: ["P29"],
      kelly_only: ["P11"],
    },
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
    detail: "Lowest live p50 RTT PoP — same-AZ as DEX / sequencers / builders",
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

/** Manual Control console — demo state for operator command center (wire to :19001/:19008 later). */
export type WindDownMode = "none" | "safe" | "derisk" | "flatten";
export type HeraldAlertLevel = "all" | "high" | "critical" | "muted";
export type PipelineRunState = "running" | "halted" | "paper" | "gated";
export type GateReceiptState = "fresh" | "stale" | "missing";
export type BftPosture = "quorum_ready" | "degraded" | "hold";

export type ManualPipelineControl = {
  id: string;
  name: string;
  phase: string;
  runState: PipelineRunState;
  advisoryEnabled: boolean;
  edge: string;
  memecoin?: boolean;
  flash?: boolean;
  humanYesRequired?: boolean;
};

export const manualControl = {
  overallPosture: "HARDENED" as "HARDENED" | "LOCKDOWN" | "DEGRADED",
  tradingHalted: false,
  killActive: portfolio.killActive,
  signingHalted: false,
  capitalProfile: portfolio.capitalProfile,
  equityUsd: portfolio.equityUsd,
  availableUsd: portfolio.availableUsd,
  drawdownPct: portfolio.drawdownPct,
  windDownMode: "none" as WindDownMode,
  evolutionFrozen: portfolio.evolutionFrozen,
  quantumDormant: true,
  quantumEnabled: false,
  honeypotArmed: true,
  huntMode: true,
  edgeFailClosed: true,
  lockdownDryRunOnly: true,
  promotionHold: true,
  bftPosture: "quorum_ready" as BftPosture,
  confidenceFloor: 0.7,
  gateReceipt: {
    state: "fresh" as GateReceiptState,
    ttlSec: 30,
    lastIssuedAt: "2026-07-09T13:02:11Z",
    code: "GATE_ALLOW",
  },
  maxActivePipelines: 4,
  selectedEdgePop: edgeMesh.defaultPop,
  heraldAlertLevel: "high" as HeraldAlertLevel,
  heraldMutedUntil: null as string | null,
  pillars: {
    impenetrable: "ARMED",
    evasion: "ACTIVE",
    stalking: "HUNTING",
    predatory: "ENGAGED",
  },
  inferenceTiers: modelTiers.map((t) => ({
    tier: t.tier,
    port: t.port,
    model: t.model,
    role: t.role,
    live: t.live,
    status: t.live ? ("online" as const) : ("offline_rd" as const),
  })),
  controlPlaneServices: services,
  pipelines: pipelinesCatalog.map((p): ManualPipelineControl => {
    const funded = p.phase === "funded";
    const gated = p.phase === "pending_yes" || Boolean("memecoin" in p && p.memecoin);
    return {
      id: p.id,
      name: p.name,
      phase: p.phase,
      runState: gated
        ? "gated"
        : funded
          ? "running"
          : p.phase === "defunded"
            ? "halted"
            : "paper",
      advisoryEnabled: funded || p.phase === "micro_live" || p.phase === "paper",
      edge: p.edge,
      memecoin: "memecoin" in p ? Boolean(p.memecoin) : undefined,
      flash: "flash" in p ? Boolean(p.flash) : undefined,
      humanYesRequired: p.phase === "pending_yes" || Boolean("memecoin" in p && p.memecoin),
    };
  }),
  allocator: {
    advisoryOnly: true,
    lastPlanAt: "2026-07-09T12:55:00Z",
    selectedIds: quantumInspired.result.selected_pipeline_ids,
    maxActive: 4,
    cliRefresh: "titan-safety qi demo --seed 42 --k 4 --compare-kelly",
  },
  autonomyNotes: [
    { action: "Trade >1% equity", gate: "Human YES (promotion gate)" },
    { action: "New pipeline activation", gate: "Human YES" },
    { action: "Model/skill promotion to live", gate: "Human YES (Phase 5)" },
    { action: "Evolution deploy live", gate: "Shadow only · YES for live" },
    { action: "Flash-loan live", gate: "Human YES" },
    { action: "P22 Memecoin live", gate: "Phase 5 YES + live profile" },
    { action: "Lockdown execute", gate: "HMAC · dry-run default" },
    { action: "Kill deactivate / RESUME", gate: "Signed RESUME + HMAC" },
  ],
  actionLogSeed: [] as string[],
};

/** Dead-man's switch — titan-safety heartbeat · :19005 */
export const deadMansSwitch = {
  port: 19005,
  healthUrl: "http://127.0.0.1:19005/health",
  hoursSinceHeartbeat: portfolio.dmsHoursSinceHeartbeat,
  lastHeartbeatAt: "2026-07-09T10:48:00Z",
  lastOperator: "hyperion",
  deriskAfterHours: 48,
  flattenAfterHours: 72,
  onMiss: "derisk_flatten" as const,
  neverAutoPromote: true,
  status: "armed" as "armed" | "derisk" | "flatten" | "halted",
  cliHeartbeat: "titan-safety heartbeat --operator YOU",
  cliAuthSign: "titan-safety auth sign --command HEARTBEAT --operator YOU",
  timeline: [
    { ts: "2026-07-09T10:48:00Z", event: "HEARTBEAT", operator: "hyperion", note: "Timer reset · 48h window" },
    { ts: "2026-07-08T09:12:00Z", event: "HEARTBEAT", operator: "hyperion", note: "Routine ack" },
    { ts: "2026-07-07T08:01:00Z", event: "HEARTBEAT", operator: "hyperion", note: "Post-sweep confirm" },
    { ts: "2026-07-06T22:40:00Z", event: "WARN", operator: "DMS", note: "Approaching 24h — HERALD nudge" },
  ],
};

/** Full circuit-breaker catalog from policy.yaml security_ops + memecoin + endgame */
export const circuitBreakerCatalog = [
  { id: "CB_TPM_PCR_DRIFT", family: "security", action: "halt_new_risk_critical_alert", armed: true },
  { id: "CB_KEYS_SIGNING_ENV_COMPROMISED", family: "security", action: "signing_halted", armed: true },
  { id: "CB_NETNS_POLICY_BYPASS", family: "security", action: "kill_pipeline", armed: true },
  { id: "CB_RISK_KERNEL_UNREACHABLE", family: "security", action: "fail_closed_deny", armed: true },
  { id: "CB_DARKINT_HONEYPOT", family: "security", action: "critical_alert_optional_pipeline_halt", armed: true },
  { id: "CB_HYDRA_HONEYPOT", family: "security", action: "critical_alert_optional_pipeline_halt", armed: true },
  { id: "CB_STALK_SEVERITY_HIGH", family: "security", action: "escalate_archon_herald", armed: true },
  { id: "CB_STEALTH_PUBLIC_PATH", family: "stealth", action: "fail_closed_deny", armed: true },
  { id: "CB_STEALTH_UNSHIELDED_VENUE", family: "stealth", action: "fail_closed_deny", armed: true },
  { id: "CB_SECURITY_LOCKDOWN", family: "security", action: "kill_freeze_signing_halt_honeypot_arm", armed: true },
  { id: "CB_PSU_VOLTAGE_MISMATCH", family: "power", action: "halt_trading", armed: true },
  { id: "CB_MEMECOIN_DAILY_SOL_CAP", family: "memecoin", action: "halt P22 until UTC reset", armed: true },
  { id: "CB_MEMECOIN_FILTER_BYPASS", family: "memecoin", action: "DENY fail-closed", armed: true },
  { id: "CB_MEMECOIN_HONEYPOT", family: "memecoin", action: "DENY + HERALD alert", armed: true },
  { id: "CB_MEMECOIN_GRAD_FAIL", family: "memecoin", action: "halt lane P22", armed: true },
  { id: "CB_MEMECOIN_TIP_BLEED", family: "memecoin", action: "reduce size P22", armed: true },
  { id: "CB_FUNDING_FLIP", family: "endgame", action: "halt_funding_lanes", armed: false },
  { id: "CB_RESTAKING_SLASH", family: "endgame", action: "halt_restaking_exposure", armed: false },
  { id: "CB_RESTAKING_DEPEG", family: "endgame", action: "halt_restaking_exposure", armed: false },
  { id: "CB_PRED_MARKET_RESOLVE_RISK", family: "endgame", action: "halt_pred_market_lanes", armed: false },
  { id: "CB_VOL_HARVEST_GAP", family: "endgame", action: "halt_vol_harvest", armed: false },
  { id: "CB_NEW_CHAIN_MEV_HALT", family: "endgame", action: "halt_new_chain_mev", armed: false },
  { id: "CB_AIRDROP_SYBIL", family: "endgame", action: "halt_airdrop_lanes", armed: false },
  { id: "CB_RATE_ARB_LIQUIDITY", family: "endgame", action: "halt_rate_arb", armed: false },
  { id: "CB_CLMM_IL_SPIKE", family: "endgame", action: "halt_clmm_il", armed: false },
  { id: "CB_ENDGAME_PHASE_GATE", family: "endgame", action: "block_until_phase_unlock", armed: false },
  { id: "CB_DECISION_LOG_CORRUPT", family: "memory", action: "repair_from_backup_alert", armed: true },
  { id: "CB_DECISION_LOG_FULL", family: "memory", action: "force_rotation_alert", armed: true },
  { id: "CB_REFLECTION_DRIFT", family: "memory", action: "disable_pipeline_asset_alert", armed: true },
  { id: "CB_CHECKPOINT_STALE", family: "memory", action: "abandon_restart_fresh", armed: true },
] as const;

/** TCA scorecard — titan-safety tca scorecard · :19007 */
export const tcaScorecard = {
  port: 19007,
  endpoint: "http://127.0.0.1:19007/v1/scorecard",
  lastIngestAt: "2026-07-09T13:01:44Z",
  minFillsForVerdict: 30,
  healthyNetBps: 5.0,
  marginalNetBps: 0.0,
  maxTipEfficiency: 0.4,
  maxSlippageBps: 20.0,
  minFillRate: 0.8,
  defundedLanes: ["P29"] as string[],
  cliScorecard: "titan-safety tca scorecard",
  cliProfitLoop: "titan-safety tca profit-loop --dry-run --equity 28450 --regime neutral",
  lanes: [
    {
      pipelineId: "P1",
      name: "DEX Cross-Venue Arb",
      netBps: 4.2,
      fills: 412,
      fillRate: 0.94,
      tipEfficiency: 0.12,
      slippageBps: 3.1,
      decaySlopeBps: 0.2,
      verdict: "HEALTHY" as const,
    },
    {
      pipelineId: "P5",
      name: "Intent Solver Routing",
      netBps: 2.8,
      fills: 188,
      fillRate: 0.91,
      tipEfficiency: 0.18,
      slippageBps: 5.4,
      decaySlopeBps: -0.1,
      verdict: "HEALTHY" as const,
    },
    {
      pipelineId: "P12",
      name: "MEV Bundle Capture",
      netBps: 1.1,
      fills: 96,
      fillRate: 0.86,
      tipEfficiency: 0.31,
      slippageBps: 8.2,
      decaySlopeBps: -0.4,
      verdict: "MARGINAL" as const,
    },
    {
      pipelineId: "P22",
      name: "Memecoin Trench",
      netBps: 6.4,
      fills: 54,
      fillRate: 0.72,
      tipEfficiency: 0.22,
      slippageBps: 14.0,
      decaySlopeBps: 0.8,
      verdict: "INSUFFICIENT_DATA" as const,
    },
    {
      pipelineId: "P29",
      name: "CLMM Fee Harvest",
      netBps: -2.4,
      fills: 210,
      fillRate: 0.88,
      tipEfficiency: 0.44,
      slippageBps: 11.2,
      decaySlopeBps: -1.6,
      verdict: "BLEEDING" as const,
    },
  ],
};

/** Allocator plan snapshot — titan-safety allocator plan · :19006 */
export const allocatorPlan = {
  port: 19006,
  endpoint: "http://127.0.0.1:19006/v1/plan",
  lastPlanAt: "2026-07-09T12:55:00Z",
  equityUsd: portfolio.equityUsd,
  regime: portfolio.regime,
  maxActive: 4,
  concentrationCap: 4,
  advisoryOnly: true,
  cliPlan: "titan-safety allocator plan --equity 28450 --regime neutral",
  allocations: [
    { pipelineId: "P1", weight: 0.32, notionalUsd: 9104, cappedBy: null as string | null },
    { pipelineId: "P5", weight: 0.28, notionalUsd: 7966, cappedBy: null },
    { pipelineId: "P12", weight: 0.22, notionalUsd: 6259, cappedBy: "marginal_tca" },
    { pipelineId: "P11", weight: 0.18, notionalUsd: 5121, cappedBy: null },
    { pipelineId: "P29", weight: 0, notionalUsd: 0, cappedBy: "defunded" },
  ],
  excluded: ["P29", "P22"],
  notes: [
    "≤4 funded HEALTHY lanes via CapitalAllocator",
    "BLEEDING lanes zeroed until human YES re-fund",
    "QI optimizer is advisory — does not gate ExecutionGate",
  ],
};

/** Power / UPS — power_requirements.yaml + policy power_loss */
export const powerStatus = {
  liveCapitalRequiresUps: true,
  upsAcknowledged: true,
  onMains: true,
  onBattery: false,
  model: "Eaton 9SX 3000VA / 2700W 208V Online Double-Conversion",
  runtimeMinutes: 22,
  minimumRuntimeMinutes: 15,
  loadWatts: 1840,
  capacityWatts: 2700,
  alertOnRuntimeBelowMinutes: 10,
  service: "power-chain-guard.service",
  policyRef: "~/.openclaw/infra/power_requirements.yaml",
  onPowerLoss: {
    action: "halt_trading",
    flatten: true,
    revokeKeys: true,
    notify: "CRITICAL",
    cb: "CB_PSU_VOLTAGE_MISMATCH",
  },
  protectedOutlets: [
    { id: "titanhome_workstation", status: "protected" as const },
    { id: "signing_node", status: "protected" as const },
    { id: "titanspark_gx10", status: "protected" as const },
    { id: "macmini_vault", status: "protected" as const },
    { id: "network_core_switch", status: "protected" as const },
  ],
  timing: {
    gpsdo: "LBE-1425",
    nic: "Intel E810-XXVDA4T",
    ppsState: "locked" as const,
    onPpsLostMinutes: 5,
    fallback: "chronyd NTP pool",
  },
};

/** Verify / health checklist — mirrors verify.sh + safety service ports */
export type VerifyCheckStatus = "pass" | "fail" | "warn" | "skip";

export const verifyChecklist = {
  lastRunAt: "2026-07-09T12:30:00Z",
  script: "./verify.sh",
  overall: "pass" as VerifyCheckStatus,
  groups: [
    {
      id: "bootstrap",
      label: "Bootstrap files",
      checks: [
        { id: "soul", label: "SOUL.md present ≤20KB", status: "pass" as VerifyCheckStatus },
        { id: "agents", label: "AGENTS.md present ≤20KB", status: "pass" as VerifyCheckStatus },
        { id: "tools", label: "TOOLS.md present ≤20KB", status: "pass" as VerifyCheckStatus },
        { id: "heartbeat", label: "HEARTBEAT.md present", status: "pass" as VerifyCheckStatus },
        { id: "memory", label: "MEMORY.md ≤100 lines", status: "pass" as VerifyCheckStatus },
      ],
    },
    {
      id: "config",
      label: "Config integrity",
      checks: [
        { id: "openclaw", label: "openclaw.json valid JSON", status: "pass" as VerifyCheckStatus },
        { id: "policy", label: "risk_kernel/policy.yaml present", status: "pass" as VerifyCheckStatus },
        { id: "skills", label: "Hermes skills symlink", status: "pass" as VerifyCheckStatus },
        { id: "quantum", label: "quantum.enabled=false", status: "pass" as VerifyCheckStatus },
      ],
    },
    {
      id: "safety",
      label: "Safety services",
      checks: [
        { id: "kernel", label: "risk_kernel :19001", status: "pass" as VerifyCheckStatus, port: 19001 },
        { id: "recon", label: "reconciliation :19002", status: "pass" as VerifyCheckStatus, port: 19002 },
        { id: "status", label: "status-agg :19003", status: "pass" as VerifyCheckStatus, port: 19003 },
        { id: "portfolio", label: "portfolio_risk :19004", status: "pass" as VerifyCheckStatus, port: 19004 },
        { id: "dms", label: "dead_mans_switch :19005", status: "pass" as VerifyCheckStatus, port: 19005 },
        { id: "alloc", label: "allocator :19006", status: "pass" as VerifyCheckStatus, port: 19006 },
        { id: "tca", label: "tca :19007", status: "pass" as VerifyCheckStatus, port: 19007 },
        { id: "sec", label: "security_ops :19008", status: "pass" as VerifyCheckStatus, port: 19008 },
        { id: "sign", label: "signing_node :19010", status: "pass" as VerifyCheckStatus, port: 19010 },
      ],
    },
    {
      id: "live_gates",
      label: "Live capital gates",
      checks: [
        { id: "ups", label: "UPS acknowledged for live capital", status: "pass" as VerifyCheckStatus },
        { id: "ghost", label: "ghost_evasion armed (no public RPC live)", status: "pass" as VerifyCheckStatus },
        { id: "evo", label: "evolution freeze during live", status: "pass" as VerifyCheckStatus },
        { id: "receipt", label: "signing require_gate_receipt", status: "pass" as VerifyCheckStatus },
        { id: "mock", label: "mock adapter banned (live profile)", status: "pass" as VerifyCheckStatus },
      ],
    },
  ],
};

/** Structured decision log — decision_log.jsonl style (richer than aiLog stream) */
export const decisionLog = [
  {
    id: "d-9912",
    ts: "2026-07-09T12:58:11Z",
    agent: "TRENCH-OPS",
    asset: "ETH-USDC",
    pipeline: "P1",
    action: "execute",
    decision: "ALLOW",
    confidence: 0.81,
    alphaPct: null as number | null,
    status: "pending" as const,
    rationale: "BFT 2/3 ALLOW · gate receipt fresh · net_bps 4.2",
  },
  {
    id: "d-9908",
    ts: "2026-07-09T11:42:05Z",
    agent: "PREDATOR",
    asset: "SOL-meme",
    pipeline: "P22",
    action: "paper_snipe",
    decision: "ALLOW",
    confidence: 0.58,
    alphaPct: 12.9,
    status: "resolved" as const,
    rationale: "G1–G6 pass · paper only · Phase 5 YES pending",
  },
  {
    id: "d-9891",
    ts: "2026-07-09T09:15:00Z",
    agent: "GUARDIAN",
    asset: "ARB-ETH",
    pipeline: "P12",
    action: "veto",
    decision: "DENY",
    confidence: 0.92,
    alphaPct: null,
    status: "resolved" as const,
    rationale: "STEALTH_PUBLIC_PATH — public RPC candidate rejected",
  },
  {
    id: "d-9870",
    ts: "2026-07-08T22:01:00Z",
    agent: "ARCHON",
    asset: "—",
    pipeline: "P29",
    action: "defund",
    decision: "HOLD",
    confidence: 1.0,
    alphaPct: -8.4,
    status: "resolved" as const,
    rationale: "TCA BLEEDING · profit_loop auto-defund · human YES to re-fund",
  },
  {
    id: "d-9855",
    ts: "2026-07-08T18:40:22Z",
    agent: "AUGUR",
    asset: "BTC-PERP",
    pipeline: "P5",
    action: "regime_vote",
    decision: "ALLOW",
    confidence: 0.74,
    alphaPct: 3.1,
    status: "resolved" as const,
    rationale: "Macro neutral · funding stable · BFT commit",
  },
];
