"""Edge PoP routing — venue/strategy → lowest-latency PoP from edge_mesh.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
class RouteDecision:
    primary: str
    fallback: list[str]
    wireguard_ip: str
    worker_url: str
    reason: str
    paper_latency_faithful: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "wireguard_ip": self.wireguard_ip,
            "worker_url": self.worker_url,
            "reason": self.reason,
            "paper_latency_faithful": self.paper_latency_faithful,
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
    def __init__(self, mesh: dict[str, Any]) -> None:
        self.mesh = mesh
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
    def from_path(cls, path: Path | None = None) -> EdgeRouter:
        return cls(load_edge_mesh(path))

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

        wg_ip, worker_url = self._pop_url(primary)
        return RouteDecision(
            primary=primary,
            fallback=[p for p in fallback if p != primary and p in self.pops],
            wireguard_ip=wg_ip,
            worker_url=worker_url,
            reason=reason,
            paper_latency_faithful=self.paper_faithful,
        )

    def list_pops(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.pop_id,
                "wireguard_ip": p.wireguard_ip,
                "worker_port": p.worker_port,
                "rtt_target_p95_ms": p.rtt_target_p95_ms,
                "roles": p.roles,
            }
            for p in self.pops.values()
        ]
