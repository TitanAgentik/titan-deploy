"""Unit tests for portfolio risk engine."""

from __future__ import annotations

import random

from titan_safety.portfolio_risk import (
    PipelineExposure,
    PortfolioRiskConfig,
    PortfolioRiskEngine,
    PortfolioSnapshot,
)


def _sample_returns(n: int = 30, mean: float = 0.001) -> list[float]:
    random.seed(42)
    return [mean + random.gauss(0, 0.02) for _ in range(n)]


def test_allow_small_trade() -> None:
    engine = PortfolioRiskEngine()
    snapshot = PortfolioSnapshot(
        equity_usd=2500.0,
        pipelines=[PipelineExposure("P1", 200.0, _sample_returns())],
    )
    result = engine.simulate_pre_trade(snapshot, "P30", 50.0)
    assert result.decision == "ALLOW"


def test_deny_correlation_cluster() -> None:
    cfg = PortfolioRiskConfig(max_correlated_cluster_pct=20.0)
    engine = PortfolioRiskEngine(cfg)
    snapshot = PortfolioSnapshot(
        equity_usd=2500.0,
        pipelines=[
            PipelineExposure("P1", 400.0, _sample_returns()),
            PipelineExposure("P3", 200.0, _sample_returns()),
        ],
    )
    result = engine.simulate_pre_trade(snapshot, "P7", 100.0)
    assert result.decision == "DENY"
    assert result.code == "CORRELATION_CAP"


def test_regime_risk_off_limits() -> None:
    engine = PortfolioRiskEngine()
    engine.set_regime_from_augur("risk_off")
    snapshot = PortfolioSnapshot(
        equity_usd=2500.0,
        pipelines=[PipelineExposure("P99", 1300.0, _sample_returns())],
    )
    result = engine.simulate_pre_trade(snapshot, "P99", 50.0)
    assert result.decision == "DENY"
    assert result.code == "REGIME_EXPOSURE"


def test_var_cvar_computed() -> None:
    engine = PortfolioRiskEngine()
    snapshot = PortfolioSnapshot(
        equity_usd=2500.0,
        pipelines=[PipelineExposure("P1", 500.0, _sample_returns())],
    )
    metrics = engine.compute_var_cvar(snapshot)
    assert metrics["var_95_usd"] >= 0
    assert metrics["cvar_95_usd"] >= metrics["var_95_usd"]
