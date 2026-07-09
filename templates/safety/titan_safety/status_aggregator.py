"""Status aggregator — polls safety service health endpoints."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .http_server import SafetyHTTPServer
from .observability import setup_logging
from .policy_loader import expand_path, load_policy

logger = setup_logging("status_aggregator")


def fetch_health(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"status": "unreachable", "error": str(exc)}


def aggregate(policy_path: Path) -> dict[str, Any]:
    policy = load_policy(policy_path)
    ports = policy.service
    services = {
        "risk_kernel": f"http://127.0.0.1:{ports.risk_kernel_port}/health",
        "reconciliation": f"http://127.0.0.1:{ports.reconciliation_port}/health",
        "portfolio_risk": f"http://127.0.0.1:{ports.portfolio_risk_port}/health",
        "dead_mans_switch": f"http://127.0.0.1:{ports.dead_mans_switch_port}/health",
        "allocator": f"http://127.0.0.1:{ports.allocator_port}/health",
        "tca": f"http://127.0.0.1:{ports.tca_port}/health",
        "security_ops": f"http://127.0.0.1:{getattr(ports, 'security_ops_port', 19008)}/health",
        "signing_node": f"http://127.0.0.1:{ports.signing_node_port}/health",
    }
    results: dict[str, Any] = {}
    overall = "ok"
    for name, url in services.items():
        health = fetch_health(url)
        results[name] = health
        if health.get("status") in ("unreachable", "halted", "flatten", "derisk"):
            overall = "degraded"
        if health.get("kill_switch_active"):
            overall = "halted"
        if health.get("halted"):
            overall = "halted"
    return {"status": overall, "services": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Status Aggregator")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    parser.add_argument("--once", action="store_true", help="Print status and exit")
    args = parser.parse_args(argv)
    policy_path = expand_path(args.policy)
    policy = load_policy(policy_path)

    if args.once:
        print(json.dumps(aggregate(policy_path), indent=2))
        return 0

    def status(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, aggregate(policy_path)

    def metrics(_body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        from .observability import METRICS

        agg = aggregate(policy_path)
        METRICS.set_gauge("titan_services_degraded", 1.0 if agg["status"] != "ok" else 0.0)
        if "text/plain" in headers.get("Accept", ""):
            return 200, {"_raw_prometheus": METRICS.to_prometheus()}
        return 200, {"aggregate": agg, "metrics": METRICS.to_json()}

    server = SafetyHTTPServer(
        "127.0.0.1",
        policy.service.status_aggregator_port,
        {"GET /health": status, "GET /status": status, "GET /metrics": metrics},
    )
    logger.info(f"Status aggregator on 127.0.0.1:{policy.service.status_aggregator_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
