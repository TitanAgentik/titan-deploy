/** Live security posture client — falls back to demo data when :19008 is down. */

import { authHeaders } from "@/lib/auth";

export type LiveSecurityPosture = {
  status?: string;
  overall?: string;
  threat_level?: string;
  hunt_mode?: boolean;
  honeypot_armed?: boolean;
  pcr_drift?: boolean;
  signing_halted?: boolean;
  kill_active?: boolean;
  evolution_frozen?: boolean;
  layers?: { id: string; name: string; port: string; status: string }[];
  pillars?: Record<string, string>;
  live?: boolean;
  error?: string;
};

const HMAC_NEEDED =
  "401 — HMAC required. Set operator token in Settings (sessionStorage titan-hmac-token).";

export async function fetchSecurityPosture(
  signal?: AbortSignal,
): Promise<LiveSecurityPosture> {
  try {
    const r = await fetch("/api/security/v1/status", {
      signal: signal ?? AbortSignal.timeout(2000),
    });
    if (!r.ok) {
      return { live: false, error: `HTTP ${r.status}` };
    }
    const data = (await r.json()) as LiveSecurityPosture;
    return { ...data, live: true };
  } catch (e) {
    return {
      live: false,
      error: e instanceof Error ? e.message : "unreachable",
    };
  }
}

/** Optional layer check — GET /v1/layers (no auth). */
export async function fetchSecurityLayers(
  signal?: AbortSignal,
): Promise<{
  ok: boolean;
  layers: { id: string; name: string; port: string; status: string }[];
  error?: string;
}> {
  try {
    const r = await fetch("/api/security/v1/layers", {
      signal: signal ?? AbortSignal.timeout(2000),
    });
    if (!r.ok) {
      return { ok: false, layers: [], error: `HTTP ${r.status}` };
    }
    const data = (await r.json()) as {
      layers?: { id: string; name: string; port: string; status: string }[];
      ok?: boolean;
    };
    return {
      ok: Boolean(data.ok ?? true),
      layers: data.layers ?? [],
    };
  } catch (e) {
    return {
      ok: false,
      layers: [],
      error: e instanceof Error ? e.message : "unreachable",
    };
  }
}

async function postSecurity(
  path: string,
  body: Record<string, unknown>,
): Promise<{ ok: boolean; detail: string }> {
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
      return { ok: false, detail: HMAC_NEEDED };
    }
    return {
      ok: Boolean(data.ok ?? r.ok),
      detail:
        typeof data.error === "string"
          ? data.error
          : JSON.stringify(data).slice(0, 200),
    };
  } catch (e) {
    return {
      ok: false,
      detail: e instanceof Error ? e.message : "unreachable",
    };
  }
}

export async function postSecurityLockdownDryRun(
  operator: string,
  reason: string,
): Promise<{ ok: boolean; detail: string }> {
  return postSecurity("/api/security/v1/lockdown", {
    operator,
    reason,
    dry_run: true,
  });
}
