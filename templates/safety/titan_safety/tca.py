"""Transaction-cost analysis / execution-quality engine.

Turns raw fills into per-lane, net-of-cost expectancy scorecards. This is the
feedback loop that converts *claimed* edge into *measured* edge: realized vs.
expected slippage, gas + tip drag, revert/rejection rate, tip efficiency,
capacity pressure, and edge decay. Scorecards feed the capital allocator so
capital flows to lanes that actually net positive after all costs.

Deterministic, out-of-process, non-LLM — same trust model as the risk kernel.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Fill:
    """A single executed (or attempted) trade with realized costs."""

    pipeline_id: str
    venue: str = ""
    side: str = "buy"  # buy/long or sell/short
    notional_usd: float = 0.0
    expected_price: float = 0.0
    realized_price: float = 0.0
    gross_pnl_usd: float = 0.0  # PnL before gas/tip
    gas_usd: float = 0.0
    tip_usd: float = 0.0
    reverted: bool = False
    ts: float = field(default_factory=time.time)

    def slippage_bps(self) -> float:
        """Adverse slippage in bps (positive = worse than expected)."""
        if self.expected_price <= 0 or self.realized_price <= 0:
            return 0.0
        raw = (self.realized_price - self.expected_price) / self.expected_price
        # For sells, a lower realized price is adverse -> flip sign.
        if self.side.lower() in ("sell", "short"):
            raw = -raw
        return raw * 1e4

    def net_pnl_usd(self) -> float:
        return self.gross_pnl_usd - self.gas_usd - self.tip_usd


@dataclass
class LaneScorecard:
    pipeline_id: str
    fill_count: int = 0
    revert_count: int = 0
    fill_rate: float = 1.0
    gross_bps: float = 0.0
    cost_bps: float = 0.0  # gas + tip drag, in bps of notional
    net_bps: float = 0.0  # gross - cost (the number that matters)
    avg_slippage_bps: float = 0.0
    tip_efficiency: float = 0.0  # tips / positive gross (fraction of MEV paid away)
    decay_slope_bps: float = 0.0  # net-bps trend across the window (<0 = decaying)
    capacity_pressure: float = 0.0  # corr(notional, slippage): >0 = edge fades with size
    total_notional_usd: float = 0.0
    net_pnl_usd: float = 0.0
    verdict: str = "INSUFFICIENT_DATA"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TCAConfig:
    window: int = 500  # rolling fills retained per lane
    min_fills_for_verdict: int = 30
    healthy_net_bps: float = 5.0  # >= this net bps => HEALTHY
    marginal_net_bps: float = 0.0  # between marginal and healthy => MARGINAL
    max_tip_efficiency: float = 0.40  # tips > 40% of gross MEV => bleeding
    max_slippage_bps: float = 20.0
    min_fill_rate: float = 0.80

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TCAConfig:
        t = raw.get("tca", {}) if raw else {}
        d = cls()
        return cls(
            window=int(t.get("window", d.window)),
            min_fills_for_verdict=int(t.get("min_fills_for_verdict", d.min_fills_for_verdict)),
            healthy_net_bps=float(t.get("healthy_net_bps", d.healthy_net_bps)),
            marginal_net_bps=float(t.get("marginal_net_bps", d.marginal_net_bps)),
            max_tip_efficiency=float(t.get("max_tip_efficiency", d.max_tip_efficiency)),
            max_slippage_bps=float(t.get("max_slippage_bps", d.max_slippage_bps)),
            min_fill_rate=float(t.get("min_fill_rate", d.min_fill_rate)),
        )


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx <= 0 or dy <= 0:
        return 0.0
    return num / (dx**0.5 * dy**0.5)


def _slope(ys: list[float]) -> float:
    """OLS slope of ys vs its index (per-step change)."""
    n = len(ys)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx, my = _mean([float(x) for x in xs]), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else 0.0


class TCAEngine:
    """Ingests fills and produces per-lane net-of-cost execution scorecards."""

    def __init__(self, config: TCAConfig | None = None) -> None:
        self.config = config or TCAConfig()
        self._fills: dict[str, deque[Fill]] = {}

    def ingest(self, fill: Fill) -> None:
        dq = self._fills.get(fill.pipeline_id)
        if dq is None:
            dq = deque(maxlen=self.config.window)
            self._fills[fill.pipeline_id] = dq
        dq.append(fill)

    def scorecard(self, pipeline_id: str) -> LaneScorecard:
        dq = self._fills.get(pipeline_id)
        card = LaneScorecard(pipeline_id=pipeline_id)
        if not dq:
            return card

        fills = list(dq)
        filled = [f for f in fills if not f.reverted]
        card.fill_count = len(filled)
        card.revert_count = sum(1 for f in fills if f.reverted)
        attempts = len(fills)
        card.fill_rate = (len(filled) / attempts) if attempts else 1.0

        total_notional = sum(f.notional_usd for f in filled)
        card.total_notional_usd = total_notional
        # Reverts still burn gas — count their cost against the lane.
        total_gas_tip = sum(f.gas_usd + f.tip_usd for f in fills)
        total_gross = sum(f.gross_pnl_usd for f in filled)
        card.net_pnl_usd = total_gross - total_gas_tip

        if total_notional > 0:
            card.gross_bps = total_gross / total_notional * 1e4
            card.cost_bps = total_gas_tip / total_notional * 1e4
            card.net_bps = card.net_pnl_usd / total_notional * 1e4

        card.avg_slippage_bps = _mean([f.slippage_bps() for f in filled])

        positive_gross = sum(f.gross_pnl_usd for f in filled if f.gross_pnl_usd > 0)
        total_tips = sum(f.tip_usd for f in fills)
        card.tip_efficiency = (total_tips / positive_gross) if positive_gross > 0 else (
            1.0 if total_tips > 0 else 0.0
        )

        # Edge decay: slope of per-fill net bps over the window.
        per_fill_net_bps = [
            (f.net_pnl_usd() / f.notional_usd * 1e4) for f in filled if f.notional_usd > 0
        ]
        card.decay_slope_bps = _slope(per_fill_net_bps)

        # Capacity pressure: does slippage worsen as size grows?
        sized = [f for f in filled if f.notional_usd > 0]
        card.capacity_pressure = _pearson(
            [f.notional_usd for f in sized], [f.slippage_bps() for f in sized]
        )

        card.verdict = self._verdict(card)
        return card

    def _verdict(self, card: LaneScorecard) -> str:
        cfg = self.config
        if card.fill_count < cfg.min_fills_for_verdict:
            return "INSUFFICIENT_DATA"
        bleeding = (
            card.net_bps <= cfg.marginal_net_bps
            or card.tip_efficiency > cfg.max_tip_efficiency
            or card.avg_slippage_bps > cfg.max_slippage_bps
            or card.fill_rate < cfg.min_fill_rate
        )
        if bleeding:
            return "BLEEDING"
        if card.net_bps >= cfg.healthy_net_bps and card.decay_slope_bps >= 0:
            return "HEALTHY"
        return "MARGINAL"

    def all_scorecards(self) -> list[LaneScorecard]:
        return [self.scorecard(pid) for pid in sorted(self._fills)]

    def health(self) -> dict[str, Any]:
        cards = self.all_scorecards()
        return {
            "status": "ok",
            "lanes_tracked": len(self._fills),
            "bleeding_lanes": [c.pipeline_id for c in cards if c.verdict == "BLEEDING"],
        }
