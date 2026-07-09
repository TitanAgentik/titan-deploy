"""Portfolio risk service factory tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from titan_safety.portfolio_risk_service import create_app


def test_create_app_routes(tmp_path: Path) -> None:
    data = {
        "version": "2.1",
        "mode": "enforce",
        "trading_limits": {"equity_usd": 2500},
        "allowed_venues": ["paper"],
        "portfolio_risk": {"augur_regime_stub": "neutral"},
        "service": {"portfolio_risk_port": 0},
    }
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    server, engine = create_app(path)
    assert "POST /v1/simulate" in server.routes
    assert engine.regime == "neutral"
