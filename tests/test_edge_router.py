"""Edge PoP routing — venue/strategy → lowest-latency PoP."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from titan_safety.edge_router import EdgeRouter, load_edge_mesh


def _write_mesh(tmp_path: Path, **overrides) -> Path:
    data = {
        "version": "2.0",
        "mode": "full_mesh",
        "paper_trading": {"latency_faithful": True},
        "pops": {
            "EDGE-FRA": {"wireguard_ip": "10.0.10.100", "worker_port": 19100},
            "EDGE-TKY": {"wireguard_ip": "10.0.10.101", "worker_port": 19100},
            "EDGE-SIN": {"wireguard_ip": "10.0.10.102", "worker_port": 19100},
        },
        "venue_routing": {
            "binance_spot": "EDGE-TKY",
            "jito": "EDGE-FRA",
        },
        "strategy_routing": {
            "P22": {"primary": "EDGE-FRA", "fallback": ["EDGE-AMS"]},
            "P29": {"primary": "EDGE-TKY", "fallback": ["EDGE-FRA"]},
        },
    }
    data.update(overrides)
    path = tmp_path / "edge_mesh.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def test_load_edge_mesh(tmp_path: Path) -> None:
    path = _write_mesh(tmp_path)
    mesh = load_edge_mesh(path)
    assert mesh["mode"] == "full_mesh"


def test_venue_routing(tmp_path: Path) -> None:
    router = EdgeRouter.from_path(_write_mesh(tmp_path))
    decision = router.route(venue="binance_spot")
    assert decision.primary == "EDGE-TKY"
    assert decision.worker_url == "http://10.0.10.101:19100"
    assert decision.reason == "venue_routing"


def test_strategy_routing_overrides_venue(tmp_path: Path) -> None:
    router = EdgeRouter.from_path(_write_mesh(tmp_path))
    decision = router.route(venue="jito", strategy_id="P29")
    assert decision.primary == "EDGE-TKY"
    assert decision.reason == "strategy_routing:P29"
    assert "EDGE-FRA" in decision.fallback


def test_p22_memecoin_route(tmp_path: Path) -> None:
    router = EdgeRouter.from_path(_write_mesh(tmp_path))
    decision = router.route(venue="jito", strategy_id="P22")
    assert decision.primary == "EDGE-FRA"
    assert decision.paper_latency_faithful is True


def test_default_pop_when_unknown_venue(tmp_path: Path) -> None:
    router = EdgeRouter.from_path(_write_mesh(tmp_path))
    decision = router.route(venue="unknown_venue")
    assert decision.primary == "EDGE-FRA"
    assert decision.reason == "default_pop"


def test_list_pops(tmp_path: Path) -> None:
    router = EdgeRouter.from_path(_write_mesh(tmp_path))
    pops = router.list_pops()
    assert len(pops) == 3
    ids = {p["id"] for p in pops}
    assert ids == {"EDGE-FRA", "EDGE-TKY", "EDGE-SIN"}


def test_missing_mesh_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_edge_mesh(tmp_path / "missing.yaml")
