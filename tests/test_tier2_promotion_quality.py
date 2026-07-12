"""Tier 2 promotion quality tests — items 11–14."""

from __future__ import annotations

from pathlib import Path

import pytest

from titan_safety.allocator import AllocatorConfig, CapitalAllocator, LaneEdge
from titan_safety.micro_live_caps import MicroLiveCaps
from titan_safety.promotion_gate import PromotionGate, PromotionRequest
from titan_safety.promotion_registry import PromotionRegistry
from titan_safety.promotion_stats import StatsGateConfig, StrategyStats, StrategyStatsGate
from titan_safety.profit_loop import ProfitLoop
from titan_safety.tca import Fill, TCAConfig, TCAEngine
from titan_safety.tca_daily_scorecard import build_daily_scorecard, render_telegram_scorecard
from titan_safety.v1_surface import V1SurfaceConfig, V1SurfaceLockdown


def _full_stats(**overrides) -> dict:
    returns = [0.02, -0.004, 0.03, 0.012, 0.025, -0.003, 0.028, 0.016] * 40
    base = {
        "strategy_id": "P5",
        "returns": returns,
        "trials": 5,
        "num_trades": 500,
        "gross_bps": 12.0,
        "cost_bps": 3.0,
        "backtest_sharpe": 1.8,
        "shadow_sharpe": 1.7,
        "walk_forward_folds_passed": 5,
        "purged_cv_passed": True,
        "fat_slippage_bps": 8.0,
        "capacity_curve_ok": True,
        "shadow_days": 7,
        "shadow_gas_tip_simulated": True,
    }
    base.update(overrides)
    return base


def test_registry_increments_global_trials(tmp_path: Path) -> None:
    reg = PromotionRegistry(tmp_path)
    assert reg.total_trials() == 0
    reg.register_attempt("P5", config={"a": 1}, returns=[0.01, 0.02], num_trades=10)
    reg.register_attempt("P7", config={"b": 2}, returns=[0.01, -0.01], num_trades=10)
    assert reg.total_trials() == 2
    summary = reg.summary()
    assert summary.unique_strategies == 2


def test_stats_gate_blocks_missing_walk_forward() -> None:
    stats = StrategyStats(
        strategy_id="x",
        returns=[0.02, 0.01] * 100,
        trials=2,
        num_trades=300,
        gross_bps=10.0,
        cost_bps=3.0,
        backtest_sharpe=1.5,
        shadow_sharpe=1.4,
        walk_forward_folds_passed=2,
        purged_cv_passed=True,
        fat_slippage_bps=6.0,
        capacity_curve_ok=True,
        shadow_days=5,
        shadow_gas_tip_simulated=True,
    )
    result = StrategyStatsGate().evaluate(stats)
    assert not result.passed
    assert any("walk-forward" in r for r in result.reasons)


def test_stats_gate_passes_full_evidence() -> None:
    raw = _full_stats()
    stats = StrategyStats(
        strategy_id=raw["strategy_id"],
        returns=raw["returns"],
        trials=raw["trials"],
        num_trades=raw["num_trades"],
        gross_bps=raw["gross_bps"],
        cost_bps=raw["cost_bps"],
        backtest_sharpe=raw["backtest_sharpe"],
        shadow_sharpe=raw["shadow_sharpe"],
        walk_forward_folds_passed=raw["walk_forward_folds_passed"],
        purged_cv_passed=raw["purged_cv_passed"],
        fat_slippage_bps=raw["fat_slippage_bps"],
        capacity_curve_ok=raw["capacity_curve_ok"],
        shadow_days=raw["shadow_days"],
        shadow_gas_tip_simulated=raw["shadow_gas_tip_simulated"],
    )
    result = StrategyStatsGate().evaluate(stats)
    assert result.passed, result.reasons


def test_promotion_gate_uses_registry_trials(tmp_path: Path) -> None:
    reg = PromotionRegistry(tmp_path)
    for i in range(50):
        reg.register_attempt(f"S{i}", config={"i": i}, returns=[0.001], num_trades=1)
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r1",
        category="strategy_promotion",
        subject="P5",
        operator_response="YES",
        operator_id="op",
        metadata={"strategy_stats": _full_stats(trials=1)},
    )
    decision = gate.evaluate(req)
    assert decision.approved is True


def test_micro_caps_block_large_micro_live_notional() -> None:
    caps = MicroLiveCaps()
    assert caps.calendar_is_gate() is False
    r = caps.check_trade(10_000.0, 50_000.0, phase="micro_live_conservative")
    assert not r.allowed
    assert "jump cap" in r.reason or "exceeds" in r.reason


def test_micro_caps_allow_tiny_micro_live() -> None:
    caps = MicroLiveCaps()
    r = caps.check_trade(20.0, 50_000.0, phase="micro_live_conservative")
    assert r.allowed


def test_calendar_not_gate_for_scale() -> None:
    caps = MicroLiveCaps()
    ok, reason = caps.can_scale_phase(
        current_phase="micro_live_conservative",
        target_phase="validated_scale",
        fill_count=10,
        stats_gate_passed=False,
        promotion_yes=False,
        days_elapsed=30,
    )
    assert not ok
    assert "calendar" in reason.lower() or "stats" in reason.lower()


def test_refund_requires_promotion_yes(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    fill = Fill(
        pipeline_id="P99",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.0,
        gross_pnl_usd=1.0,
        tip_usd=2.0,
    )
    for _ in range(10):
        engine.ingest(fill)
    loop = ProfitLoop(engine, safety_dir=tmp_path)
    loop.run(equity_usd=10_000.0)
    assert not loop.refund("P99", operator="human", reason="YES")


def test_refund_succeeds_with_promotion_yes(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    fill = Fill(
        pipeline_id="P99",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.0,
        gross_pnl_usd=1.0,
        tip_usd=2.0,
    )
    for _ in range(10):
        engine.ingest(fill)
    gate = PromotionGate(tmp_path)
    gate.evaluate(
        PromotionRequest(
            request_id="ref1",
            category="strategy_promotion",
            subject="P99",
            operator_response="YES",
            operator_id="op",
            metadata={"strategy_stats": _full_stats(strategy_id="P99")},
        )
    )
    loop = ProfitLoop(engine, safety_dir=tmp_path)
    loop.run(equity_usd=10_000.0)
    assert loop.refund("P99", operator="human", reason="YES")


def test_v1_surface_blocks_p22_and_cex() -> None:
    lock = V1SurfaceLockdown(V1SurfaceConfig(enabled=True))
    assert not lock.check_pipeline("P22").allowed
    assert not lock.check_venue("binance_spot").allowed
    assert lock.check_venue("hyperliquid").allowed


def test_allocator_v1_caps_at_two_strategies() -> None:
    lock = V1SurfaceLockdown(V1SurfaceConfig(enabled=True, max_active_strategies=2))
    alloc = CapitalAllocator(AllocatorConfig(max_active_pipelines=4), v1_lockdown=lock)
    lanes = [
        LaneEdge(f"P{i}", net_bps=10.0, return_std=0.02, trade_count=200)
        for i in range(5)
    ]
    plan = alloc.allocate(100_000.0, lanes)
    assert len(plan.allocations) == 2


def test_daily_scorecard_digest() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=3))
    for _ in range(5):
        engine.ingest(
            Fill(
                pipeline_id="P1",
                notional_usd=1000.0,
                expected_price=100.0,
                realized_price=100.05,
                gross_pnl_usd=5.0,
                gas_usd=0.1,
                tip_usd=0.1,
            )
        )
    digest = build_daily_scorecard(engine, equity_usd=25_000.0)
    text = render_telegram_scorecard(digest)
    assert "TCA Daily Scorecard" in text
    assert digest.lanes_tracked == 1
