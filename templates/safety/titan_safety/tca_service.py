"""TCA / execution-quality HTTP service on :19007.

Ingests fills and serves per-lane net-of-cost scorecards. After ingest, the
profit loop can auto-de-fund BLEEDING lanes and produce an allocator plan.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .allocator import CapitalAllocator, AllocatorConfig
from .http_server import SafetyHTTPServer
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy
from .profit_loop import ProfitLoop
from .tca import Fill, TCAConfig, TCAEngine

logger = setup_logging("tca")


def _body_to_fill(body: dict[str, Any]) -> Fill:
    return Fill(
        pipeline_id=str(body.get("pipeline_id", body.get("strategy_id", ""))),
        venue=str(body.get("venue", "")),
        side=str(body.get("side", "buy")),
        notional_usd=float(body.get("notional_usd", 0.0)),
        expected_price=float(body.get("expected_price", 0.0)),
        realized_price=float(body.get("realized_price", 0.0)),
        gross_pnl_usd=float(body.get("gross_pnl_usd", 0.0)),
        gas_usd=float(body.get("gas_usd", 0.0)),
        tip_usd=float(body.get("tip_usd", 0.0)),
        reverted=bool(body.get("reverted", False)),
    )


def create_app(
    policy_path: Path,
    safety_dir: Path | None = None,
) -> tuple[SafetyHTTPServer, TCAEngine, ProfitLoop]:
    policy = load_policy(policy_path)
    engine = TCAEngine(TCAConfig.from_raw(policy.raw))
    allocator = CapitalAllocator(AllocatorConfig.from_raw(policy.raw))
    sdir = safety_dir or Path(
        os.environ.get("TITAN_SAFETY_DIR", str(Path.home() / ".openclaw" / "safety"))
    )
    loop = ProfitLoop(engine, allocator, safety_dir=sdir)

    def ingest(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        fills = body.get("fills")
        if isinstance(fills, list):
            for f in fills:
                engine.ingest(_body_to_fill(f))
            count = len(fills)
        else:
            engine.ingest(_body_to_fill(body))
            count = 1
        METRICS.inc("tca_fills_ingested_total", count)
        # Optional auto-run of profit loop after ingest
        run_loop = bool(body.get("run_profit_loop", False))
        payload: dict[str, Any] = {"ingested": count}
        if run_loop:
            result = loop.run(
                equity_usd=float(
                    body.get("equity_usd", policy.trading_limits.equity_usd)
                ),
                regime=str(body.get("regime", "neutral")),
                drawdown_pct=float(body.get("drawdown_pct", 0.0)),
            )
            METRICS.inc("profit_loop_runs_total")
            METRICS.set_gauge("profit_loop_defunded", float(len(loop.defunded_lanes())))
            payload["profit_loop"] = result.to_dict()
        return 200, payload

    def scorecard(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        pid = str(body.get("pipeline_id", body.get("strategy_id", "")))
        if pid:
            card = engine.scorecard(pid)
            METRICS.set_gauge(f"tca_net_bps_{pid}", card.net_bps)
            return 200, card.to_dict()
        cards = engine.all_scorecards()
        return 200, {"scorecards": [c.to_dict() for c in cards]}

    def profit_loop_run(
        body: dict[str, Any], _headers: dict[str, str]
    ) -> tuple[int, dict[str, Any]]:
        result = loop.run(
            equity_usd=float(body.get("equity_usd", policy.trading_limits.equity_usd)),
            regime=str(body.get("regime", "neutral")),
            drawdown_pct=float(body.get("drawdown_pct", 0.0)),
        )
        METRICS.inc("profit_loop_runs_total")
        METRICS.set_gauge("profit_loop_defunded", float(len(loop.defunded_lanes())))
        return 200, result.to_dict()

    def refund(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        pid = str(body.get("pipeline_id", ""))
        operator = str(body.get("operator", ""))
        if not pid or not operator:
            return 400, {"error": "pipeline_id and operator required", "ok": False}
        ok = loop.refund(pid, operator, reason=str(body.get("reason", "human YES")))
        return 200, {"ok": ok, "pipeline_id": pid, "defunded": sorted(loop.defunded_lanes())}

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        h = engine.health()
        h["defunded_lanes"] = sorted(loop.defunded_lanes())
        METRICS.set_gauge("tca_bleeding_lanes", float(len(h.get("bleeding_lanes", []))))
        return 200, h

    def metrics(_body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        if "text/plain" in headers.get("Accept", ""):
            return 200, {"_raw_prometheus": METRICS.to_prometheus()}
        return 200, METRICS.to_json()

    port = policy.service.tca_port
    routes = {
        "POST /v1/ingest": ingest,
        "POST /v1/scorecard": scorecard,
        "POST /v1/profit_loop": profit_loop_run,
        "POST /v1/refund": refund,
        "GET /health": health,
        "GET /metrics": metrics,
    }
    server = SafetyHTTPServer(
        "127.0.0.1",
        port,
        routes,
        auth_commands={
            "POST /v1/ingest": "TCA_INGEST",
            "POST /v1/profit_loop": "PROFIT_LOOP",
            "POST /v1/refund": "REFUND",
        },
        safety_dir=sdir,
    )
    return server, engine, loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN TCA / Execution-Quality Service")
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
    server, _engine, _loop = create_app(policy_path)
    policy = load_policy(policy_path)
    logger.info(f"TCA service on 127.0.0.1:{policy.service.tca_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
