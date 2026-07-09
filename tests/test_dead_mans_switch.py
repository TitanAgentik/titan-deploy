"""Unit tests for dead-man's switch."""

from __future__ import annotations

from pathlib import Path

from titan_safety.dead_mans_switch import DeadMansConfig, DeadMansSwitch


def test_heartbeat_resets(tmp_path: Path) -> None:
    state_path = tmp_path / "dms.json"
    dms = DeadMansSwitch(DeadMansConfig(), state_path)
    dms.set_last_heartbeat_hours_ago(50)
    ev = dms.evaluate()
    assert ev["action"] == "derisk"
    dms.heartbeat("op")
    ev2 = dms.evaluate()
    assert ev2["action"] == "none"


def test_flatten_at_72h(tmp_path: Path) -> None:
    state_path = tmp_path / "dms.json"
    dms = DeadMansSwitch(
        DeadMansConfig(operator_heartbeat_hours=48, flatten_after_hours=72),
        state_path,
    )
    dms.set_last_heartbeat_hours_ago(73)
    ev = dms.evaluate()
    assert ev["action"] == "flatten"
    assert ev["promotion_allowed"] is False


def test_never_auto_promote(tmp_path: Path) -> None:
    dms = DeadMansSwitch(DeadMansConfig(never_auto_promote=True), tmp_path / "d.json")
    ev = dms.evaluate()
    assert ev["never_auto_promote"] is True
    assert ev["promotion_allowed"] is False
