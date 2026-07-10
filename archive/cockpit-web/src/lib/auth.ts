/** Session HMAC for mutating control-plane calls (X-Titan-Auth). */

const HMAC_KEY = "titan-hmac-token";

export function getHmacToken(): string {
  try {
    return sessionStorage.getItem(HMAC_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setHmacToken(t: string): void {
  try {
    if (t) sessionStorage.setItem(HMAC_KEY, t);
    else sessionStorage.removeItem(HMAC_KEY);
  } catch {
    /* private mode / blocked storage */
  }
}

export function clearHmacToken(): void {
  try {
    sessionStorage.removeItem(HMAC_KEY);
  } catch {
    /* ignore */
  }
}

export function authHeaders(): Record<string, string> {
  const token = getHmacToken();
  return token ? { "X-Titan-Auth": token } : {};
}
