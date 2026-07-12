"""Integration: paper → shadow → micro-live go-live path (mock chain / signer)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from titan_safety.flatten_executor import validate_flatten_config_for_live
from titan_safety.kernel import RiskKernel, RiskKernelState, TradeRequest
from titan_safety.policy_loader import load_policy, validate_live_capital_readiness
from titan_safety.recon_aggregator import ReconAggregator
from titan_safety.reconciliation import BelievedPosition, MockPaperAdapter, ReconciliationService
from titan_safety.risk_kernel_service import create_app


def _tier1_policy(tmp_path: Path, profile: str, **extra) -> Path:
    base: dict = {
        "version": "2.2",
        "mode": "enforce",
        "capital_profile": profile,
        "drawdown_notify_only": True,
        "trading_limits": {
            "equity_usd": 10000,
            "max_notional_usd_per_trade": 500,
            "max_aggregate_exposure_usd": 2500,
        },
        "allowed_venues": ["paper"],
        "reconciliation": {"adapter": "mock", "divergence_threshold_usd": 25.0},
        "autonomous_signing": {"enabled": False},
        "allocator": {"advisory_mode": True, "max_active_pipelines": 2},
        "flash_loan_live": {"enabled": False},
        "flatten": {"closer": "mock", "revoker": "mock"},
        "signing": {"signer_module": "titan_safety.signing_service:mock_signer"},
        "tier1_capital_risk": {
            "profiles": {
                "paper": {
                    "allowed_venues": ["paper"],
                    "drawdown_notify_only": True,
                    "autonomous_signing": {"enabled": False},
                    "reconciliation": {"adapter": "mock"},
                    "allocator": {"advisory_mode": True, "max_active_pipelines": 2},
                },
                "live": {
                    "allowed_venues": ["paper", "hyperliquid"],
                    "drawdown_notify_only": False,
                    "autonomous_signing": {"enabled": True},
                    "reconciliation": {
                        "adapter": "live",
                        "recon_module": "titan_safety.signing_service:mock_signer",
                    },
                    "allocator": {"advisory_mode": False, "max_active_pipelines": 2},
                    "flatten": {
                        "closer": "signing_node",
                        "revoker": "titan_safety.flatten_executor:MockKeyRevoker",
                    },
                },
            }
        },
        "tier0_money_path": {
            "enabled": True,
            "venue": "hyperliquid",
            "builtin_aggregator": True,
        },
        "service": {"risk_kernel_port": 0},
    }
    base.update(extra)
    path = tmp_path / f"policy_{profile}.yaml"
    path.write_text(yaml.dump(base), encoding="utf-8")
    return path


def test_step1_paper_profile_trade_allowed(tmp_path: Path) -> None:
    """Step 1: paper only — capital on paper venue, signing off."""
    policy = load_policy(_tier1_policy(tmp_path, "paper"))
    assert policy.raw.get("autonomous_signing", {}).get("enabled") is False
    assert policy.allowed_venues == ["paper"]

    kernel = RiskKernel(policy, RiskKernelState())
    trade = TradeRequest("t-paper", "paper", "0x0", "buy", 50.0, 1.0, strategy_id="P1")
    assert kernel.validate_trade(trade).decision == "ALLOW"

    hl = TradeRequest("t-hl", "hyperliquid", "eth", "buy", 50.0, 1.0, strategy_id="P1")
    assert kernel.validate_trade(hl).decision == "DENY"


def test_step1_paper_recon_empty_without_wallet(tmp_path: Path) -> None:
    agg = ReconAggregator(venues=["paper"], policy_raw={"allowed_venues": ["paper"]})
    assert agg.fetch_positions() == []


def test_step3_shadow_hyperliquid_recon_mock_chain(tmp_path: Path) -> None:
    """Step 3: one venue loop — built-in HL recon with mocked clearinghouse."""
    hl_positions = {
        "assetPositions": [
            {
                "position": {
                    "coin": "ETH",
                    "szi": "0.5",
                    "entryPx": "2000",
                }
            }
        ]
    }

    class _FakeResp:
        def read(self) -> bytes:
            return json.dumps(hl_positions).encode()

        def __enter__(self) -> "_FakeResp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with patch.dict(os.environ, {"HYPERLIQUID_WALLET_ADDRESS": "0xabc"}):
        with patch("urllib.request.urlopen", return_value=_FakeResp()):
            positions = ReconAggregator(
                venues=["hyperliquid"],
                policy_raw={"allowed_venues": ["hyperliquid", "paper"]},
            ).fetch_positions()

    assert len(positions) == 1
    assert positions[0].venue == "hyperliquid"
    assert positions[0].notional_usd == 1000.0


def test_step3_full_paper_venue_loop_recon_simulate(tmp_path: Path) -> None:
    """Recon + simulate on paper venue before any live broadcast."""
    policy = load_policy(_tier1_policy(tmp_path, "paper"))
    adapter = MockPaperAdapter([BelievedPosition("paper", "0x0", 0.0)])
    svc = ReconciliationService(policy, adapter)
    believed = [BelievedPosition("paper", "0x0", 0.0)]
    pending = BelievedPosition("paper", "0x0", 25.0, side="long")
    gate = svc.pre_trade_gate(believed, pending)
    assert gate.decision == "ALLOW"

    kernel = RiskKernel(policy, RiskKernelState())
    trade = TradeRequest("loop-1", "paper", "0x0", "buy", 25.0, 1.0, strategy_id="P1")
    assert kernel.validate_trade(trade).decision == "ALLOW"


def test_step5_micro_live_caps_from_template() -> None:
    """Step 5: micro-live phase caps exist in template policy."""
    tpl = Path(__file__).resolve().parents[1] / "templates" / "risk_kernel" / "policy.yaml"
    raw = yaml.safe_load(tpl.read_text(encoding="utf-8"))
    phases = (raw.get("tier2_promotion_quality") or {}).get("micro_live_caps") or {}
    assert phases.get("default_phase") == "micro_live_conservative"
    assert "micro_live_conservative" in (phases.get("phases") or {})


def test_live_startup_refused_without_signing_ready(tmp_path: Path) -> None:
    policy = load_policy(
        _tier1_policy(
            tmp_path,
            "live",
            flatten={
                "closer": "signing_node",
                "revoker": "titan_safety.flatten_executor:MockKeyRevoker",
            },
            signing={"signer_module": "titan_safety.signing_service:mock_signer"},
        )
    )
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="TITAN_LIVE_SIGNING_READY"):
            validate_live_capital_readiness(policy)


def test_live_startup_refused_when_signer_raises(tmp_path: Path) -> None:
    policy = load_policy(
        _tier1_policy(
            tmp_path,
            "live",
            flatten={
                "closer": "signing_node",
                "revoker": "titan_safety.flatten_executor:MockKeyRevoker",
            },
            signing={"signer_module": "titan_safety.adapters.live_bundle:live_signer"},
        )
    )
    with patch.dict(os.environ, {"TITAN_LIVE_SIGNING_READY": "1"}, clear=False):
        with pytest.raises(ValueError, match="signer.*not ready"):
            validate_live_capital_readiness(policy)


def test_live_startup_ok_with_mock_signer_when_armed(tmp_path: Path) -> None:
    policy = load_policy(
        _tier1_policy(
            tmp_path,
            "live",
            flatten={
                "closer": "signing_node",
                "revoker": "titan_safety.flatten_executor:MockKeyRevoker",
            },
            signing={"signer_module": "titan_safety.signing_service:mock_signer"},
        )
    )
    with patch.dict(os.environ, {"TITAN_LIVE_SIGNING_READY": "1"}, clear=False):
        validate_live_capital_readiness(policy)  # mock_signer returns without raise


def test_paper_kernel_service_starts(tmp_path: Path) -> None:
    policy_path = _tier1_policy(tmp_path, "paper")
    server, kernel = create_app(policy_path, tmp_path / "state.json", tmp_path)
    assert server is not None
    trade = TradeRequest("svc-1", "paper", "0x0", "buy", 10.0, 1.0, strategy_id="P1")
    assert kernel.validate_trade(trade).decision == "ALLOW"


def test_live_flatten_still_requires_non_mock_closer(tmp_path: Path) -> None:
    path = _tier1_policy(tmp_path, "live")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    (raw.get("tier1_capital_risk", {}).get("profiles", {}).get("live") or {}).pop(
        "flatten", None
    )
    path.write_text(yaml.dump(raw), encoding="utf-8")
    policy = load_policy(path)
    with pytest.raises(ValueError, match="mock closer banned"):
        validate_flatten_config_for_live(policy)
