"""Tests for P22 memecoin paper simulator."""

from __future__ import annotations

from titan_safety.memecoin_sim import run_simulation


def test_sim_produces_pass_and_reject() -> None:
    r = run_simulation(count=50, seed=7, equity_usd=2500.0)
    assert r["pipeline_id"] == "P22"
    assert r["events"] == 50
    assert r["passed"] + r["rejected"] == 50
    assert 0.0 < r["pass_rate"] < 1.0
    assert r["fills"] == r["passed"]


def test_sim_deterministic_seed() -> None:
    a = run_simulation(count=20, seed=99)
    b = run_simulation(count=20, seed=99)
    assert a["passed"] == b["passed"]
    assert a["rejected"] == b["rejected"]
