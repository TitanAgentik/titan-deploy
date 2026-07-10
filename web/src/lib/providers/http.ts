/**
 * HTTP helpers for live adapters — soft-fail, typed errors, short timeouts.
 */

export type FetchJsonError = {
  ok: false;
  status?: number;
  error: string;
};

export type FetchJsonOk<T> = {
  ok: true;
  data: T;
  status: number;
};

export type FetchJsonResult<T> = FetchJsonOk<T> | FetchJsonError;

const DEFAULT_MS = 2500;

export async function fetchJson<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<FetchJsonResult<T>> {
  const timeoutMs = init?.timeoutMs ?? DEFAULT_MS;
  const { timeoutMs: _t, ...rest } = init ?? {};
  try {
    const r = await fetch(path, {
      ...rest,
      signal: rest.signal ?? AbortSignal.timeout(timeoutMs),
    });
    if (!r.ok) {
      return { ok: false, status: r.status, error: `HTTP ${r.status}` };
    }
    const data = (await r.json()) as T;
    return { ok: true, data, status: r.status };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "unreachable",
    };
  }
}

export function nowIso(): string {
  return new Date().toISOString();
}
