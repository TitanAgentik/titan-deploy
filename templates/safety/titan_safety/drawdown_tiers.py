"""Drawdown tier evaluation — notify-only; never block trading on tier breach."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .kernel import TradeRequest

# Legacy blocking actions → notify-only (trading continues autonomously).
_NOTIFY_ACTIONS = frozenset(
    {
        "notify_operator",
        "notify_continue",
        "notify_critical_continue",
        "alert_operator",
        "soft_pause_new_entries",
        "reduce_exposure_50pct",
        "critical_alert_human_required",
        "full_halt_flatten",
    }
)

_DEFAULT_SEVERITY = {
    2.0: "MEDIUM",
    5.0: "HIGH",
    8.0: "HIGH",
    10.0: "CRITICAL",
    12.0: "CRITICAL",
}


@dataclass
class VolatileExempt:
    """Volatile lanes — no portfolio drawdown tier enforcement (lane-local CBs only)."""

    pipelines: list[str] = field(default_factory=list)
    correlation_groups: list[str] = field(default_factory=list)
    venues: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class DrawdownTier:
    pct: float
    action: str
    severity: str = "HIGH"
    scope: str = "portfolio"
    note: str = ""


@dataclass
class DrawdownAlert:
    tier_pct: float
    action: str
    severity: str
    drawdown_pct: float
    message: str
    trading_continues: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_pct": self.tier_pct,
            "action": self.action,
            "severity": self.severity,
            "drawdown_pct": self.drawdown_pct,
            "message": self.message,
            "trading_continues": self.trading_continues,
        }


def drawdown_notify_only(raw: dict[str, Any]) -> bool:
    dd = raw.get("drawdown") or {}
    if isinstance(dd, dict) and "notify_only" in dd:
        return bool(dd["notify_only"])
    return bool(raw.get("drawdown_notify_only", True))


def parse_volatile_exempt(raw: dict[str, Any]) -> VolatileExempt:
    cfg = raw.get("drawdown_volatile_exempt") or {}
    if not cfg:
        legacy = raw.get("drawdown_tiers", {})
        if isinstance(legacy, dict):
            cfg = legacy.get("volatile_exempt") or legacy.get("halt_excludes") or {}
    return VolatileExempt(
        pipelines=[str(p) for p in cfg.get("pipelines", [])],
        correlation_groups=[str(g) for g in cfg.get("correlation_groups", [])],
        venues=[str(v).lower() for v in cfg.get("venues", [])],
        note=str(cfg.get("note", "")),
    )


def parse_drawdown_tiers(raw: dict[str, Any]) -> list[DrawdownTier]:
    tiers_cfg = raw.get("drawdown_tiers") or []
    out: list[DrawdownTier] = []
    if isinstance(tiers_cfg, dict):
        mapping = [
            ("alert", "notify_operator", "MEDIUM"),
            ("soft_pause", "notify_operator", "HIGH"),
            ("reduce", "notify_operator", "HIGH"),
            ("critical", "notify_critical_continue", "CRITICAL"),
            ("halt", "notify_critical_continue", "CRITICAL"),
        ]
        for key, action, sev in mapping:
            pct = tiers_cfg.get(key)
            if pct is not None and not isinstance(pct, dict):
                out.append(DrawdownTier(pct=float(pct), action=action, severity=sev))
        return sorted(out, key=lambda t: t.pct)

    for entry in tiers_cfg:
        if not isinstance(entry, dict) or "pct" not in entry:
            continue
        pct = float(entry["pct"])
        action = str(entry.get("action", "notify_operator"))
        if action not in _NOTIFY_ACTIONS:
            action = "notify_critical_continue" if pct >= 10.0 else "notify_operator"
        out.append(
            DrawdownTier(
                pct=pct,
                action=action,
                severity=str(entry.get("severity", _DEFAULT_SEVERITY.get(pct, "HIGH"))),
                scope=str(entry.get("scope", "portfolio")),
                note=str(entry.get("note", "")),
            )
        )
    return sorted(out, key=lambda t: t.pct)


class DrawdownTierEngine:
    """Drawdown tiers alert only — autonomous trading continues (no pause/halt gates)."""

    def __init__(self, policy_raw: dict[str, Any]) -> None:
        self.tiers = parse_drawdown_tiers(policy_raw)
        self.notify_only = drawdown_notify_only(policy_raw)
        self.volatile_exempt = parse_volatile_exempt(policy_raw)
        self.correlation_groups: dict[str, list[str]] = (
            policy_raw.get("portfolio_risk", {}).get("correlation_groups") or {}
        )

    def is_volatile_exempt(self, trade: TradeRequest) -> bool:
        sid = trade.strategy_id or ""
        venue = trade.venue.lower()
        if sid and sid in self.volatile_exempt.pipelines:
            return True
        if venue in self.volatile_exempt.venues:
            return True
        if sid:
            for group in self.volatile_exempt.correlation_groups:
                if sid in self.correlation_groups.get(group, []):
                    return True
        return False

    def active_tier(self, drawdown_pct: float) -> DrawdownTier | None:
        active: DrawdownTier | None = None
        for tier in self.tiers:
            if drawdown_pct >= tier.pct:
                active = tier
        return active

    def tiers_newly_crossed(
        self, previous_pct: float, current_pct: float
    ) -> list[DrawdownTier]:
        """Tiers whose boundary was crossed upward since previous_pct."""
        if current_pct <= previous_pct:
            return []
        return [t for t in self.tiers if current_pct >= t.pct > previous_pct]

    def build_alert(self, tier: DrawdownTier, drawdown_pct: float) -> DrawdownAlert:
        msg = (
            f"Portfolio drawdown {drawdown_pct:.2f}% crossed {tier.pct}% tier "
            f"({tier.action}) — trading continues autonomously; no operator ack required"
        )
        return DrawdownAlert(
            tier_pct=tier.pct,
            action=tier.action,
            severity=tier.severity,
            drawdown_pct=drawdown_pct,
            message=msg,
            trading_continues=True,
        )

    def check_trade(self, drawdown_pct: float, trade: TradeRequest) -> tuple[str, str] | None:
        """Never deny trades on portfolio drawdown tiers (notify-only policy)."""
        return None
