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


def test_sim_rejects_majority_rugs() -> None:
    r = run_simulation(count=80, seed=3, equity_usd=5000.0)
    assert r["pipeline_id"] == "P22"
    assert r["pass_rate"] < 0.95  # six-gate rejects most synthetic rugs
    assert "scorecard" in r
    if r["fills"] > 0:
        assert isinstance(r["scorecard"], dict)
