"""Statistical promotion gates — kill overfit strategies before they get capital.

The old lifecycle promoted on "Sharpe >= 0, return >= 0, 20 trades" and
auto-promoted on operator timeout. That systematically funds noise. This module
adds the statistics real desks use to separate edge from luck when many
strategies are mined against limited data:

  * Probabilistic Sharpe Ratio (PSR) — confidence the true SR exceeds a benchmark.
  * Deflated Sharpe Ratio (DSR) — PSR with the benchmark raised to the expected
    maximum SR under N independent trials (Bailey & Lopez de Prado, 2014),
    correcting for multiple-testing / selection bias.
  * Cost realism — costs must be modeled and net expectancy positive.
  * Shadow divergence — live/shadow Sharpe must track the backtest.
  * Minimum trade count — hundreds, not twenty.

Pure-stdlib, deterministic.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

_EULER_MASCHERONI = 0.5772156649015329


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse normal CDF (Acklam's rational approximation)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _moments(returns: list[float]) -> tuple[float, float, float, float]:
    """Return (mean, std, skew, kurtosis) — kurtosis is non-excess (normal=3)."""
    n = len(returns)
    if n < 2:
        return 0.0, 0.0, 0.0, 3.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / n
    std = math.sqrt(var)
    if std == 0:
        return mean, 0.0, 0.0, 3.0
    skew = sum(((r - mean) / std) ** 3 for r in returns) / n
    kurt = sum(((r - mean) / std) ** 4 for r in returns) / n
    return mean, std, skew, kurt


def sharpe_ratio(returns: list[float]) -> float:
    """Per-observation (non-annualized) Sharpe."""
    mean, std, _, _ = _moments(returns)
    return mean / std if std > 0 else 0.0


def probabilistic_sharpe_ratio(returns: list[float], benchmark_sr: float = 0.0) -> float:
    """P(true SR > benchmark_sr) given observed higher-moment-adjusted SR."""
    n = len(returns)
    if n < 3:
        return 0.0
    _, _, skew, kurt = _moments(returns)
    sr = sharpe_ratio(returns)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr))
    z = (sr - benchmark_sr) * math.sqrt(n - 1) / denom
    return _norm_cdf(z)


def expected_max_sharpe(trials: int, sr_variance: float) -> float:
    """Expected maximum SR across `trials` independent strategies under the null.

    sr_variance is the variance of the SR estimates across trials.
    """
    if trials < 2 or sr_variance <= 0:
        return 0.0
    inv1 = _norm_ppf(1.0 - 1.0 / trials)
    inv2 = _norm_ppf(1.0 - 1.0 / (trials * math.e))
    return math.sqrt(sr_variance) * (
        (1.0 - _EULER_MASCHERONI) * inv1 + _EULER_MASCHERONI * inv2
    )


def deflated_sharpe_ratio(
    returns: list[float], trials: int, sr_variance: float | None = None
) -> float:
    """DSR = PSR with benchmark = expected max SR under `trials` (selection bias)."""
    if not returns:
        return 0.0
    if sr_variance is None:
        # Heuristic when the trial SR distribution isn't supplied: assume trial
        # SRs are dispersed on the order of the observed per-obs SR variance.
        _, std, _, _ = _moments(returns)
        sr_variance = 1.0 / max(1, len(returns))
    benchmark = expected_max_sharpe(trials, sr_variance)
    return probabilistic_sharpe_ratio(returns, benchmark_sr=benchmark)


@dataclass
class StrategyStats:
    strategy_id: str
    returns: list[float] = field(default_factory=list)  # per-trade net returns (fraction)
    trials: int = 1  # number of configs/strategies mined to find this one
    sr_variance: float | None = None
    num_trades: int = 0
    gross_bps: float = 0.0
    cost_bps: float = 0.0  # modeled gas+tip+slippage; must be > 0 to prove realism
    backtest_sharpe: float = 0.0
    shadow_sharpe: float = 0.0  # live/shadow period Sharpe
    # Tier 2 promotion evidence (walk-forward / purged CV / shadow / capacity)
    walk_forward_folds_passed: int = 0
    walk_forward_folds_required: int = 5
    purged_cv_passed: bool = False
    fat_slippage_bps: float = 0.0  # fat-tail slippage component in cost model
    capacity_curve_ok: bool = False  # edge holds across size curve
    shadow_days: int = 0
    shadow_gas_tip_simulated: bool = False
    shadow_divergence_pct: float | None = None  # explicit override; else computed from SR


@dataclass
class StatsGateConfig:
    min_trades: int = 200
    min_deflated_sharpe: float = 0.90  # DSR is a probability in [0,1]
    min_psr: float = 0.90
    max_shadow_divergence_pct: float = 15.0
    min_net_bps: float = 1.0
    require_cost_model: bool = True
    require_walk_forward: bool = True
    min_walk_forward_folds: int = 5
    require_purged_cv: bool = True
    min_fat_slippage_bps: float = 5.0
    require_capacity_curve: bool = True
    min_shadow_days: int = 3
    require_shadow_gas_tip_sim: bool = True

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> StatsGateConfig:
        s = raw.get("promotion_stats", {}) if raw else {}
        d = cls()
        return cls(
            min_trades=int(s.get("min_trades", d.min_trades)),
            min_deflated_sharpe=float(s.get("min_deflated_sharpe", d.min_deflated_sharpe)),
            min_psr=float(s.get("min_psr", d.min_psr)),
            max_shadow_divergence_pct=float(
                s.get("max_shadow_divergence_pct", d.max_shadow_divergence_pct)
            ),
            min_net_bps=float(s.get("min_net_bps", d.min_net_bps)),
            require_cost_model=bool(s.get("require_cost_model", d.require_cost_model)),
            require_walk_forward=bool(s.get("require_walk_forward", d.require_walk_forward)),
            min_walk_forward_folds=int(
                s.get("min_walk_forward_folds", d.min_walk_forward_folds)
            ),
            require_purged_cv=bool(s.get("require_purged_cv", d.require_purged_cv)),
            min_fat_slippage_bps=float(
                s.get("min_fat_slippage_bps", d.min_fat_slippage_bps)
            ),
            require_capacity_curve=bool(
                s.get("require_capacity_curve", d.require_capacity_curve)
            ),
            min_shadow_days=int(s.get("min_shadow_days", d.min_shadow_days)),
            require_shadow_gas_tip_sim=bool(
                s.get("require_shadow_gas_tip_sim", d.require_shadow_gas_tip_sim)
            ),
        )


@dataclass
class StatsGateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StrategyStatsGate:
    """Evaluates whether a strategy's evidence is strong enough for live capital."""

    def __init__(self, config: StatsGateConfig | None = None) -> None:
        self.config = config or StatsGateConfig()

    def evaluate(self, stats: StrategyStats) -> StatsGateResult:
        cfg = self.config
        reasons: list[str] = []

        psr = probabilistic_sharpe_ratio(stats.returns) if stats.returns else 0.0
        dsr = (
            deflated_sharpe_ratio(stats.returns, max(1, stats.trials), stats.sr_variance)
            if stats.returns
            else 0.0
        )
        net_bps = stats.gross_bps - stats.cost_bps
        divergence = (
            stats.shadow_divergence_pct
            if stats.shadow_divergence_pct is not None
            else self._divergence_pct(stats.backtest_sharpe, stats.shadow_sharpe)
        )

        metrics = {
            "psr": round(psr, 4),
            "deflated_sharpe": round(dsr, 4),
            "net_bps": round(net_bps, 4),
            "shadow_divergence_pct": round(divergence, 4),
            "num_trades": float(stats.num_trades),
            "trials": float(stats.trials),
            "walk_forward_folds_passed": float(stats.walk_forward_folds_passed),
            "shadow_days": float(stats.shadow_days),
            "fat_slippage_bps": float(stats.fat_slippage_bps),
        }

        if stats.num_trades < cfg.min_trades:
            reasons.append(f"num_trades {stats.num_trades} < min {cfg.min_trades}")
        if dsr < cfg.min_deflated_sharpe:
            reasons.append(
                f"deflated_sharpe {dsr:.3f} < min {cfg.min_deflated_sharpe} "
                f"(overfit risk across {stats.trials} trials)"
            )
        if psr < cfg.min_psr:
            reasons.append(f"PSR {psr:.3f} < min {cfg.min_psr}")
        if cfg.require_cost_model and stats.cost_bps <= 0:
            reasons.append("costs not modeled (cost_bps <= 0) — unrealistic backtest")
        if net_bps < cfg.min_net_bps:
            reasons.append(f"net_bps {net_bps:.2f} < min {cfg.min_net_bps}")
        if divergence > cfg.max_shadow_divergence_pct:
            reasons.append(
                f"shadow divergence {divergence:.1f}% > max {cfg.max_shadow_divergence_pct}%"
            )
        if cfg.require_walk_forward and stats.walk_forward_folds_passed < cfg.min_walk_forward_folds:
            reasons.append(
                f"walk-forward {stats.walk_forward_folds_passed}/{cfg.min_walk_forward_folds} folds passed"
            )
        if cfg.require_purged_cv and not stats.purged_cv_passed:
            reasons.append("purged cross-validation not passed")
        if cfg.min_fat_slippage_bps > 0 and stats.fat_slippage_bps < cfg.min_fat_slippage_bps:
            reasons.append(
                f"fat_slippage_bps {stats.fat_slippage_bps:.1f} < min {cfg.min_fat_slippage_bps} "
                "(cost model must include fat-tail slippage)"
            )
        if cfg.require_capacity_curve and not stats.capacity_curve_ok:
            reasons.append("capacity curve not validated (edge must hold across sizes)")
        if cfg.min_shadow_days > 0 and stats.shadow_days < cfg.min_shadow_days:
            reasons.append(
                f"shadow_days {stats.shadow_days} < min {cfg.min_shadow_days} "
                "(live market + gas/tip sim required)"
            )
        if cfg.require_shadow_gas_tip_sim and not stats.shadow_gas_tip_simulated:
            reasons.append("shadow period missing live gas/tip simulation")

        return StatsGateResult(passed=not reasons, reasons=reasons, metrics=metrics)

    @staticmethod
    def _divergence_pct(backtest_sr: float, shadow_sr: float) -> float:
        if backtest_sr == 0:
            return 0.0 if shadow_sr == 0 else 100.0
        return abs(backtest_sr - shadow_sr) / abs(backtest_sr) * 100.0
