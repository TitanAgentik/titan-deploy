"""Formal property-based tests on risk kernel — table-driven (no hypothesis dep)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from titan_safety.broadcast_authority import BroadcastAuthority, BroadcastSubmission
from titan_safety.gate_receipt import (
    consume_gate_receipt,
    issue_gate_receipt,
    reset_consumed_receipts,
)
from titan_safety.kernel import RiskKernel, RiskKernelState, TradeRequest, Position
from titan_safety.portfolio_risk import PortfolioRiskEngine, PortfolioSnapshot


def _base_policy() -> dict:
    return {
        "version": "2.2",
        "mode": "enforce",
        "trading_limits": {
            "max_notional_usd_per_trade": 500.0,
            "max_aggregate_exposure_usd": 1000.0,
            "max_leverage": 3.0,
            "max_loss_velocity_usd_per_60s": 500.0,
            "max_open_positions": 8,
            "max_slippage_bps": 50,
            "equity_usd": 2500.0,
        },
        "allowed_venues": ["paper", "hyperliquid"],
        "allowed_contracts": ["0xabc", "eth"],
        "position_limits": {"max_equity_pct_per_trade": 50.0, "human_approval_above_pct": 100.0},
        "drawdown_tiers": [],
        "drawdown_velocity": {"max_loss_usd_per_15m": 9999.0},
    }


def _kernel(tmp_path: Path, policy: dict | None = None, **state_kw) -> RiskKernel:
    p = tmp_path / "policy.yaml"
    p.write_text(yaml.dump(policy or _base_policy()))
    state_path = tmp_path / "state.json"
    k = RiskKernel.from_policy_path(p, state_path)
    for k_attr, v in state_kw.items():
        setattr(k.state, k_attr, v)
    k.state.save()
    return RiskKernel.from_policy_path(p, state_path)


def _trade(**kw) -> TradeRequest:
    defaults = dict(
        trade_id="prop-1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=100.0,
    )
    defaults.update(kw)
    return TradeRequest(**defaults)


# --- Property: never exceed aggregate notional ---

AGGREGATE_NOTIONAL_CASES = [
    {"existing": 600.0, "trade_notional": 500.0, "expect": "DENY", "code": "EXPOSURE_CAP"},
    {"existing": 0.0, "trade_notional": 500.0, "expect": "ALLOW"},
    {"existing": 500.0, "trade_notional": 400.0, "expect": "ALLOW"},
    {"existing": 900.0, "trade_notional": 50.0, "expect": "ALLOW"},
    {"existing": 950.0, "trade_notional": 60.0, "expect": "DENY", "code": "EXPOSURE_CAP"},
    {"existing": 400.0, "trade_notional": 500.0, "expect": "ALLOW"},
]


@pytest.mark.parametrize("case", AGGREGATE_NOTIONAL_CASES, ids=lambda c: f"exp{c['existing']}_tr{c['trade_notional']}")
def test_property_never_exceed_aggregate_notional(tmp_path: Path, case: dict) -> None:
    k = _kernel(tmp_path)
    if case["existing"] > 0:
        k.state.positions["paper:0xabc"] = Position(
            venue="paper", contract="0xabc", notional_usd=case["existing"], leverage=1.0
        )
    r = k.validate_trade(_trade(notional_usd=case["trade_notional"]))
    assert r.decision == case["expect"]
    if case["expect"] == "DENY":
        assert r.code == case.get("code", "EXPOSURE_CAP")


# --- Property: never trade while halted ---

HALTED_CASES = [
    {"halted": True, "kill_switch": False, "keys_revoked": False},
    {"halted": False, "kill_switch": True, "keys_revoked": False},
    {"halted": False, "kill_switch": False, "keys_revoked": True},
    {"halted": True, "kill_switch": True, "keys_revoked": True},
]


@pytest.mark.parametrize("case", HALTED_CASES, ids=lambda c: f"h{c['halted']}_k{c['kill_switch']}_r{c['keys_revoked']}")
def test_property_never_trade_while_halted(tmp_path: Path, case: dict) -> None:
    k = _kernel(
        tmp_path,
        halted=case["halted"],
        keys_revoked=case["keys_revoked"],
    )
    k.kill_switch_active = case["kill_switch"]
    r = k.validate_trade(_trade(notional_usd=10.0))
    assert r.decision == "DENY"


# --- Property: receipt single-use ---

RECEIPT_SINGLE_USE_CASES = [
    {"reuse": False, "expect_second": False},
    {"reuse": True, "expect_second": False},
]


@pytest.mark.parametrize("case", RECEIPT_SINGLE_USE_CASES, ids=lambda c: f"reuse_{c['reuse']}")
def test_property_receipt_single_use(tmp_path: Path, case: dict) -> None:
    reset_consumed_receipts()
    trade = _trade(trade_id=f"rcpt-{case['reuse']}")
    receipt = issue_gate_receipt(trade, tmp_path)
    ok1, _ = consume_gate_receipt(receipt.token, trade, tmp_path)
    assert ok1 is True
    if case["reuse"]:
        ok2, reason2 = consume_gate_receipt(receipt.token, trade, tmp_path)
        assert ok2 is case["expect_second"]
        assert "consumed" in reason2.lower()


def test_property_broadcast_rejects_reused_receipt(tmp_path: Path) -> None:
    reset_consumed_receipts()
    policy = _base_policy()
    policy["tier0_money_path"] = {"enabled": True, "broadcast_authority_enforced": True}
    trade = _trade(venue="hyperliquid")
    receipt = issue_gate_receipt(trade, tmp_path)
    body = {"typed_data": {"message": {"coin": "ETH"}}, "calldata": None}
    from titan_safety.trade_verifier import compute_payload_hash

    phash = compute_payload_hash(body)
    from titan_safety.gate_receipt import bind_receipt_to_payload

    bound = bind_receipt_to_payload(receipt.token, trade, phash, tmp_path)
    sub = BroadcastSubmission(
        caller_id="trench-ops",
        trade=trade,
        gate_receipt=bound.token,
        typed_data=body["typed_data"],
    )

    def mock_submit(sub, t):
        return {"status": "submitted"}

    auth = BroadcastAuthority(policy, tmp_path, venue_submit=mock_submit)
    r1 = auth.submit(sub)
    assert r1.decision == "ALLOW"
    r2 = auth.submit(sub)
    assert r2.decision == "DENY"
    assert "consumed" in r2.reason.lower() or r2.code == "GATE_RECEIPT_INVALID"


# --- Property: kernel DENY always wins ---

KERNEL_DENY_WINS_CASES = [
    {
        "portfolio_decision": "DENY",
        "portfolio_code": "PORTFOLIO_VAR",
        "kernel_should": "DENY",
    },
    {
        "portfolio_decision": "ALLOW",
        "portfolio_code": "OK",
        "kernel_should": "ALLOW",
    },
]


@pytest.mark.parametrize("case", KERNEL_DENY_WINS_CASES, ids=lambda c: c["portfolio_code"])
def test_property_kernel_deny_always_wins(tmp_path: Path, case: dict) -> None:
    k = _kernel(tmp_path)

    def simulator(trade: TradeRequest) -> dict:
        return {
            "decision": case["portfolio_decision"],
            "code": case["portfolio_code"],
            "reason": "simulated portfolio risk",
        }

    k.portfolio_simulator = simulator
    r = k.validate_trade(_trade(strategy_id="P1", notional_usd=50.0))
    assert r.decision == case["kernel_should"]
    if case["kernel_should"] == "DENY":
        assert r.code == case["portfolio_code"]


def test_property_portfolio_simulator_deny_overrides_allow_path(tmp_path: Path) -> None:
    """Portfolio DENY must win even when trade is otherwise within kernel limits."""
    k = _kernel(tmp_path)
    k.portfolio_simulator = lambda t: {
        "decision": "DENY",
        "code": "PORTFOLIO_CVAR",
        "reason": "CVaR breach",
    }
    r = k.validate_trade(_trade(strategy_id="P3", notional_usd=1.0))
    assert r.decision == "DENY"
    assert r.code == "PORTFOLIO_CVAR"


def test_property_enforce_mode_bypasses_notional_limits(tmp_path: Path) -> None:
    policy = _base_policy()
    policy["mode"] = "monitor"
    k = _kernel(tmp_path, policy)
    r = k.validate_trade(_trade(notional_usd=99999.0))
    assert r.decision == "ALLOW"
    assert r.reason == "policy_monitor_mode"
