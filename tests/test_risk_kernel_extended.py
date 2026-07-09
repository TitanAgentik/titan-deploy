"""Extended risk kernel tests — velocity and agent verification gates."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.trade_verifier import sign_bft_vote


@pytest.fixture
def kernel(tmp_path: Path) -> RiskKernel:
    policy = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {
            "max_notional_usd_per_trade": 500.0,
            "max_aggregate_exposure_usd": 2500.0,
            "max_leverage": 3.0,
            "max_loss_velocity_usd_per_60s": 200.0,
            "max_open_positions": 8,
            "max_slippage_bps": 50,
            "equity_usd": 2500.0,
        },
        "allowed_venues": ["paper"],
        "allowed_contracts": ["0xabc"],
        "position_limits": {"max_equity_pct_per_trade": 2.0, "human_approval_above_pct": 1.0},
        "autonomous_signing": {"enabled": True, "paper_min_confidence": 0.30},
        "drawdown_velocity": {"max_loss_usd_per_15m": 100.0},
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(policy), encoding="utf-8")
    return RiskKernel.from_policy_path(path, tmp_path / "state.json")


def test_agent_verification_above_1pct_paper(kernel: RiskKernel) -> None:
    trade = TradeRequest(
        trade_id="t1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=30.0,
        confidence=0.55,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"


def test_loss_velocity_15m(kernel: RiskKernel) -> None:
    kernel.state.record_loss(40.0)
    kernel.state.record_loss(40.0)
    kernel.state.record_loss(30.0)
    trade = TradeRequest(
        trade_id="t2",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "LOSS_VELOCITY_15M"


def test_pipeline_halt_checker(kernel: RiskKernel) -> None:
    kernel.pipeline_halt_checker = lambda pid: pid == "P30"
    trade = TradeRequest(
        trade_id="t3",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=5.0,
        strategy_id="P30",
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "PIPELINE_HALT"
