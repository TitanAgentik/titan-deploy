"""Drawdown notify-only policy — never blocks; alerts on tier cross."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

from titan_safety.drawdown_notifier import process_drawdown_update
from titan_safety.drawdown_tiers import DrawdownTierEngine
from titan_safety.kernel import RiskKernel, RiskKernelState, TradeRequest
from titan_safety.policy_loader import load_policy


def _policy(tmp_path: Path, **overrides) -> Path:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "drawdown_notify_only": True,
        "trading_limits": {"equity_usd": 10000, "max_notional_usd_per_trade": 5000},
        "allowed_venues": ["paper", "jito", "hyperliquid"],
        "reconciliation": {"adapter": "mock"},
        "drawdown_volatile_exempt": {
            "pipelines": ["P22"],
            "correlation_groups": ["memecoin_trench"],
            "venues": ["jito"],
        },
        "portfolio_risk": {"correlation_groups": {"memecoin_trench": ["P22"], "defi_yield": ["P1"]}},
        "drawdown_tiers": [
            {"pct": 5.0, "action": "notify_operator", "severity": "HIGH"},
            {"pct": 12.0, "action": "notify_critical_continue", "severity": "CRITICAL"},
        ],
    }
    data.update(overrides)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_drawdown_never_blocks_trades(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    kernel = RiskKernel(policy, RiskKernelState())
    kernel.state.drawdown_pct_24h = 13.0

    core = TradeRequest("d1", "hyperliquid", "0xabc", "buy", 100.0, 1.0, strategy_id="P1")
    trench = TradeRequest("m1", "jito", "mint", "buy", 50.0, 1.0, strategy_id="P22")

    assert kernel.validate_trade(core).decision == "ALLOW"
    assert kernel.validate_trade(trench).decision == "ALLOW"
    assert DrawdownTierEngine(policy.raw or {}).check_trade(13.0, core) is None


def test_notifier_fires_on_tier_cross(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    safety = tmp_path / "safety"
    safety.mkdir()
    raw = policy.raw or {}

    r1 = process_drawdown_update(raw, safety, previous_pct=1.0, current_pct=6.0)
    assert r1["alerts_sent"] >= 1
    assert r1["trading_continues"] is True

    queue = (safety / "herald_queue.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(queue) >= 1
    event = json.loads(queue[-1])
    assert event["event"] == "drawdown_tier"
    assert event["trading_continues"] is True
    assert event["immediate"] is True

    r2 = process_drawdown_update(raw, safety, previous_pct=6.0, current_pct=7.0)
    assert r2["alerts_sent"] == 0


def test_notifier_critical_at_12(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    safety = tmp_path / "safety2"
    safety.mkdir()
    raw = policy.raw or {}

    result = process_drawdown_update(raw, safety, previous_pct=4.0, current_pct=12.5)
    assert result["alerts_sent"] >= 1
    events = [
        json.loads(line)
        for line in (safety / "herald_queue.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(e.get("level") == "CRITICAL" for e in events)
