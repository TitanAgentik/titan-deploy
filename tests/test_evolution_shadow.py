"""Additional evolution shadow-only gate tests — no regression on live promotion."""

from __future__ import annotations

from pathlib import Path

from titan_safety.evolution_freeze import EvolutionFreeze
from titan_safety.promotion_gate import PromotionGate, PromotionRequest


def _strong_stats() -> dict:
    returns = [0.02, -0.005, 0.03, 0.01, 0.025, -0.004, 0.028, 0.015] * 40
    return {
        "strategy_id": "dgm-h",
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


def test_evolution_deploy_blocked_when_frozen_even_with_yes_and_stats(tmp_path: Path) -> None:
    EvolutionFreeze(tmp_path).freeze("op", "live capital")
    gate = PromotionGate(tmp_path)
    decision = gate.evaluate(
        PromotionRequest(
            request_id="evo1",
            category="evolution_deploy",
            subject="dgm-h live",
            operator_response="YES",
            operator_id="op",
            metadata={"strategy_stats": _strong_stats()},
        )
    )
    assert decision.approved is False
    assert "frozen" in decision.reason.lower()


def test_evolution_deploy_unfrozen_still_requires_explicit_yes(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    decision = gate.evaluate(
        PromotionRequest(
            request_id="evo2",
            category="evolution_deploy",
            subject="dgm-h live",
            operator_response="approve",
            operator_id="op",
            metadata={"strategy_stats": _strong_stats()},
        )
    )
    assert decision.approved is False
    assert "YES" in decision.reason


def test_evolution_freeze_blocks_phase5_not_routine_categories(tmp_path: Path) -> None:
    ef = EvolutionFreeze(tmp_path)
    ef.freeze("op")
    assert ef.block_reason("phase5_go_nogo") is not None
    assert ef.block_reason("leverage_change") is None
