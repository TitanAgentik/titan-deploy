"""Autonomous agent verification — confidence + BFT replaces human approval."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.trade_verifier import sign_bft_vote, verify_agent_authorization


@pytest.fixture
def policy_path(tmp_path: Path) -> Path:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 2500.0, "max_notional_usd_per_trade": 500.0},
        "allowed_venues": ["paper", "binance_spot"],
        "allowed_contracts": ["0xabc"],
        "position_limits": {"max_equity_pct_per_trade": 2.0, "human_approval_above_pct": 1.0},
        "autonomous_signing": {
            "enabled": True,
            "min_confidence_reduced": 0.50,
            "min_confidence_full": 0.70,
            "bft_required_above_equity_pct": 1.0,
            "bft_threshold": 2,
        },
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_low_confidence_denied(policy_path: Path, tmp_path: Path) -> None:
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "s.json")
    trade = TradeRequest(
        trade_id="t1",
        venue="binance_spot",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        confidence=0.40,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "CONFIDENCE_TOO_LOW"


def test_bft_required_above_1pct(policy_path: Path, tmp_path: Path) -> None:
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "s.json")
    trade = TradeRequest(
        trade_id="t-big",
        venue="binance_spot",
        contract="0xabc",
        side="buy",
        notional_usd=30.0,
        confidence=0.85,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "BFT_INSUFFICIENT"


def test_bft_allows_above_1pct(policy_path: Path, tmp_path: Path) -> None:
    safety = tmp_path / "safety"
    safety.mkdir()
    votes = [
        sign_bft_vote("AUGUR", "t-big2", "ALLOW", 0.8, safety_dir=safety),
        sign_bft_vote("PREDATOR", "t-big2", "ALLOW", 0.82, safety_dir=safety),
    ]
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "s.json")
    trade = TradeRequest(
        trade_id="t-big2",
        venue="binance_spot",
        contract="0xabc",
        side="buy",
        notional_usd=30.0,
        confidence=0.85,
        bft_votes=votes,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"


def test_paper_lower_confidence(policy_path: Path, tmp_path: Path) -> None:
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "s.json")
    trade = TradeRequest(
        trade_id="t-paper",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=30.0,
        confidence=0.35,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"
