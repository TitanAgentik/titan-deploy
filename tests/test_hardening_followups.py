"""Flatten executor, evolution freeze, AUGUR feed, DMS→wind-down tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.augur_feed import FileRegimeFeed, get_regime_feed, write_regime_file
from titan_safety.evolution_freeze import EvolutionFreeze
from titan_safety.flatten_executor import FlattenExecutor
from titan_safety.kernel import RiskKernel, TradeRequest
from titan_safety.policy_loader import load_policy
from titan_safety.promotion_gate import PromotionGate, PromotionRequest
from titan_safety.dead_mans_service import DeadMansDaemon
from titan_safety.dead_mans_switch import DeadMansConfig, DeadMansSwitch
from titan_safety.wind_down import WindDownPhase


def _policy(tmp_path: Path) -> Path:
    data = {
        "version": "2.0",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 10000, "max_notional_usd_per_trade": 100},
        "allowed_venues": ["paper"],
        "allowed_contracts": ["0xabc"],
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_flatten_executor_closes_and_revokes(tmp_path: Path) -> None:
    policy = load_policy(_policy(tmp_path))
    from titan_safety.kernel import RiskKernelState

    kernel = RiskKernel(policy, state=RiskKernelState(tmp_path / "state.json"))
    kernel.apply_fill(
        TradeRequest(
            trade_id="t1",
            venue="paper",
            contract="0xabc",
            side="buy",
            notional_usd=50.0,
        )
    )
    ex = FlattenExecutor(tmp_path)
    out = ex.execute(kernel, operator="test", reason="unit")
    assert out["ok"] is True
    assert kernel.state.flatten_requested is True
    assert kernel.state.keys_revoked is True
    assert len(out["orders"]) == 1
    assert out["revoke"]["status"] == "mock_revoked"
    assert (tmp_path / "SIGNING_HALTED").exists()


def test_evolution_freeze_blocks_promotion(tmp_path: Path) -> None:
    ef = EvolutionFreeze(tmp_path)
    ef.freeze("op", "live")
    gate = PromotionGate(tmp_path)
    # Use a non-stats category that is still freeze-blocked
    decision = gate.evaluate(
        PromotionRequest(
            request_id="r1",
            category="evolution_deploy",
            subject="dgm-h",
            operator_response="YES",
            operator_id="op",
            metadata={},  # stats will also fail — freeze should win first
        )
    )
    assert decision.approved is False
    assert "frozen" in decision.reason.lower()
    ef.unfreeze("op")
    assert not ef.is_frozen()


def test_augur_file_feed(tmp_path: Path) -> None:
    path = tmp_path / "augur_regime.json"
    write_regime_file(path, "bear")
    feed = FileRegimeFeed(path)
    reading = feed.read()
    assert reading.regime == "bear"
    assert reading.source == "file"
    stub = get_regime_feed("stub", regime="neutral")
    assert stub.read().regime == "neutral"


def test_dms_derisk_enters_wind_down(tmp_path: Path) -> None:
    dms = DeadMansSwitch(
        DeadMansConfig(operator_heartbeat_hours=48.0, flatten_after_hours=72.0),
        state_path=tmp_path / "dms.json",
    )
    dms.set_last_heartbeat_hours_ago(50.0)
    daemon = DeadMansDaemon(dms, _policy(tmp_path), tmp_path)
    result = daemon.tick()
    assert result["action"] == "derisk"
    wd = daemon.wind_down.load_state()
    assert wd.phase == WindDownPhase.DERISK.value
    assert wd.safe_mode is True


def test_dms_flatten_triggers_executor(tmp_path: Path) -> None:
    dms = DeadMansSwitch(
        DeadMansConfig(operator_heartbeat_hours=48.0, flatten_after_hours=72.0),
        state_path=tmp_path / "dms_f.json",
    )
    dms.set_last_heartbeat_hours_ago(80.0)
    daemon = DeadMansDaemon(dms, _policy(tmp_path), tmp_path)
    result = daemon.tick()
    assert result["action"] == "flatten"
    assert daemon.ks.is_active()
    wd = daemon.wind_down.load_state()
    assert wd.phase == WindDownPhase.FLATTEN.value
    assert (tmp_path / "SIGNING_HALTED").exists() or "flatten_executor" in result