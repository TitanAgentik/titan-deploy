/** External wallet watchlist — whales, smart money, manual adds (localStorage). */

import type { walletTracker } from "@/lib/data";

type BaseAccount = (typeof walletTracker.accounts)[number];

export type TrackerAccount = Omit<BaseAccount, "kind"> & {
  kind: BaseAccount["kind"] | "watched";
  owner: "self" | "external";
  category?: WatchCategory;
  custom?: boolean;
  notes?: string;
  alertsEnabled?: boolean;
};

export type WatchCategory = "whale" | "smart_money" | "competitor" | "influencer" | "custom";

export type WatchedWalletPreset = {
  id: string;
  label: string;
  category: WatchCategory;
  chains: string[];
  addressFull: string;
  balanceUsd: number;
  change24hUsd: number;
  change24hPct: number;
  lastTxTs: string;
  role: string;
  holdings: TrackerAccount["holdings"];
  tags?: string[];
};

export type CustomWatchedWallet = {
  id: string;
  label: string;
  category: WatchCategory;
  chains: string[];
  addressFull: string;
  notes?: string;
  alertsEnabled: boolean;
  addedAt: string;
};

export type AddWalletInput = {
  label: string;
  address: string;
  chain: string;
  category: WatchCategory;
  notes?: string;
  alertsEnabled: boolean;
};

const STORAGE_KEY = "titan-agentik-watched-wallets";

export const WATCH_CATEGORIES: { id: WatchCategory; label: string }[] = [
  { id: "whale", label: "Whale" },
  { id: "smart_money", label: "Smart money" },
  { id: "competitor", label: "Competitor / copy-trader" },
  { id: "influencer", label: "Influencer / KOL" },
  { id: "custom", label: "Custom" },
];

export const WATCH_CHAINS = [
  "ethereum",
  "solana",
  "arbitrum",
  "base",
  "bitcoin",
  "bsc",
  "multi",
] as const;

export function shortenAddress(addr: string, head = 6, tail = 4): string {
  if (addr.length <= head + tail + 1) return addr;
  if (addr.includes(":") && !addr.startsWith("0x")) return addr;
  return `${addr.slice(0, head)}…${addr.slice(-tail)}`;
}

export function validateWatchAddress(address: string, chain: string): string | null {
  const a = address.trim();
  if (!a) return "Address is required";
  if (chain === "ethereum" || chain === "arbitrum" || chain === "base" || chain === "bsc") {
    if (!/^0x[a-fA-F0-9]{40}$/.test(a)) return "EVM address must be 0x + 40 hex chars";
    return null;
  }
  if (chain === "solana") {
    if (a.length < 32 || a.length > 44) return "Solana address looks invalid (32–44 chars)";
    return null;
  }
  if (chain === "bitcoin") {
    if (!/^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$/.test(a)) return "Bitcoin address format invalid";
    return null;
  }
  if (a.length < 8) return "Address too short";
  return null;
}

function pseudoUsd(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return Math.round(((h % 900_000) + 50_000) * 100) / 100;
}

export function loadCustomWatchedWallets(): CustomWatchedWallet[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CustomWatchedWallet[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveCustomWatchedWallets(wallets: CustomWatchedWallet[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(wallets));
}

export function createCustomWallet(input: AddWalletInput): CustomWatchedWallet {
  const addressFull = input.address.trim();
  const chains =
    input.chain === "multi" ? ["ethereum", "solana"] : [input.chain];
  return {
    id: `watch-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    label: input.label.trim(),
    category: input.category,
    chains,
    addressFull,
    notes: input.notes?.trim() || undefined,
    alertsEnabled: input.alertsEnabled,
    addedAt: new Date().toISOString(),
  };
}

export function presetToAccount(p: WatchedWalletPreset): TrackerAccount {
  return {
    id: p.id,
    label: p.label,
    group: categoryGroup(p.category),
    kind: "watched",
    owner: "external",
    category: p.category,
    custom: false,
    chains: p.chains,
    address: shortenAddress(p.addressFull),
    addressFull: p.addressFull,
    balanceUsd: p.balanceUsd,
    change24hUsd: p.change24hUsd,
    change24hPct: p.change24hPct,
    allocationPct: 0,
    status: "synced",
    lastTxTs: p.lastTxTs,
    role: p.role,
    holdings: p.holdings,
    alertsEnabled: true,
  };
}

export function customToAccount(c: CustomWatchedWallet): TrackerAccount {
  const balanceUsd = pseudoUsd(c.addressFull);
  const change24hPct = Number(((pseudoUsd(c.id) % 800) / 100 - 4).toFixed(2));
  const change24hUsd = (balanceUsd * change24hPct) / 100;
  const chain = c.chains[0] ?? "ethereum";
  return {
    id: c.id,
    label: c.label,
    group: categoryGroup(c.category),
    kind: "watched",
    owner: "external",
    category: c.category,
    custom: true,
    notes: c.notes,
    alertsEnabled: c.alertsEnabled,
    chains: c.chains,
    address: shortenAddress(c.addressFull),
    addressFull: c.addressFull,
    balanceUsd,
    change24hUsd,
    change24hPct,
    allocationPct: 0,
    status: "synced",
    lastTxTs: c.addedAt,
    role: c.notes || `Operator watchlist · ${c.category.replace(/_/g, " ")}`,
    holdings: [
      {
        symbol: chain === "solana" ? "SOL" : chain === "bitcoin" ? "BTC" : "ETH",
        name: chain === "solana" ? "Solana" : chain === "bitcoin" ? "Bitcoin" : "Ether",
        amount: balanceUsd / (chain === "bitcoin" ? 95000 : chain === "solana" ? 140 : 2000),
        usd: balanceUsd * 0.85,
        chain,
        pct: 85,
      },
    ],
  };
}

export function selfToAccount(
  a: (typeof walletTracker.accounts)[number],
): TrackerAccount {
  return { ...a, owner: "self", kind: a.kind };
}

function categoryGroup(category: WatchCategory): string {
  switch (category) {
    case "whale":
      return "Whale";
    case "smart_money":
      return "Smart money";
    case "competitor":
      return "Competitor";
    case "influencer":
      return "Influencer";
    default:
      return "Watchlist";
  }
}

export function categoryTagKind(
  category: WatchCategory,
): "healthy" | "watch" | "info" | "neutral" | "bleeding" {
  switch (category) {
    case "whale":
      return "info";
    case "smart_money":
      return "healthy";
    case "competitor":
      return "bleeding";
    case "influencer":
      return "watch";
    default:
      return "neutral";
  }
}
