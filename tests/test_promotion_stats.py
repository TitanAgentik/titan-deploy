"""Unit tests for statistical promotion gates."""

from __future__ import annotations

from titan_safety.promotion_stats import (
    StatsGateConfig,
    StrategyStats,
    StrategyStatsGate,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
)


def test_psr_higher_for_stronger_edge() -> None:
    weak = [0.001, -0.02, 0.03, -0.025, 0.02, -0.018] * 30
    strong = [0.02, 0.015, 0.03, 0.01, 0.025, 0.018] * 30
    assert probabilistic_sharpe_ratio(strong) > probabilistic_sharpe_ratio(weak)
    assert probabilistic_sharpe_ratio(strong) > 0.9


def test_expected_max_sharpe_increases_with_trials() -> None:
    assert expected_max_sharpe(100, 0.01) > expected_max_sharpe(10, 0.01)
    assert expected_max_sharpe(1, 0.01) == 0.0


# Realistically noisy per-trade returns: small positive mean, large dispersion
# (per-observation Sharpe ~0.07, as real strategies exhibit — not a clean sine).
NOISY_RETURNS = [0.02, -0.018, 0.021, -0.017, 0.019, -0.02, 0.022, -0.016] * 30


def test_deflation_penalizes_many_trials() -> None:
    dsr_few = deflated_sharpe_ratio(NOISY_RETURNS, trials=2, sr_variance=0.01)
    dsr_many = deflated_sharpe_ratio(NOISY_RETURNS, trials=5000, sr_variance=0.01)
    assert dsr_few > dsr_many
    assert dsr_many < 0.5


def test_gate_passes_strong_strategy() -> None:
    returns = [0.02, -0.004, 0.03, 0.012, 0.025, -0.003, 0.028, 0.016] * 40
    stats = StrategyStats(
        strategy_id="P5",
        returns=returns,
        trials=5,
        sr_variance=0.01,
        num_trades=500,
        gross_bps=12.0,
        cost_bps=3.0,
        backtest_sharpe=1.8,
        shadow_sharpe=1.7,
        walk_forward_folds_passed=5,
        purged_cv_passed=True,
        fat_slippage_bps=8.0,
        capacity_curve_ok=True,
        shadow_days=7,
        shadow_gas_tip_simulated=True,
    )
    result = StrategyStatsGate().evaluate(stats)
    assert result.passed, result.reasons


def test_gate_blocks_thin_sample() -> None:
    stats = StrategyStats(
        strategy_id="thin",
        returns=[0.02, 0.01, 0.03] * 5,
        trials=1,
        num_trades=15,
        gross_bps=12.0,
        cost_bps=3.0,
        backtest_sharpe=1.5,
        shadow_sharpe=1.5,
    )
    result = StrategyStatsGate().evaluate(stats)
    assert not result.passed
    assert any("num_trades" in r for r in result.reasons)


def test_gate_blocks_unmodeled_costs() -> None:
    returns = [0.02, -0.004, 0.03, 0.012, 0.025, -0.003] * 50
    stats = StrategyStats(
        strategy_id="nocost",
        returns=returns,
        trials=2,
        sr_variance=0.01,
        num_trades=300,
        gross_bps=12.0,
        cost_bps=0.0,
        backtest_sharpe=1.8,
        shadow_sharpe=1.75,
    )
    result = StrategyStatsGate().evaluate(stats)
    assert not result.passed
    assert any("costs not modeled" in r for r in result.reasons)


def test_gate_blocks_shadow_divergence() -> None:
    returns = [0.02, -0.004, 0.03, 0.012, 0.025, -0.003] * 50
    stats = StrategyStats(
        strategy_id="diverge",
        returns=returns,
        trials=2,
        sr_variance=0.01,
        num_trades=300,
        gross_bps=12.0,
        cost_bps=3.0,
        backtest_sharpe=2.0,
        shadow_sharpe=0.5,  # 75% divergence
    )
    result = StrategyStatsGate().evaluate(stats)
    assert not result.passed
    assert any("divergence" in r for r in result.reasons)


def test_gate_blocks_overfit_high_trials() -> None:
    stats = StrategyStats(
        strategy_id="overfit",
        returns=NOISY_RETURNS,
        trials=100000,
        sr_variance=0.05,
        num_trades=300,
        gross_bps=12.0,
        cost_bps=3.0,
        backtest_sharpe=1.5,
        shadow_sharpe=1.4,
    )
    result = StrategyStatsGate().evaluate(stats)
    assert not result.passed
    assert any("deflated_sharpe" in r for r in result.reasons)


def test_config_from_raw() -> None:
    cfg = StatsGateConfig.from_raw({"promotion_stats": {"min_trades": 42, "min_psr": 0.8}})
    assert cfg.min_trades == 42
    assert cfg.min_psr == 0.8
