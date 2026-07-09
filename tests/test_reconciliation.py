"""Unit tests for position reconciliation."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.policy_loader import load_policy
from titan_safety.reconciliation import (
    BelievedPosition,
    MockPaperAdapter,
    ReconciliationService,
)


def policy_file(tmp_path: Path) -> Path:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 1000},
        "reconciliation": {
            "divergence_threshold_usd": 10.0,
            "divergence_threshold_pct": 1.0,
            "adapter": "mock",
        },
    }
    p = tmp_path / "policy.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


def test_reconcile_allow(tmp_path: Path) -> None:
    policy = load_policy(policy_file(tmp_path))
    adapter = MockPaperAdapter(
        [BelievedPosition("paper", "0xabc", 100.0)]
    )
    svc = ReconciliationService(policy, adapter)
    believed = [BelievedPosition("paper", "0xabc", 100.0)]
    result = svc.reconcile(believed)
    assert result.decision == "ALLOW"


def test_reconcile_halt_on_divergence(tmp_path: Path) -> None:
    policy = load_policy(policy_file(tmp_path))
    adapter = MockPaperAdapter(
        [BelievedPosition("paper", "0xabc", 200.0)]
    )
    svc = ReconciliationService(policy, adapter)
    believed = [BelievedPosition("paper", "0xabc", 100.0)]
    result = svc.reconcile(believed)
    assert result.decision == "HALT"
    assert result.halted is True


def test_pre_trade_gate_blocks_when_halted(tmp_path: Path) -> None:
    policy = load_policy(policy_file(tmp_path))
    adapter = MockPaperAdapter([BelievedPosition("paper", "0xabc", 500.0)])
    svc = ReconciliationService(policy, adapter)
    believed = [BelievedPosition("paper", "0xabc", 100.0)]
    svc.reconcile(believed)
    pending = BelievedPosition("paper", "0xabc", 10.0)
    result = svc.pre_trade_gate(believed, pending)
    assert result.decision == "DENY"
