"""Unit tests for the capital allocator."""

from __future__ import annotations

from titan_safety.allocator import AllocatorConfig, CapitalAllocator, LaneEdge


def _lanes() -> list[LaneEdge]:
    return [
        LaneEdge("P5", net_bps=15.0, return_std=0.01, trade_count=800, cluster="funding"),
        LaneEdge("P29", net_bps=30.0, return_std=0.03, trade_count=1200, cluster="mev_arb"),
        LaneEdge("P34", net_bps=8.0, return_std=0.02, trade_count=500, cluster="lp"),
    ]


def test_allocates_within_gross_budget() -> None:
    alloc = CapitalAllocator(AllocatorConfig(kelly_fraction=1.0, max_lane_pct=100, max_cluster_pct=100))
    plan = alloc.allocate(10000.0, _lanes(), regime="neutral", drawdown_pct=0.0)
    assert plan.gross_budget_usd == 10000.0
    assert plan.deployed_usd <= plan.gross_budget_usd + 1e-6
    assert len(plan.allocations) == 3


def test_higher_edge_gets_more_capital() -> None:
    alloc = CapitalAllocator(AllocatorConfig(kelly_fraction=1.0, max_lane_pct=100, max_cluster_pct=100))
    plan = alloc.allocate(10000.0, _lanes())
    by_id = {a.pipeline_id: a for a in plan.allocations}
    # P5: edge/var = 0.0015/0.0001 = 15 ; P29: 0.003/0.0009 = 3.33 ; P34: 0.0008/0.0004 = 2
    assert by_id["P5"].target_notional_usd > by_id["P29"].target_notional_usd
    assert by_id["P29"].target_notional_usd > by_id["P34"].target_notional_usd


def test_min_edge_and_min_trades_exclusion() -> None:
    alloc = CapitalAllocator(AllocatorConfig(min_net_bps=5.0, min_trades=100))
    lanes = [
        LaneEdge("weak", net_bps=2.0, return_std=0.01, trade_count=500),
        LaneEdge("thin", net_bps=20.0, return_std=0.01, trade_count=10),
        LaneEdge("good", net_bps=20.0, return_std=0.01, trade_count=500),
    ]
    plan = alloc.allocate(10000.0, lanes)
    ids = {a.pipeline_id for a in plan.allocations}
    assert ids == {"good"}
    assert "weak" in plan.excluded and "thin" in plan.excluded


def test_decaying_lane_defunded() -> None:
    alloc = CapitalAllocator()
    lanes = [LaneEdge("dead", net_bps=50.0, return_std=0.01, trade_count=999, decaying=True)]
    plan = alloc.allocate(10000.0, lanes)
    assert not plan.allocations
    assert "dead" in plan.excluded


def test_drawdown_degrossing() -> None:
    alloc = CapitalAllocator()
    assert alloc.degross_multiplier(0.0) == 1.0
    assert alloc.degross_multiplier(4.0) == 0.75
    assert alloc.degross_multiplier(6.0) == 0.5
    assert alloc.degross_multiplier(8.0) == 0.25
    assert alloc.degross_multiplier(12.0) == 0.0
    plan = alloc.allocate(10000.0, _lanes(), drawdown_pct=12.0)
    assert plan.gross_budget_usd == 0.0
    assert not plan.allocations


def test_max_active_pipelines_cap() -> None:
    alloc = CapitalAllocator(
        AllocatorConfig(
            kelly_fraction=1.0,
            max_lane_pct=100,
            max_cluster_pct=100,
            max_active_pipelines=2,
        )
    )
    lanes = [
        LaneEdge(f"P{i}", net_bps=20.0 - i, return_std=0.01, trade_count=500)
        for i in range(5)
    ]
    plan = alloc.allocate(10000.0, lanes)
    assert len(plan.allocations) == 2
    assert any("max_active_pipelines" in v for v in plan.excluded.values())


def test_cluster_cap_enforced() -> None:
    alloc = CapitalAllocator(
        AllocatorConfig(kelly_fraction=1.0, max_lane_pct=100, max_cluster_pct=15.0)
    )
    lanes = [
        LaneEdge("A", net_bps=20.0, return_std=0.01, trade_count=500, cluster="same"),
        LaneEdge("B", net_bps=20.0, return_std=0.01, trade_count=500, cluster="same"),
    ]
    plan = alloc.allocate(10000.0, lanes)
    cluster_total = sum(a.target_notional_usd for a in plan.allocations if a.cluster == "same")
    assert cluster_total <= 1500.0 + 1e-6


def test_capacity_cap_enforced() -> None:
    alloc = CapitalAllocator(AllocatorConfig(kelly_fraction=1.0, max_lane_pct=100, max_cluster_pct=100))
    lanes = [LaneEdge("cap", net_bps=30.0, return_std=0.01, trade_count=500, capacity_usd=250.0)]
    plan = alloc.allocate(10000.0, lanes)
    assert plan.allocations[0].target_notional_usd == 250.0
    assert plan.allocations[0].capped_by == "capacity"


def test_regime_scales_budget() -> None:
    alloc = CapitalAllocator()
    off = alloc.gross_budget(10000.0, "risk_off", 0.0)
    neutral = alloc.gross_budget(10000.0, "neutral", 0.0)
    on = alloc.gross_budget(10000.0, "risk_on", 0.0)
    assert off < neutral < on


def test_from_policy_raw() -> None:
    raw = {
        "allocator": {"kelly_fraction": 0.5, "base_gross_pct": 80.0},
        "portfolio_risk": {"correlation_groups": {"g": ["P1"]}},
    }
    cfg = AllocatorConfig.from_raw(raw)
    assert cfg.kelly_fraction == 0.5
    assert cfg.base_gross_pct == 80.0
    assert cfg.correlation_groups == {"g": ["P1"]}
