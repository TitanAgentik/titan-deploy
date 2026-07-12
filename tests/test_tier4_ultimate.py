"""Tier 4 ultimate scaffold tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.allocator import CapitalAllocator, LaneEdge
from titan_safety.edge_router import EdgeRouter
from titan_safety.intent_solver import IntentSolverClient, IntentSubmission
from titan_safety.kernel import TradeRequest
from titan_safety.mev_tip_optimizer import MevTipOptimizer
from titan_safety.portfolio_risk import PipelineExposure, PortfolioRiskEngine, PortfolioSnapshot
from titan_safety.red_team_runner import RedTeamRunner
from titan_safety.shadow_twin import ShadowMetrics, ShadowTwin
from titan_safety.tier4_gate import tier4_active, tier4_prerequisites
from titan_safety.v1_surface import V1SurfaceLockdown


def _tier4_policy(**overrides) -> dict:
    base = {
        "capital_profile": "live",
        "tier0_money_path": {"enabled": True},
        "tier1_capital_risk": {
            "profiles": {
                "live": {"drawdown_notify_only": False},
            }
        },
        "tier2_promotion_quality": {"promotion_registry": {"enabled": True}},
        "security_ops": {"enabled": True},
        "tier4_ultimate": {
            "enabled": True,
            "tier_checklist": {
                "tier0_complete": True,
                "tier1_complete": True,
                "tier2_complete": True,
                "tier3_complete": True,
            },
            "intent_solver": {"enabled": True, "stub_submit": True},
            "mev_tip_optimizer": {"enabled": True},
            "shadow_twin": {"enabled": True, "max_divergence_pct": 15.0},
            "red_team_continuous": {"enabled": True},
            "portfolio_construction": {
                "borrow_rate_cap_annual_pct": 20.0,
                "funding_rate_cap_8h_pct": 0.1,
                "capacity_curve_enabled": True,
            },
        },
    }
    t4 = base["tier4_ultimate"]
    t4.update(overrides.get("tier4_ultimate") or {})
    base.update({k: v for k, v in overrides.items() if k != "tier4_ultimate"})
    return base


def _mesh() -> dict:
    return {
        "pops": {
            "EDGE-FRA": {"wireguard_ip": "10.0.0.1", "worker_port": 19100, "rtt_target_p95_ms": 2.0},
            "EDGE-TKY": {"wireguard_ip": "10.0.0.2", "worker_port": 19100, "rtt_target_p95_ms": 1.0},
            "EDGE-SIN": {"wireguard_ip": "10.0.0.3", "worker_port": 19100, "rtt_target_p95_ms": 3.0},
        },
        "venue_routing": {"hyperliquid": "EDGE-TKY"},
        "paper_trading": {"latency_faithful": True},
    }


def test_tier4_inactive_by_default() -> None:
    status = tier4_prerequisites({"tier4_ultimate": {"enabled": False}})
    assert status.enabled is False
    assert status.active is False
    assert tier4_active({}) is False


def test_tier4_active_when_complete() -> None:
    policy = _tier4_policy()
    status = tier4_prerequisites(policy)
    assert status.active is True
    assert tier4_active(policy) is True


def test_tier4_blocked_without_checklist() -> None:
    policy = _tier4_policy()
    policy["tier4_ultimate"]["tier_checklist"]["tier2_complete"] = False
    assert tier4_active(policy) is False


def test_edge_router_tier4_unlocks_multi_pop() -> None:
    policy = _tier4_policy()
    router = EdgeRouter(_mesh(), policy_raw=policy)
    router.measure_rtt("EDGE-TKY", measured_ms=1.0)
    router.measure_rtt("EDGE-FRA", measured_ms=5.0)
    decision = router.route(venue="hyperliquid")
    assert decision.primary == "EDGE-TKY"
    assert "tier4" in decision.reason or decision.rtt_ms is not None


def test_edge_router_failover_on_unhealthy_pop() -> None:
    policy = _tier4_policy()
    router = EdgeRouter(_mesh(), policy_raw=policy)
    router.measure_rtt("EDGE-TKY", measured_ms=100.0)
    router.measure_rtt("EDGE-FRA", measured_ms=2.0)
    router.measure_rtt("EDGE-SIN", measured_ms=3.0)
    decision = router.route(venue="hyperliquid")
    assert decision.failover_applied or decision.primary != "EDGE-TKY"


def test_v1_surface_tier4_allows_any_pop() -> None:
    v1 = V1SurfaceLockdown.from_path()
    r = v1.check_edge_pop("EDGE-TKY", tier4_active=True)
    assert r.allowed is True


def test_intent_solver_stub_submit() -> None:
    client = IntentSolverClient(_tier4_policy())
    trade = TradeRequest(
        trade_id="i1", venue="hyperliquid", contract="eth", side="buy", notional_usd=50.0
    )
    result = client.submit(IntentSubmission(trade=trade, solver_network="stub"))
    assert result.decision == "STUB"
    assert result.intent_id.startswith("intent-stub-")


def test_intent_solver_denied_when_tier4_off() -> None:
    client = IntentSolverClient({})
    trade = TradeRequest(
        trade_id="i2", venue="paper", contract="eth", side="buy", notional_usd=10.0
    )
    result = client.submit(IntentSubmission(trade=trade))
    assert result.decision == "DENY"


def test_mev_tip_optimizer_advisory() -> None:
    opt = MevTipOptimizer(_tier4_policy())
    trade = TradeRequest(
        trade_id="t1", venue="hyperliquid", contract="eth", side="buy", notional_usd=100.0
    )
    rec = opt.recommend(trade, urgency=0.8, recent_fill_rate=0.6)
    assert rec is not None
    assert rec.advisory_only is True
    assert rec.suggested_tip_bps > 0


def test_portfolio_borrow_funding_capacity_denies() -> None:
    raw = _tier4_policy()
    engine = PortfolioRiskEngine.from_policy_raw(raw)
    snap = PortfolioSnapshot(
        equity_usd=10000.0,
        pipelines=[
            PipelineExposure(
                pipeline_id="P1",
                notional_usd=500.0,
                borrow_rate_annual_pct=30.0,
                funding_rate_8h_pct=0.0,
                capacity_usd=1000.0,
            )
        ],
    )
    r = engine.simulate_pre_trade(snap, "P1", 100.0)
    assert r.decision == "DENY"
    assert r.code == "BORROW_RATE"


def test_allocator_excludes_high_borrow_lane() -> None:
    policy = _tier4_policy()
    alloc = CapitalAllocator(policy_raw=policy)
    lanes = [
        LaneEdge(
            pipeline_id="P1",
            net_bps=5.0,
            return_std=0.02,
            trade_count=200,
            borrow_rate_annual_pct=25.0,
        )
    ]
    plan = alloc.allocate(10000.0, lanes)
    assert "P1" in plan.excluded


def test_shadow_twin_blocks_deploy_on_divergence() -> None:
    twin = ShadowTwin(_tier4_policy())
    metrics = ShadowMetrics(pipeline_id="P1", live_sharpe=2.0, shadow_sharpe=1.0)
    verdict = twin.check_deploy(metrics)
    assert verdict.decision == "DENY"
    assert verdict.code == "SHADOW_DIVERGENCE"


def test_red_team_runner_health() -> None:
    runner = RedTeamRunner(_tier4_policy())
    h = runner.health()
    assert h["enabled"] is True
    assert "harness_path" in h


def test_policy_template_has_tier4_disabled(tmp_path: Path) -> None:
    policy_path = Path(__file__).resolve().parents[1] / "templates" / "risk_kernel" / "policy.yaml"
    data = yaml.safe_load(policy_path.read_text())
    t4 = data.get("tier4_ultimate") or {}
    assert t4.get("enabled") is False
    checklist = t4.get("tier_checklist") or {}
    assert checklist.get("tier0_complete") is False
