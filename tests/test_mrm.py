"""Unit tests for Model Risk Management."""

from __future__ import annotations

from titan_safety.mrm import ModelRiskManager, SignalMetrics


def test_throttle_on_sharpe_degradation() -> None:
    mrm = ModelRiskManager()
    mrm.record_baseline(
        SignalMetrics("sig1", "P30", "neutral", sharpe=2.0, hit_rate=0.6, sample_count=50)
    )
    mrm.record_current(
        SignalMetrics("sig1", "P30", "neutral", sharpe=0.5, hit_rate=0.55, sample_count=50)
    )
    verdict = mrm.evaluate_drift("P30", "sig1", "neutral")
    assert verdict.status == "throttled"
    assert mrm.get_throttle_factor("P30") == 0.5


def test_challenger_stub() -> None:
    mrm = ModelRiskManager()
    result = mrm.register_challenger("P30", "P30-challenger-v2")
    assert result["status"] == "pending_promotion_gate"


def test_hit_rate_floor() -> None:
    mrm = ModelRiskManager()
    mrm.record_current(
        SignalMetrics("sig1", "P1", "neutral", sharpe=1.5, hit_rate=0.3, sample_count=50)
    )
    verdict = mrm.evaluate_drift("P1", "sig1", "neutral")
    assert verdict.status == "throttled"
