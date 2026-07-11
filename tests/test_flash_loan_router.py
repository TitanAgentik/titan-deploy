"""Flash-loan router unit tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.flash_loan_router import (
    FlashLoanConfig,
    FlashLoanRequest,
    FlashLoanRouter,
    FlashOperation,
)
from titan_safety.flash_loan_sim import run_simulation
from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.policy_loader import load_policy
from titan_safety.promotion_gate import PromotionGate, PromotionRequest


def _policy_with_flash(tmp_path: Path, **fl_overrides) -> Path:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {
            "max_notional_usd_per_trade": 1000.0,
            "max_aggregate_exposure_usd": 5000.0,
            "max_leverage": 3.0,
            "max_loss_velocity_usd_per_60s": 500.0,
            "max_open_positions": 8,
            "max_slippage_bps": 50,
            "equity_usd": 2500.0,
        },
        "allowed_venues": ["paper", "uniswap_v3", "flashbots_protect"],
        "allowed_contracts": [
            "0xabc",
            "0xba12222222228d8ba445958a685a0a280785497",
        ],
        "position_limits": {"flash_loan_live_requires_approval": False},
        "flash_loan_live": {
            "enabled": False,
            "max_amount_usd": 100_000.0,
            "pipeline_ids": ["P3", "P6"],
            "sources": {"ethereum": ["balancer", "morpho", "aave_v3"]},
        },
    }
    fl = data["flash_loan_live"]
    fl.update(fl_overrides)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_route_prefers_zero_fee_source() -> None:
    router = FlashLoanRouter(FlashLoanConfig())
    decision = router.route("WETH", 10_000, "ethereum")
    assert decision.selected_source == "balancer"
    assert decision.fee_bps == 0.0


def test_compose_requires_repay_or_injects_for_probe() -> None:
    router = FlashLoanRouter(FlashLoanConfig())
    req = FlashLoanRequest(asset="WETH", amount_usd=1000, chain="ethereum", strategy_id="P3")
    result = router.compose(req)
    assert result.passed is True
    assert result.selected_source == "balancer"
    assert result.typed_data.get("primaryType") == "FlashLoanExecution"
    assert result.trade_hints["uses_flash_loan"] is True


def test_compose_rejects_over_max_amount() -> None:
    cfg = FlashLoanConfig(max_amount_usd=500.0)
    router = FlashLoanRouter(cfg)
    req = FlashLoanRequest(
        asset="WETH",
        amount_usd=1000,
        chain="ethereum",
        strategy_id="P3",
        operations=[
            FlashOperation("swap", "uniswap_v3", "WETH", "1"),
            FlashOperation("repay_flash", "flash_loan_router", "WETH", "1"),
        ],
    )
    result = router.compose(req)
    assert result.passed is False
    assert "max" in result.reject_reason


def test_paper_flash_loan_allowed_without_promotion(tmp_path: Path) -> None:
    policy_path = _policy_with_flash(tmp_path)
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "state.json")
    trade = TradeRequest(
        trade_id="fl1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
        confidence=0.55,
        uses_flash_loan=True,
        flash_loan_source="balancer",
        flash_loan_amount_usd=10.0,
        strategy_id="P3",
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"


def test_live_flash_loan_allowed_without_promotion_when_autonomous(tmp_path: Path) -> None:
    policy_path = _policy_with_flash(tmp_path, enabled=True)
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "state.json")
    trade = TradeRequest(
        trade_id="fl2",
        venue="uniswap_v3",
        contract="0xba12222222228d8ba445958a685a0a280785497",
        side="buy",
        notional_usd=10.0,
        confidence=0.75,
        uses_flash_loan=True,
        flash_loan_source="balancer",
        flash_loan_amount_usd=10.0,
        strategy_id="P3",
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"


def test_live_flash_loan_denied_when_legacy_approval_required(tmp_path: Path) -> None:
    policy_path = _policy_with_flash(tmp_path, enabled=True)
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    data["position_limits"]["flash_loan_live_requires_approval"] = True
    policy_path.write_text(yaml.dump(data), encoding="utf-8")
    kernel = RiskKernel.from_policy_path(policy_path, tmp_path / "state.json")
    trade = TradeRequest(
        trade_id="fl2b",
        venue="uniswap_v3",
        contract="0xba12222222228d8ba445958a685a0a280785497",
        side="buy",
        notional_usd=10.0,
        uses_flash_loan=True,
        flash_loan_source="balancer",
        flash_loan_amount_usd=10.0,
        strategy_id="P3",
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "DENY"
    assert result.code == "FLASH_LOAN_NOT_APPROVED"


def test_live_flash_loan_allowed_after_promotion(tmp_path: Path) -> None:
    policy_path = _policy_with_flash(tmp_path, enabled=True)
    gate = PromotionGate(tmp_path / "safety")
    gate.evaluate(
        PromotionRequest(
            request_id="fl-1",
            category="flash_loan_live",
            subject="flash_loan_global",
            operator_response="YES",
            operator_id="hyperion",
        )
    )
    kernel = RiskKernel.from_policy_path(
        policy_path, tmp_path / "state.json", safety_dir=tmp_path / "safety"
    )
    trade = TradeRequest(
        trade_id="fl3",
        venue="uniswap_v3",
        contract="0xba12222222228d8ba445958a685a0a280785497",
        side="buy",
        notional_usd=10.0,
        confidence=0.75,
        uses_flash_loan=True,
        flash_loan_source="balancer",
        flash_loan_amount_usd=10.0,
        strategy_id="P3",
    )
    result = kernel.validate_trade(trade)
    assert result.decision == "ALLOW"


def test_has_approved_global_subject(tmp_path: Path) -> None:
    gate = PromotionGate(tmp_path)
    assert gate.has_approved("flash_loan_live") is False
    gate.evaluate(
        PromotionRequest(
            request_id="fl-2",
            category="flash_loan_live",
            subject="flash_loan_global",
            operator_response="YES",
            operator_id="hyperion",
        )
    )
    assert gate.has_approved("flash_loan_live") is True
    assert gate.has_approved("flash_loan_live", "P3") is True


def test_flash_loan_sim_runs() -> None:
    result = run_simulation(count=20, seed=1, equity_usd=2500.0)
    assert result["count"] == 20
    assert result["passed"] + result["rejected"] == 20
