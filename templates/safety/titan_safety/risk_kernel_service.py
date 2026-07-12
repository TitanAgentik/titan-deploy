"""Risk kernel HTTP service."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from .http_server import SafetyHTTPServer
from .kill_switch import KillSwitch
from .kernel import RiskKernel, TradeRequest
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy, validate_live_capital_readiness
from .reconciliation import BelievedPosition
from .reconciliation_service import build_reconciliation_service

logger = setup_logging("risk_kernel")


def create_app(
    policy_path: Path,
    state_path: Path | None = None,
    safety_dir: Path | None = None,
) -> tuple[SafetyHTTPServer, RiskKernel]:
    policy = load_policy(policy_path)

    # Fail-closed startup: live capital profile refuses to start on mock
    # flatten adapters (the emergency exit must be real before going live).
    from .flatten_executor import validate_flatten_config_for_live

    validate_flatten_config_for_live(policy)
    validate_live_capital_readiness(policy)

    ks = KillSwitch(safety_dir)
    kernel = RiskKernel.from_policy_path(
        policy_path,
        state_path,
        kill_switch_active=ks.is_active(),
    )
    kernel.pipeline_halt_checker = ks.is_pipeline_halted
    kernel.kill_switch_active = ks.is_active()

    pr_engine = None
    try:
        from .portfolio_risk import PortfolioRiskEngine, PortfolioSnapshot, PipelineExposure

        pr_engine = PortfolioRiskEngine.from_policy_raw(policy.raw)

        def _portfolio_sim(trade: TradeRequest) -> dict[str, Any]:
            # Group by strategy_id when present on position metadata; fall back
            # to contract (never venue — that was a production bug).
            by_strategy: dict[str, float] = {}
            for k, p in kernel.state.positions.items():
                sid = getattr(p, "strategy_id", None) or (
                    k.split(":")[-1] if ":" in k else k
                )
                by_strategy[sid] = by_strategy.get(sid, 0.0) + abs(p.notional_usd)
            snapshot = PortfolioSnapshot(
                equity_usd=policy.trading_limits.equity_usd,
                pipelines=[
                    PipelineExposure(pipeline_id=sid, notional_usd=n)
                    for sid, n in by_strategy.items()
                ],
            )
            result = pr_engine.simulate_pre_trade(
                snapshot, trade.strategy_id or "unknown", trade.notional_usd, trade.side
            )
            return result.to_dict()

        kernel.portfolio_simulator = _portfolio_sim
    except Exception as exc:
        logger.error(f"Portfolio risk wiring failed: {exc}")
        if policy.enforce:
            raise RuntimeError(
                f"Portfolio risk init failed in enforce mode: {exc}"
            ) from exc

    def validate(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        kernel.kill_switch_active = ks.is_active()
        if "drawdown_pct_24h" in body:
            previous = kernel.state.drawdown_pct_24h
            kernel.state.drawdown_pct_24h = float(body["drawdown_pct_24h"])
            kernel.state.save()
            from .drawdown_notifier import process_drawdown_update

            process_drawdown_update(
                policy.raw or {},
                safety_dir or Path.home() / ".openclaw" / "safety",
                previous_pct=previous,
                current_pct=kernel.state.drawdown_pct_24h,
                source=str(body.get("source", "GUARDIAN")),
                kernel=kernel,
                kernel_state=kernel.state,
            )
        trade = TradeRequest.from_dict(body)
        result = kernel.validate_trade(trade)
        METRICS.inc("risk_kernel_validations_total")
        if result.decision == "ALLOW":
            METRICS.inc("risk_kernel_allow_total")
        else:
            METRICS.inc("risk_kernel_deny_total")
        logger.info(f"validate {trade.trade_id}: {result.decision} {result.code}")
        return 200, result.to_dict()

    recon_service = build_reconciliation_service(policy)

    def fast_validate(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        """Single-process recon + kernel — one HTTP hop for ms hot path."""
        kernel.kill_switch_active = ks.is_active()
        try:
            believed = [
                BelievedPosition(
                    venue=str(p["venue"]),
                    contract=str(p["contract"]).lower(),
                    notional_usd=float(p["notional_usd"]),
                    side=str(p.get("side", "long")),
                )
                for p in body.get("believed", [])
            ]
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"decision": "DENY", "code": "INVALID_BELIEVED", "reason": str(exc)}
        pending_raw = body.get("pending", {})
        try:
            pending = BelievedPosition(
                venue=str(pending_raw.get("venue", "paper")),
                contract=str(pending_raw.get("contract", "")).lower(),
                notional_usd=float(pending_raw.get("notional_usd", 0)),
                side=str(pending_raw.get("side", "long")),
            )
        except (TypeError, ValueError) as exc:
            return 400, {"decision": "DENY", "code": "INVALID_PENDING", "reason": str(exc)}

        recon = recon_service.pre_trade_gate(believed, pending)
        METRICS.inc("fast_validate_total")
        if recon.decision != "ALLOW":
            METRICS.inc("fast_validate_recon_deny_total")
            payload = recon.to_dict()
            payload["stage"] = "reconciliation"
            return 200, payload

        trade_raw = body.get("trade", body)
        try:
            trade = TradeRequest.from_dict(trade_raw)
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"decision": "DENY", "code": "INVALID_TRADE", "reason": str(exc)}

        if "drawdown_pct_24h" in body:
            previous = kernel.state.drawdown_pct_24h
            kernel.state.drawdown_pct_24h = float(body["drawdown_pct_24h"])
            kernel.state.save()
            from .drawdown_notifier import process_drawdown_update

            process_drawdown_update(
                policy.raw or {},
                safety_dir or Path.home() / ".openclaw" / "safety",
                previous_pct=previous,
                current_pct=kernel.state.drawdown_pct_24h,
                source=str(body.get("source", "GUARDIAN")),
                kernel=kernel,
                kernel_state=kernel.state,
            )

        result = kernel.validate_trade(trade)
        METRICS.inc("risk_kernel_validations_total")
        if result.decision == "ALLOW":
            METRICS.inc("risk_kernel_allow_total")
            METRICS.inc("fast_validate_allow_total")
        else:
            METRICS.inc("risk_kernel_deny_total")
            METRICS.inc("fast_validate_kernel_deny_total")
        payload = result.to_dict()
        payload["stage"] = "risk_kernel"
        payload["reconciliation"] = "ALLOW"
        logger.info(f"fast_validate {trade.trade_id}: {result.decision} {result.code}")
        return 200, payload

    def flatten(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        from .flatten_executor import FlattenExecutor

        executor = FlattenExecutor.from_policy(policy, safety_dir)
        payload = executor.execute(
            kernel,
            operator="risk_kernel",
            reason="POST /v1/flatten",
            revoke_keys=True,
        )
        METRICS.inc("risk_kernel_flatten_total")
        return 200, payload

    def flatten_status(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, {
            "flatten_requested": kernel.state.flatten_requested,
            "keys_revoked": kernel.state.keys_revoked,
            "halted": kernel.state.halted,
            "positions": [
                {"venue": p.venue, "contract": p.contract, "notional_usd": p.notional_usd}
                for p in kernel.state.positions.values()
            ],
        }

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        kernel.kill_switch_active = ks.is_active()
        payload = kernel.health()
        payload["drawdown_pct_24h"] = kernel.state.drawdown_pct_24h
        return 200, payload

    def drawdown(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        previous = kernel.state.drawdown_pct_24h
        pct = float(body.get("drawdown_pct_24h", body.get("drawdown_pct", 0.0)))
        kernel.state.drawdown_pct_24h = pct
        kernel.state.save()
        from .drawdown_notifier import process_drawdown_update

        payload = process_drawdown_update(
            policy.raw or {},
            safety_dir or Path.home() / ".openclaw" / "safety",
            previous_pct=previous,
            current_pct=pct,
            source=str(body.get("source", "GUARDIAN")),
        )
        return 200, payload

    def metrics(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        accept = _headers.get("Accept", "")
        if "text/plain" in accept:
            return 200, {"_raw_prometheus": METRICS.to_prometheus()}
        return 200, METRICS.to_json()

    routes = {
        "POST /v1/validate": validate,
        "POST /v1/fast_validate": fast_validate,
        "POST /v1/drawdown": drawdown,
        "POST /v1/flatten": flatten,
        "GET /v1/flatten_status": flatten_status,
        "GET /health": health,
        "GET /metrics": metrics,
    }

    port = policy.service.risk_kernel_port
    server = SafetyHTTPServer(
        "127.0.0.1",
        port,
        routes,
        auth_commands={"POST /v1/flatten": "FLATTEN"},
        safety_dir=safety_dir,
    )
    return server, kernel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Risk Kernel Service")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    parser.add_argument(
        "--state",
        default=os.environ.get(
            "TITAN_KERNEL_STATE",
            str(Path.home() / ".openclaw" / "safety" / "kernel_state.json"),
        ),
    )
    parser.add_argument(
        "--safety-dir",
        default=os.environ.get("TITAN_SAFETY_DIR", str(Path.home() / ".openclaw" / "safety")),
    )
    args = parser.parse_args(argv)

    policy_path = expand_path(args.policy)
    state_path = expand_path(args.state)
    safety_dir = expand_path(args.safety_dir)

    if not policy_path.exists():
        logger.error(f"Policy not found: {policy_path}")
        return 1

    server, _kernel = create_app(policy_path, state_path, safety_dir)
    policy = load_policy(policy_path)
    logger.info(f"Risk kernel listening on 127.0.0.1:{policy.service.risk_kernel_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
