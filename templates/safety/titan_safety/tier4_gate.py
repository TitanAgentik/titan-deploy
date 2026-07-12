"""Tier 4 ultimate gate — only active when tiers 0–3 complete + tier4.enabled.

Does NOT enable live capital. Evolution remains shadow-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Tier4Status:
    enabled: bool
    active: bool
    missing_prerequisites: list[str]
    tier_checklist: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "active": self.active,
            "missing_prerequisites": self.missing_prerequisites,
            "tier_checklist": self.tier_checklist,
        }


def tier4_cfg(policy_raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": False,
        "requires_tiers": [0, 1, 2, 3],
        "tier_checklist": {
            "tier0_complete": False,
            "tier1_complete": False,
            "tier2_complete": False,
            "tier3_complete": False,
        },
        "shadow_twin": {
            "enabled": False,
            "max_divergence_pct": 15.0,
            "block_live_on_divergence": True,
        },
        "multi_pop": {
            "rtt_probe_interval_s": 30,
            "unhealthy_rtt_p95_ms": 50.0,
            "failover_enabled": True,
        },
        "intent_solver": {
            "enabled": False,
            "stub_submit": True,
            "networks": [],
        },
        "mev_tip_optimizer": {
            "enabled": False,
            "advisory_only": True,
            "max_tip_bps": 40.0,
        },
        "red_team_continuous": {
            "enabled": False,
            "interval_minutes": 60,
        },
        "portfolio_construction": {
            "borrow_rate_cap_annual_pct": 25.0,
            "funding_rate_cap_8h_pct": 0.15,
            "capacity_curve_enabled": True,
        },
        "note": "Tier 4 scaffold — operator must complete tiers 0–3 checklist before enable",
    }
    raw = (policy_raw or {}).get("tier4_ultimate") or {}
    cfg = dict(defaults)
    cfg.update(raw)
    checklist = dict(defaults["tier_checklist"])
    checklist.update(raw.get("tier_checklist") or {})
    cfg["tier_checklist"] = checklist
    return cfg


def _tier_complete(policy_raw: dict[str, Any], tier: int, checklist: dict[str, bool]) -> bool:
    key = f"tier{tier}_complete"
    if not checklist.get(key, False):
        return False
    raw = policy_raw or {}
    if tier == 0:
        return bool((raw.get("tier0_money_path") or {}).get("enabled", False))
    if tier == 1:
        profile = str(raw.get("capital_profile", "paper")).lower()
        t1 = raw.get("tier1_capital_risk") or {}
        live = (t1.get("profiles") or {}).get("live") or {}
        return profile == "live" and live.get("drawdown_notify_only") is False
    if tier == 2:
        t2 = raw.get("tier2_promotion_quality") or {}
        return bool((t2.get("promotion_registry") or {}).get("enabled", False))
    if tier == 3:
        return bool((raw.get("security_ops") or {}).get("enabled", False))
    return False


def tier4_prerequisites(policy_raw: dict[str, Any] | None) -> Tier4Status:
    cfg = tier4_cfg(policy_raw)
    checklist = cfg.get("tier_checklist") or {}
    requires = [int(t) for t in cfg.get("requires_tiers", [0, 1, 2, 3])]
    missing: list[str] = []
    for tier in requires:
        key = f"tier{tier}_complete"
        if not checklist.get(key, False):
            missing.append(f"{key} not marked complete in policy")
        elif not _tier_complete(policy_raw or {}, tier, checklist):
            missing.append(f"tier{tier} policy preconditions not met")

    enabled = bool(cfg.get("enabled", False))
    active = enabled and not missing
    return Tier4Status(
        enabled=enabled,
        active=active,
        missing_prerequisites=missing,
        tier_checklist={k: bool(v) for k, v in checklist.items()},
    )


def tier4_active(policy_raw: dict[str, Any] | None) -> bool:
    return tier4_prerequisites(policy_raw).active
