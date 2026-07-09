"""HMAC control-plane authentication for mutating safety HTTP endpoints.

Any local process can reach 127.0.0.1 — localhost is not a security boundary.
Mutating POSTs (flatten, regime, heartbeat, TCA ingest, allocate) require a
signed header using the shared control-plane secret (same store as kill switch).

Header format:
  X-Titan-Auth: <command>|<operator>|<unix_ts>|<hex_hmac>
  where payload = f"{command}|{operator}|{ts}" and HMAC-SHA256 over that payload.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any

DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
SECRET_FILE = "control_plane.secret"
# Fall back to kill_switch.secret so one secret covers halt + control plane.
KILL_SECRET_FILE = "kill_switch.secret"
MAX_AGE_SECONDS = 300
AUTH_HEADER = "X-Titan-Auth"


def _safety_dir(path: Path | None = None) -> Path:
    d = path or Path(os.environ.get("TITAN_SAFETY_DIR", str(DEFAULT_SAFETY_DIR)))
    d = Path(d).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_control_secret(safety_dir: Path | None = None) -> bytes:
    """Return control-plane HMAC secret, creating it if missing."""
    base = _safety_dir(safety_dir)
    primary = base / SECRET_FILE
    if primary.exists():
        return primary.read_bytes()
    # Prefer existing kill-switch secret for operational simplicity.
    kill = base / KILL_SECRET_FILE
    if kill.exists():
        secret = kill.read_bytes()
        primary.write_bytes(secret)
        os.chmod(primary, 0o600)
        return secret
    secret = secrets.token_bytes(32)
    primary.write_bytes(secret)
    os.chmod(primary, 0o600)
    return secret


def sign_control_command(
    command: str,
    operator: str = "operator",
    safety_dir: Path | None = None,
    ts: int | None = None,
) -> str:
    secret = ensure_control_secret(safety_dir)
    timestamp = int(time.time()) if ts is None else int(ts)
    payload = f"{command}|{operator}|{timestamp}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_control_auth(
    headers: dict[str, str],
    expected_command: str,
    safety_dir: Path | None = None,
    max_age_seconds: int = MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Verify X-Titan-Auth header for a mutating endpoint.

    Returns (ok, reason). ok=False means the request must be rejected with 401.
    """
    # Header lookup is case-insensitive in HTTP; BaseHTTPRequestHandler keeps
    # original casing — check common variants.
    signed = ""
    for k, v in headers.items():
        if k.lower() == AUTH_HEADER.lower():
            signed = v.strip()
            break
    if not signed:
        return False, f"missing {AUTH_HEADER} header"
    parts = signed.split("|")
    if len(parts) != 4:
        return False, "malformed auth token"
    command, operator, ts_str, sig = parts
    if command != expected_command:
        return False, f"command mismatch: got '{command}', expected '{expected_command}'"
    try:
        ts = int(ts_str)
    except ValueError:
        return False, "invalid timestamp"
    if time.time() - ts > max_age_seconds:
        return False, "auth token expired"
    if ts > time.time() + 60:
        return False, "auth token timestamp in future"
    secret = ensure_control_secret(safety_dir)
    payload = f"{command}|{operator}|{ts}"
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "invalid signature"
    return True, operator


def require_auth(
    expected_command: str,
    safety_dir: Path | None = None,
):
    """Decorator factory for route handlers: (body, headers) -> (code, payload)."""

    def decorator(handler):
        def wrapped(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
            ok, reason = verify_control_auth(headers, expected_command, safety_dir)
            if not ok:
                return 401, {"error": "unauthorized", "reason": reason, "decision": "DENY"}
            return handler(body, headers)

        return wrapped

    return decorator
