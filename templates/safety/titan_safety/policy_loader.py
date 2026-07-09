"""Load and validate risk kernel policy YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TradingLimits:
    max_notional_usd_per_trade: float = 500.0
    max_aggregate_exposure_usd: float = 2500.0
    max_leverage: float = 3.0
    max_loss_velocity_usd_per_60s: float = 200.0
    max_open_positions: int = 8
    max_slippage_bps: int = 50
    equity_usd: float = 2500.0


@dataclass
class ReconciliationConfig:
    divergence_threshold_usd: float = 25.0
    divergence_threshold_pct: float = 1.0
    adapter: str = "mock"


@dataclass
class ServicePorts:
    risk_kernel_port: int = 19001
    reconciliation_port: int = 19002
    status_aggregator_port: int = 19003
    portfolio_risk_port: int = 19004
    dead_mans_switch_port: int = 19005
    allocator_port: int = 19006
    tca_port: int = 19007
    signing_node_port: int = 19010


@dataclass
class Policy:
    version: str
    mode: str
    trading_limits: TradingLimits
    allowed_venues: list[str]
    allowed_contracts: list[str]
    reconciliation: ReconciliationConfig
    service: ServicePorts
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def enforce(self) -> bool:
        return self.mode == "enforce"


def expand_path(path: str | Path) -> Path:
    return Path(str(path).replace("~", str(Path.home()))).expanduser().resolve()


def load_component(spec: str) -> Any:
    """Load a pluggable component from a "module.path:attr" spec.

    Used for live signer / position-closer / key-revoker wiring so mock
    implementations never silently run against a live capital profile.
    """
    module_path, sep, attr = spec.partition(":")
    if not sep or not module_path or not attr:
        raise ValueError(f"Component spec must be 'module.path:attr', got: {spec!r}")
    import importlib

    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise ValueError(f"{module_path} has no attribute {attr!r}") from exc


def capital_profile_of(policy: "Policy") -> str:
    return str(policy.raw.get("capital_profile", "paper")).lower()


def load_policy(path: str | Path) -> Policy:
    p = expand_path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid policy format: {p}")

    tl = data.get("trading_limits", {})
    rc = data.get("reconciliation", {})
    svc = data.get("service", {})

    return Policy(
        version=str(data.get("version", "1.0")),
        mode=str(data.get("mode", "enforce")),
        trading_limits=TradingLimits(
            max_notional_usd_per_trade=float(tl.get("max_notional_usd_per_trade", 500)),
            max_aggregate_exposure_usd=float(tl.get("max_aggregate_exposure_usd", 2500)),
            max_leverage=float(tl.get("max_leverage", 3.0)),
            max_loss_velocity_usd_per_60s=float(tl.get("max_loss_velocity_usd_per_60s", 200)),
            max_open_positions=int(tl.get("max_open_positions", 8)),
            max_slippage_bps=int(tl.get("max_slippage_bps", 50)),
            equity_usd=float(tl.get("equity_usd", 2500)),
        ),
        allowed_venues=[str(v) for v in data.get("allowed_venues", ["paper"])],
        allowed_contracts=[str(c).lower() for c in data.get("allowed_contracts", [])],
        reconciliation=ReconciliationConfig(
            divergence_threshold_usd=float(rc.get("divergence_threshold_usd", 25)),
            divergence_threshold_pct=float(rc.get("divergence_threshold_pct", 1.0)),
            adapter=str(rc.get("adapter", "mock")),
        ),
        service=ServicePorts(
            risk_kernel_port=int(svc.get("risk_kernel_port", 19001)),
            reconciliation_port=int(svc.get("reconciliation_port", 19002)),
            status_aggregator_port=int(svc.get("status_aggregator_port", 19003)),
            portfolio_risk_port=int(svc.get("portfolio_risk_port", 19004)),
            dead_mans_switch_port=int(svc.get("dead_mans_switch_port", 19005)),
            allocator_port=int(svc.get("allocator_port", 19006)),
            tca_port=int(svc.get("tca_port", 19007)),
            signing_node_port=int(svc.get("signing_node_port", 19010)),
        ),
        raw=data,
    )
