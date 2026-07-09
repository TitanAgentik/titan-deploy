"""Allocator service factory tests — advisory mode surfaces on plans."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.allocator_service import create_app


def test_create_app_advisory_default(tmp_path: Path) -> None:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 10000},
        "allowed_venues": ["paper"],
        "allocator": {
            "kelly_fraction": 1.0,
            "max_lane_pct": 100,
            "max_cluster_pct": 100,
            "min_trades": 1,
        },
        "service": {"allocator_port": 0},
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    server, allocator = create_app(path)
    assert "POST /v1/allocate" in server.routes
    assert allocator.config.advisory_mode is True
    assert allocator.is_enforced() is False

    code, body = server.routes["POST /v1/allocate"](
        {
            "equity_usd": 10000.0,
            "lanes": [
                {
                    "pipeline_id": "P5",
                    "net_bps": 15.0,
                    "return_std": 0.01,
                    "trade_count": 100,
                }
            ],
        },
        {},
    )
    assert code == 200
    assert body["advisory"] is True
    assert any("ADVISORY" in n for n in body["notes"])


def test_create_app_enforced_when_advisory_false(tmp_path: Path) -> None:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 10000},
        "allowed_venues": ["paper"],
        "allocator": {"advisory_mode": False, "min_trades": 1},
        "service": {"allocator_port": 0},
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    _server, allocator = create_app(path)
    assert allocator.config.advisory_mode is False
    assert allocator.is_enforced() is True
