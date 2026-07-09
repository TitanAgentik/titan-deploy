"""Unit tests for wind-down / safe mode."""

from __future__ import annotations

from pathlib import Path

from titan_safety.wind_down import WindDownController, WindDownPhase


def test_safe_mode_flag(tmp_path: Path) -> None:
    wd = WindDownController(tmp_path)
    assert not wd.is_safe_mode()
    wd.enter_safe_mode("op", "test")
    assert wd.is_safe_mode()
    health = wd.health()
    assert health["phase"] == WindDownPhase.SAFE_MODE.value


def test_gradual_derisk_steps(tmp_path: Path) -> None:
    wd = WindDownController(tmp_path)
    wd.start_derisk("op", "test", current_pct=100.0)
    result = wd.step(current_exposure_pct=100.0)
    assert result["action"] == "reduce"
    assert result["new_exposure_pct"] < 100.0


def test_resume_clears_safe_mode(tmp_path: Path) -> None:
    wd = WindDownController(tmp_path)
    wd.enter_safe_mode("op", "test")
    wd.resume_normal("op")
    assert not wd.is_safe_mode()
