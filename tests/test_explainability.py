"""Unit tests for explainability layer."""

from __future__ import annotations

from titan_safety.explainability import ExplainabilityLayer


def test_material_trade_explained() -> None:
    layer = ExplainabilityLayer()
    expl = layer.explain(
        trade_id="t1",
        pipeline_id="P30",
        side="buy",
        notional_usd=20.0,
        equity_usd=2500.0,
        confidence=0.85,
        signals=[{"name": "liquidation_cascade", "confidence": 0.85, "source": "ORACLE"}],
        regime="neutral",
    )
    assert expl is not None
    assert expl.equity_pct == 0.8
    assert "P30" in expl.plain_english
    herald = layer.format_herald_payload(expl)
    assert herald["type"] == "trade_explanation"
    assert herald["severity"] == "HIGH"


def test_small_trade_skipped() -> None:
    layer = ExplainabilityLayer()
    expl = layer.explain(
        trade_id="t2",
        pipeline_id="P1",
        side="buy",
        notional_usd=5.0,
        equity_usd=2500.0,
        confidence=0.5,
    )
    assert expl is None


def test_high_confidence_triggers() -> None:
    layer = ExplainabilityLayer()
    expl = layer.explain(
        trade_id="t3",
        pipeline_id="P7",
        side="sell",
        notional_usd=5.0,
        equity_usd=2500.0,
        confidence=0.9,
    )
    assert expl is not None
