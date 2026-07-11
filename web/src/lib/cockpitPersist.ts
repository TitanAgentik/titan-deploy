/**
 * Cockpit UI preference persistence (localStorage).
 * Explicit Save required — drafts are not auto-written.
 * Not live API / backend state.
 *
 * Storage: localStorage["titan.cockpit.v1"] = { v: 1, sections: { [id]: prefs } }
 */

export const COCKPIT_STORAGE_KEY = "titan.cockpit.v1";

export const COCKPIT_SECTION_IDS = [
  "shell",
  "dashboard",
  "commandCenter",
  "manualControl",
  "capital",
  "walletTracker",
  "pnl",
  "risk",
  "dms",
  "security",
  "forge",
  "healthVerify",
  "power",
  "ops",
  "tcaScorecard",
  "pipelines",
  "qiOptimizer",
  "promotions",
  "edge",
  "latency",
  "flashLoans",
  "memecoin",
  "signing",
  "automations",
  "cryptoNews",
  "cryptoTwitter",
  "goals",
  "identity",
  "models",
  "aiLog",
  "decisionLog",
  "questions",
  "skills",
  "agentTeams",
  "agentManager",
  "workspace",
  "reports",
  "settings",
] as const;

export type CockpitSectionId = (typeof COCKPIT_SECTION_IDS)[number];

export type CockpitStore = {
  v: 1;
  sections: Partial<Record<CockpitSectionId, unknown>>;
};

function emptyStore(): CockpitStore {
  return { v: 1, sections: {} };
}

export function loadAll(): CockpitStore {
  try {
    const raw = localStorage.getItem(COCKPIT_STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as Partial<CockpitStore>;
    if (parsed?.v !== 1 || typeof parsed.sections !== "object" || !parsed.sections) {
      return emptyStore();
    }
    return { v: 1, sections: { ...parsed.sections } };
  } catch {
    return emptyStore();
  }
}

function writeStore(store: CockpitStore): void {
  localStorage.setItem(COCKPIT_STORAGE_KEY, JSON.stringify(store));
}

export function loadSection<T>(id: CockpitSectionId): T | null {
  const store = loadAll();
  const value = store.sections[id];
  if (value === undefined || value === null) return null;
  return value as T;
}

export function saveSection<T extends object>(id: CockpitSectionId, data: T): string {
  const store = loadAll();
  const savedAt = new Date().toISOString();
  store.sections[id] = { ...data, savedAt };
  writeStore(store);
  return savedAt;
}

export function clearSection(id: CockpitSectionId): void {
  const store = loadAll();
  delete store.sections[id];
  writeStore(store);
}

export function clearAll(): void {
  localStorage.removeItem(COCKPIT_STORAGE_KEY);
}

/** Stable compare payload (drops savedAt). */
export function fingerprint(data: unknown): string {
  if (data === null || typeof data !== "object") return JSON.stringify(data);
  const { savedAt: _s, ...rest } = data as Record<string, unknown>;
  return JSON.stringify(rest);
}

export function deepEqual(a: unknown, b: unknown): boolean {
  return fingerprint(a) === fingerprint(b);
}
