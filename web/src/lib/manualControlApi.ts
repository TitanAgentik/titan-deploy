/**
 * Thin control-plane stubs for Manual Control.
 * Mirrors titan-safety CLI / HTTP surfaces (:19001, :19008, :19010).
 * Demo mode returns structured results when backends are unreachable.
 */

import { authHeaders, getHmacToken } from "@/lib/auth";

export type ControlResult = {
  ok: boolean;
  demo: boolean;
  detail: string;
  requiresHmac?: boolean;
  requiresHumanYes?: boolean;
};

const HMAC_NEEDED =
  "401 — HMAC required. Set operator token in Settings (sessionStorage titan-hmac-token).";

async function postControl(
  path: string,
  body: Record<string, unknown>,
  demoDetail: string,
): Promise<ControlResult> {
  const hasToken = Boolean(getHmacToken());
  try {
    const r = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(3000),
    });
    const data = (await r.json().catch(() => ({}))) as Record<string, unknown>;
    if (r.status === 401) {
      return { ok: false, demo: false, detail: HMAC_NEEDED, requiresHmac: true };
    }
    return {
      ok: Boolean(data.ok ?? r.ok),
      demo: false,
      detail:
        typeof data.error === "string"
          ? data.error
          : typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data).slice(0, 200),
      requiresHmac: !hasToken,
    };
  } catch {
    return {
      ok: true,
      demo: true,
      detail: `[demo] ${demoDetail}${hasToken ? "" : " · HMAC not set (would be required live)"}`,
      requiresHmac: !hasToken,
    };
  }
}

export async function postKillActivate(
  operator: string,
  reason: string,
  scope: "global" | "portfolio" | "pipeline",
  pipelineId?: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/kill",
    { action: "activate", operator, reason, scope, pipeline_id: pipelineId },
    `KILL activate scope=${scope}${pipelineId ? ":" + pipelineId : ""} · ${reason}`,
  );
}

export async function postKillResume(
  operator: string,
  reason: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/kill",
    { action: "deactivate", operator, reason, signed: true },
    `Signed RESUME — kill deactivated · ${reason}`,
  );
}

export async function postTradingHalt(
  halt: boolean,
  operator: string,
  reason: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/trading",
    { halt, operator, reason },
    halt ? `Trading HALTED · ${reason}` : `Trading RESUMED · ${reason}`,
  );
}

export async function postWindDown(
  mode: "safe" | "derisk" | "flatten",
  operator: string,
  reason: string,
  revokeKeys?: boolean,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/wind_down",
    { mode, operator, reason, revoke_keys: Boolean(revokeKeys) },
    `Wind-down ${mode}${revokeKeys ? " + revoke_keys" : ""} · ${reason}`,
  );
}

export async function postPipelineHalt(
  pipelineId: string,
  halt: boolean,
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/pipeline",
    { pipeline_id: pipelineId, halt, operator },
    `Pipeline ${pipelineId} ${halt ? "HALTED" : "RESUMED"} (advisory UI)`,
  );
}

export async function postPipelineAdvisory(
  pipelineId: string,
  enabled: boolean,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/pipeline_advisory",
    { pipeline_id: pipelineId, enabled },
    `Pipeline ${pipelineId} advisory ${enabled ? "ENABLED" : "DISABLED"}`,
  );
}

export async function postEvolutionFreeze(
  frozen: boolean,
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/evolution",
    { frozen, operator },
    frozen
      ? "Evolution FROZEN (shadow deploys only)"
      : "Evolution UNFROZEN — live still requires Human YES",
  );
}

export async function postSigningHalt(
  halted: boolean,
  operator: string,
  reason: string,
): Promise<ControlResult> {
  return postControl(
    "/api/signing/v1/halt",
    { halted, operator, reason },
    halted
      ? `SIGNING_HALTED · ${reason}`
      : `Signing resumed · ${reason}`,
  );
}

export async function postHoneypotArm(
  armed: boolean,
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/security/v1/honeypot",
    { armed, operator },
    armed ? "Honeypot lattice ARMED" : "Honeypot lattice DISARMED (advisory)",
  );
}

export async function postLockdown(
  operator: string,
  reason: string,
  dryRun: boolean,
): Promise<ControlResult> {
  const r = await postControl(
    "/api/security/v1/lockdown",
    { operator, reason, dry_run: dryRun },
    dryRun
      ? `Lockdown DRY-RUN ok · ${reason}`
      : `Lockdown EXECUTE queued · HMAC + Human YES · ${reason}`,
  );
  if (!dryRun) {
    return { ...r, requiresHumanYes: true, requiresHmac: true };
  }
  return r;
}

export async function postEdgeSelect(
  popId: string,
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/edge",
    { pop_id: popId, operator },
    `Preferred edge PoP → ${popId} (routing still lowest live p50)`,
  );
}

export async function postAllocatorRefresh(
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/allocator_refresh",
    { operator, advisory: true },
    "Allocator plan refresh queued (advisory · QI compare available)",
  );
}

export async function postHeraldAlertLevel(
  level: "all" | "high" | "critical" | "muted",
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/herald",
    { level, operator },
    `HERALD alert level → ${level}`,
  );
}

export async function postPromotionHold(
  hold: boolean,
  operator: string,
): Promise<ControlResult> {
  return postControl(
    "/api/status/v1/promotion_hold",
    { hold, operator },
    hold
      ? "Promotion HOLD engaged — Phase 5 YES still required for live"
      : "Promotion HOLD cleared (advisory) — Human YES still gates live",
  );
}
