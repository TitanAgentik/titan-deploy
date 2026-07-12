"""Daily TCA scorecard digest for HERALD / Telegram."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .profit_loop import ProfitLoop
from .tca import LaneScorecard, TCAEngine


@dataclass
class DailyScorecardDigest:
    date_utc: str
    lanes_tracked: int
    healthy: list[str] = field(default_factory=list)
    marginal: list[str] = field(default_factory=list)
    bleeding: list[str] = field(default_factory=list)
    insufficient: list[str] = field(default_factory=list)
    defunded: list[str] = field(default_factory=list)
    scorecards: list[dict[str, Any]] = field(default_factory=list)
    totals: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_daily_scorecard(
    engine: TCAEngine,
    *,
    safety_dir: Path | None = None,
    equity_usd: float = 0.0,
) -> DailyScorecardDigest:
    """Build digest from current TCA state."""
    cards = engine.all_scorecards()
    safety = safety_dir or Path.home() / ".openclaw" / "safety"
    defunded = sorted(ProfitLoop(engine, safety_dir=safety, auto_halt_bleeding=False).defunded_lanes())

    healthy, marginal, bleeding, insufficient = [], [], [], []
    total_net_pnl = 0.0
    total_notional = 0.0
    for c in cards:
        total_net_pnl += c.net_pnl_usd
        total_notional += c.total_notional_usd
        bucket = {
            "HEALTHY": healthy,
            "MARGINAL": marginal,
            "BLEEDING": bleeding,
            "INSUFFICIENT_DATA": insufficient,
        }.get(c.verdict, insufficient)
        bucket.append(c.pipeline_id)

    notes: list[str] = []
    if bleeding:
        notes.append(f"{len(bleeding)} BLEEDING lane(s) — profit_loop auto-defunds on run")
    if defunded:
        notes.append(f"{len(defunded)} defunded — refund requires promotion YES")

    return DailyScorecardDigest(
        date_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        lanes_tracked=len(cards),
        healthy=healthy,
        marginal=marginal,
        bleeding=bleeding,
        insufficient=insufficient,
        defunded=defunded,
        scorecards=[c.to_dict() for c in cards],
        totals={
            "net_pnl_usd": round(total_net_pnl, 2),
            "notional_usd": round(total_notional, 2),
            "equity_usd": round(equity_usd, 2),
        },
        notes=notes,
    )


def render_telegram_scorecard(digest: DailyScorecardDigest) -> str:
    lines = [
        f"*TCA Daily Scorecard* — {digest.date_utc} UTC",
        f"Lanes: {digest.lanes_tracked} | Net PnL: ${digest.totals.get('net_pnl_usd', 0):,.2f}",
    ]
    if digest.healthy:
        lines.append(f"HEALTHY ({len(digest.healthy)}): {', '.join(digest.healthy[:6])}")
    if digest.marginal:
        lines.append(f"MARGINAL ({len(digest.marginal)}): {', '.join(digest.marginal[:6])}")
    if digest.bleeding:
        lines.append(f"BLEEDING ({len(digest.bleeding)}): {', '.join(digest.bleeding)}")
    if digest.defunded:
        lines.append(f"Defunded: {', '.join(digest.defunded)}")
    for card in digest.scorecards[:8]:
        lines.append(
            f"  `{card['pipeline_id']}` net {card['net_bps']:.1f}bps "
            f"fill {card['fill_rate']*100:.0f}% tip_eff {card['tip_efficiency']:.2f}"
        )
    if digest.notes:
        lines.append("_" + " · ".join(digest.notes) + "_")
    return "\n".join(lines)


def publish_daily_scorecard(
    engine: TCAEngine,
    *,
    safety_dir: Path | None = None,
    equity_usd: float = 0.0,
    send: bool = True,
) -> dict[str, Any]:
    digest = build_daily_scorecard(engine, safety_dir=safety_dir, equity_usd=equity_usd)
    text = render_telegram_scorecard(digest)
    result: dict[str, Any] = {
        "ok": True,
        "digest": digest.to_dict(),
        "telegram_text": text,
        "ts": time.time(),
    }
    if send:
        try:
            from .telegram_notify import notify_tca_daily_scorecard

            notify_result = notify_tca_daily_scorecard(
                digest.to_dict(),
                telegram_text=text,
                safety_dir=safety_dir,
            )
            result["notify"] = notify_result
            result["ok"] = bool(notify_result.get("ok", True))
        except Exception as exc:
            result["ok"] = False
            result["notify_error"] = str(exc)
    return result
