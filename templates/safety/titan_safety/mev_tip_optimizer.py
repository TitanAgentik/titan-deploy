"""MEV tip optimizer — advisory competitive tip suggestion for broadcast path.

Advisory only unless operator explicitly disables advisory_only in policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .kernel import TradeRequest
from .tier4_gate import tier4_active, tier4_cfg


@dataclass
class TipRecommendation:
    trade_id: str
    venue: str
    suggested_tip_bps: float
    confidence: float
    rationale: str
    advisory_only: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MevTipOptimizer:
    """Heuristic tip advisor — STUB competitive model until live mempool data wired."""

    def __init__(self, policy_raw: dict[str, Any] | None = None) -> None:
        self.policy_raw = policy_raw or {}
        self.cfg = tier4_cfg(self.policy_raw).get("mev_tip_optimizer") or {}

    def is_enabled(self) -> bool:
        if not tier4_active(self.policy_raw):
            return False
        return bool(self.cfg.get("enabled", False))

    def recommend(
        self,
        trade: TradeRequest | dict[str, Any],
        *,
        urgency: float = 0.5,
        recent_fill_rate: float = 1.0,
        competitor_tip_bps: float | None = None,
    ) -> TipRecommendation | None:
        if not self.is_enabled():
            return None

        t = trade if isinstance(trade, TradeRequest) else TradeRequest.from_dict(trade)
        max_tip = float(self.cfg.get("max_tip_bps", 40.0))
        advisory = bool(self.cfg.get("advisory_only", True))

        base = 2.0 + urgency * 8.0
        if recent_fill_rate < 0.8:
            base += (0.8 - recent_fill_rate) * 20.0
        if competitor_tip_bps is not None:
            base = max(base, competitor_tip_bps * 1.05)

        suggested = min(max_tip, round(base, 2))
        return TipRecommendation(
            trade_id=t.trade_id,
            venue=t.venue,
            suggested_tip_bps=suggested,
            confidence=0.55 if competitor_tip_bps is None else 0.72,
            rationale="stub heuristic — wire live mempool / builder fee data for production",
            advisory_only=advisory,
            details={
                "urgency": urgency,
                "recent_fill_rate": recent_fill_rate,
                "competitor_tip_bps": competitor_tip_bps,
                "max_tip_bps": max_tip,
            },
        )
