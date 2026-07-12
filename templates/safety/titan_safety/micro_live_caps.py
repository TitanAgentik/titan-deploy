"""Micro-live capital caps — calendar is NOT a gate.

Phase progression is enforced by equity % caps in software, not elapsed days.
Paper ≠ micro-live: micro-live uses real signing/submit at ≤0.05–0.1% equity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PhaseCap:
    phase_id: int
    name: str
    max_equity_pct_per_trade: float
    max_aggregate_equity_pct: float
    min_fills_before_scale: int = 200
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_PHASE_CAPS: dict[str, PhaseCap] = {
    "infrastructure_paper": PhaseCap(
        0, "infrastructure_paper", 0.0, 0.0, min_fills_before_scale=0,
        note="Paper only — no live signing",
    ),
    "micro_live": PhaseCap(
        1, "micro_live", 0.10, 0.50, min_fills_before_scale=50,
        note="Real signing/submit at ≤0.1% equity per trade",
    ),
    "micro_live_conservative": PhaseCap(
        1, "micro_live_conservative", 0.05, 0.25, min_fills_before_scale=50,
        note="Conservative micro-live at ≤0.05% equity",
    ),
    "validated_scale": PhaseCap(
        2, "validated_scale", 0.50, 2.0, min_fills_before_scale=200,
        note="Requires stats gate + Phase 5 YES — not calendar alone",
    ),
    "mature_production": PhaseCap(
        3, "mature_production", 2.0, 25.0, min_fills_before_scale=500,
        note="Full policy envelope after evidence — never skip from 2-day phases",
    ),
}


@dataclass
class CapCheckResult:
    allowed: bool
    reason: str
    phase: str
    max_notional_usd: float
    pct_of_equity: float
    calendar_is_gate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MicroLiveCapsConfig:
    calendar_is_gate: bool = False  # always false — enforced in code
    default_phase: str = "micro_live_conservative"
    phases: dict[str, PhaseCap] = field(default_factory=lambda: dict(DEFAULT_PHASE_CAPS))
    forbid_calendar_only_promotion: bool = True
    max_jump_notional_usd: float = 500.0  # no $10–50k jumps from 2-day phases

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> MicroLiveCapsConfig:
        r = raw or {}
        ml = r.get("micro_live_caps", r)
        d = cls()
        phases = dict(DEFAULT_PHASE_CAPS)
        for name, cfg in (ml.get("phases") or {}).items():
            if isinstance(cfg, dict):
                base = phases.get(name, PhaseCap(0, name, 0.05, 0.25))
                phases[name] = PhaseCap(
                    phase_id=int(cfg.get("phase_id", base.phase_id)),
                    name=str(name),
                    max_equity_pct_per_trade=float(
                        cfg.get("max_equity_pct_per_trade", base.max_equity_pct_per_trade)
                    ),
                    max_aggregate_equity_pct=float(
                        cfg.get("max_aggregate_equity_pct", base.max_aggregate_equity_pct)
                    ),
                    min_fills_before_scale=int(
                        cfg.get("min_fills_before_scale", base.min_fills_before_scale)
                    ),
                    note=str(cfg.get("note", base.note)),
                )
        return cls(
            calendar_is_gate=False,
            default_phase=str(ml.get("default_phase", d.default_phase)),
            phases=phases,
            forbid_calendar_only_promotion=bool(
                ml.get("forbid_calendar_only_promotion", d.forbid_calendar_only_promotion)
            ),
            max_jump_notional_usd=float(
                ml.get("max_jump_notional_usd", d.max_jump_notional_usd)
            ),
        )


class MicroLiveCaps:
    """Enforces per-phase equity caps — time alone never authorizes scale-up."""

    def __init__(self, config: MicroLiveCapsConfig | None = None) -> None:
        self.config = config or MicroLiveCapsConfig()

    def calendar_is_gate(self) -> bool:
        return False

    def phase_cap(self, phase: str | None = None) -> PhaseCap:
        name = phase or self.config.default_phase
        return self.config.phases.get(name, self.config.phases[self.config.default_phase])

    def check_trade(
        self,
        notional_usd: float,
        equity_usd: float,
        *,
        phase: str | None = None,
        aggregate_exposure_usd: float = 0.0,
    ) -> CapCheckResult:
        cap = self.phase_cap(phase)
        if equity_usd <= 0:
            return CapCheckResult(
                allowed=False,
                reason="invalid equity",
                phase=cap.name,
                max_notional_usd=0.0,
                pct_of_equity=0.0,
            )
        max_trade = equity_usd * cap.max_equity_pct_per_trade / 100.0
        max_agg = equity_usd * cap.max_aggregate_equity_pct / 100.0
        pct = (notional_usd / equity_usd * 100.0) if equity_usd else 0.0

        if cap.max_equity_pct_per_trade <= 0 and notional_usd > 0:
            return CapCheckResult(
                allowed=False,
                reason=f"phase {cap.name} is paper-only (0% live cap)",
                phase=cap.name,
                max_notional_usd=0.0,
                pct_of_equity=pct,
            )
        if notional_usd > max_trade:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"notional ${notional_usd:.2f} exceeds phase {cap.name} "
                    f"max {cap.max_equity_pct_per_trade}% (${max_trade:.2f})"
                ),
                phase=cap.name,
                max_notional_usd=max_trade,
                pct_of_equity=pct,
            )
        if aggregate_exposure_usd + notional_usd > max_agg:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"aggregate exposure would exceed phase {cap.name} "
                    f"max {cap.max_aggregate_equity_pct}% (${max_agg:.2f})"
                ),
                phase=cap.name,
                max_notional_usd=max_trade,
                pct_of_equity=pct,
            )
        if notional_usd > self.config.max_jump_notional_usd and cap.phase_id <= 1:
            return CapCheckResult(
                allowed=False,
                reason=(
                    f"notional ${notional_usd:.2f} exceeds micro-live jump cap "
                    f"${self.config.max_jump_notional_usd:.2f} — no $10–50k on short phases"
                ),
                phase=cap.name,
                max_notional_usd=min(max_trade, self.config.max_jump_notional_usd),
                pct_of_equity=pct,
            )
        return CapCheckResult(
            allowed=True,
            reason="within phase cap",
            phase=cap.name,
            max_notional_usd=max_trade,
            pct_of_equity=pct,
        )

    def can_scale_phase(
        self,
        *,
        current_phase: str,
        target_phase: str,
        fill_count: int,
        stats_gate_passed: bool,
        promotion_yes: bool,
        days_elapsed: int = 0,
    ) -> tuple[bool, str]:
        """Scale-up requires evidence + YES — calendar days alone never suffice."""
        cur = self.phase_cap(current_phase)
        tgt = self.phase_cap(target_phase)
        if tgt.phase_id <= cur.phase_id:
            return True, "same or lower phase"
        if self.config.forbid_calendar_only_promotion and not stats_gate_passed:
            return False, "stats gate required — calendar is not a gate"
        if fill_count < cur.min_fills_before_scale:
            return False, (
                f"fill_count {fill_count} < min {cur.min_fills_before_scale} for phase scale"
            )
        if tgt.phase_id >= 2 and not promotion_yes:
            return False, "Phase 5 / strategy_promotion YES required for validated_scale+"
        if days_elapsed > 0 and not stats_gate_passed and not promotion_yes:
            return False, f"{days_elapsed} days elapsed but calendar alone does not authorize scale"
        return True, "evidence + caps satisfied"
