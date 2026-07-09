"""Drawdown tier notifications — HERALD queue; never blocks trading."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .drawdown_tiers import DrawdownAlert, DrawdownTierEngine
from .observability import METRICS, setup_logging

logger = setup_logging("drawdown_notifier")

HERALD_QUEUE = "herald_queue.jsonl"
DRAWDOWN_STATE = "drawdown_notify_state.json"


def _queue_path(safety_dir: Path) -> Path:
    return safety_dir / HERALD_QUEUE


def _state_path(safety_dir: Path) -> Path:
    return safety_dir / DRAWDOWN_STATE


def _load_state(safety_dir: Path) -> dict[str, Any]:
    path = _state_path(safety_dir)
    if not path.exists():
        return {"last_notified_tier_pct": 0.0, "last_drawdown_pct": 0.0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_notified_tier_pct": 0.0, "last_drawdown_pct": 0.0}


def _save_state(safety_dir: Path, state: dict[str, Any]) -> None:
    safety_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(safety_dir)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    path.chmod(0o600)


def enqueue_herald_alert(safety_dir: Path, alert: DrawdownAlert, source: str = "GUARDIAN") -> dict[str, Any]:
    """Append urgent HERALD event — operator notified; trading not paused."""
    event = {
        "level": alert.severity,
        "event": "drawdown_tier",
        "event_type": "drawdown_tier",
        "source": source,
        "tier_pct": alert.tier_pct,
        "drawdown_pct": alert.drawdown_pct,
        "action": alert.action,
        "trading_continues": True,
        "immediate": True,
        "reason_codes": ["DRAWDOWN_TIER", "AUTONOMOUS_CONTINUE"],
        "message": alert.message,
        "ts": time.time(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    safety_dir.mkdir(parents=True, exist_ok=True)
    with _queue_path(safety_dir).open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    METRICS.inc("drawdown_tier_notify_total")
    logger.warning(f"drawdown tier notify: {alert.message}")
    return event


def process_drawdown_update(
    policy_raw: dict[str, Any],
    safety_dir: Path,
    previous_pct: float,
    current_pct: float,
    source: str = "GUARDIAN",
) -> dict[str, Any]:
    """Notify on newly crossed tiers; reset tracking when drawdown recovers below 2%."""
    engine = DrawdownTierEngine(policy_raw)
    state = _load_state(safety_dir)

    floor_reset = engine.tiers[0].pct if engine.tiers else 2.0
    if current_pct < floor_reset:
        state["last_notified_tier_pct"] = 0.0

    crossed = engine.tiers_newly_crossed(previous_pct, current_pct)
    # Also notify if we jumped tiers without intermediate updates
    last_notified = float(state.get("last_notified_tier_pct", 0.0))
    crossed = [t for t in crossed if t.pct > last_notified]
    if not crossed and current_pct > previous_pct:
        active = engine.active_tier(current_pct)
        if active and active.pct > last_notified:
            crossed = [active]

    alerts: list[dict[str, Any]] = []
    for tier in crossed:
        alert = engine.build_alert(tier, current_pct)
        alerts.append(enqueue_herald_alert(safety_dir, alert, source=source))
        state["last_notified_tier_pct"] = max(
            float(state.get("last_notified_tier_pct", 0.0)), tier.pct
        )

    state["last_drawdown_pct"] = current_pct
    _save_state(safety_dir, state)

    active = engine.active_tier(current_pct)
    return {
        "ok": True,
        "drawdown_pct_24h": current_pct,
        "previous_pct": previous_pct,
        "active_tier_pct": active.pct if active else None,
        "active_tier_action": active.action if active else None,
        "alerts_sent": len(alerts),
        "alerts": alerts,
        "trading_continues": True,
    }
