"""Policy loader and service port tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.policy_loader import load_policy


def test_load_policy_ports(tmp_path: Path) -> None:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 2500},
        "allowed_venues": ["paper"],
        "service": {
            "portfolio_risk_port": 19004,
            "dead_mans_switch_port": 19005,
        },
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    policy = load_policy(path)
    assert policy.service.portfolio_risk_port == 19004
    assert policy.service.dead_mans_switch_port == 19005


def test_drawdown_velocity_in_raw_policy(tmp_path: Path) -> None:
    tpl = Path(__file__).resolve().parent.parent / "templates" / "risk_kernel" / "policy.yaml"
    if not tpl.exists():
        return
    policy = load_policy(tpl)
    assert "drawdown_velocity" in policy.raw
    assert policy.raw["drawdown_velocity"]["max_loss_usd_per_15m"] > 0
