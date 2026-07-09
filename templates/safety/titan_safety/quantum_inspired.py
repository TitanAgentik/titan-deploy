"""Quantum-inspired lane selection — offline classical QUBO + simulated annealing.

advisory_only: true
live_path: false
backend: classical_sa

No cloud QPU, no quantum.enabled policy changes, no live execution gate wiring.
Compares against fractional-Kelly ``CapitalAllocator`` for R&D / offline advisory use.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Any

from .allocator import AllocatorConfig, CapitalAllocator, LaneEdge

QMatrix = dict[tuple[int, int], float]


@dataclass
class QiConfig:
    k: int = 4
    risk_lambda: float = 1.0
    cluster_penalty: float = 2.0
    cardinality_lambda: float = 5.0
    seed: int = 42
    sweeps: int = 5000
    t0: float = 10.0
    t_min: float = 0.01
    min_net_bps: float = 1.0
    min_trades: int = 100

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> QiConfig:
        r = raw or {}
        qi = r.get("quantum_inspired", r)
        d = cls()
        return cls(
            k=int(qi.get("k", d.k)),
            risk_lambda=float(qi.get("risk_lambda", d.risk_lambda)),
            cluster_penalty=float(qi.get("cluster_penalty", d.cluster_penalty)),
            cardinality_lambda=float(qi.get("cardinality_lambda", d.cardinality_lambda)),
            seed=int(qi.get("seed", d.seed)),
            sweeps=int(qi.get("sweeps", d.sweeps)),
            t0=float(qi.get("t0", d.t0)),
            t_min=float(qi.get("t_min", d.t_min)),
            min_net_bps=float(qi.get("min_net_bps", d.min_net_bps)),
            min_trades=int(qi.get("min_trades", d.min_trades)),
        )


@dataclass
class QiResult:
    selected_pipeline_ids: list[str]
    bitstring: str
    energy: float
    meta: dict[str, Any] = field(default_factory=dict)
    advisory_only: bool = True
    backend: str = "classical_sa"
    live_path: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _eligible_lanes(
    lanes: list[LaneEdge],
    *,
    min_net_bps: float,
    min_trades: int,
) -> tuple[list[LaneEdge], dict[str, str]]:
    eligible: list[LaneEdge] = []
    excluded: dict[str, str] = {}
    for lane in lanes:
        if lane.net_bps < min_net_bps:
            excluded[lane.pipeline_id] = f"net_bps {lane.net_bps:.1f} < min {min_net_bps}"
            continue
        if lane.trade_count < min_trades:
            excluded[lane.pipeline_id] = (
                f"trade_count {lane.trade_count} < min {min_trades}"
            )
            continue
        if lane.decaying:
            excluded[lane.pipeline_id] = "edge decaying"
            continue
        eligible.append(lane)
    return eligible, excluded


def _lane_reward(lane: LaneEdge) -> float:
    std = lane.return_std if lane.return_std > 0 else 0.02
    variance = std * std
    edge = lane.net_bps / 1e4
    return max(0.0, edge / variance)


def _lane_variance(lane: LaneEdge) -> float:
    std = lane.return_std if lane.return_std > 0 else 0.02
    return std * std


def build_lane_qubo(
    lanes: list[LaneEdge],
    *,
    k: int = 4,
    risk_lambda: float = 1.0,
    cluster_penalty: float = 2.0,
    cardinality_lambda: float = 5.0,
    min_net_bps: float = 1.0,
    min_trades: int = 100,
) -> tuple[QMatrix, dict[str, Any]]:
    """Build QUBO for lane subset selection.

    Minimize energy E(x) = x^T Q x with binary x_i per eligible lane.
    Rewards high edge/variance lanes, penalizes variance, cluster overlap,
    and deviation from cardinality k.
    """
    eligible, excluded = _eligible_lanes(
        lanes, min_net_bps=min_net_bps, min_trades=min_trades
    )
    n = len(eligible)
    Q: QMatrix = {}
    rewards = [_lane_reward(lane) for lane in eligible]
    max_reward = max(rewards) if rewards else 1.0

    for i, lane in enumerate(eligible):
        reward_norm = rewards[i] / max_reward if max_reward > 0 else 0.0
        h_i = -reward_norm
        h_i += risk_lambda * _lane_variance(lane)
        h_i += cardinality_lambda * (1.0 - 2.0 * k)
        Q[(i, i)] = Q.get((i, i), 0.0) + h_i

    for i in range(n):
        for j in range(i + 1, n):
            coeff = 2.0 * cardinality_lambda
            if eligible[i].cluster and eligible[i].cluster == eligible[j].cluster:
                coeff += cluster_penalty
            if coeff != 0.0:
                Q[(i, j)] = coeff

    meta = {
        "n_vars": n,
        "k": k,
        "risk_lambda": risk_lambda,
        "cluster_penalty": cluster_penalty,
        "cardinality_lambda": cardinality_lambda,
        "pipeline_ids": [lane.pipeline_id for lane in eligible],
        "clusters": [lane.cluster for lane in eligible],
        "rewards": [round(r, 6) for r in rewards],
        "excluded": excluded,
    }
    return Q, meta


def qubo_to_matrix(Q: QMatrix, n: int) -> list[list[float]]:
    """Expand upper-triangle Q dict to symmetric n×n matrix."""
    mat = [[0.0] * n for _ in range(n)]
    for (i, j), coeff in Q.items():
        mat[i][j] = coeff
        if i != j:
            mat[j][i] = coeff
    return mat


def qubo_energy(bits: list[int], Q: QMatrix) -> float:
    energy = 0.0
    for (i, j), coeff in Q.items():
        if i == j:
            energy += coeff * bits[i]
        else:
            energy += coeff * bits[i] * bits[j]
    return energy


def simulated_annealing(
    Q: QMatrix,
    *,
    seed: int = 42,
    sweeps: int = 5000,
    t0: float = 10.0,
    t_min: float = 0.01,
    n_vars: int | None = None,
) -> tuple[str, float]:
    """Classical Metropolis simulated annealing on a QUBO."""
    if n_vars is None:
        indices = [i for i, _ in Q.keys()] + [j for _, j in Q.keys()]
        n_vars = max(indices) + 1 if indices else 0
    if n_vars <= 0:
        return "", 0.0

    rng = random.Random(seed)
    bits = [rng.randint(0, 1) for _ in range(n_vars)]
    energy = qubo_energy(bits, Q)
    best_bits = bits[:]
    best_energy = energy

    if sweeps <= 0:
        return "".join(str(b) for b in best_bits), best_energy

    log_ratio = math.log(t_min / t0) if t0 > 0 and t_min > 0 else -1.0
    for step in range(sweeps):
        t = t0 * math.exp(log_ratio * step / max(sweeps - 1, 1))
        if t <= 0:
            break
        flip = rng.randrange(n_vars)
        bits[flip] = 1 - bits[flip]
        new_energy = qubo_energy(bits, Q)
        delta = new_energy - energy
        if delta <= 0 or (t > 0 and rng.random() < math.exp(-delta / t)):
            energy = new_energy
            if energy < best_energy:
                best_bits = bits[:]
                best_energy = energy
        else:
            bits[flip] = 1 - bits[flip]

    return "".join(str(b) for b in best_bits), best_energy


def decode_selection(bitstring: str, lanes: list[LaneEdge]) -> list[str]:
    """Map bitstring to selected pipeline_ids (1 = selected)."""
    selected: list[str] = []
    for i, bit in enumerate(bitstring):
        if bit == "1" and i < len(lanes):
            selected.append(lanes[i].pipeline_id)
    return selected


def synthetic_demo_lanes() -> list[LaneEdge]:
    """Synthetic lane edges for offline demo (P1/P5/P11/P12/P22/P29 style)."""
    return [
        LaneEdge("P1", net_bps=12.0, return_std=0.015, trade_count=1500, cluster="arb"),
        LaneEdge("P5", net_bps=18.0, return_std=0.012, trade_count=900, cluster="funding"),
        LaneEdge("P11", net_bps=22.0, return_std=0.025, trade_count=600, cluster="lp"),
        LaneEdge("P12", net_bps=28.0, return_std=0.02, trade_count=1100, cluster="mev_arb"),
        LaneEdge("P22", net_bps=35.0, return_std=0.04, trade_count=400, cluster="memecoin"),
        LaneEdge("P29", net_bps=30.0, return_std=0.03, trade_count=1200, cluster="mev_arb"),
    ]


def optimize_lanes(lanes: list[LaneEdge], config: QiConfig | None = None) -> QiResult:
    """Run QUBO + simulated annealing lane selection (advisory only)."""
    cfg = config or QiConfig()
    eligible, excluded = _eligible_lanes(
        lanes, min_net_bps=cfg.min_net_bps, min_trades=cfg.min_trades
    )
    if not eligible:
        return QiResult(
            selected_pipeline_ids=[],
            bitstring="",
            energy=0.0,
            meta={"excluded": excluded, "n_vars": 0},
            advisory_only=True,
            backend="classical_sa",
            live_path=False,
        )

    Q, meta = build_lane_qubo(
        lanes,
        k=cfg.k,
        risk_lambda=cfg.risk_lambda,
        cluster_penalty=cfg.cluster_penalty,
        cardinality_lambda=cfg.cardinality_lambda,
        min_net_bps=cfg.min_net_bps,
        min_trades=cfg.min_trades,
    )
    bitstring, energy = simulated_annealing(
        Q,
        seed=cfg.seed,
        sweeps=cfg.sweeps,
        t0=cfg.t0,
        t_min=cfg.t_min,
        n_vars=meta["n_vars"],
    )
    selected = decode_selection(bitstring, eligible)
    meta["excluded"] = excluded
    meta["cardinality"] = bitstring.count("1")
    meta["matrix"] = qubo_to_matrix(Q, meta["n_vars"])
    return QiResult(
        selected_pipeline_ids=selected,
        bitstring=bitstring,
        energy=round(energy, 6),
        meta=meta,
        advisory_only=True,
        backend="classical_sa",
        live_path=False,
    )


def compare_to_kelly(
    lanes: list[LaneEdge],
    equity: float,
    allocator_cfg: AllocatorConfig | None = None,
    qi_config: QiConfig | None = None,
    *,
    regime: str = "neutral",
    drawdown_pct: float = 0.0,
) -> dict[str, Any]:
    """Compare SA lane selection vs fractional-Kelly CapitalAllocator."""
    qi_cfg = qi_config or QiConfig()
    alloc_cfg = allocator_cfg or AllocatorConfig()
    qi_cfg.k = min(qi_cfg.k, alloc_cfg.max_active_pipelines)

    qi_result = optimize_lanes(lanes, qi_cfg)
    allocator = CapitalAllocator(alloc_cfg)
    kelly_plan = allocator.allocate(
        equity, lanes, regime=regime, drawdown_pct=drawdown_pct
    )
    kelly_ids = [a.pipeline_id for a in kelly_plan.allocations]
    qi_ids = qi_result.selected_pipeline_ids
    overlap = sorted(set(kelly_ids) & set(qi_ids))

    return {
        "advisory_only": True,
        "live_path": False,
        "backend": "classical_sa",
        "equity_usd": equity,
        "regime": regime,
        "drawdown_pct": drawdown_pct,
        "quantum_inspired": qi_result.to_dict(),
        "kelly": kelly_plan.to_dict(),
        "comparison": {
            "qi_selected": qi_ids,
            "kelly_funded": kelly_ids,
            "overlap": overlap,
            "overlap_count": len(overlap),
            "qi_only": sorted(set(qi_ids) - set(kelly_ids)),
            "kelly_only": sorted(set(kelly_ids) - set(qi_ids)),
            "qi_cardinality": qi_result.meta.get("cardinality", len(qi_ids)),
            "kelly_active_count": len(kelly_ids),
            "target_k": qi_cfg.k,
        },
    }
