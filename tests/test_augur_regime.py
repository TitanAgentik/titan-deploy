"""Augur regime stub tests."""

from __future__ import annotations

from titan_safety.portfolio_risk import PortfolioRiskEngine


def test_augur_regime_mapping() -> None:
    engine = PortfolioRiskEngine()
    engine.set_regime_from_augur("bear")
    assert engine.regime == "risk_off"
    engine.set_regime_from_augur("bull")
    assert engine.regime == "risk_on"
    engine.set_regime_from_augur("neutral")
    assert engine.regime == "neutral"
