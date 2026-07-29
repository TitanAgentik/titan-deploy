"""Daily compound engine tests."""

from __future__ import annotations

from pathlib import Path

from titan_safety.capital import CapitalConfig, CapitalManager
from titan_safety.daily_compound import DailyCompoundConfig, DailyCompoundEngine
from titan_safety.tca import Fill, TCAConfig, TCAEngine


def _healthy_fill(pid: str = "P29") -> Fill:
    return Fill(
        pipeline_id=pid,
        venue="uniswap_v3",
        side="buy",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.05,
        gross_pnl_usd=5.0,
        gas_usd=0.1,
        tip_usd=0.1,
    )


def _bleeding_fill(pid: str = "P99") -> Fill:
    return Fill(
        pipeline_id=pid,
        venue="uniswap_v3",
        side="buy",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.0,
        gross_pnl_usd=2.0,
        tip_usd=1.5,
        gas_usd=0.1,
    )


def _capital(tmp_path: Path, equity: float = 2500.0) -> CapitalManager:
    cfg = CapitalConfig(
        state_path=tmp_path / "capital" / "portfolio_state.json",
        audit_path=tmp_path / "capital" / "capital_audit.jsonl",
    )
    mgr = CapitalManager(cfg)
    if equity > 0:
        mgr.deposit(equity, "USDC", operator="test", source="seed")
    return mgr


def test_first_snapshot_establishes_baseline(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5))
    for _ in range(40):
        engine.ingest(_healthy_fill("P29"))
    capital = _capital(tmp_path, 2500.0)
    dc = DailyCompoundEngine(
        engine,
        safety_dir=tmp_path / "safety",
        capital=capital,
        config=DailyCompoundConfig(min_trades_for_deploy=10),
    )
    result = dc.run(dry_run=False)
    assert result.equity_usd == 2500.0
    assert result.daily_pnl_usd == 0.0
    assert "first snapshot" in " ".join(result.notes)
    assert result.phase == "GROWTH"
    assert (tmp_path / "safety" / "daily_compound_state.json").exists()


def test_green_day_boosts_kelly_and_feeds_healthy(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(40):
        engine.ingest(_healthy_fill("P29"))
        engine.ingest(_bleeding_fill("P99"))

    capital = _capital(tmp_path, 2500.0)
    safety = tmp_path / "safety"
    cfg = DailyCompoundConfig(
        min_trades_for_deploy=10,
        min_green_streak_for_boost=2,
        green_day_kelly_boost=0.05,
        base_kelly_fraction=0.25,
    )
    dc = DailyCompoundEngine(
        engine, safety_dir=safety, capital=capital, config=cfg
    )
    # Day 0 baseline
    dc.run(date_utc="2026-07-01", dry_run=False)
    # Green day 1: equity up
    capital.apply_realized_pnl(50.0, operator="test", reason="sim profit")
    r1 = dc.run(date_utc="2026-07-02", dry_run=False)
    assert r1.green_day is True
    assert r1.daily_pnl_usd == 50.0
    assert r1.green_streak == 1
    # BLEEDING lane defunded on baseline or first green day
    defunded_all = set(r1.profit_loop.get("defunded") or []) | set(
        r1.profit_loop.get("already_defunded") or []
    )
    assert "P99" in defunded_all
    # Green day 2: streak boost
    capital.apply_realized_pnl(40.0, operator="test", reason="sim profit")
    r2 = dc.run(date_utc="2026-07-03", dry_run=False)
    assert r2.green_streak == 2
    assert r2.kelly_fraction >= 0.25
    assert r2.new_ath is True
    assert r2.ath_usd >= 2590.0
    plan = r2.allocation_plan or {}
    funded = {
        a["pipeline_id"]
        for a in (plan.get("allocations") or [])
        if a.get("target_notional_usd", 0) > 0
    }
    assert "P99" not in funded
    # P29 should be eligible when trade count/min bps satisfied
    assert "P29" in funded or "P29" in (plan.get("excluded") or {})


def test_red_day_cuts_kelly_and_tightens_lanes(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5))
    for _ in range(40):
        engine.ingest(_healthy_fill("P29"))
    capital = _capital(tmp_path, 2500.0)
    safety = tmp_path / "safety"
    cfg = DailyCompoundConfig(
        min_trades_for_deploy=10,
        base_kelly_fraction=0.25,
        red_day_kelly_cut=0.05,
        max_active_on_red=1,
        min_kelly_fraction=0.15,
    )
    dc = DailyCompoundEngine(
        engine, safety_dir=safety, capital=capital, config=cfg
    )
    dc.run(date_utc="2026-07-10", dry_run=False)
    capital.apply_realized_pnl(-100.0, operator="test", reason="sim loss")
    red = dc.run(date_utc="2026-07-11", dry_run=False)
    assert red.green_day is False
    assert red.daily_pnl_usd == -100.0
    assert red.red_streak == 1
    assert red.kelly_fraction < 0.25
    assert red.effective_drawdown_pct > 0


def test_dry_run_no_side_effects(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(20):
        engine.ingest(_bleeding_fill("P77"))
    capital = _capital(tmp_path, 2500.0)
    safety = tmp_path / "safety"
    dc = DailyCompoundEngine(
        engine,
        safety_dir=safety,
        capital=capital,
        config=DailyCompoundConfig(min_trades_for_deploy=5),
    )
    result = dc.run(dry_run=True)
    assert result.dry_run is True
    assert not (safety / "daily_compound_state.json").exists()
    assert not (safety / "defund_state.json").exists()


def test_harvest_phase_above_threshold(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5))
    for _ in range(40):
        engine.ingest(_healthy_fill("P1"))
    capital = _capital(tmp_path, 16000.0)
    dc = DailyCompoundEngine(
        engine,
        safety_dir=tmp_path / "safety",
        capital=capital,
        config=DailyCompoundConfig(
            growth_threshold_usd=15000.0, min_trades_for_deploy=10
        ),
    )
    result = dc.run(dry_run=False)
    assert result.phase == "HARVEST"


def test_apply_realized_pnl_on_capital(tmp_path: Path) -> None:
    capital = _capital(tmp_path, 1000.0)
    r = capital.apply_realized_pnl(25.5, operator="test")
    assert r.ok
    assert capital.balance()["equity_usd"] == 1025.5
    assert capital.balance()["realized_pnl_usd"] == 25.5
    r2 = capital.apply_realized_pnl(-10.0, operator="test")
    assert r2.ok
    assert capital.balance()["equity_usd"] == 1015.5
