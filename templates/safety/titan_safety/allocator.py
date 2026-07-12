"""Capital allocator — attribution -> forward fractional-Kelly allocation.

This is the compounding engine. It reads per-lane, cost-adjusted edge (from the
TCA engine / LAMARCK attribution) and decides *where next dollar of risk goes*:

  1. Gross risk budget (the "risk envelope") is human/policy-set and scaled by
     regime and live drawdown (de-grossing ladder). This is "how much risk".
  2. Within that budget, capital is split across lanes by fractional-Kelly
     weights (edge / variance), so winners get fed and losers get starved.
  3. Per-lane caps, correlation-cluster caps, and per-lane capacity limits keep
     any single bet or correlated cluster from dominating.

Separation of concerns is deliberate: humans own the envelope (how much),
the machine owns allocation (where). Deterministic and out-of-process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .tier4_gate import tier4_active, tier4_cfg
from .v1_surface import V1SurfaceLockdown, load_v1_surface_config


@dataclass
class LaneEdge:
    """Cost-adjusted edge stats for one pipeline/strategy lane."""

    pipeline_id: str
    net_bps: float = 0.0  # net-of-cost expected return per trade (bps) — from TCA
    return_std: float = 0.0  # per-trade return std (fraction, e.g. 0.01 = 1%)
    trade_count: int = 0
    capacity_usd: float = 0.0  # 0 => unconstrained
    borrow_rate_annual_pct: float = 0.0
    funding_rate_8h_pct: float = 0.0
    decaying: bool = False  # TCA decay_slope < 0 sustained
    cluster: str = ""


@dataclass
class Allocation:
    pipeline_id: str
    target_notional_usd: float
    weight: float
    kelly_signal: float
    cluster: str = ""
    capped_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AllocationPlan:
    equity_usd: float
    regime: str
    drawdown_pct: float
    gross_budget_usd: float
    gross_pct: float
    deployed_usd: float
    utilization: float
    allocations: list[Allocation] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    advisory: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["allocations"] = [a.to_dict() for a in self.allocations]
        return d


@dataclass
class AllocatorConfig:
    kelly_fraction: float = 0.25  # fraction of full Kelly (1/4-Kelly default)
    base_gross_pct: float = 100.0  # gross exposure cap as % equity (risk envelope)
    max_lane_pct: float = 25.0  # per-lane cap as % equity
    max_cluster_pct: float = 40.0  # per-correlation-cluster cap as % equity
    min_net_bps: float = 1.0  # lanes below this net edge get no capital
    min_trades: int = 100  # lanes below this sample size get no capital
    max_active_pipelines: int = 4  # hard cap on funded lanes (concentration)
    selective_activation: bool = True  # catalog ≠ all-on
    advisory_mode: bool = True  # Phase 1: log targets only; Phase 2+: enforce
    regime_multipliers: dict[str, float] = field(
        default_factory=lambda: {"risk_off": 0.5, "neutral": 1.0, "risk_on": 1.2}
    )
    # Drawdown de-grossing ladder: (drawdown_pct_threshold, gross_multiplier).
    degross_ladder: list[list[float]] = field(
        default_factory=lambda: [[3.0, 0.75], [5.0, 0.5], [7.0, 0.25], [10.0, 0.0]]
    )
    correlation_groups: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> AllocatorConfig:
        a = raw.get("allocator", {}) if raw else {}
        d = cls()
        pr = raw.get("portfolio_risk", {}) if raw else {}
        groups = a.get("correlation_groups", pr.get("correlation_groups", {}))
        return cls(
            kelly_fraction=float(a.get("kelly_fraction", d.kelly_fraction)),
            base_gross_pct=float(a.get("base_gross_pct", d.base_gross_pct)),
            max_lane_pct=float(a.get("max_lane_pct", d.max_lane_pct)),
            max_cluster_pct=float(a.get("max_cluster_pct", d.max_cluster_pct)),
            min_net_bps=float(a.get("min_net_bps", d.min_net_bps)),
            min_trades=int(a.get("min_trades", d.min_trades)),
            max_active_pipelines=int(a.get("max_active_pipelines", d.max_active_pipelines)),
            selective_activation=bool(a.get("selective_activation", d.selective_activation)),
            advisory_mode=bool(a.get("advisory_mode", d.advisory_mode)),
            regime_multipliers=a.get("regime_multipliers", d.regime_multipliers),
            degross_ladder=a.get("degross_ladder", d.degross_ladder),
            correlation_groups=groups,
        )


class CapitalAllocator:
    def __init__(
        self,
        config: AllocatorConfig | None = None,
        v1_lockdown: V1SurfaceLockdown | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> None:
        self.config = config or AllocatorConfig()
        self.v1 = v1_lockdown or V1SurfaceLockdown(load_v1_surface_config())
        self.policy_raw = policy_raw or {}

    def effective_max_active_pipelines(self) -> int:
        base = self.config.max_active_pipelines
        if self.v1.is_active():
            return self.v1.apply_allocator_limits(base)
        return base

    def is_enforced(self) -> bool:
        return not self.config.advisory_mode

    def _cluster_for(self, pipeline_id: str, declared: str) -> str:
        if declared:
            return declared
        for cluster, members in self.config.correlation_groups.items():
            if pipeline_id in members:
                return cluster
        return ""

    def degross_multiplier(self, drawdown_pct: float) -> float:
        mult = 1.0
        for threshold, m in sorted(self.config.degross_ladder, key=lambda x: x[0]):
            if drawdown_pct >= threshold:
                mult = m
        return mult

    def gross_budget(self, equity_usd: float, regime: str, drawdown_pct: float) -> float:
        regime_mult = self.config.regime_multipliers.get(regime, 1.0)
        degross = self.degross_multiplier(drawdown_pct)
        pct = self.config.base_gross_pct * regime_mult * degross
        return max(0.0, equity_usd * pct / 100.0)

    def allocate(
        self,
        equity_usd: float,
        lanes: list[LaneEdge],
        regime: str = "neutral",
        drawdown_pct: float = 0.0,
    ) -> AllocationPlan:
        cfg = self.config
        excluded: dict[str, str] = {}
        notes: list[str] = []

        budget = self.gross_budget(equity_usd, regime, drawdown_pct)
        plan = AllocationPlan(
            equity_usd=equity_usd,
            regime=regime,
            drawdown_pct=drawdown_pct,
            gross_budget_usd=budget,
            gross_pct=(budget / equity_usd * 100.0) if equity_usd > 0 else 0.0,
            deployed_usd=0.0,
            utilization=0.0,
            excluded=excluded,
            notes=notes,
            advisory=self.config.advisory_mode,
        )
        if self.config.advisory_mode:
            notes.append("ADVISORY — targets logged only; not enforced on execution")
        if equity_usd <= 0:
            notes.append("invalid equity")
            return plan
        if budget <= 0:
            notes.append(f"gross budget is zero (drawdown {drawdown_pct:.1f}% de-grossing)")
            return plan

        # Eligibility + Kelly signal (edge / variance). return_std defaults to a
        # conservative floor so a missing/zero std can't manufacture huge leverage.
        eligible: list[tuple[LaneEdge, float]] = []
        for lane in lanes:
            if self.v1.is_active():
                surf = self.v1.check_pipeline(lane.pipeline_id)
                if not surf.allowed:
                    excluded[lane.pipeline_id] = surf.reason
                    continue
            if lane.net_bps < cfg.min_net_bps:
                excluded[lane.pipeline_id] = f"net_bps {lane.net_bps:.1f} < min {cfg.min_net_bps}"
                continue
            if lane.trade_count < cfg.min_trades:
                excluded[lane.pipeline_id] = (
                    f"trade_count {lane.trade_count} < min {cfg.min_trades}"
                )
                continue
            if lane.decaying:
                excluded[lane.pipeline_id] = "edge decaying (de-funded)"
                continue
            pc = tier4_cfg(self.policy_raw).get("portfolio_construction") or {}
            if tier4_active(self.policy_raw):
                borrow_cap = float(pc.get("borrow_rate_cap_annual_pct", 25.0))
                funding_cap = float(pc.get("funding_rate_cap_8h_pct", 0.15))
                if lane.borrow_rate_annual_pct > borrow_cap:
                    excluded[lane.pipeline_id] = (
                        f"borrow_rate {lane.borrow_rate_annual_pct:.1f}% > cap {borrow_cap}%"
                    )
                    continue
                if abs(lane.funding_rate_8h_pct) > funding_cap:
                    excluded[lane.pipeline_id] = (
                        f"funding_rate {lane.funding_rate_8h_pct:.3f}% > cap {funding_cap}%"
                    )
                    continue
            std = lane.return_std if lane.return_std > 0 else 0.02
            variance = std * std
            edge = lane.net_bps / 1e4
            kelly_signal = max(0.0, edge / variance)
            if kelly_signal <= 0:
                excluded[lane.pipeline_id] = "non-positive kelly signal"
                continue
            eligible.append((lane, kelly_signal))

        if not eligible:
            notes.append("no eligible lanes")
            return plan

        total_signal = sum(sig for _, sig in eligible)
        deployable = budget * cfg.kelly_fraction
        # Kelly fraction scales *within* the human gross envelope; never exceed it.
        deployable = min(deployable, budget)

        lane_cap = equity_usd * cfg.max_lane_pct / 100.0
        cluster_cap = equity_usd * cfg.max_cluster_pct / 100.0
        cluster_running: dict[str, float] = {}
        allocations: list[Allocation] = []
        max_active = self.effective_max_active_pipelines()

        active_count = 0
        for lane, sig in sorted(eligible, key=lambda x: x[1], reverse=True):
            if active_count >= max_active:
                excluded[lane.pipeline_id] = (
                    f"max_active_pipelines={max_active}"
                )
                continue

            weight = sig / total_signal
            target = weight * deployable
            capped_by = ""

            if target > lane_cap:
                target = lane_cap
                capped_by = "lane_cap"

            cluster = self._cluster_for(lane.pipeline_id, lane.cluster)
            if cluster:
                used = cluster_running.get(cluster, 0.0)
                if used + target > cluster_cap:
                    target = max(0.0, cluster_cap - used)
                    capped_by = "cluster_cap"
                cluster_running[cluster] = used + target

            if lane.capacity_usd > 0 and target > lane.capacity_usd:
                target = lane.capacity_usd
                capped_by = "capacity"

            if target <= 0:
                excluded[lane.pipeline_id] = "zero after caps"
                continue

            allocations.append(
                Allocation(
                    pipeline_id=lane.pipeline_id,
                    target_notional_usd=round(target, 2),
                    weight=round(weight, 4),
                    kelly_signal=round(sig, 4),
                    cluster=cluster,
                    capped_by=capped_by,
                )
            )
            active_count += 1
        if active_count >= max_active and len(eligible) > active_count:
            notes.append(
                f"capped to {max_active} active pipelines "
                f"(of {len(eligible)} eligible)"
            )
        if self.v1.is_active() and self.config.selective_activation:
            notes.append(
                f"v1 surface lockdown: max {max_active} strategies, "
                f"chain={self.v1.config.chain}"
            )

        deployed = sum(a.target_notional_usd for a in allocations)
        plan.allocations = allocations
        plan.deployed_usd = round(deployed, 2)
        plan.utilization = round(deployed / budget, 4) if budget else 0.0
        return plan

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "kelly_fraction": self.config.kelly_fraction,
            "base_gross_pct": self.config.base_gross_pct,
            "advisory_mode": self.config.advisory_mode,
            "enforced": self.is_enforced(),
        }
