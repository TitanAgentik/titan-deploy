"""Independent risk inputs — chain/index MTM, fill-ledger velocity, stub detection."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .policy_loader import capital_profile_of
from .recon_aggregator import ReconAggregator

FILL_LEDGER_NAMES = (
    "hyperliquid_fill_ledger.jsonl",
    "fill_ledger.jsonl",
)


def _read_fill_ledger(safety_dir: Path) -> list[dict[str, Any]]:
    for name in FILL_LEDGER_NAMES:
        path = safety_dir / name
        if not path.exists():
            continue
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows
    return []


def loss_velocity_from_fills(
    safety_dir: Path,
    window_seconds: float = 60.0,
    *,
    now: float | None = None,
) -> float:
    """Loss velocity from fill ledger — not agent-reported PnL."""
    cutoff = (now or time.time()) - window_seconds
    total = 0.0
    for row in _read_fill_ledger(safety_dir):
        ts = float(row.get("ts", row.get("timestamp", 0)) or 0)
        if ts < cutoff:
            continue
        pnl = row.get("realized_pnl_usd", row.get("pnl_usd"))
        if pnl is None:
            continue
        pnl_f = float(pnl)
        if pnl_f < 0:
            total += abs(pnl_f)
    return total


def mark_to_market_equity(
    policy_raw: dict[str, Any],
    *,
    safety_dir: Path | None = None,
    cash_usd: float | None = None,
) -> dict[str, Any]:
    """Equity from recon positions (chain/index) — not agent claims."""
    sd = safety_dir or (Path.home() / ".openclaw" / "safety")
    venues = [str(v).lower() for v in (policy_raw.get("allowed_venues") or [])]
    aggregator = ReconAggregator(venues=venues, policy_raw=policy_raw)
    try:
        positions = aggregator.fetch_all()
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "source": "recon_aggregator",
            "equity_usd": cash_usd or float(
                (policy_raw.get("trading_limits") or {}).get("equity_usd", 0)
            ),
        }

    exposure = sum(abs(p.notional_usd) for p in positions)
    equity = float(cash_usd if cash_usd is not None else exposure)
    return {
        "ok": True,
        "source": "recon_aggregator",
        "position_count": len(positions),
        "gross_exposure_usd": round(exposure, 2),
        "equity_usd": round(equity, 2),
        "positions": [
            {
                "venue": p.venue,
                "contract": p.contract,
                "notional_usd": p.notional_usd,
                "side": p.side,
            }
            for p in positions
        ],
    }


def pipeline_returns_from_fills(
    safety_dir: Path,
    pipeline_id: str,
    *,
    min_samples: int = 1,
) -> list[float]:
    """Per-pipeline return series from fill ledger for VaR."""
    returns: list[float] = []
    for row in _read_fill_ledger(safety_dir):
        pid = str(row.get("pipeline_id", row.get("strategy_id", "")))
        if pid and pid != pipeline_id:
            continue
        ret = row.get("return_pct", row.get("return"))
        if ret is None:
            pnl = row.get("realized_pnl_usd", row.get("pnl_usd"))
            notional = row.get("notional_usd", 0)
            if pnl is not None and notional:
                ret = float(pnl) / float(notional)
            else:
                continue
        returns.append(float(ret))
    return returns if len(returns) >= min_samples else []


def detect_live_risk_stubs(policy_raw: dict[str, Any]) -> list[str]:
    """Return stub identifiers that must be cleared before live capital."""
    profile = str(policy_raw.get("capital_profile", "paper")).lower()
    if profile != "live":
        return []

    issues: list[str] = []
    pr = policy_raw.get("portfolio_risk") or {}
    feed = str(pr.get("augur_feed", "stub")).lower()
    if feed in ("stub", ""):
        issues.append("augur_regime_stub")

    recon = policy_raw.get("reconciliation") or {}
    if str(recon.get("adapter", "mock")).lower() == "mock":
        issues.append("mock_recon_adapter")

    tier0 = policy_raw.get("tier0_money_path") or {}
    if tier0.get("enabled") and not tier0.get("builtin_aggregator"):
        issues.append("tier0_missing_builtin_aggregator")

    return issues


def live_risk_inputs_ok(policy_raw: dict[str, Any], safety_dir: Path | None = None) -> dict[str, Any]:
    """Health payload for portfolio risk / kernel wiring."""
    sd = safety_dir or (Path.home() / ".openclaw" / "safety")
    stubs = detect_live_risk_stubs(policy_raw)
    mtm = mark_to_market_equity(policy_raw, safety_dir=sd)
    velocity_60s = loss_velocity_from_fills(sd, 60.0)
    velocity_15m = loss_velocity_from_fills(sd, 900.0)
    return {
        "capital_profile": capital_profile_of_from_raw(policy_raw),
        "stubs_detected": stubs,
        "live_blocked": bool(stubs),
        "mark_to_market": mtm,
        "loss_velocity_60s_usd": round(velocity_60s, 2),
        "loss_velocity_15m_usd": round(velocity_15m, 2),
        "velocity_source": "fill_ledger",
    }


def capital_profile_of_from_raw(policy_raw: dict[str, Any]) -> str:
    return str(policy_raw.get("capital_profile", "paper")).lower()
