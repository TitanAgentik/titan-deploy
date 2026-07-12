"""Tier 1 capital risk — items 6–10 enforcement tests."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from titan_safety.allocator import AllocatorConfig, CapitalAllocator
from titan_safety.drawdown_notifier import process_drawdown_update
from titan_safety.drawdown_tiers import DrawdownTierEngine
from titan_safety.kernel import RiskKernel, RiskKernelState, TradeRequest
from titan_safety.kill_switch import KillSwitch
from titan_safety.policy_loader import apply_capital_profile, load_policy
from titan_safety.risk_inputs import detect_live_risk_stubs, loss_velocity_from_fills


def _tier1_policy(tmp_path: Path, profile: str = "paper") -> Path:
    base = {
        "version": "2.2",
        "mode": "enforce",
        "capital_profile": profile,
        "drawdown_notify_only": True,
        "trading_limits": {"equity_usd": 10000, "max_notional_usd_per_trade": 5000},
        "allowed_venues": ["paper", "hyperliquid"],
        "reconciliation": {"adapter": "mock"},
        "portfolio_risk": {"correlation_groups": {"defi_yield": ["P1"]}},
        "drawdown_tiers": [
            {"pct": 5.0, "action": "notify_operator", "severity": "HIGH"},
        ],
        "tier1_capital_risk": {
            "profiles": {
                "paper": {
                    "drawdown_notify_only": True,
                    "reconciliation": {"adapter": "mock"},
                    "allocator": {"advisory_mode": True},
                    "portfolio_risk": {"augur_feed": "stub", "allow_augur_stub": True},
                },
                "live": {
                    "drawdown_notify_only": False,
                    "reconciliation": {"adapter": "live"},
                    "allocator": {"advisory_mode": False},
                    "portfolio_risk": {"augur_feed": "file", "allow_augur_stub": False},
                    "kill_switch": {"dual_control_resume": True},
                    "drawdown_tiers": [
                        {"pct": 8.0, "action": "halt_new_risk", "severity": "HIGH"},
                        {"pct": 12.0, "action": "full_halt_flatten", "severity": "CRITICAL"},
                    ],
                },
            }
        },
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(base), encoding="utf-8")
    return path


def test_default_template_is_paper(tmp_path: Path) -> None:
    policy_path = Path(__file__).resolve().parents[1] / "templates" / "risk_kernel" / "policy.yaml"
    raw = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    assert raw.get("capital_profile") == "paper"
    assert raw.get("autonomous_signing", {}).get("enabled") is False
    venues = [v.lower() for v in raw.get("allowed_venues", [])]
    assert venues == ["paper"]
    assert raw.get("flash_loan_live", {}).get("enabled") is False
    assert raw.get("allocator", {}).get("max_active_pipelines") == 2
    assert raw.get("allocator", {}).get("advisory_mode") is True


def test_apply_capital_profile_live_enforcement(tmp_path: Path) -> None:
    policy = load_policy(_tier1_policy(tmp_path, profile="live"))
    assert policy.raw.get("drawdown_notify_only") is False
    assert policy.reconciliation.adapter == "live"
    cfg = AllocatorConfig.from_raw(policy.raw)
    assert cfg.advisory_mode is False


def test_live_drawdown_halts_new_risk(tmp_path: Path) -> None:
    policy = load_policy(_tier1_policy(tmp_path, profile="live"))
    kernel = RiskKernel(policy, RiskKernelState())
    kernel.state.drawdown_pct_24h = 9.0
    engine = DrawdownTierEngine(policy.raw or {})
    engine.apply_tier_enforcement(kernel.state, 9.0, kernel=kernel)

    trade = TradeRequest("t1", "paper", "0xabc", "buy", 100.0, 1.0, strategy_id="P1")
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "DRAWDOWN_HALT_NEW_RISK"


def test_paper_drawdown_never_blocks(tmp_path: Path) -> None:
    policy = load_policy(_tier1_policy(tmp_path, profile="paper"))
    kernel = RiskKernel(policy, RiskKernelState())
    kernel.state.drawdown_pct_24h = 15.0
    trade = TradeRequest("t1", "paper", "0xabc", "buy", 100.0, 1.0, strategy_id="P1")
    assert kernel.validate_trade(trade).decision == "ALLOW"


def test_live_stub_detection(tmp_path: Path) -> None:
    raw = yaml.safe_load(_tier1_policy(tmp_path, profile="live").read_text())
    merged = apply_capital_profile(raw)
    assert "augur_regime_stub" not in detect_live_risk_stubs(merged) or merged["portfolio_risk"]["augur_feed"] != "stub"

    bad = dict(merged)
    bad["portfolio_risk"] = {"augur_feed": "stub"}
    stubs = detect_live_risk_stubs(bad)
    assert "augur_regime_stub" in stubs


def test_dual_resume_requires_two_operators(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    s1 = ks.sign_command("RESUME", "op_a")
    s2 = ks.sign_command("RESUME", "op_a")
    ok, msg = ks.verify_dual_resume(s1, s2)
    assert not ok
    assert "distinct" in msg

    s3 = ks.sign_command("RESUME", "op_b")
    ok2, _ = ks.verify_dual_resume(s1, s3)
    assert ok2


def test_fill_ledger_velocity(tmp_path: Path) -> None:
    ledger = tmp_path / "hyperliquid_fill_ledger.jsonl"
    ledger.write_text(
        json.dumps({"ts": 1e9, "realized_pnl_usd": -50.0, "pipeline_id": "P1"}) + "\n",
        encoding="utf-8",
    )
    v = loss_velocity_from_fills(tmp_path, window_seconds=1e12, now=1e9 + 10)
    assert v == 50.0


def test_allocator_enforced_degross_on_live(tmp_path: Path) -> None:
    policy = load_policy(_tier1_policy(tmp_path, profile="live"))
    alloc = CapitalAllocator(AllocatorConfig.from_raw(policy.raw))
    assert alloc.is_enforced()
    budget = alloc.gross_budget(10000.0, "neutral", drawdown_pct=6.0)
    assert budget == 5000.0  # 50% at 5% hard de-gross ladder step
