"""Unit tests for kill switch."""

from __future__ import annotations

from pathlib import Path

from titan_safety.kill_switch import KillSwitch


def test_activate_and_deactivate(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    assert not ks.is_active()
    ks.activate("op", "test halt")
    assert ks.is_active()
    state = ks.load_state()
    assert state.flatten_requested is True
    ks.deactivate("op")
    assert not ks.is_active()


def test_signed_command(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    signed = ks.sign_command("HALT", "operator")
    ok, cmd = ks.verify_signed_command(signed)
    assert ok is True
    assert cmd == "HALT"


def test_invalid_signature(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    ks.ensure_secret()
    ok, msg = ks.verify_signed_command("HALT|operator|0|bad")
    assert ok is False
