/**
 * Manual Control form prefs — stored under titan.cockpit.v1 → sections.manualControl.
 * Migrates legacy titan.manualControl.v1 on first read.
 */

import {
  manualControl,
  type HeraldAlertLevel,
  type ManualPipelineControl,
  type PipelineRunState,
  type WindDownMode,
} from "@/lib/data";
import {
  clearSection,
  fingerprint,
  loadSection,
  saveSection,
} from "@/lib/cockpitPersist";

export const MANUAL_CONTROL_LEGACY_KEY = "titan.manualControl.v1";

export type ManualControlPrefs = {
  v: 1;
  savedAt: string;
  tradingHalted: boolean;
  killActive: boolean;
  signingHalted: boolean;
  windDownMode: WindDownMode;
  evolutionFrozen: boolean;
  honeypotArmed: boolean;
  promotionHold: boolean;
  selectedEdgePop: string;
  heraldAlertLevel: HeraldAlertLevel;
  maxActivePipelines: number;
  pipelines: Array<{
    id: string;
    advisoryEnabled: boolean;
    runState: PipelineRunState;
  }>;
};

export type ManualControlFormState = {
  tradingHalted: boolean;
  killActive: boolean;
  signingHalted: boolean;
  windDown: WindDownMode;
  evolutionFrozen: boolean;
  honeypotArmed: boolean;
  promotionHold: boolean;
  edgePop: string;
  heraldLevel: HeraldAlertLevel;
  maxActivePipelines: number;
  pipelines: ManualPipelineControl[];
};

const WIND_DOWN: WindDownMode[] = ["none", "safe", "derisk", "flatten"];
const HERALD: HeraldAlertLevel[] = ["all", "high", "critical", "muted"];
const RUN_STATES: PipelineRunState[] = ["running", "halted", "paper", "gated"];

function isWindDown(v: unknown): v is WindDownMode {
  return typeof v === "string" && (WIND_DOWN as string[]).includes(v);
}

function isHerald(v: unknown): v is HeraldAlertLevel {
  return typeof v === "string" && (HERALD as string[]).includes(v);
}

function isRunState(v: unknown): v is PipelineRunState {
  return typeof v === "string" && (RUN_STATES as string[]).includes(v);
}

export function defaultsFromSeed(): ManualControlFormState {
  const seed = manualControl;
  return {
    tradingHalted: seed.tradingHalted,
    killActive: seed.killActive,
    signingHalted: seed.signingHalted,
    windDown: seed.windDownMode,
    evolutionFrozen: seed.evolutionFrozen,
    honeypotArmed: seed.honeypotArmed,
    promotionHold: seed.promotionHold,
    edgePop: seed.selectedEdgePop,
    heraldLevel: seed.heraldAlertLevel,
    maxActivePipelines: seed.maxActivePipelines,
    pipelines: seed.pipelines.map((p) => ({ ...p })),
  };
}

export function formToPrefs(form: ManualControlFormState): ManualControlPrefs {
  return {
    v: 1,
    savedAt: new Date().toISOString(),
    tradingHalted: form.tradingHalted,
    killActive: form.killActive,
    signingHalted: form.signingHalted,
    windDownMode: form.windDown,
    evolutionFrozen: form.evolutionFrozen,
    honeypotArmed: form.honeypotArmed,
    promotionHold: form.promotionHold,
    selectedEdgePop: form.edgePop,
    heraldAlertLevel: form.heraldLevel,
    maxActivePipelines: form.maxActivePipelines,
    pipelines: form.pipelines.map((p) => ({
      id: p.id,
      advisoryEnabled: p.advisoryEnabled,
      runState: p.runState,
    })),
  };
}

/** Stable compare payload (excludes savedAt). */
export function prefsFingerprint(prefs: ManualControlPrefs): string {
  return fingerprint(prefs);
}

function parsePrefs(parsed: Partial<ManualControlPrefs>): ManualControlPrefs | null {
  if (parsed.v !== 1 || typeof parsed !== "object" || parsed === null) return null;
  if (!isWindDown(parsed.windDownMode) || !isHerald(parsed.heraldAlertLevel)) {
    return null;
  }
  if (typeof parsed.selectedEdgePop !== "string") return null;
  if (typeof parsed.maxActivePipelines !== "number") return null;
  if (!Array.isArray(parsed.pipelines)) return null;

  const pipelines = parsed.pipelines
    .filter(
      (p): p is ManualControlPrefs["pipelines"][number] =>
        Boolean(p) &&
        typeof p.id === "string" &&
        typeof p.advisoryEnabled === "boolean" &&
        isRunState(p.runState),
    )
    .map((p) => ({
      id: p.id,
      advisoryEnabled: p.advisoryEnabled,
      runState: p.runState,
    }));

  return {
    v: 1,
    savedAt: typeof parsed.savedAt === "string" ? parsed.savedAt : new Date(0).toISOString(),
    tradingHalted: Boolean(parsed.tradingHalted),
    killActive: Boolean(parsed.killActive),
    signingHalted: Boolean(parsed.signingHalted),
    windDownMode: parsed.windDownMode,
    evolutionFrozen: Boolean(parsed.evolutionFrozen),
    honeypotArmed: Boolean(parsed.honeypotArmed),
    promotionHold: Boolean(parsed.promotionHold),
    selectedEdgePop: parsed.selectedEdgePop,
    heraldAlertLevel: parsed.heraldAlertLevel,
    maxActivePipelines: Math.max(1, Math.min(12, Math.round(parsed.maxActivePipelines))),
    pipelines,
  };
}

function migrateLegacy(): ManualControlPrefs | null {
  try {
    const raw = localStorage.getItem(MANUAL_CONTROL_LEGACY_KEY);
    if (!raw) return null;
    const parsed = parsePrefs(JSON.parse(raw) as Partial<ManualControlPrefs>);
    if (parsed) {
      saveSection("manualControl", parsed);
      localStorage.removeItem(MANUAL_CONTROL_LEGACY_KEY);
    }
    return parsed;
  } catch {
    return null;
  }
}

export function loadManualControlPrefs(): ManualControlPrefs | null {
  const fromStore = loadSection<Partial<ManualControlPrefs>>("manualControl");
  if (fromStore) {
    const parsed = parsePrefs(fromStore);
    if (parsed) return parsed;
  }
  return migrateLegacy();
}

export function saveManualControlPrefs(prefs: ManualControlPrefs): void {
  saveSection("manualControl", prefs);
  localStorage.removeItem(MANUAL_CONTROL_LEGACY_KEY);
}

export function clearManualControlPrefs(): void {
  clearSection("manualControl");
  localStorage.removeItem(MANUAL_CONTROL_LEGACY_KEY);
}

export function hydrateFormState(
  saved: ManualControlPrefs | null = loadManualControlPrefs(),
): ManualControlFormState {
  const base = defaultsFromSeed();
  if (!saved) return base;

  const byId = new Map(saved.pipelines.map((p) => [p.id, p]));
  return {
    tradingHalted: saved.tradingHalted,
    killActive: saved.killActive,
    signingHalted: saved.signingHalted,
    windDown: saved.windDownMode,
    evolutionFrozen: saved.evolutionFrozen,
    honeypotArmed: saved.honeypotArmed,
    promotionHold: saved.promotionHold,
    edgePop: saved.selectedEdgePop || base.edgePop,
    heraldLevel: saved.heraldAlertLevel,
    maxActivePipelines: saved.maxActivePipelines,
    pipelines: base.pipelines.map((p) => {
      const overlay = byId.get(p.id);
      if (!overlay) return p;
      return {
        ...p,
        advisoryEnabled: overlay.advisoryEnabled,
        runState: overlay.runState,
      };
    }),
  };
}
