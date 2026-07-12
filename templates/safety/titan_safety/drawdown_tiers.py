"""Drawdown tier evaluation — notify-only (paper) or enforced (live)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .kernel import TradeRequest

if TYPE_CHECKING:
    from .kernel import RiskKernel, RiskKernelState

# Paper / shadow — alert only; trading continues.
_NOTIFY_ACTIONS = frozenset(
    {
        "notify_operator",
        "notify_continue",
        "notify_critical_continue",
        "alert_operator",
    }
)

# Live enforcement ladder (items 6 / tier1_capital_risk).
_ENFORCE_ACTIONS = frozenset(
    {
        "soft_de_gross",
        "hard_de_gross",
        "halt_new_risk",
        "halt_new_entries",
        "full_halt_flatten",
        "flatten",
        # Legacy names mapped to enforcement
        "soft_pause_new_entries",
        "reduce_exposure_50pct",
        "critical_alert_human_required",
        "full_halt_flatten",
    }
)

_LEGACY_NOTIFY_MAP = {
    "soft_pause_new_entries": "soft_de_gross",
    "reduce_exposure_50pct": "hard_de_gross",
    "critical_alert_human_required": "halt_new_risk",
    "full_halt_flatten": "full_halt_flatten",
}

_TIER_EXPOSURE_CAP = {
    "soft_de_gross": 75.0,
    "hard_de_gross": 50.0,
}

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
    enforced: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_pct": self.tier_pct,
            "action": self.action,
            "severity": self.severity,
            "drawdown_pct": self.drawdown_pct,
            "message": self.message,
            "trading_continues": self.trading_continues,
            "enforced": self.enforced,
        }


def drawdown_notify_only(raw: dict[str, Any]) -> bool:
    dd = raw.get("drawdown") or {}
    if isinstance(dd, dict) and "notify_only" in dd:
        return bool(dd["notify_only"])
    return bool(raw.get("drawdown_notify_only", True))


def normalize_tier_action(action: str, pct: float, notify_only: bool) -> str:
    action = str(action)
    if action in _LEGACY_NOTIFY_MAP:
        action = _LEGACY_NOTIFY_MAP[action]
    if notify_only:
        if action in _ENFORCE_ACTIONS:
            return "notify_critical_continue" if pct >= 10.0 else "notify_operator"
        return action if action in _NOTIFY_ACTIONS else "notify_operator"
    if action in _NOTIFY_ACTIONS:
        if pct >= 12.0:
            return "full_halt_flatten"
        if pct >= 8.0:
            return "halt_new_risk"
        if pct >= 5.0:
            return "hard_de_gross"
        if pct >= 2.0:
            return "soft_de_gross"
    return action


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
    notify_only = drawdown_notify_only(raw)
    tiers_cfg = raw.get("drawdown_tiers") or []
    out: list[DrawdownTier] = []
    if isinstance(tiers_cfg, dict):
        mapping = [
            ("alert", "notify_operator", "MEDIUM"),
            ("soft_pause", "soft_de_gross", "HIGH"),
            ("reduce", "hard_de_gross", "HIGH"),
            ("critical", "halt_new_risk", "CRITICAL"),
            ("halt", "full_halt_flatten", "CRITICAL"),
        ]
        for key, action, sev in mapping:
            pct = tiers_cfg.get(key)
            if pct is not None and not isinstance(pct, dict):
                out.append(
                    DrawdownTier(
                        pct=float(pct),
                        action=normalize_tier_action(action, float(pct), notify_only),
                        severity=sev,
                    )
                )
        return sorted(out, key=lambda t: t.pct)

    for entry in tiers_cfg:
        if not isinstance(entry, dict) or "pct" not in entry:
            continue
        pct = float(entry["pct"])
        action = normalize_tier_action(
            str(entry.get("action", "notify_operator")), pct, notify_only
        )
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


def is_risk_increasing_trade(trade: TradeRequest, positions: dict[str, Any]) -> bool:
    """True when trade adds net exposure (not a de-risk / close)."""
    side = trade.side.lower()
    if side in ("sell", "short", "close", "reduce"):
        return False
    key = f"{trade.venue}:{trade.contract}"
    pos = positions.get(key)
    if pos is not None:
        notional = getattr(pos, "notional_usd", None)
        if notional is None and isinstance(pos, dict):
            notional = float(pos.get("notional_usd", 0))
        else:
            notional = float(notional or 0)
        if notional < 0 and side in ("buy", "long"):
            return abs(trade.notional_usd) > abs(notional)
        if notional > 0 and side in ("sell", "short"):
            return False
    return True


class DrawdownTierEngine:
    """Drawdown tiers — notify-only (paper) or enforce de-gross / halt / flatten (live)."""

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
        if current_pct <= previous_pct:
            return []
        return [t for t in self.tiers if current_pct >= t.pct > previous_pct]

    def build_alert(self, tier: DrawdownTier, drawdown_pct: float) -> DrawdownAlert:
        if self.notify_only:
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
                enforced=False,
            )
        msg = (
            f"Portfolio drawdown {drawdown_pct:.2f}% crossed {tier.pct}% tier "
            f"({tier.action}) — ENFORCED"
        )
        continues = tier.action in ("soft_de_gross", "hard_de_gross")
        return DrawdownAlert(
            tier_pct=tier.pct,
            action=tier.action,
            severity=tier.severity,
            drawdown_pct=drawdown_pct,
            message=msg,
            trading_continues=continues,
            enforced=True,
        )

    def apply_tier_enforcement(
        self,
        state: RiskKernelState,
        drawdown_pct: float,
        kernel: RiskKernel | None = None,
    ) -> dict[str, Any]:
        """Apply kernel state changes for active drawdown tier (live profile only)."""
        if self.notify_only:
            return {"enforced": False, "action": None}

        tier = self.active_tier(drawdown_pct)
        if tier is None:
            state.safe_mode_exposure_cap_pct = None
            state.halt_new_entries = False
            state.save()
            return {"enforced": False, "action": None, "drawdown_pct": drawdown_pct}

        action = tier.action
        result: dict[str, Any] = {
            "enforced": True,
            "action": action,
            "tier_pct": tier.pct,
            "drawdown_pct": drawdown_pct,
        }

        if action == "soft_de_gross":
            state.safe_mode_exposure_cap_pct = _TIER_EXPOSURE_CAP["soft_de_gross"]
            state.halt_new_entries = False
        elif action == "hard_de_gross":
            state.safe_mode_exposure_cap_pct = _TIER_EXPOSURE_CAP["hard_de_gross"]
            state.halt_new_entries = False
        elif action in ("halt_new_risk", "halt_new_entries"):
            state.halt_new_entries = True
        elif action in ("full_halt_flatten", "flatten"):
            state.halt_new_entries = True
            if kernel is not None:
                flatten = kernel.trigger_flatten(revoke_keys=False)
                result["flatten"] = flatten
            else:
                state.halted = True
                state.flatten_requested = True

        state.save()
        return result

    def check_trade(
        self,
        drawdown_pct: float,
        trade: TradeRequest,
        state: RiskKernelState | None = None,
    ) -> tuple[str, str] | None:
        """Return (code, reason) to DENY when live enforcement active."""
        if self.notify_only:
            return None
        if self.is_volatile_exempt(trade):
            return None

        tier = self.active_tier(drawdown_pct)
        if tier is None:
            return None

        positions = state.positions if state is not None else {}

        if tier.action in ("full_halt_flatten", "flatten"):
            return (
                "DRAWDOWN_FLATTEN",
                f"Drawdown {drawdown_pct:.1f}% >= {tier.pct}% — flatten/halt active",
            )

        if tier.action in ("halt_new_risk", "halt_new_entries"):
            if state is not None and getattr(state, "halt_new_entries", False):
                if is_risk_increasing_trade(trade, positions):
                    return (
                        "DRAWDOWN_HALT_NEW_RISK",
                        f"Drawdown {drawdown_pct:.1f}% — no new risk until recovery",
                    )
            elif is_risk_increasing_trade(trade, positions):
                return (
                    "DRAWDOWN_HALT_NEW_RISK",
                    f"Drawdown {drawdown_pct:.1f}% >= {tier.pct}% — new risk halted",
                )

        return None
