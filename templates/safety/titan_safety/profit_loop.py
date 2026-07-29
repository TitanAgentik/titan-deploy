"""TCA → allocator profit loop: auto-de-fund BLEEDING lanes.

After fills are ingested into TCA, this module:
  1. Reads per-lane scorecards
  2. Marks BLEEDING / decaying lanes as de-funded (target_notional = 0)
  3. Builds an allocator plan from remaining HEALTHY/MARGINAL lanes
  4. Persists a defund ledger (append-only) — re-funding requires human YES

This is the compounding feedback loop: measured edge drives capital.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .allocator import AllocationPlan, AllocatorConfig, CapitalAllocator, LaneEdge
from .kill_switch import KillSwitch
from .tca import LaneScorecard, TCAEngine


DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
DEFUND_LEDGER = "defund_ledger.jsonl"
DEFUND_STATE = "defund_state.json"


@dataclass
class ProfitLoopResult:
    plan: AllocationPlan | None
    defunded: list[str] = field(default_factory=list)
    already_defunded: list[str] = field(default_factory=list)
    scorecards: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict() if self.plan else None,
            "defunded": self.defunded,
            "already_defunded": self.already_defunded,
            "scorecards": self.scorecards,
            "notes": self.notes,
        }


class ProfitLoop:
    """Connects TCA scorecards to allocator + pipeline halt for BLEEDING lanes."""

    def __init__(
        self,
        tca: TCAEngine,
        allocator: CapitalAllocator | None = None,
        safety_dir: Path | None = None,
        auto_halt_bleeding: bool = True,
    ) -> None:
        self.tca = tca
        self.allocator = allocator or CapitalAllocator()
        self.safety_dir = safety_dir or DEFAULT_SAFETY_DIR
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.auto_halt_bleeding = auto_halt_bleeding
        self.ks = KillSwitch(self.safety_dir)
        self._defunded: set[str] = set(self._load_defunded())

    @property
    def ledger_path(self) -> Path:
        return self.safety_dir / DEFUND_LEDGER

    @property
    def state_path(self) -> Path:
        return self.safety_dir / DEFUND_STATE

    def _load_defunded(self) -> list[str]:
        if not self.state_path.exists():
            return []
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        return list(data.get("defunded", []))

    def _save_defunded(self) -> None:
        self.state_path.write_text(
            json.dumps({"defunded": sorted(self._defunded), "ts": time.time()}, indent=2),
            encoding="utf-8",
        )

    def _append_ledger(self, record: dict[str, Any]) -> None:
        record = {**record, "ts": time.time()}
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    def defunded_lanes(self) -> set[str]:
        return set(self._defunded)

    def is_defunded(self, pipeline_id: str) -> bool:
        return pipeline_id in self._defunded

    def defund(self, pipeline_id: str, reason: str, operator: str = "profit_loop") -> None:
        if pipeline_id in self._defunded:
            return
        self._defunded.add(pipeline_id)
        self._save_defunded()
        self._append_ledger(
            {
                "action": "defund",
                "pipeline_id": pipeline_id,
                "reason": reason,
                "operator": operator,
            }
        )
        if self.auto_halt_bleeding:
            self.ks.activate_pipeline(pipeline_id, operator, reason)

    def refund(
        self,
        pipeline_id: str,
        operator: str,
        reason: str = "human YES",
        *,
        require_promotion_yes: bool = True,
    ) -> bool:
        """Re-fund a lane — requires explicit operator YES + promotion gate approval."""
        if pipeline_id not in self._defunded:
            return False
        if require_promotion_yes:
            from .promotion_gate import PromotionGate

            yes = reason.strip().upper() == "YES" or reason.strip().upper().startswith("YES")
            if not yes:
                self._append_ledger(
                    {
                        "action": "refund_denied",
                        "pipeline_id": pipeline_id,
                        "reason": "explicit YES required in reason",
                        "operator": operator,
                    }
                )
                return False
            pg = PromotionGate(self.safety_dir)
            if not pg.has_approved("strategy_promotion", pipeline_id):
                self._append_ledger(
                    {
                        "action": "refund_denied",
                        "pipeline_id": pipeline_id,
                        "reason": "no strategy_promotion YES in audit log",
                        "operator": operator,
                    }
                )
                return False
        self._defunded.discard(pipeline_id)
        self._save_defunded()
        self._append_ledger(
            {
                "action": "refund",
                "pipeline_id": pipeline_id,
                "reason": reason,
                "operator": operator,
            }
        )
        self.ks.deactivate_pipeline(pipeline_id)
        return True

    def run(
        self,
        equity_usd: float,
        regime: str = "neutral",
        drawdown_pct: float = 0.0,
        lane_overrides: list[LaneEdge] | None = None,
    ) -> ProfitLoopResult:
        cards = self.tca.all_scorecards()
        newly_defunded: list[str] = []
        already: list[str] = []
        notes: list[str] = []

        for card in cards:
            if card.verdict == "BLEEDING":
                if card.pipeline_id in self._defunded:
                    already.append(card.pipeline_id)
                else:
                    self.defund(
                        card.pipeline_id,
                        reason=(
                            f"TCA BLEEDING: net_bps={card.net_bps:.2f} "
                            f"tip_eff={card.tip_efficiency:.2f} "
                            f"fill_rate={card.fill_rate:.2f}"
                        ),
                    )
                    newly_defunded.append(card.pipeline_id)
                    notes.append(f"auto-defunded {card.pipeline_id}")

        # Build allocator inputs from scorecards (or overrides), marking defunded as decaying
        if lane_overrides is not None:
            lanes = list(lane_overrides)
            for lane in lanes:
                if lane.pipeline_id in self._defunded:
                    lane.decaying = True
        else:
            lanes = []
            for card in cards:
                if card.verdict == "INSUFFICIENT_DATA":
                    continue
                # Prefer HEALTHY: scale MARGINAL edge down so Kelly starves weak lanes
                net = card.net_bps
                if card.verdict == "MARGINAL" and net > 0:
                    net = net * 0.35
                lanes.append(
                    LaneEdge(
                        pipeline_id=card.pipeline_id,
                        net_bps=net,
                        return_std=max(0.01, abs(card.net_bps) / 1e4 * 2),
                        trade_count=card.fill_count,
                        capacity_usd=0.0,
                        decaying=(
                            card.pipeline_id in self._defunded
                            or card.decay_slope_bps < 0
                            or card.verdict == "BLEEDING"
                        ),
                        cluster="",
                    )
                )

        plan = self.allocator.allocate(
            equity_usd, lanes, regime=regime, drawdown_pct=drawdown_pct
        )
        # Force zero notional for any still-defunded lane that slipped through
        for alloc in plan.allocations:
            if alloc.pipeline_id in self._defunded:
                alloc.target_notional_usd = 0.0
                alloc.capped_by = "defunded"

        return ProfitLoopResult(
            plan=plan,
            defunded=newly_defunded,
            already_defunded=already,
            scorecards=[c.to_dict() for c in cards],
            notes=notes,
        )
