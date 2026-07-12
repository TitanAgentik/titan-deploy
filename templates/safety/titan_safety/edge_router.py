"""Edge PoP routing — venue/strategy → lowest-latency PoP from edge_mesh.yaml.

Tier 4: measured RTT probes, health tracking, failover when PoP unhealthy.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .tier4_gate import tier4_active, tier4_cfg
from .v1_surface import V1SurfaceLockdown, load_v1_surface_config

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class PopInfo:
    pop_id: str
    wireguard_ip: str = ""
    worker_port: int = 19100
    rtt_target_p95_ms: float = 5.0
    roles: list[str] = field(default_factory=list)


@dataclass
class PopHealth:
    pop_id: str
    measured_rtt_p95_ms: float = 0.0
    healthy: bool = True
    last_probe_ts: float = 0.0
    probe_source: str = "stub"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pop_id": self.pop_id,
            "measured_rtt_p95_ms": self.measured_rtt_p95_ms,
            "healthy": self.healthy,
            "last_probe_ts": self.last_probe_ts,
            "probe_source": self.probe_source,
        }


@dataclass
class RouteDecision:
    primary: str
    fallback: list[str]
    wireguard_ip: str
    worker_url: str
    reason: str
    paper_latency_faithful: bool = True
    rtt_ms: float | None = None
    failover_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "wireguard_ip": self.wireguard_ip,
            "worker_url": self.worker_url,
            "reason": self.reason,
            "paper_latency_faithful": self.paper_latency_faithful,
            "rtt_ms": self.rtt_ms,
            "failover_applied": self.failover_applied,
        }


def _expand(path: str) -> Path:
    return Path(path.replace("~", str(Path.home()))).expanduser()


def load_edge_mesh(path: Path | None = None) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required for edge mesh routing")
    if path is None:
        path = _expand(os.environ.get("TITAN_EDGE_MESH", "~/.openclaw/infra/edge_mesh.yaml"))
    if not path.exists():
        raise FileNotFoundError(f"edge mesh config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid edge mesh yaml: {path}")
    return data


class EdgeRouter:
    def __init__(
        self,
        mesh: dict[str, Any],
        v1_lockdown: V1SurfaceLockdown | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> None:
        self.mesh = mesh
        self.v1 = v1_lockdown or V1SurfaceLockdown(load_v1_surface_config())
        self.policy_raw = policy_raw or {}
        self._pop_health: dict[str, PopHealth] = {}
        self.pops: dict[str, PopInfo] = {}
        for pop_id, cfg in (mesh.get("pops") or {}).items():
            if not isinstance(cfg, dict):
                continue
            self.pops[str(pop_id)] = PopInfo(
                pop_id=str(pop_id),
                wireguard_ip=str(cfg.get("wireguard_ip", "")),
                worker_port=int(cfg.get("worker_port", 19100)),
                rtt_target_p95_ms=float(cfg.get("rtt_target_p95_ms", 5)),
                roles=list(cfg.get("roles") or []),
            )
        self.venue_routing: dict[str, str] = {
            str(k).lower(): str(v) for k, v in (mesh.get("venue_routing") or {}).items()
        }
        self.strategy_routing: dict[str, dict[str, Any]] = mesh.get("strategy_routing") or {}
        self.paper_faithful = bool((mesh.get("paper_trading") or {}).get("latency_faithful", True))

    @classmethod
    def from_path(
        cls,
        path: Path | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> EdgeRouter:
        return cls(load_edge_mesh(path), policy_raw=policy_raw)

    def _tier4_multi_pop_allowed(self) -> bool:
        return tier4_active(self.policy_raw)

    def measure_rtt(
        self,
        pop_id: str,
        *,
        measured_ms: float | None = None,
        force: bool = False,
    ) -> PopHealth:
        """RTT probe hook — STUB returns target p95 until wireguard ICMP/HTTP probe wired."""
        if measured_ms is None and not force:
            cached = self._pop_health.get(pop_id)
            if cached is not None:
                return cached
        info = self.pops.get(pop_id)
        target = info.rtt_target_p95_ms if info else 5.0
        rtt = measured_ms if measured_ms is not None else target
        cfg = tier4_cfg(self.policy_raw).get("multi_pop") or {}
        unhealthy_threshold = float(cfg.get("unhealthy_rtt_p95_ms", 50.0))
        healthy = rtt <= unhealthy_threshold
        health = PopHealth(
            pop_id=pop_id,
            measured_rtt_p95_ms=round(rtt, 3),
            healthy=healthy,
            last_probe_ts=time.time(),
            probe_source="measured" if measured_ms is not None else "stub_target",
        )
        self._pop_health[pop_id] = health
        return health

    def probe_all_pops(self) -> dict[str, PopHealth]:
        for pop_id in self.pops:
            self.measure_rtt(pop_id, force=True)
        return dict(self._pop_health)

    def pop_health(self, pop_id: str) -> PopHealth | None:
        return self._pop_health.get(pop_id)

    def _select_lowest_rtt(self, candidates: list[str]) -> str:
        if not candidates:
            return "EDGE-FRA"
        scored: list[tuple[float, str]] = []
        for pop_id in candidates:
            h = self._pop_health.get(pop_id)
            if h is None:
                h = self.measure_rtt(pop_id)
            if not h.healthy:
                continue
            scored.append((h.measured_rtt_p95_ms, pop_id))
        if not scored:
            return candidates[0]
        scored.sort(key=lambda x: x[0])
        return scored[0][1]

    def _pop_url(self, pop_id: str) -> tuple[str, str]:
        info = self.pops.get(pop_id)
        if not info or not info.wireguard_ip:
            return pop_id, f"http://127.0.0.1:{info.worker_port if info else 19100}"
        return info.wireguard_ip, f"http://{info.wireguard_ip}:{info.worker_port}"

    def route(
        self,
        venue: str = "",
        strategy_id: str = "",
        *,
        prefer: str | None = None,
    ) -> RouteDecision:
        venue_l = venue.lower()
        primary = prefer or self.venue_routing.get(venue_l, "")
        fallback: list[str] = []
        reason = "venue_routing"

        if strategy_id and strategy_id in self.strategy_routing:
            sr = self.strategy_routing[strategy_id]
            primary = str(sr.get("primary") or primary or "EDGE-FRA")
            fallback = [str(p) for p in sr.get("fallback") or []]
            reason = f"strategy_routing:{strategy_id}"
        elif not primary:
            primary = "EDGE-FRA"
            reason = "default_pop"

        if primary not in self.pops:
            primary = "EDGE-FRA" if "EDGE-FRA" in self.pops else next(iter(self.pops), "EDGE-FRA")

        tier4_mesh = self._tier4_multi_pop_allowed()
        if self.v1.is_active() and self.v1.config.disabled.get("full_edge_mesh_5_pop", True):
            if not tier4_mesh:
                allowed = self.v1.config.allowed_pops
                if allowed and primary not in allowed:
                    primary = allowed[0]
                    reason = f"v1_single_pop:{primary}"
                fallback = [p for p in fallback if p in allowed]
            else:
                reason = f"tier4_full_mesh:{reason}"

        pop_check = self.v1.check_edge_pop(primary, tier4_active=tier4_mesh)
        if not pop_check.allowed and self.v1.config.allowed_pops and not tier4_mesh:
            primary = self.v1.config.allowed_pops[0]
            reason = pop_check.reason

        failover_applied = False
        multi_cfg = tier4_cfg(self.policy_raw).get("multi_pop") or {}
        if tier4_mesh and multi_cfg.get("failover_enabled", True):
            health = self._pop_health.get(primary)
            if health is None:
                health = self.measure_rtt(primary)
            if not health.healthy:
                candidates = list(self.pops.keys())
                new_primary = self._select_lowest_rtt(candidates)
                if new_primary != primary:
                    failover_applied = True
                    reason = f"failover:{primary}->{new_primary}"
                    primary = new_primary
            elif multi_cfg.get("rtt_routing", True):
                all_candidates = list({primary, *fallback} & set(self.pops.keys()))
                if len(all_candidates) > 1:
                    best = self._select_lowest_rtt(all_candidates)
                    if best != primary:
                        reason = f"rtt_routing:{primary}->{best}"
                        primary = best

        wg_ip, worker_url = self._pop_url(primary)
        rtt_ms = None
        h = self._pop_health.get(primary)
        if h:
            rtt_ms = h.measured_rtt_p95_ms
        return RouteDecision(
            primary=primary,
            fallback=[p for p in fallback if p != primary and p in self.pops],
            wireguard_ip=wg_ip,
            worker_url=worker_url,
            reason=reason,
            paper_latency_faithful=self.paper_faithful,
            rtt_ms=rtt_ms,
            failover_applied=failover_applied,
        )

    def list_pops(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for p in self.pops.values():
            row: dict[str, Any] = {
                "id": p.pop_id,
                "wireguard_ip": p.wireguard_ip,
                "worker_port": p.worker_port,
                "rtt_target_p95_ms": p.rtt_target_p95_ms,
                "roles": p.roles,
            }
            health = self._pop_health.get(p.pop_id)
            if health:
                row["health"] = health.to_dict()
            out.append(row)
        return out
