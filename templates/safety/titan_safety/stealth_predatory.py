"""Ghost evasion + predatory engagement gates — detect them, stay invisible."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .policy_loader import Policy, capital_profile_of

PAPER_VENUES = frozenset({"paper", "mock", "test"})

DEFAULT_FORBIDDEN_VENUES = [
    "public_rpc",
    "public_mempool",
    "eth_public_rpc",
    "solana_public_rpc",
    "alchemy_public",
    "infura_public",
    "quicknode_public",
    "helius_public_unshielded",
    "jupiter_public_api",
    "binance_public",
    "cex_api_direct",
]

DEFAULT_SHIELDED_VENUES = [
    "uniswap_v3",
    "curve",
    "aave_v3",
    "hyperliquid",
    "solana_jupiter",
    "solana_pumpfun",
    "solana_pumpswap",
    "jito",
    "flashbots_protect",
    "intent_solver",
    "cowswap",
    "uniswapx",
    "mev_share",
    "across_intent",
]

DEFAULT_STEALTH_PIPELINES = ["P22", "P29", "P12", "P30"]

DEFAULT_PIPELINE_REQUIRED_VENUES: dict[str, list[str]] = {
    "P22": ["jito", "solana_pumpfun", "solana_pumpswap"],
    "P29": ["flashbots_protect", "jito", "intent_solver", "mev_share"],
    "P12": ["intent_solver", "uniswapx", "cowswap", "across_intent"],
    "P30": ["flashbots_protect", "intent_solver"],
}


class StealthTrade(Protocol):
    venue: str
    strategy_id: str


@dataclass
class StealthCheckResult:
    decision: str
    reason: str
    code: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "code": self.code,
            "details": self.details,
        }


@dataclass
class GhostEvasionConfig:
    enabled: bool = True
    require_shielded_path_live: bool = True
    forbidden_venues: list[str] = field(default_factory=lambda: list(DEFAULT_FORBIDDEN_VENUES))
    shielded_venues: list[str] = field(default_factory=lambda: list(DEFAULT_SHIELDED_VENUES))
    stealth_pipelines: list[str] = field(default_factory=lambda: list(DEFAULT_STEALTH_PIPELINES))
    pipeline_required_venues: dict[str, list[str]] = field(
        default_factory=lambda: dict(DEFAULT_PIPELINE_REQUIRED_VENUES)
    )
    structural_invisibility_max_detection_pct: float = 1.0
    fingerprint_rotate_hours: int = 168
    traffic_jitter_enabled: bool = True
    hunt_mode_default: bool = True
    honeypot_armed_default: bool = True

    @classmethod
    def from_policy(cls, policy: Policy) -> GhostEvasionConfig:
        raw = (policy.raw or {}).get("ghost_evasion") or {}
        if not raw:
            sec = (policy.raw or {}).get("security_ops") or {}
            return cls(
                hunt_mode_default=bool(sec.get("hunt_mode_default", True)),
                honeypot_armed_default=bool(sec.get("honeypot_armed_default", True)),
            )
        pr_venues = raw.get("pipeline_required_venues") or DEFAULT_PIPELINE_REQUIRED_VENUES
        return cls(
            enabled=bool(raw.get("enabled", True)),
            require_shielded_path_live=bool(raw.get("require_shielded_path_live", True)),
            forbidden_venues=[str(v).lower() for v in raw.get("forbidden_venues", DEFAULT_FORBIDDEN_VENUES)],
            shielded_venues=[str(v).lower() for v in raw.get("shielded_venues", DEFAULT_SHIELDED_VENUES)],
            stealth_pipelines=[str(p) for p in raw.get("stealth_pipelines", DEFAULT_STEALTH_PIPELINES)],
            pipeline_required_venues={
                str(k): [str(v).lower() for v in vals]
                for k, vals in pr_venues.items()
            },
            structural_invisibility_max_detection_pct=float(
                raw.get("structural_invisibility_max_detection_pct", 1.0)
            ),
            fingerprint_rotate_hours=int(raw.get("fingerprint_rotate_hours", 168)),
            traffic_jitter_enabled=bool(raw.get("traffic_jitter_enabled", True)),
            hunt_mode_default=bool(raw.get("hunt_mode_default", True)),
            honeypot_armed_default=bool(raw.get("honeypot_armed_default", True)),
        )


def is_paper_venue(venue: str) -> bool:
    return venue.lower() in PAPER_VENUES


def is_live_capital(policy: Policy) -> bool:
    return capital_profile_of(policy) == "live"


def is_forbidden_venue(venue: str, config: GhostEvasionConfig) -> bool:
    v = venue.lower()
    return v in {x.lower() for x in config.forbidden_venues}


def is_shielded_venue(venue: str, config: GhostEvasionConfig) -> bool:
    v = venue.lower()
    return v in {x.lower() for x in config.shielded_venues}


def check_stealth_evasion(trade: StealthTrade, policy: Policy) -> StealthCheckResult | None:
    """Return DENY when evasion rules fail; None when check passes."""
    config = GhostEvasionConfig.from_policy(policy)
    if not config.enabled or not policy.enforce:
        return None

    venue = trade.venue.lower()

    if is_forbidden_venue(venue, config):
        return StealthCheckResult(
            decision="DENY",
            reason=f"Public/detectable path forbidden: {trade.venue}",
            code="STEALTH_PUBLIC_PATH",
            details={"venue": trade.venue, "pillar": "evasion"},
        )

    if is_paper_venue(venue):
        return None

    if config.require_shielded_path_live and is_live_capital(policy):
        if not is_shielded_venue(venue, config):
            return StealthCheckResult(
                decision="DENY",
                reason=(
                    f"Live capital requires MEV-shielded venue; {trade.venue} is not shielded "
                    "(no public RPC / CEX-direct / mempool broadcast)"
                ),
                code="STEALTH_UNSHIELDED_VENUE",
                details={"venue": trade.venue, "pillar": "evasion"},
            )

    sid = trade.strategy_id or ""
    if sid in config.stealth_pipelines:
        required = config.pipeline_required_venues.get(sid, [])
        if required and venue not in {r.lower() for r in required}:
            return StealthCheckResult(
                decision="DENY",
                reason=(
                    f"Stealth pipeline {sid} requires shielded route "
                    f"({', '.join(required)}); got {trade.venue}"
                ),
                code="STEALTH_PIPELINE_ROUTE",
                details={
                    "strategy_id": sid,
                    "venue": trade.venue,
                    "required_venues": required,
                    "pillar": "evasion",
                },
            )

    return None


def stealth_posture(policy: Policy | None = None) -> dict[str, Any]:
    """Structured posture for security_ops status / cockpit."""
    config = GhostEvasionConfig.from_policy(policy) if policy else GhostEvasionConfig()
    return {
        "enabled": config.enabled,
        "require_shielded_path_live": config.require_shielded_path_live,
        "structural_invisibility_max_detection_pct": config.structural_invisibility_max_detection_pct,
        "fingerprint_rotate_hours": config.fingerprint_rotate_hours,
        "traffic_jitter_enabled": config.traffic_jitter_enabled,
        "stealth_pipelines": config.stealth_pipelines,
        "forbidden_venue_count": len(config.forbidden_venues),
        "shielded_venue_count": len(config.shielded_venues),
        "doctrine": "detect_adversaries_profit_invisible",
        "controls": [
            "mev_shield_intents",
            "edge_rtt",
            "nostr_nip44",
            "fingerprint_rotate",
            "traffic_jitter",
            "structural_invisibility_gate",
        ],
    }


def predatory_posture(*, hunt_mode: bool, honeypot_armed: bool) -> dict[str, Any]:
    return {
        "hunt_mode": hunt_mode,
        "honeypot_armed": honeypot_armed,
        "stalking": "hunt" if hunt_mode else "idle",
        "predatory": "engaged" if honeypot_armed else "idle",
        "modules": [
            "mempool_stalk",
            "copy_trade_detect",
            "honeypot_lattice",
            "poison_fills",
            "graph_r1_fraud",
        ],
        "doctrine": "observe_classify_disrupt_under_kernel",
    }
