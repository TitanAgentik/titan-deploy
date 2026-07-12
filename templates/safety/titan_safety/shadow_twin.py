"""Shadow twin — parallel shadow path with divergence bounds; gates live deploys.

Always-on companion when tier4 shadow_twin.enabled — compares live vs shadow metrics.
Does NOT auto-promote; blocks live deploy when divergence exceeds bounds.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .tier4_gate import tier4_active, tier4_cfg


@dataclass
class ShadowMetrics:
    pipeline_id: str
    live_sharpe: float = 0.0
    shadow_sharpe: float = 0.0
    live_pnl_usd: float = 0.0
    shadow_pnl_usd: float = 0.0
    fill_count_live: int = 0
    fill_count_shadow: int = 0

    @property
    def sharpe_divergence_pct(self) -> float:
        if self.shadow_sharpe == 0:
            return 100.0 if self.live_sharpe != 0 else 0.0
        return abs(self.live_sharpe - self.shadow_sharpe) / abs(self.shadow_sharpe) * 100.0


@dataclass
class ShadowTwinVerdict:
    decision: str  # ALLOW | DENY | ADVISORY
    reason: str
    code: str = ""
    divergence_pct: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShadowTwin:
    """Compare live lane metrics to shadow twin; gate deploys on divergence."""

    def __init__(
        self,
        policy_raw: dict[str, Any] | None = None,
        state_dir: Path | None = None,
    ) -> None:
        self.policy_raw = policy_raw or {}
        self.cfg = tier4_cfg(self.policy_raw).get("shadow_twin") or {}
        self.state_dir = state_dir or (Path.home() / ".openclaw" / "safety")
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        if not tier4_active(self.policy_raw):
            return False
        return bool(self.cfg.get("enabled", False))

    def record_metrics(self, metrics: ShadowMetrics) -> None:
        path = self.state_dir / "shadow_twin_metrics.jsonl"
        row = {**asdict(metrics), "ts": time.time()}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    def check_deploy(self, metrics: ShadowMetrics) -> ShadowTwinVerdict:
        if not self.is_enabled():
            return ShadowTwinVerdict(
                decision="ADVISORY",
                reason="shadow twin disabled — no deploy gate",
                code="SHADOW_TWIN_OFF",
            )

        max_div = float(self.cfg.get("max_divergence_pct", 15.0))
        div = metrics.sharpe_divergence_pct
        block = bool(self.cfg.get("block_live_on_divergence", True))

        if div > max_div:
            if block:
                return ShadowTwinVerdict(
                    decision="DENY",
                    reason=(
                        f"shadow divergence {div:.1f}% exceeds cap {max_div}% "
                        f"— live deploy blocked"
                    ),
                    code="SHADOW_DIVERGENCE",
                    divergence_pct=div,
                    details={"pipeline_id": metrics.pipeline_id},
                )
            return ShadowTwinVerdict(
                decision="ADVISORY",
                reason=f"shadow divergence {div:.1f}% exceeds cap — advisory only",
                code="SHADOW_DIVERGENCE_WARN",
                divergence_pct=div,
            )

        return ShadowTwinVerdict(
            decision="ALLOW",
            reason="shadow twin within divergence bounds",
            code="OK",
            divergence_pct=div,
        )

    def health(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "tier4_active": tier4_active(self.policy_raw),
            "max_divergence_pct": self.cfg.get("max_divergence_pct", 15.0),
            "block_live_on_divergence": self.cfg.get("block_live_on_divergence", True),
        }
