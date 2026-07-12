"""Portfolio risk HTTP service on :19004."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from .http_server import SafetyHTTPServer
from .observability import METRICS, setup_logging
from .policy_loader import capital_profile_of, expand_path, load_policy
from .portfolio_risk import PipelineExposure, PortfolioRiskEngine, PortfolioSnapshot
from .risk_inputs import detect_live_risk_stubs, live_risk_inputs_ok, pipeline_returns_from_fills

logger = setup_logging("portfolio_risk")


def create_app(policy_path: Path) -> tuple[SafetyHTTPServer, PortfolioRiskEngine]:
    policy = load_policy(policy_path)
    engine = PortfolioRiskEngine.from_policy_raw(policy.raw)

    # Optional live AUGUR feed (file/http); refreshes on each simulate/var call
    from .augur_feed import get_regime_feed

    pr = (policy.raw or {}).get("portfolio_risk", {})
    feed_kind = str(pr.get("augur_feed", "stub"))
    if capital_profile_of(policy) == "live" and feed_kind == "stub":
        feed_kind = str(pr.get("augur_feed_live", "file"))
    feed_url = pr.get("augur_feed_url")
    feed_path = pr.get("augur_regime_file")
    regime_feed = get_regime_feed(
        feed_kind,
        regime=str(pr.get("augur_regime_stub", "neutral")),
        path=Path(str(feed_path).replace("~", str(Path.home()))).expanduser()
        if feed_path
        else None,
        url=str(feed_url) if feed_url else None,
    )
    engine._regime_feed = regime_feed  # type: ignore[attr-defined]
    engine._augur_stub = feed_kind == "stub"  # type: ignore[attr-defined]
    safety_dir = Path.home() / ".openclaw" / "safety"

    def _live_stub_block() -> tuple[int, dict[str, Any]] | None:
        stubs = detect_live_risk_stubs(policy.raw or {})
        if stubs:
            return 503, {
                "decision": "DENY",
                "code": "LIVE_RISK_STUB",
                "reason": f"Live capital blocked — stub inputs: {', '.join(stubs)}",
                "stubs": stubs,
            }
        return None

    def simulate(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        blocked = _live_stub_block()
        if blocked:
            return blocked
        snapshot = _body_to_snapshot(body)
        pipeline_id = str(body.get("pipeline_id", body.get("strategy_id", "")))
        notional = float(body.get("notional_usd", 0))
        side = str(body.get("side", "buy"))
        regime = body.get("regime")
        if regime:
            engine.set_regime_from_augur(str(regime))
        else:
            _refresh_regime()
        # Enrich returns from fill ledger when not supplied (independent of agent claims)
        if pipeline_id:
            for p in snapshot.pipelines:
                if p.pipeline_id == pipeline_id and not p.returns:
                    p.returns = pipeline_returns_from_fills(safety_dir, pipeline_id)
        result = engine.simulate_pre_trade(snapshot, pipeline_id, notional, side)
        METRICS.inc("portfolio_risk_simulations_total")
        if result.decision == "DENY":
            METRICS.inc("portfolio_risk_deny_total")
        return 200, result.to_dict()

    def var_report(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        blocked = _live_stub_block()
        if blocked:
            return blocked
        _refresh_regime()
        snapshot = _body_to_snapshot(body)
        metrics = engine.compute_var_cvar(snapshot)
        METRICS.set_gauge("portfolio_var_95_usd", metrics["var_95_usd"])
        METRICS.set_gauge("portfolio_cvar_95_usd", metrics["cvar_95_usd"])
        return 200, {"regime": engine.regime, **metrics}

    def set_regime(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        regime = str(body.get("regime", "neutral"))
        engine.set_regime_from_augur(regime)
        # Persist for file-feed consumers / AUGUR agent round-trip
        from .augur_feed import write_regime_file

        write_regime_file(
            Path.home() / ".openclaw" / "safety" / "augur_regime.json",
            regime,
            {"source": "http_set"},
        )
        return 200, {
            "regime": engine.regime,
            "source": getattr(engine, "_last_regime_source", feed_kind),
        }

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        h = engine.health()
        h["augur_stub"] = getattr(engine, "_augur_stub", True)
        h["augur_feed"] = feed_kind
        h["augur_source"] = getattr(engine, "_last_regime_source", "stub")
        h["risk_inputs"] = live_risk_inputs_ok(policy.raw or {}, safety_dir)
        h["live_blocked"] = bool(h["risk_inputs"].get("live_blocked"))
        return 200, h

    def _refresh_regime() -> None:
        reading = regime_feed.read()
        engine.set_regime_from_augur(reading.regime)
        engine._last_regime_source = reading.source  # type: ignore[attr-defined]

    def metrics(_body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        if "text/plain" in headers.get("Accept", ""):
            return 200, {"_raw_prometheus": METRICS.to_prometheus()}
        return 200, METRICS.to_json()

    port = policy.service.portfolio_risk_port
    routes = {
        "POST /v1/simulate": simulate,
        "POST /v1/var": var_report,
        "POST /v1/regime": set_regime,
        "GET /health": health,
        "GET /metrics": metrics,
    }
    return (
        SafetyHTTPServer(
            "127.0.0.1",
            port,
            routes,
            auth_commands={"POST /v1/regime": "REGIME"},
        ),
        engine,
    )


def _body_to_snapshot(body: dict[str, Any]) -> PortfolioSnapshot:
    pipelines = []
    for p in body.get("pipelines", []):
        pipelines.append(
            PipelineExposure(
                pipeline_id=str(p.get("pipeline_id", p.get("strategy_id", ""))),
                notional_usd=float(p.get("notional_usd", 0)),
                returns=[float(r) for r in p.get("returns", [])],
            )
        )
    return PortfolioSnapshot(
        equity_usd=float(body.get("equity_usd", 2500.0)),
        pipelines=pipelines,
        regime=str(body.get("regime", "neutral")),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Portfolio Risk Service")
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
    server, _engine = create_app(policy_path)
    policy = load_policy(policy_path)
    logger.info(f"Portfolio risk on 127.0.0.1:{policy.service.portfolio_risk_port}")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
