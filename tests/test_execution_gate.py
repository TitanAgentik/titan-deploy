"""Fail-closed execution gate + mock-adapter ban tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from titan_safety.execution_gate import ExecutionGate
from titan_safety.kernel import TradeRequest
from titan_safety.policy_loader import load_policy
from titan_safety.reconciliation import (
    LiveExchangeAdapter,
    assert_adapter_allowed_for_policy,
    get_adapter,
)


def _write_policy(tmp_path: Path, **overrides) -> Path:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 10000},
        "allowed_venues": ["paper"],
        "reconciliation": {"adapter": "mock", "divergence_threshold_usd": 10.0},
        "service": {"risk_kernel_port": 19001, "reconciliation_port": 19002},
    }
    data.update(overrides)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_mock_allowed_for_paper_only(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path))
    assert_adapter_allowed_for_policy("mock", policy)  # no raise


def test_mock_forbidden_with_live_venues(tmp_path: Path) -> None:
    policy = load_policy(
        _write_policy(tmp_path, allowed_venues=["hyperliquid", "paper"])
    )
    with pytest.raises(ValueError, match="MOCK_ADAPTER_FORBIDDEN"):
        assert_adapter_allowed_for_policy("mock", policy)


def test_live_adapter_refuses_unwired_fetch() -> None:
    adapter = LiveExchangeAdapter()
    with pytest.raises(RuntimeError, match="no fetcher"):
        adapter.fetch_positions()


def test_live_adapter_with_fetcher() -> None:
    def fetcher(_venues):
        return [{"venue": "hyperliquid", "contract": "0xabc", "notional_usd": 50.0}]

    adapter = get_adapter("live", fetcher=fetcher)
    positions = adapter.fetch_positions()
    assert len(positions) == 1
    assert positions[0].venue == "hyperliquid"


def test_gate_denies_mock_on_live_venues(tmp_path: Path) -> None:
    policy = load_policy(
        _write_policy(tmp_path, allowed_venues=["hyperliquid"])
    )
    gate = ExecutionGate(policy)
    trade = TradeRequest(
        trade_id="t1",
        venue="hyperliquid",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        leverage=1.0,
        expected_price=100.0,
        worst_price=100.1,
    )
    decision = gate.gate(trade)
    assert decision.decision == "DENY"
    assert decision.code == "MOCK_ADAPTER_FORBIDDEN"


def test_gate_fail_closed_when_recon_unreachable(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path))
    gate = ExecutionGate(policy, recon_url="http://127.0.0.1:1", kernel_url="http://127.0.0.1:1")
    trade = TradeRequest(
        trade_id="t1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        leverage=1.0,
        expected_price=100.0,
        worst_price=100.1,
    )
    decision = gate.gate(trade)
    assert decision.decision == "DENY"
    assert decision.code == "RECON_UNREACHABLE"


def test_gate_allow_when_stages_pass(tmp_path: Path) -> None:
    policy = load_policy(_write_policy(tmp_path))
    gate = ExecutionGate(policy, safety_dir=tmp_path)

    def fake_post(url, body, auth_command=None, timeout=None):
        if "pre_trade" in url:
            return {"decision": "ALLOW", "reason": "ok"}
        return {"decision": "ALLOW", "reason": "ok"}

    trade = TradeRequest(
        trade_id="t1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        leverage=1.0,
        expected_price=100.0,
        worst_price=100.1,
    )
    with patch.object(gate, "_post", side_effect=fake_post):
        decision = gate.gate(trade)
    assert decision.allowed is True
    assert decision.code == "OK"
    assert decision.receipt
    assert decision.receipt.startswith("GATE_ALLOW|")


def test_gate_fast_path_single_hop(tmp_path: Path) -> None:
    policy = load_policy(
        _write_policy(
            tmp_path,
            latency={
                "hot_path": {
                    "enabled": True,
                    "combined_validate": True,
                    "pipelines": ["P22"],
                }
            },
        )
    )
    gate = ExecutionGate(policy, safety_dir=tmp_path)

    def fake_post(url, body, auth_command=None, timeout=None):
        assert "fast_validate" in url
        return {"decision": "ALLOW", "reason": "ok", "stage": "risk_kernel"}

    trade = TradeRequest(
        trade_id="t2",
        venue="jito",
        contract="mint123",
        side="buy",
        notional_usd=5.0,
        leverage=1.0,
        expected_price=1.0,
        worst_price=1.1,
        strategy_id="P22",
    )
    with patch.object(gate, "_post", side_effect=fake_post):
        decision = gate.gate(trade, fast_path=True)
    assert decision.allowed is True
    assert decision.code == "OK_FAST"
