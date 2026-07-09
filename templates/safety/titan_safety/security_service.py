"""Security Ops HTTP service — four-pillar posture, honeypot, lockdown.

Port default: 19008 (see risk_kernel/policy.yaml service.security_ops_port).
GET  /health /v1/status — posture JSON (no auth)
POST /v1/lockdown — requires X-Titan-Auth HMAC (LOCKDOWN or HALT)
POST /v1/honeypot/{arm|disarm} — requires HMAC (HONEYPOT)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .auth import verify_control_auth
from .http_server import SafetyHTTPServer
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy
from .security_ops import SecurityOps

logger = setup_logging("security_ops")


def create_app(
    safety_dir: Path,
    policy_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 19008,
) -> SafetyHTTPServer:
    ops = SecurityOps(safety_dir)

    def _auth(headers: dict[str, str], command: str) -> tuple[bool, str]:
        return verify_control_auth(headers, command, safety_dir=safety_dir)

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        st = ops.status()
        METRICS.set_gauge("security_kill_active", 1.0 if st.get("kill_active") else 0.0)
        METRICS.set_gauge("security_honeypot_armed", 1.0 if st.get("honeypot_armed") else 0.0)
        METRICS.set_gauge("security_signing_halted", 1.0 if st.get("signing_halted") else 0.0)
        overall = "halted" if st.get("overall") == "LOCKDOWN" else "ok"
        return 200, {"status": overall, **st}

    def status(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, ops.status()

    def layer_check(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        layer = body.get("layer") if isinstance(body, dict) else None
        return 200, ops.layer_check(layer)

    def lockdown(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        ok, msg = _auth(headers, "LOCKDOWN")
        if not ok:
            ok2, msg2 = _auth(headers, "HALT")
            if not ok2:
                return 401, {"ok": False, "error": msg or msg2}
        operator = str((body or {}).get("operator", "operator"))
        reason = str((body or {}).get("reason", "api lockdown"))
        dry_run = bool((body or {}).get("dry_run", False))
        result = ops.lockdown(operator, reason, dry_run=dry_run)
        return (200 if result.get("ok") else 400), result

    def honeypot_arm(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        ok, msg = _auth(headers, "HONEYPOT")
        if not ok:
            return 401, {"ok": False, "error": msg}
        operator = str((body or {}).get("operator", "SENTINEL"))
        return 200, ops.honeypot_arm(operator)

    def honeypot_disarm(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        ok, msg = _auth(headers, "HONEYPOT")
        if not ok:
            return 401, {"ok": False, "error": msg}
        operator = str((body or {}).get("operator", "SENTINEL"))
        return 200, ops.honeypot_disarm(operator)

    def honeypot_status(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, ops.honeypot_status()

    routes = {
        "GET /health": health,
        "GET /v1/status": status,
        "GET /v1/layers": layer_check,
        "POST /v1/layers": layer_check,
        "POST /v1/lockdown": lockdown,
        "POST /v1/honeypot/arm": honeypot_arm,
        "POST /v1/honeypot/disarm": honeypot_disarm,
        "GET /v1/honeypot": honeypot_status,
    }
    return SafetyHTTPServer(host, port, routes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Security Ops service")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    parser.add_argument(
        "--safety-dir",
        default=os.environ.get(
            "TITAN_SAFETY_DIR",
            str(Path.home() / ".openclaw" / "safety"),
        ),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    policy_path = expand_path(args.policy)
    safety_dir = Path(args.safety_dir)
    port = args.port
    if port <= 0:
        try:
            policy = load_policy(policy_path)
            port = int(getattr(policy.service, "security_ops_port", 19008) or 19008)
        except Exception:
            port = 19008

    server = create_app(safety_dir, policy_path, host=args.host, port=port)
    logger.info(f"Security Ops on {args.host}:{port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
