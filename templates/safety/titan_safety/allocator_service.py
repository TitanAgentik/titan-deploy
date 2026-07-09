"""Capital allocator HTTP service on :19006."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .allocator import AllocatorConfig, CapitalAllocator, LaneEdge
from .http_server import SafetyHTTPServer
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy

logger = setup_logging("allocator")


def _body_to_lanes(body: dict[str, Any]) -> list[LaneEdge]:
    lanes: list[LaneEdge] = []
    for lane in body.get("lanes", []):
        lanes.append(
            LaneEdge(
                pipeline_id=str(lane.get("pipeline_id", lane.get("strategy_id", ""))),
                net_bps=float(lane.get("net_bps", 0.0)),
                return_std=float(lane.get("return_std", 0.0)),
                trade_count=int(lane.get("trade_count", 0)),
                capacity_usd=float(lane.get("capacity_usd", 0.0)),
                decaying=bool(lane.get("decaying", False)),
                cluster=str(lane.get("cluster", "")),
            )
        )
    return lanes


def create_app(policy_path: Path) -> tuple[SafetyHTTPServer, CapitalAllocator]:
    policy = load_policy(policy_path)
    allocator = CapitalAllocator(AllocatorConfig.from_raw(policy.raw))

    def allocate(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        equity = float(body.get("equity_usd", policy.trading_limits.equity_usd))
        regime = str(body.get("regime", "neutral"))
        drawdown = float(body.get("drawdown_pct", 0.0))
        lanes = _body_to_lanes(body)
        plan = allocator.allocate(equity, lanes, regime=regime, drawdown_pct=drawdown)
        METRICS.inc("allocator_plans_total")
        METRICS.set_gauge("allocator_gross_pct", plan.gross_pct)
        METRICS.set_gauge("allocator_deployed_usd", plan.deployed_usd)
        METRICS.set_gauge("allocator_utilization", plan.utilization)
        return 200, plan.to_dict()

    def budget(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        equity = float(body.get("equity_usd", policy.trading_limits.equity_usd))
        regime = str(body.get("regime", "neutral"))
        drawdown = float(body.get("drawdown_pct", 0.0))
        gross = allocator.gross_budget(equity, regime, drawdown)
        return 200, {
            "equity_usd": equity,
            "regime": regime,
            "drawdown_pct": drawdown,
            "degross_multiplier": allocator.degross_multiplier(drawdown),
            "gross_budget_usd": round(gross, 2),
            "gross_pct": round(gross / equity * 100.0, 2) if equity else 0.0,
        }

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, allocator.health()

    def metrics(_body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        if "text/plain" in headers.get("Accept", ""):
            return 200, {"_raw_prometheus": METRICS.to_prometheus()}
        return 200, METRICS.to_json()

    port = policy.service.allocator_port
    routes = {
        "POST /v1/allocate": allocate,
        "POST /v1/budget": budget,
        "GET /health": health,
        "GET /metrics": metrics,
    }
    return (
        SafetyHTTPServer(
            "127.0.0.1",
            port,
            routes,
            auth_commands={"POST /v1/allocate": "ALLOCATE"},
        ),
        allocator,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Capital Allocator Service")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    args = parser.parse_args(argv)
    policy_path = expand_path(args.policy)
    if not policy_path.exists():
        logger.error(f"Policy not found: {policy_path}")
        return 1
    server, _allocator = create_app(policy_path)
    policy = load_policy(policy_path)
    logger.info(f"Capital allocator on 127.0.0.1:{policy.service.allocator_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
