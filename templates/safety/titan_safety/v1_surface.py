"""v1 surface lockdown — enforce catalog ≠ checklist at runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


DEFAULT_LOCKDOWN_PATH = Path.home() / ".openclaw" / "risk_kernel" / "v1_surface_lockdown.yaml"


@dataclass
class V1SurfaceConfig:
    enabled: bool = True
    chain: str = "hyperliquid"
    venue_class: str = "perp_dex"
    allowed_venues: list[str] = field(default_factory=lambda: ["hyperliquid", "paper"])
    max_active_strategies: int = 2
    allowed_pipeline_ids: list[str] = field(default_factory=list)
    blocked_pipeline_ids: list[str] = field(
        default_factory=lambda: ["P22", "P12", "P29", "P30"]
    )
    disabled: dict[str, bool] = field(
        default_factory=lambda: {
            "memecoin_p22": True,
            "flash_loans": True,
            "predatory_honeypots": True,
            "quantum_inspired_live": True,
            "multi_cex_allowlists": True,
            "full_edge_mesh_5_pop": True,
        }
    )
    edge_mesh_mode: str = "single_pop"
    allowed_pops: list[str] = field(default_factory=lambda: ["EDGE-FRA"])

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> V1SurfaceConfig:
        if not raw:
            return cls()
        disabled_raw = raw.get("disabled_for_v1") or {}
        edge = raw.get("edge_mesh") or {}
        return cls(
            enabled=bool(raw.get("enabled", True)),
            chain=str(raw.get("chain", "hyperliquid")),
            venue_class=str(raw.get("venue_class", "perp_dex")),
            allowed_venues=[str(v) for v in (raw.get("allowed_venues") or ["hyperliquid", "paper"])],
            max_active_strategies=int(raw.get("max_active_strategies", 2)),
            allowed_pipeline_ids=[str(p) for p in (raw.get("allowed_pipeline_ids") or [])],
            blocked_pipeline_ids=[
                str(p) for p in (raw.get("blocked_pipeline_ids") or ["P22", "P12", "P29", "P30"])
            ],
            disabled={
                "memecoin_p22": bool(disabled_raw.get("memecoin_p22", True)),
                "flash_loans": bool(disabled_raw.get("flash_loans", True)),
                "predatory_honeypots": bool(disabled_raw.get("predatory_honeypots", True)),
                "quantum_inspired_live": bool(disabled_raw.get("quantum_inspired_live", True)),
                "multi_cex_allowlists": bool(disabled_raw.get("multi_cex_allowlists", True)),
                "full_edge_mesh_5_pop": bool(disabled_raw.get("full_edge_mesh_5_pop", True)),
            },
            edge_mesh_mode=str(edge.get("mode", "single_pop")),
            allowed_pops=[str(p) for p in (edge.get("allowed_pops") or ["EDGE-FRA"])],
        )


@dataclass
class SurfaceCheckResult:
    allowed: bool
    reason: str
    surface: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "surface": self.surface}


def load_v1_surface_config(path: Path | None = None) -> V1SurfaceConfig:
    if yaml is None:
        return V1SurfaceConfig()
    p = path or Path(
        os.environ.get("TITAN_V1_SURFACE", str(DEFAULT_LOCKDOWN_PATH))
    ).expanduser()
    if not p.exists():
        repo_fallback = Path(__file__).resolve().parents[2] / "risk_kernel" / "v1_surface_lockdown.yaml"
        p = repo_fallback if repo_fallback.exists() else p
    if not p.exists():
        return V1SurfaceConfig()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return V1SurfaceConfig()
    return V1SurfaceConfig.from_raw(data)


class V1SurfaceLockdown:
    """Runtime enforcement for v1 operator surface area."""

    def __init__(self, config: V1SurfaceConfig | None = None) -> None:
        self.config = config or load_v1_surface_config()

    @classmethod
    def from_path(cls, path: Path | None = None) -> V1SurfaceLockdown:
        return cls(load_v1_surface_config(path))

    def is_active(self) -> bool:
        return self.config.enabled

    def check_pipeline(self, pipeline_id: str) -> SurfaceCheckResult:
        if not self.config.enabled:
            return SurfaceCheckResult(True, "v1 lockdown disabled")
        pid = str(pipeline_id)
        if pid in self.config.blocked_pipeline_ids:
            return SurfaceCheckResult(
                False, f"pipeline {pid} blocked for v1 surface lockdown"
            )
        if self.config.allowed_pipeline_ids and pid not in self.config.allowed_pipeline_ids:
            return SurfaceCheckResult(
                False, f"pipeline {pid} not in v1 allowlist"
            )
        if pid == "P22" and self.config.disabled.get("memecoin_p22", True):
            return SurfaceCheckResult(False, "P22 memecoin disabled for v1")
        return SurfaceCheckResult(True, "pipeline allowed")

    def check_venue(self, venue: str) -> SurfaceCheckResult:
        if not self.config.enabled:
            return SurfaceCheckResult(True, "v1 lockdown disabled")
        v = venue.lower()
        if self.config.disabled.get("multi_cex_allowlists", True):
            cex_markers = ("binance", "okx", "bybit", "coinbase", "kraken", "cex")
            if any(m in v for m in cex_markers):
                return SurfaceCheckResult(False, f"CEX venue {venue} blocked for v1")
        allowed = {a.lower() for a in self.config.allowed_venues}
        if v not in allowed and "paper" not in allowed:
            return SurfaceCheckResult(False, f"venue {venue} not in v1 allowlist")
        if v not in allowed and v != "paper":
            return SurfaceCheckResult(False, f"venue {venue} not in v1 allowlist")
        return SurfaceCheckResult(True, "venue allowed")

    def check_edge_pop(self, pop_id: str) -> SurfaceCheckResult:
        if not self.config.enabled:
            return SurfaceCheckResult(True, "v1 lockdown disabled")
        if self.config.disabled.get("full_edge_mesh_5_pop", True):
            if pop_id not in self.config.allowed_pops:
                return SurfaceCheckResult(
                    False,
                    f"PoP {pop_id} not allowed — v1 mode {self.config.edge_mesh_mode}",
                )
        return SurfaceCheckResult(True, "PoP allowed")

    def check_flash_loan(self) -> SurfaceCheckResult:
        if self.config.enabled and self.config.disabled.get("flash_loans", True):
            return SurfaceCheckResult(False, "flash loans disabled for v1")
        return SurfaceCheckResult(True, "flash loans allowed")

    def check_quantum_inspired_live(self) -> SurfaceCheckResult:
        if self.config.enabled and self.config.disabled.get("quantum_inspired_live", True):
            return SurfaceCheckResult(False, "quantum-inspired live path disabled for v1")
        return SurfaceCheckResult(True, "QI advisory-only")

    def max_active_strategies(self) -> int:
        if not self.config.enabled:
            return 4
        return self.config.max_active_strategies

    def apply_allocator_limits(self, max_active: int) -> int:
        if not self.config.enabled:
            return max_active
        return min(max_active, self.config.max_active_strategies)

    def status(self) -> dict[str, Any]:
        c = self.config
        return {
            "enabled": c.enabled,
            "chain": c.chain,
            "venue_class": c.venue_class,
            "max_active_strategies": c.max_active_strategies,
            "blocked_pipelines": c.blocked_pipeline_ids,
            "allowed_venues": c.allowed_venues,
            "edge_mesh_mode": c.edge_mesh_mode,
            "disabled": c.disabled,
        }
