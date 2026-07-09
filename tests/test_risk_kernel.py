"""Unit tests for deterministic risk kernel."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from titan_safety.kernel import RiskKernel, RiskKernelState, TradeRequest
from titan_safety.policy_loader import load_policy


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    policy = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {
            "max_notional_usd_per_trade": 100.0,
            "max_aggregate_exposure_usd": 500.0,
            "max_leverage": 2.0,
            "max_loss_velocity_usd_per_60s": 50.0,
            "max_open_positions": 2,
            "max_slippage_bps": 30,
            "equity_usd": 10000.0,
        },
        "allowed_venues": ["paper"],
        "allowed_contracts": ["0xabc", "0xdef", "0x999"],
        "position_limits": {"max_equity_pct_per_trade": 2.0},
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(policy), encoding="utf-8")
    return path


@pytest.fixture
def kernel(policy_file: Path, tmp_path: Path) -> RiskKernel:
    state_path = tmp_path / "state.json"
    return RiskKernel.from_policy_path(policy_file, state_path)


def base_trade(**kwargs) -> TradeRequest:
    defaults = dict(
        trade_id="t1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        leverage=1.0,
        expected_price=100.0,
        worst_price=100.2,
    )
    defaults.update(kwargs)
    return TradeRequest(**defaults)


def test_allow_within_limits(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(base_trade())
    assert result.decision == "ALLOW"


def test_deny_notional_cap(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(base_trade(notional_usd=150.0))
    assert result.decision == "DENY"
    assert result.code == "NOTIONAL_CAP"


def test_deny_exposure_cap(kernel: RiskKernel) -> None:
    kernel.apply_fill(base_trade(notional_usd=450.0))
    result = kernel.validate_trade(base_trade(notional_usd=60.0))
    assert result.decision == "DENY"
    assert result.code == "EXPOSURE_CAP"


def test_deny_leverage_cap(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(base_trade(leverage=5.0))
    assert result.decision == "DENY"
    assert result.code == "LEVERAGE_CAP"


def test_deny_loss_velocity(kernel: RiskKernel) -> None:
    kernel.state.record_loss(60.0)
    result = kernel.validate_trade(base_trade())
    assert result.decision == "DENY"
    assert result.code == "LOSS_VELOCITY"


def test_deny_position_count(kernel: RiskKernel) -> None:
    kernel.apply_fill(base_trade(trade_id="a", contract="0xabc", notional_usd=10))
    kernel.apply_fill(base_trade(trade_id="b", contract="0xdef", notional_usd=10))
    result = kernel.validate_trade(base_trade(trade_id="c", contract="0x999"))
    assert result.decision == "DENY"
    assert result.code == "POSITION_COUNT"


def test_deny_venue(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(base_trade(venue="binance"))
    assert result.decision == "DENY"
    assert result.code == "VENUE_DENIED"


def test_deny_contract(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(base_trade(contract="0xbad"))
    assert result.decision == "DENY"
    assert result.code == "CONTRACT_DENIED"


def test_deny_slippage(kernel: RiskKernel) -> None:
    result = kernel.validate_trade(
        base_trade(notional_usd=10.0, expected_price=100.0, worst_price=110.0)
    )
    assert result.decision == "DENY"
    assert result.code == "SLIPPAGE"


def test_kill_switch_denies(kernel: RiskKernel) -> None:
    kernel.kill_switch_active = True
    result = kernel.validate_trade(base_trade())
    assert result.decision == "DENY"
    assert result.code == "KILL_SWITCH"


def test_flatten_revokes_keys(kernel: RiskKernel) -> None:
    payload = kernel.trigger_flatten()
    assert payload["halted"] is True
    assert kernel.state.keys_revoked is True
    result = kernel.validate_trade(base_trade())
    assert result.decision == "DENY"


def test_fail_closed_client_unreachable() -> None:
    from titan_safety.client import RiskKernelClient

    client = RiskKernelClient("http://127.0.0.1:1")
    result = client.validate(base_trade())
    assert result.decision == "DENY"
    assert result.code == "KERNEL_UNREACHABLE"
