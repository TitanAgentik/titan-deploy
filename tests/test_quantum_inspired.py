"""Tests for offline quantum-inspired QUBO + simulated annealing lane selection."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from titan_safety.allocator import AllocatorConfig, LaneEdge
from titan_safety.quantum_inspired import (
    QiConfig,
    build_lane_qubo,
    compare_to_kelly,
    decode_selection,
    optimize_lanes,
    qubo_energy,
    qubo_to_matrix,
    simulated_annealing,
    synthetic_demo_lanes,
)


def _demo_lanes() -> list[LaneEdge]:
    return synthetic_demo_lanes()


def test_qubo_shape_and_symmetry() -> None:
    Q, meta = build_lane_qubo(_demo_lanes(), k=4)
    n = meta["n_vars"]
    assert n == 6
    mat = qubo_to_matrix(Q, n)
    assert len(mat) == n
    assert all(len(row) == n for row in mat)
    for i in range(n):
        for j in range(n):
            assert mat[i][j] == mat[j][i]
    for (i, j), coeff in Q.items():
        assert i <= j
        assert mat[i][j] == coeff
        if i != j:
            assert mat[j][i] == coeff


def test_cardinality_near_k() -> None:
    cfg = QiConfig(k=4, seed=42, sweeps=8000)
    result = optimize_lanes(_demo_lanes(), cfg)
    cardinality = result.bitstring.count("1")
    assert 2 <= cardinality <= 5
    assert result.meta["cardinality"] == cardinality


def test_seed_reproducibility() -> None:
    cfg = QiConfig(k=4, seed=99, sweeps=6000)
    a = optimize_lanes(_demo_lanes(), cfg)
    b = optimize_lanes(_demo_lanes(), cfg)
    assert a.bitstring == b.bitstring
    assert a.energy == b.energy
    assert a.selected_pipeline_ids == b.selected_pipeline_ids


def test_advisory_only_in_output() -> None:
    result = optimize_lanes(_demo_lanes(), QiConfig(k=3, seed=7))
    d = result.to_dict()
    assert d["advisory_only"] is True
    assert d["live_path"] is False
    assert d["backend"] == "classical_sa"
    cmp_out = compare_to_kelly(_demo_lanes(), 10000.0)
    assert cmp_out["advisory_only"] is True
    assert cmp_out["live_path"] is False


def test_decode_selection_maps_pipeline_ids() -> None:
    lanes = _demo_lanes()
    bitstring = "101010"
    selected = decode_selection(bitstring, lanes)
    assert selected == ["P1", "P11", "P22"]


def test_no_dormant_quantum_imports() -> None:
    mod_path = Path(inspect.getfile(optimize_lanes)).resolve()
    tree = ast.parse(mod_path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    forbidden = [name for name in imports if "quantum" in name.lower()]
    assert forbidden == []
    source = mod_path.read_text(encoding="utf-8").lower()
    assert "qiskit" not in source
    assert "dwave" not in source


def test_compare_to_kelly_structure() -> None:
    out = compare_to_kelly(
        _demo_lanes(),
        10000.0,
        allocator_cfg=AllocatorConfig(max_active_pipelines=4),
        qi_config=QiConfig(k=4, seed=42),
    )
    assert "quantum_inspired" in out
    assert "kelly" in out
    assert "comparison" in out
    assert "overlap" in out["comparison"]
    assert isinstance(out["comparison"]["qi_selected"], list)


def test_simulated_annealing_improves_or_matches_start() -> None:
    Q, meta = build_lane_qubo(_demo_lanes(), k=4)
    n = meta["n_vars"]
    rng_seed = 1
    import random

    rng = random.Random(rng_seed)
    start = [rng.randint(0, 1) for _ in range(n)]
    start_energy = qubo_energy(start, Q)
    bitstring, energy = simulated_annealing(Q, seed=rng_seed, sweeps=10000, n_vars=n)
    assert energy <= start_energy + 1e-9
    assert len(bitstring) == n
