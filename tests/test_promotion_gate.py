"""Unit tests for promotion gate."""

from __future__ import annotations

from pathlib import Path

from titan_safety.promotion_gate import PromotionGate, PromotionRequest


def test_requires_explicit_yes(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r1",
        category="phase5_go_nogo",
        subject="strategy P30",
        operator_response="maybe",
        operator_id="op",
    )
    decision = gate.evaluate(req)
    assert decision.approved is False


def _strong_stats() -> dict:
    # A clearly-profitable, well-sampled strategy that clears the stats gate.
    returns = [0.02, -0.005, 0.03, 0.01, 0.025, -0.004, 0.028, 0.015] * 40
    return {
        "strategy_id": "P5",
        "returns": returns,
        "trials": 5,
        "num_trades": 500,
        "gross_bps": 12.0,
        "cost_bps": 3.0,
        "backtest_sharpe": 1.8,
        "shadow_sharpe": 1.7,
    }


def test_yes_approved_and_audited(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r2",
        category="strategy_promotion",
        subject="P5 live",
        operator_response="YES",
        operator_id="op",
        metadata={"strategy_stats": _strong_stats()},
    )
    decision = gate.evaluate(req)
    assert decision.approved is True
    assert decision.audit_hash
    ok, msg = gate.verify_audit_chain()
    assert ok is True


def test_strategy_promotion_requires_stats(tmp_path: Path) -> None:
    """Fail-closed: a stats-gated promotion with no evidence is denied even on YES."""
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r2b",
        category="strategy_promotion",
        subject="no-evidence strat",
        operator_response="YES",
        operator_id="op",
    )
    decision = gate.evaluate(req)
    assert decision.approved is False
    assert "strategy_stats required" in decision.reason


def test_overfit_strategy_blocked_despite_yes(tmp_path: Path) -> None:
    """A thin-sample, cost-free (unrealistic) strategy must be blocked."""
    gate = PromotionGate(tmp_path)
    stats = _strong_stats()
    stats["num_trades"] = 12
    stats["cost_bps"] = 0.0  # costs not modeled
    req = PromotionRequest(
        request_id="r2c",
        category="strategy_promotion",
        subject="overfit strat",
        operator_response="YES",
        operator_id="op",
        metadata={"strategy_stats": stats},
    )
    decision = gate.evaluate(req)
    assert decision.approved is False
    assert "Statistical evidence gate failed" in decision.reason


def test_audit_chain_tamper_detected(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    req = PromotionRequest(
        request_id="r3",
        category="leverage_change",
        subject="3x",
        operator_response="YES",
        operator_id="op",
    )
    gate.evaluate(req)
    audit = gate.audit_path.read_text()
    tampered = audit.replace("YES", "NO")
    gate.audit_path.write_text(tampered)
    ok, msg = gate.verify_audit_chain()
    assert ok is False
