"""Stealth evasion + predatory gate tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.execution_gate import ExecutionGate
from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.policy_loader import load_policy
from titan_safety.stealth_predatory import check_stealth_evasion


def _policy(tmp_path: Path, **overrides) -> Path:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "capital_profile": "live",
        "trading_limits": {"equity_usd": 2500, "max_notional_usd_per_trade": 500},
        "allowed_venues": ["paper", "hyperliquid", "jito", "binance_spot"],
        "ghost_evasion": {
            "enabled": True,
            "require_shielded_path_live": True,
            "shielded_venues": ["hyperliquid", "jito"],
            "stealth_pipelines": ["P22"],
            "pipeline_required_venues": {"P22": ["jito"]},
        },
        "reconciliation": {"adapter": "mock"},
        "service": {"risk_kernel_port": 19001},
    }
    data.update(overrides)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_public_rpc_always_denied(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    trade = TradeRequest(
        trade_id="t1",
        venue="public_rpc",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    result = check_stealth_evasion(trade, policy)
    assert result is not None
    assert result.decision == "DENY"
    assert result.code == "STEALTH_PUBLIC_PATH"


def test_unshielded_live_venue_denied(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    trade = TradeRequest(
        trade_id="t2",
        venue="binance_spot",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    result = check_stealth_evasion(trade, policy)
    assert result is not None
    assert result.code == "STEALTH_UNSHIELDED_VENUE"


def test_shielded_live_venue_allowed(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    trade = TradeRequest(
        trade_id="t3",
        venue="hyperliquid",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    assert check_stealth_evasion(trade, policy) is None


def test_stealth_pipeline_requires_jito(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    trade = TradeRequest(
        trade_id="t4",
        venue="hyperliquid",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        strategy_id="P22",
    )
    result = check_stealth_evasion(trade, policy)
    assert result is not None
    assert result.code == "STEALTH_PIPELINE_ROUTE"


def test_kernel_denies_public_rpc(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    kernel = RiskKernel(policy)
    trade = TradeRequest(
        trade_id="t5",
        venue="public_rpc",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        confidence=0.8,
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "STEALTH_PUBLIC_PATH"


def test_gate_stealth_stage_denies_public_rpc(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    gate = ExecutionGate(policy)
    trade = TradeRequest(
        trade_id="t6",
        venue="public_rpc",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    decision = gate.gate(trade)
    assert decision.decision == "DENY"
    assert decision.code == "STEALTH_PUBLIC_PATH"
    assert decision.stages.get("stealth_evasion", {}).get("code") == "STEALTH_PUBLIC_PATH"
