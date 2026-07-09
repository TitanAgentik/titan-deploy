#!/usr/bin/env python3
"""Adversarial / red-team harness — runnable in verify.sh."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "templates" / "safety"))

from titan_safety.kernel import RiskKernel, TradeRequest  # noqa: E402
from titan_safety.kill_switch import KillSwitch  # noqa: E402
from titan_safety.portfolio_risk import PortfolioRiskEngine, PortfolioSnapshot  # noqa: E402
from titan_safety.promotion_gate import PromotionGate, PromotionRequest  # noqa: E402

import yaml  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  OK: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


def scenario_data_poisoning() -> None:
    """Poisoned feed with extreme slippage should DENY."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {
                "max_notional_usd_per_trade": 500,
                "max_aggregate_exposure_usd": 2500,
                "max_leverage": 3,
                "max_loss_velocity_usd_per_60s": 200,
                "max_open_positions": 8,
                "max_slippage_bps": 50,
                "equity_usd": 2500,
            },
            "allowed_venues": ["paper"],
            "allowed_contracts": ["0xabc"],
            "position_limits": {"human_approval_above_pct": 1.0},
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        trade = TradeRequest(
            trade_id="poison1",
            venue="paper",
            contract="0xabc",
            side="buy",
            notional_usd=50,
            expected_price=100,
            worst_price=200,
            strategy_id="P30",
        )
        r = k.validate_trade(trade)
        check("data_poisoning_slippage_deny", r.decision == "DENY", r.code)


def scenario_prompt_injection_feed() -> None:
    """Injected strategy_id with halt flag should DENY."""
    with tempfile.TemporaryDirectory() as td:
        ks = KillSwitch(Path(td))
        ks.activate_pipeline("P-INJECT", "redteam", "prompt injection sim")
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {
                "max_notional_usd_per_trade": 500,
                "max_aggregate_exposure_usd": 2500,
                "max_leverage": 3,
                "max_loss_velocity_usd_per_60s": 200,
                "max_open_positions": 8,
                "max_slippage_bps": 50,
                "equity_usd": 2500,
            },
            "allowed_venues": ["paper"],
            "allowed_contracts": ["0xabc"],
            "position_limits": {"human_approval_above_pct": 1.0},
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        k.pipeline_halt_checker = ks.is_pipeline_halted
        trade = TradeRequest(
            trade_id="inj1",
            venue="paper",
            contract="0xabc",
            side="buy",
            notional_usd=10,
            strategy_id="P-INJECT",
        )
        r = k.validate_trade(trade)
        check("prompt_injection_pipeline_halt", r.decision == "DENY", r.code)


def scenario_correlated_pipeline_failure() -> None:
    """Correlated cluster over cap should DENY via portfolio risk."""
    engine = PortfolioRiskEngine.from_policy_raw(
        {
            "portfolio_risk": {
                "max_correlated_cluster_pct": 20,
                "correlation_groups": {"defi": ["P1", "P3"]},
            }
        }
    )
    snap = PortfolioSnapshot(equity_usd=2500, pipelines=[])
    from titan_safety.portfolio_risk import PipelineExposure

    snap.pipelines = [PipelineExposure("P1", 450)]
    r = engine.simulate_pre_trade(snap, "P3", 100)
    check("correlated_failure_cap", r.decision == "DENY", r.code)


def scenario_self_mod_promotion() -> None:
    """Self-mod touching SOUL must fail even with YES."""
    with tempfile.TemporaryDirectory() as td:
        gate = PromotionGate(Path(td))
        req = PromotionRequest(
            request_id="adv1",
            category="evolution_deploy",
            subject="inject soul",
            operator_response="YES",
            operator_id="attacker",
            metadata={"changed_paths": ["SOUL.md"]},
        )
        d = gate.evaluate(req)
        check("self_mod_soul_blocked", not d.approved, d.reason)


def scenario_black_swan_replay_stub() -> None:
    """FTX-style velocity spike should trip loss velocity."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {
                "max_notional_usd_per_trade": 500,
                "max_aggregate_exposure_usd": 2500,
                "max_leverage": 3,
                "max_loss_velocity_usd_per_60s": 100,
                "max_open_positions": 8,
                "max_slippage_bps": 50,
                "equity_usd": 2500,
            },
            "allowed_venues": ["paper"],
            "allowed_contracts": ["0xabc"],
            "position_limits": {"human_approval_above_pct": 1.0},
            "drawdown_velocity": {"max_loss_usd_per_15m": 200},
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        for _ in range(5):
            k.state.record_loss(50.0)
        trade = TradeRequest(
            trade_id="swan1",
            venue="paper",
            contract="0xabc",
            side="buy",
            notional_usd=10,
        )
        r = k.validate_trade(trade)
        check("black_swan_velocity_halt", r.decision == "DENY", r.code)


def scenario_flash_crash_stub() -> None:
    """Flash crash — 60s velocity breaker."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {
                "max_notional_usd_per_trade": 500,
                "max_aggregate_exposure_usd": 2500,
                "max_leverage": 3,
                "max_loss_velocity_usd_per_60s": 80,
                "max_open_positions": 8,
                "max_slippage_bps": 50,
                "equity_usd": 2500,
            },
            "allowed_venues": ["paper"],
            "allowed_contracts": ["0xabc"],
            "position_limits": {"human_approval_above_pct": 1.0},
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        k.state.record_loss(90.1)
        trade = TradeRequest(
            trade_id="flash1",
            venue="paper",
            contract="0xabc",
            side="buy",
            notional_usd=10,
        )
        r = k.validate_trade(trade)
        check("flash_crash_60s_velocity", r.decision == "DENY", r.code)


def scenario_security_lockdown_halts_signing() -> None:
    """Predatory lockdown must set SIGNING_HALTED so signing_node DENYs."""
    from titan_safety.security_ops import SecurityOps
    from titan_safety.signing_service import SigningNode

    with tempfile.TemporaryDirectory() as td:
        safety = Path(td)
        ops = SecurityOps(safety)
        result = ops.lockdown("redteam", "adversarial lockdown drill")
        check("security_lockdown_ok", result.get("ok") is True, str(result))
        check("security_lockdown_signing_flag", ops.signing_halted(), "flag missing")
        node = SigningNode(safety_dir=safety)
        code, body = node.sign(
            {"request_id": "adv-1", "trade_id": "t1", "venue": "paper"},
            {},
        )
        check(
            "security_lockdown_signing_deny",
            code == 403 and body.get("code") == "SIGNING_HALTED",
            str(body),
        )


def scenario_honeypot_default_armed() -> None:
    """Impenetrable/predatory: honeypots default armed until explicit disarm."""
    from titan_safety.security_ops import SecurityOps

    with tempfile.TemporaryDirectory() as td:
        ops = SecurityOps(Path(td))
        check("honeypot_default_armed", ops.honeypot_armed() is True)
        ops.honeypot_disarm("redteam")
        check("honeypot_disarm", ops.honeypot_armed() is False)
        ops.honeypot_arm("SENTINEL")
        check("honeypot_rearm", ops.honeypot_armed() is True)


def scenario_stalk_posture_pillars() -> None:
    """Status exposes all four pillars for Cockpit / SENTINEL heartbeat."""
    from titan_safety.security_ops import SecurityOps

    with tempfile.TemporaryDirectory() as td:
        st = SecurityOps(Path(td)).status()
        pillars = st.get("pillars") or {}
        check(
            "four_pillars_present",
            set(pillars) >= {"impenetrable", "evasion", "stalking", "predatory"},
            str(pillars),
        )
        check("six_impenetrable_layers", len(st.get("layers") or []) == 6)


def scenario_memecoin_honeypot_filter() -> None:
    """P22 six-gate filter must reject freeze-authority honeypot mints."""
    from titan_safety.memecoin_filter import MemecoinFilter, MintCandidate

    v = MemecoinFilter().evaluate(
        MintCandidate(
            mint="honeypot1",
            mint_authority_revoked=True,
            freeze_authority_revoked=False,
            sell_sim_ok=True,
        )
    )
    check("memecoin_honeypot_filter_deny", not v.passed, v.reject_reason)


def scenario_autonomous_low_confidence_deny() -> None:
    """Live venue trades without confidence must DENY (no human bypass)."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {"equity_usd": 2500, "max_notional_usd_per_trade": 500},
            "allowed_venues": ["binance_spot"],
            "allowed_contracts": ["0xabc"],
            "autonomous_signing": {"enabled": True, "min_confidence_reduced": 0.50},
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        trade = TradeRequest(
            trade_id="noc1",
            venue="binance_spot",
            contract="0xabc",
            side="buy",
            notional_usd=10,
            confidence=0.0,
        )
        r = k.validate_trade(trade)
        check("autonomous_low_confidence_deny", r.decision == "DENY" and r.code == "CONFIDENCE_TOO_LOW", r.code)


def scenario_autonomous_bft_required() -> None:
    """Trades >1% equity on live venues require 2-of-3 BFT votes."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {"equity_usd": 2500, "max_notional_usd_per_trade": 500},
            "allowed_venues": ["binance_spot"],
            "allowed_contracts": ["0xabc"],
            "position_limits": {"human_approval_above_pct": 1.0},
            "autonomous_signing": {
                "enabled": True,
                "bft_required_above_equity_pct": 1.0,
                "bft_threshold": 2,
            },
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        trade = TradeRequest(
            trade_id="bft1",
            venue="binance_spot",
            contract="0xabc",
            side="buy",
            notional_usd=30,
            confidence=0.85,
        )
        r = k.validate_trade(trade)
        check("autonomous_bft_insufficient", r.decision == "DENY" and r.code == "BFT_INSUFFICIENT", r.code)


def scenario_blind_sign_rejected_live() -> None:
    """Signing node must reject live-venue sign without typed_data/calldata."""
    from titan_safety.signing_service import SigningNode
    from titan_safety.trade_verifier import verify_sign_payload

    trade = TradeRequest(
        trade_id="blind1",
        venue="binance_spot",
        contract="0xabc",
        side="buy",
        notional_usd=10,
    )
    policy_raw = {"autonomous_signing": {"require_typed_data_live": True}}
    ok, reason = verify_sign_payload(trade, {}, policy_raw)
    check("blind_sign_rejected_live", not ok and "BLIND" in reason, reason)


def scenario_flash_loan_unapproved_live() -> None:
    """Live flash-loan tx must DENY without operator flash_loan_live YES."""
    with tempfile.TemporaryDirectory() as td:
        policy = {
            "version": "2.1",
            "mode": "enforce",
            "trading_limits": {
                "max_notional_usd_per_trade": 500,
                "max_aggregate_exposure_usd": 2500,
                "max_leverage": 3,
                "max_loss_velocity_usd_per_60s": 500,
                "max_open_positions": 8,
                "max_slippage_bps": 50,
                "equity_usd": 2500,
            },
            "allowed_venues": ["paper", "uniswap_v3"],
            "allowed_contracts": ["0xba12222222228d8ba445958a685a0a280785497"],
            "position_limits": {"flash_loan_live_requires_approval": True},
            "flash_loan_live": {
                "enabled": True,
                "pipeline_ids": ["P3"],
                "sources": {"ethereum": ["balancer"]},
            },
        }
        p = Path(td) / "policy.yaml"
        p.write_text(yaml.dump(policy))
        k = RiskKernel.from_policy_path(p, Path(td) / "state.json")
        trade = TradeRequest(
            trade_id="fl_adv1",
            venue="uniswap_v3",
            contract="0xba12222222228d8ba445958a685a0a280785497",
            side="buy",
            notional_usd=10,
            uses_flash_loan=True,
            flash_loan_source="balancer",
            flash_loan_amount_usd=10,
            strategy_id="P3",
        )
        r = k.validate_trade(trade)
        check("flash_loan_unapproved_live", r.decision == "DENY" and r.code == "FLASH_LOAN_NOT_APPROVED", r.code)


def main() -> int:
    print("[adversarial] Running red-team scenarios...")
    scenario_data_poisoning()
    scenario_prompt_injection_feed()
    scenario_correlated_pipeline_failure()
    scenario_self_mod_promotion()
    scenario_black_swan_replay_stub()
    scenario_flash_crash_stub()
    scenario_security_lockdown_halts_signing()
    scenario_honeypot_default_armed()
    scenario_stalk_posture_pillars()
    scenario_memecoin_honeypot_filter()
    scenario_autonomous_low_confidence_deny()
    scenario_autonomous_bft_required()
    scenario_blind_sign_rejected_live()
    scenario_flash_loan_unapproved_live()
    print(f"[adversarial] {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
