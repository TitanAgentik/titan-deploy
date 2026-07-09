"""Extend kill switch tests — per-pipeline halt."""

from __future__ import annotations

from pathlib import Path

from titan_safety.kill_switch import KillSwitch


def test_pipeline_halt_independent(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    ks.activate_pipeline("P30", "op", "drill")
    assert ks.is_pipeline_halted("P30")
    assert not ks.is_pipeline_halted("P1")
    assert not ks.is_active()
    ks.deactivate_pipeline("P30")
    assert not ks.is_pipeline_halted("P30")


def test_global_halt_blocks_all_pipelines(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    ks.activate("op", "global", scope="global")
    assert ks.is_pipeline_halted("P30")


def test_portfolio_halt_scope(tmp_path: Path) -> None:
    ks = KillSwitch(tmp_path)
    state = ks.activate_portfolio("op", "portfolio drill", flatten=False)
    assert state.scope == "portfolio"
    assert ks.is_active()
