"""Unit tests for the TCA / execution-quality engine."""

from __future__ import annotations

from titan_safety.tca import Fill, TCAConfig, TCAEngine


def _profitable_fill(pid: str = "P29", notional: float = 1000.0) -> Fill:
    # gross 20 bps, cost ~2 bps => healthy net
    return Fill(
        pipeline_id=pid,
        venue="uniswap_v3",
        side="buy",
        notional_usd=notional,
        expected_price=100.0,
        realized_price=100.05,
        gross_pnl_usd=2.0,
        gas_usd=0.1,
        tip_usd=0.1,
    )


def test_net_bps_after_costs() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5))
    for _ in range(10):
        engine.ingest(_profitable_fill())
    card = engine.scorecard("P29")
    assert card.fill_count == 10
    assert round(card.gross_bps, 1) == 20.0
    assert round(card.cost_bps, 1) == 2.0
    assert round(card.net_bps, 1) == 18.0
    assert card.verdict == "HEALTHY"


def test_revert_drag_and_fill_rate() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, min_fill_rate=0.9))
    for _ in range(8):
        engine.ingest(_profitable_fill())
    for _ in range(4):
        engine.ingest(
            Fill(pipeline_id="P29", notional_usd=1000.0, reverted=True, gas_usd=0.5)
        )
    card = engine.scorecard("P29")
    assert card.revert_count == 4
    assert card.fill_rate < 0.9
    # reverted gas still charged against the lane
    assert card.net_pnl_usd < 8 * 1.8
    assert card.verdict == "BLEEDING"


def test_tip_efficiency_flags_bleeding() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5, max_tip_efficiency=0.4))
    for _ in range(10):
        engine.ingest(
            Fill(
                pipeline_id="P29",
                notional_usd=1000.0,
                expected_price=100.0,
                realized_price=100.0,
                gross_pnl_usd=2.0,
                tip_usd=1.5,  # 75% of gross paid as tips
            )
        )
    card = engine.scorecard("P29")
    assert card.tip_efficiency > 0.4
    assert card.verdict == "BLEEDING"


def test_insufficient_data_verdict() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=30))
    engine.ingest(_profitable_fill())
    card = engine.scorecard("P29")
    assert card.verdict == "INSUFFICIENT_DATA"


def test_capacity_pressure_detected() -> None:
    engine = TCAEngine(TCAConfig(min_fills_for_verdict=5))
    # larger fills get worse realized price (more slippage)
    for i in range(20):
        notional = 100.0 * (i + 1)
        slip = 0.01 * (i + 1)
        engine.ingest(
            Fill(
                pipeline_id="P34",
                notional_usd=notional,
                side="buy",
                expected_price=100.0,
                realized_price=100.0 + slip,
                gross_pnl_usd=notional * 0.001,
            )
        )
    card = engine.scorecard("P34")
    assert card.capacity_pressure > 0.5
