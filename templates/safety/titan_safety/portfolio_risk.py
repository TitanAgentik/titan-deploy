"""Portfolio-level risk engine — VaR/CVaR, correlation caps, regime limits."""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PipelineExposure:
    pipeline_id: str
    notional_usd: float
    returns: list[float] = field(default_factory=list)
    borrow_rate_annual_pct: float = 0.0
    funding_rate_8h_pct: float = 0.0
    capacity_usd: float = 0.0


@dataclass
class PortfolioSnapshot:
    equity_usd: float
    pipelines: list[PipelineExposure] = field(default_factory=list)
    regime: str = "neutral"
    timestamp: float = field(default_factory=time.time)


@dataclass
class PreTradeSimResult:
    decision: str  # ALLOW | DENY | WARN
    reason: str
    code: str = ""
    var_95_usd: float = 0.0
    cvar_95_usd: float = 0.0
    projected_exposure_usd: float = 0.0
    correlation_cluster: str = ""
    regime_limit_pct: float = 100.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioRiskConfig:
    var_confidence: float = 0.95
    max_var_pct_equity: float = 8.0
    max_cvar_pct_equity: float = 12.0
    max_correlated_cluster_pct: float = 25.0
    min_return_samples: int = 20
    regime_limits: dict[str, float] = field(
        default_factory=lambda: {
            "risk_off": 50.0,
            "neutral": 100.0,
            "risk_on": 120.0,
        }
    )
    correlation_groups: dict[str, list[str]] = field(
        default_factory=lambda: {
            "defi_yield": ["P1", "P3", "P7", "P8"],
            "mev_arb": ["P29", "P30", "P41"],
            "liquidations": ["P6", "P11", "P18"],
        }
    )
    borrow_rate_cap_annual_pct: float = 25.0
    funding_rate_cap_8h_pct: float = 0.15
    capacity_curve_enabled: bool = False


class PortfolioRiskEngine:
    """Real-time portfolio VaR/CVaR with correlation and regime-aware caps."""

    def __init__(self, config: PortfolioRiskConfig | None = None) -> None:
        self.config = config or PortfolioRiskConfig()
        self._augur_regime: str = "neutral"

    def set_regime_from_augur(self, regime: str) -> None:
        """Stub hook — AUGUR macro regime feed."""
        normalized = regime.lower().replace(" ", "_")
        if normalized in self.config.regime_limits:
            self._augur_regime = normalized
        elif normalized in ("bull", "expansion"):
            self._augur_regime = "risk_on"
        elif normalized in ("bear", "crisis", "crash"):
            self._augur_regime = "risk_off"
        else:
            self._augur_regime = "neutral"

    @property
    def regime(self) -> str:
        return self._augur_regime

    def _historical_var_cvar(
        self, returns: list[float], confidence: float = 0.95
    ) -> tuple[float, float]:
        if len(returns) < self.config.min_return_samples:
            return 0.0, 0.0
        losses = sorted(-r for r in returns)
        idx = max(0, int(math.ceil((1 - confidence) * len(losses))) - 1)
        var = losses[idx] if losses else 0.0
        tail = losses[: idx + 1] or [0.0]
        cvar = sum(tail) / len(tail)
        return max(var, 0.0), max(cvar, 0.0)

    def aggregate_returns(self, snapshot: PortfolioSnapshot) -> list[float]:
        if not snapshot.pipelines:
            return []
        with_returns = [p for p in snapshot.pipelines if p.returns]
        if not with_returns:
            return []
        n = min(len(p.returns) for p in with_returns)
        combined: list[float] = []
        total = sum(abs(p.notional_usd) for p in snapshot.pipelines) or 1.0
        for i in range(n):
            weighted = sum(
                (p.returns[-n + i] if len(p.returns) >= n else 0.0)
                * (abs(p.notional_usd) / total)
                for p in snapshot.pipelines
            )
            combined.append(weighted)
        return combined

    def _cluster_exposure(
        self, snapshot: PortfolioSnapshot, pipeline_id: str, add_notional: float = 0.0
    ) -> tuple[str, float, float]:
        for cluster, members in self.config.correlation_groups.items():
            if pipeline_id not in members:
                continue
            cluster_exp = sum(
                abs(p.notional_usd) for p in snapshot.pipelines if p.pipeline_id in members
            )
            found = any(p.pipeline_id == pipeline_id for p in snapshot.pipelines)
            if not found:
                cluster_exp += abs(add_notional)
            pct = (cluster_exp / snapshot.equity_usd * 100.0) if snapshot.equity_usd else 100.0
            return cluster, cluster_exp, pct
        return "", 0.0, 0.0

    def compute_var_cvar(self, snapshot: PortfolioSnapshot) -> dict[str, float]:
        returns = self.aggregate_returns(snapshot)
        if not returns:
            per_pipe = []
            for p in snapshot.pipelines:
                if p.returns:
                    v, c = self._historical_var_cvar(p.returns, self.config.var_confidence)
                    per_pipe.append((v * abs(p.notional_usd), c * abs(p.notional_usd)))
            if per_pipe:
                var = sum(v for v, _ in per_pipe)
                cvar = sum(c for _, c in per_pipe)
            else:
                var, cvar = 0.0, 0.0
        else:
            var_pct, cvar_pct = self._historical_var_cvar(returns, self.config.var_confidence)
            total_exp = sum(abs(p.notional_usd) for p in snapshot.pipelines)
            var = var_pct * total_exp
            cvar = cvar_pct * total_exp
        return {"var_95_usd": var, "cvar_95_usd": cvar}

    def simulate_pre_trade(
        self,
        snapshot: PortfolioSnapshot,
        pipeline_id: str,
        add_notional_usd: float,
        side: str = "buy",
    ) -> PreTradeSimResult:
        if snapshot.equity_usd <= 0:
            return PreTradeSimResult(
                decision="DENY", reason="Invalid equity", code="INVALID_EQUITY"
            )

        pipe = next((p for p in snapshot.pipelines if p.pipeline_id == pipeline_id), None)
        borrow = pipe.borrow_rate_annual_pct if pipe else 0.0
        funding = pipe.funding_rate_8h_pct if pipe else 0.0
        capacity = pipe.capacity_usd if pipe else 0.0

        if self.config.capacity_curve_enabled and capacity > 0:
            projected_notional = abs(add_notional_usd)
            if pipe:
                projected_notional = abs(pipe.notional_usd) + abs(add_notional_usd)
            if projected_notional > capacity:
                return PreTradeSimResult(
                    decision="DENY",
                    reason=(
                        f"Capacity curve cap {capacity:.0f} USD — "
                        f"projected {projected_notional:.0f} USD"
                    ),
                    code="CAPACITY_CURVE",
                    projected_exposure_usd=projected_notional,
                )

        if borrow > self.config.borrow_rate_cap_annual_pct:
            return PreTradeSimResult(
                decision="DENY",
                reason=(
                    f"Borrow rate {borrow:.1f}% exceeds cap "
                    f"{self.config.borrow_rate_cap_annual_pct}%"
                ),
                code="BORROW_RATE",
            )

        if abs(funding) > self.config.funding_rate_cap_8h_pct:
            return PreTradeSimResult(
                decision="DENY",
                reason=(
                    f"Funding rate {funding:.3f}% (8h) exceeds cap "
                    f"{self.config.funding_rate_cap_8h_pct}%"
                ),
                code="FUNDING_RATE",
            )

        sign = 1.0 if side.lower() in ("buy", "long") else -1.0
        projected = PortfolioSnapshot(
            equity_usd=snapshot.equity_usd,
            pipelines=list(snapshot.pipelines),
            regime=self.regime,
        )
        found = False
        for p in projected.pipelines:
            if p.pipeline_id == pipeline_id:
                p.notional_usd += sign * add_notional_usd
                found = True
                break
        if not found:
            projected.pipelines.append(
                PipelineExposure(pipeline_id=pipeline_id, notional_usd=sign * add_notional_usd)
            )

        metrics = self.compute_var_cvar(projected)
        var_usd = metrics["var_95_usd"]
        cvar_usd = metrics["cvar_95_usd"]
        var_pct = (var_usd / snapshot.equity_usd) * 100.0
        cvar_pct = (cvar_usd / snapshot.equity_usd) * 100.0

        if var_pct > self.config.max_var_pct_equity:
            return PreTradeSimResult(
                decision="DENY",
                reason=f"Portfolio VaR {var_pct:.1f}% exceeds cap {self.config.max_var_pct_equity}%",
                code="PORTFOLIO_VAR",
                var_95_usd=var_usd,
                cvar_95_usd=cvar_usd,
                projected_exposure_usd=sum(abs(p.notional_usd) for p in projected.pipelines),
            )

        if cvar_pct > self.config.max_cvar_pct_equity:
            return PreTradeSimResult(
                decision="DENY",
                reason=f"Portfolio CVaR {cvar_pct:.1f}% exceeds cap {self.config.max_cvar_pct_equity}%",
                code="PORTFOLIO_CVAR",
                var_95_usd=var_usd,
                cvar_95_usd=cvar_usd,
                projected_exposure_usd=sum(abs(p.notional_usd) for p in projected.pipelines),
            )

        cluster, cluster_exp, cluster_pct = self._cluster_exposure(
            projected, pipeline_id, add_notional_usd
        )
        if cluster and cluster_pct > self.config.max_correlated_cluster_pct:
            return PreTradeSimResult(
                decision="DENY",
                reason=(
                    f"Correlation cluster '{cluster}' exposure {cluster_pct:.1f}% "
                    f"exceeds cap {self.config.max_correlated_cluster_pct}%"
                ),
                code="CORRELATION_CAP",
                var_95_usd=var_usd,
                cvar_95_usd=cvar_usd,
                correlation_cluster=cluster,
                projected_exposure_usd=cluster_exp,
            )

        regime_limit = self.config.regime_limits.get(self.regime, 100.0)
        total_exp = sum(abs(p.notional_usd) for p in projected.pipelines)
        exp_pct = (total_exp / snapshot.equity_usd) * 100.0
        effective_cap = (snapshot.equity_usd * regime_limit / 100.0)
        if total_exp > effective_cap:
            return PreTradeSimResult(
                decision="DENY",
                reason=(
                    f"Regime '{self.regime}' exposure {exp_pct:.1f}% "
                    f"exceeds dynamic limit {regime_limit}%"
                ),
                code="REGIME_EXPOSURE",
                var_95_usd=var_usd,
                cvar_95_usd=cvar_usd,
                regime_limit_pct=regime_limit,
                projected_exposure_usd=total_exp,
            )

        return PreTradeSimResult(
            decision="ALLOW",
            reason="within portfolio risk limits",
            code="OK",
            var_95_usd=var_usd,
            cvar_95_usd=cvar_usd,
            regime_limit_pct=regime_limit,
            correlation_cluster=cluster,
            projected_exposure_usd=total_exp,
        )

    @classmethod
    def from_policy_raw(cls, raw: dict[str, Any]) -> PortfolioRiskEngine:
        pr = raw.get("portfolio_risk", {})
        t4 = (raw.get("tier4_ultimate") or {}).get("portfolio_construction") or {}
        cfg = PortfolioRiskConfig(
            var_confidence=float(pr.get("var_confidence", 0.95)),
            max_var_pct_equity=float(pr.get("max_var_pct_equity", 8.0)),
            max_cvar_pct_equity=float(pr.get("max_cvar_pct_equity", 12.0)),
            max_correlated_cluster_pct=float(pr.get("max_correlated_cluster_pct", 25.0)),
            min_return_samples=int(pr.get("min_return_samples", 20)),
            regime_limits=pr.get("regime_limits", PortfolioRiskConfig().regime_limits),
            correlation_groups=pr.get(
                "correlation_groups", PortfolioRiskConfig().correlation_groups
            ),
            borrow_rate_cap_annual_pct=float(
                t4.get("borrow_rate_cap_annual_pct", pr.get("borrow_rate_cap_annual_pct", 25.0))
            ),
            funding_rate_cap_8h_pct=float(
                t4.get("funding_rate_cap_8h_pct", pr.get("funding_rate_cap_8h_pct", 0.15))
            ),
            capacity_curve_enabled=bool(
                t4.get("capacity_curve_enabled", pr.get("capacity_curve_enabled", False))
            ),
        )
        engine = cls(cfg)
        regime = pr.get("augur_regime_stub", "neutral")
        engine.set_regime_from_augur(str(regime))
        return engine

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "regime": self.regime,
            "augur_stub": True,
        }
