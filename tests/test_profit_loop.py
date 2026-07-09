"""TCA → allocator profit loop tests."""

from __future__ import annotations

from pathlib import Path

from titan_safety.profit_loop import ProfitLoop
from titan_safety.tca import Fill, TCAConfig, TCAEngine


def _bleeding_fill(pid: str = "P99") -> Fill:
    return Fill(
        pipeline_id=pid,
        venue="uniswap_v3",
        side="buy",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.0,
        gross_pnl_usd=2.0,
        tip_usd=1.5,  # tip-heavy → BLEEDING under default tip_efficiency cap
        gas_usd=0.1,
    )


def _healthy_fill(pid: str = "P29") -> Fill:
    return Fill(
        pipeline_id=pid,
        venue="uniswap_v3",
        side="buy",
        notional_usd=1000.0,
        expected_price=100.0,
        realized_price=100.05,
        gross_pnl_usd=2.0,
        gas_usd=0.1,
        tip_usd=0.1,
    )


def test_auto_defund_bleeding(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(10):
        engine.ingest(_bleeding_fill("P99"))
        engine.ingest(_healthy_fill("P29"))

    loop = ProfitLoop(engine, safety_dir=tmp_path)
    result = loop.run(equity_usd=100_000.0)
    assert "P99" in result.defunded
    assert loop.is_defunded("P99")
    assert loop.ks.is_pipeline_halted("P99")
    # Defunded lane forced to zero in plan
    for alloc in result.plan.allocations if result.plan else []:
        if alloc.pipeline_id == "P99":
            assert alloc.target_notional_usd == 0.0


def test_refund_requires_explicit_call(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(10):
        engine.ingest(_bleeding_fill("P99"))
    loop = ProfitLoop(engine, safety_dir=tmp_path)
    loop.run(equity_usd=50_000.0)
    assert loop.is_defunded("P99")
    # Second run: already defunded, not newly
    result2 = loop.run(equity_usd=50_000.0)
    assert "P99" in result2.already_defunded
    assert "P99" not in result2.defunded
    # Human refund
    assert loop.refund("P99", operator="human", reason="YES") is True
    assert not loop.is_defunded("P99")
    assert not loop.ks.is_pipeline_halted("P99")


def test_defund_persists_across_instances(tmp_path: Path) -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(10):
        engine.ingest(_bleeding_fill("P77"))
    ProfitLoop(engine, safety_dir=tmp_path).run(equity_usd=10_000.0)
    loop2 = ProfitLoop(TCAEngine(), safety_dir=tmp_path)
    assert loop2.is_defunded("P77")
