"""Unit tests for capital deposit, withdraw limits, balance, audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from titan_safety.capital import CapitalConfig, CapitalManager, TrezorSweepConfig
from titan_safety.telegram_capital import handle_capital_command, parse_capital_command


@pytest.fixture
def capital_env(tmp_path: Path) -> CapitalManager:
    cfg = CapitalConfig(
        min_operating_capital_usd=500.0,
        max_single_withdrawal_pct=20.0,
        state_path=tmp_path / "portfolio_state.json",
        audit_path=tmp_path / "capital_audit.jsonl",
        withdrawal_adapter="mock",
        trezor_sweep=TrezorSweepConfig(harvest_threshold_usd=15000.0),
    )
    return CapitalManager(cfg)


def test_deposit_increases_equity(capital_env: CapitalManager) -> None:
    result = capital_env.deposit(2500.0, "USDC", operator="test")
    assert result.ok is True
    assert result.state["equity_usd"] == 2500.0
    assert result.state["available_usd"] == 2500.0
    assert result.state["assets"]["USDC"] == 2500.0


def test_balance_after_deposit(capital_env: CapitalManager) -> None:
    capital_env.deposit(1000.0, "USDC", operator="test")
    bal = capital_env.balance()
    assert bal["equity_usd"] == 1000.0
    assert bal["max_withdrawable_usd"] == 500.0
    assert bal["harvest_phase"] is False


def test_withdraw_small_succeeds(capital_env: CapitalManager) -> None:
    capital_env.deposit(2500.0, "USDC", operator="test")
    result = capital_env.withdraw(100.0, "USDC", operator="test")
    assert result.ok is True
    assert result.action == "withdraw_executed"
    assert result.state["equity_usd"] == 2400.0


def test_withdraw_breaches_min_reserve_denied(capital_env: CapitalManager) -> None:
    capital_env.deposit(1000.0, "USDC", operator="test")
    result = capital_env.withdraw(600.0, "USDC", operator="test")
    assert result.ok is False
    assert "min operating capital" in result.message.lower()


def test_large_withdrawal_requires_confirm(capital_env: CapitalManager) -> None:
    capital_env.deposit(2500.0, "USDC", operator="test")
    result = capital_env.withdraw(600.0, "USDC", operator="test")
    assert result.ok is True
    assert result.needs_confirm is True
    assert result.request_id is not None
    assert result.state["reserved_usd"] == 600.0
    assert result.state["available_usd"] == 1900.0


def test_confirm_large_withdrawal(capital_env: CapitalManager) -> None:
    capital_env.deposit(2500.0, "USDC", operator="test")
    pending = capital_env.withdraw(600.0, "USDC", operator="test")
    assert pending.request_id
    confirmed = capital_env.withdraw(
        0.0,
        "USDC",
        operator="test",
        confirm_request_id=pending.request_id,
    )
    assert confirmed.ok is True
    assert confirmed.action == "withdraw_executed"
    assert confirmed.state["equity_usd"] == 1900.0


def test_audit_chain_valid(capital_env: CapitalManager) -> None:
    capital_env.deposit(500.0, "USDC", tx_hash="0xabc", operator="test")
    capital_env.withdraw(50.0, "USDC", operator="test")
    ok, msg = capital_env.verify_audit()
    assert ok is True
    assert "valid" in msg


def test_sweep_growth_phase_skipped(capital_env: CapitalManager) -> None:
    capital_env.deposit(2500.0, "USDC", operator="test")
    result = capital_env.sweep(weekly_profit_usd=500.0, operator="test")
    assert result.ok is False
    assert "growth phase" in result.message.lower()


def test_sweep_harvest_phase(capital_env: CapitalManager) -> None:
    capital_env.deposit(40000.0, "USDC", operator="test")
    result = capital_env.sweep(weekly_profit_usd=1000.0, operator="test")
    assert result.ok is True
    assert result.action == "sweep_executed"
    assert result.state["equity_usd"] == 39800.0


def test_telegram_parse_deposit() -> None:
    action, kw = parse_capital_command("/deposit 2500 USDC")
    assert action == "deposit"
    assert kw["amount"] == 2500.0
    assert kw["asset"] == "USDC"


def test_telegram_parse_capital_subcommand() -> None:
    action, kw = parse_capital_command("/capital deposit 100 USDC")
    assert action == "deposit"
    assert kw["amount"] == 100.0


def test_telegram_handle_balance(capital_env: CapitalManager) -> None:
    capital_env.deposit(2500.0, "USDC", operator="test")
    result = handle_capital_command("/balance", operator="test", manager=capital_env)
    assert result.ok is True
    assert result.state["equity_usd"] == 2500.0


def test_state_persisted(capital_env: CapitalManager) -> None:
    capital_env.deposit(100.0, "USDC", operator="test")
    path = capital_env.config.state_path
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["equity_usd"] == 100.0
