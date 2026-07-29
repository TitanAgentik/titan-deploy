"""Daily compound engine — make capital *tend* more profitable over time.

Honest scope
------------
No software can guarantee profit every calendar day. Markets gap, costs bite,
and edges decay. This module does the next-best thing that is enforceable and
deterministic:

1. **Cut losers daily** — run the TCA→allocator profit loop; auto-defund BLEEDING.
2. **Feed winners** — fractional-Kelly reallocation into HEALTHY lanes only.
3. **Compound green days** — 100% reinvest below harvest threshold; track ATH.
4. **Protect red days** — synthetic de-gross, lower Kelly, tighten active lanes.
5. **Never auto-promote** — iron-laws TIMEOUT=HOLD; refund still needs YES.

Designed for growth-phase capital ($2.5K start → $15K reinvest-all).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .allocator import AllocatorConfig, CapitalAllocator, LaneEdge
from .capital import CapitalManager, load_capital_config
from .profit_loop import ProfitLoop, ProfitLoopResult
from .tca import TCAEngine


DEFAULT_SAFETY_DIR = Path.home() / ".openclaw" / "safety"
LEDGER_NAME = "daily_equity.jsonl"
STATE_NAME = "daily_compound_state.json"
PLAN_NAME = "daily_allocation_plan.json"


@dataclass
class DailyCompoundConfig:
    """Policy knobs for day-over-day compounding."""

    enabled: bool = True
    growth_threshold_usd: float = 15000.0
    # Green-day risk: slight Kelly boost after consecutive profitable days
    min_green_streak_for_boost: int = 2
    green_day_kelly_boost: float = 0.05
    max_kelly_fraction: float = 0.35
    min_kelly_fraction: float = 0.15
    base_kelly_fraction: float = 0.25
    # Red-day protection
    red_day_degross_mult: float = 0.70
    red_day_kelly_cut: float = 0.05
    max_active_on_red: int = 1
    max_active_on_green: int = 2
    # Require measured edge before deploying (paper can lower)
    min_trades_for_deploy: int = 30
    min_net_bps_for_deploy: float = 1.0
    # Starve MARGINAL harder than default profit loop
    starve_marginal: bool = True
    marginal_weight_scale: float = 0.35
    # Persist realized TCA net into capital equity when requested
    apply_tca_pnl_to_equity: bool = False
    note: str = (
        "Compound measured edge only — never invents alpha; "
        "red days de-gross; green days reinvest within risk envelope"
    )

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> DailyCompoundConfig:
        d = cls()
        if not raw:
            return d
        c = raw.get("daily_compound", raw) if isinstance(raw, dict) else {}
        if not isinstance(c, dict):
            return d
        return cls(
            enabled=bool(c.get("enabled", d.enabled)),
            growth_threshold_usd=float(
                c.get("growth_threshold_usd", d.growth_threshold_usd)
            ),
            min_green_streak_for_boost=int(
                c.get("min_green_streak_for_boost", d.min_green_streak_for_boost)
            ),
            green_day_kelly_boost=float(
                c.get("green_day_kelly_boost", d.green_day_kelly_boost)
            ),
            max_kelly_fraction=float(c.get("max_kelly_fraction", d.max_kelly_fraction)),
            min_kelly_fraction=float(c.get("min_kelly_fraction", d.min_kelly_fraction)),
            base_kelly_fraction=float(
                c.get("base_kelly_fraction", d.base_kelly_fraction)
            ),
            red_day_degross_mult=float(
                c.get("red_day_degross_mult", d.red_day_degross_mult)
            ),
            red_day_kelly_cut=float(c.get("red_day_kelly_cut", d.red_day_kelly_cut)),
            max_active_on_red=int(c.get("max_active_on_red", d.max_active_on_red)),
            max_active_on_green=int(c.get("max_active_on_green", d.max_active_on_green)),
            min_trades_for_deploy=int(
                c.get("min_trades_for_deploy", d.min_trades_for_deploy)
            ),
            min_net_bps_for_deploy=float(
                c.get("min_net_bps_for_deploy", d.min_net_bps_for_deploy)
            ),
            starve_marginal=bool(c.get("starve_marginal", d.starve_marginal)),
            marginal_weight_scale=float(
                c.get("marginal_weight_scale", d.marginal_weight_scale)
            ),
            apply_tca_pnl_to_equity=bool(
                c.get("apply_tca_pnl_to_equity", d.apply_tca_pnl_to_equity)
            ),
            note=str(c.get("note", d.note)),
        )


@dataclass
class DailyCompoundResult:
    date_utc: str
    equity_usd: float
    previous_equity_usd: float
    daily_pnl_usd: float
    daily_pnl_pct: float
    green_day: bool
    green_streak: int
    red_streak: int
    ath_usd: float
    new_ath: bool
    phase: str  # GROWTH | HARVEST
    kelly_fraction: float
    drawdown_pct: float
    effective_drawdown_pct: float
    profit_loop: dict[str, Any] = field(default_factory=dict)
    allocation_plan: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)
    dry_run: bool = False
    telegram_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DailyCompoundEngine:
    """Day-over-day equity tracker + profit-maximizing reallocator."""

    def __init__(
        self,
        tca: TCAEngine,
        *,
        safety_dir: Path | None = None,
        capital: CapitalManager | None = None,
        config: DailyCompoundConfig | None = None,
        allocator: CapitalAllocator | None = None,
        auto_halt_bleeding: bool = True,
    ) -> None:
        self.tca = tca
        self.safety_dir = safety_dir or DEFAULT_SAFETY_DIR
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.capital = capital or CapitalManager(load_capital_config())
        self.config = config or DailyCompoundConfig()
        self.allocator = allocator
        self.auto_halt_bleeding = auto_halt_bleeding

    @property
    def ledger_path(self) -> Path:
        return self.safety_dir / LEDGER_NAME

    @property
    def state_path(self) -> Path:
        return self.safety_dir / STATE_NAME

    @property
    def plan_path(self) -> Path:
        return self.safety_dir / PLAN_NAME

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "green_streak": 0,
                "red_streak": 0,
                "ath_usd": 0.0,
                "last_date_utc": None,
                "last_equity_usd": None,
                "kelly_fraction": self.config.base_kelly_fraction,
                "updated_at": None,
            }
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = time.time()
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _append_ledger(self, record: dict[str, Any]) -> None:
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    def _resolve_equity(self, equity_override: float | None) -> float:
        if equity_override is not None and equity_override > 0:
            return float(equity_override)
        bal = self.capital.balance()
        eq = float(bal.get("equity_usd") or 0.0)
        if eq > 0:
            return eq
        # Fallback: sum TCA net PnL is not equity; use policy trading_limits.equity
        return 0.0

    def _phase(self, equity: float) -> str:
        return (
            "HARVEST"
            if equity >= self.config.growth_threshold_usd
            else "GROWTH"
        )

    def _compute_kelly(
        self,
        *,
        green: bool,
        green_streak: int,
        red_streak: int,
        prior_kelly: float,
    ) -> float:
        k = prior_kelly if prior_kelly > 0 else self.config.base_kelly_fraction
        if green and green_streak >= self.config.min_green_streak_for_boost:
            k = k + self.config.green_day_kelly_boost
        if not green:
            k = k - self.config.red_day_kelly_cut * max(1, min(red_streak, 3))
        return max(
            self.config.min_kelly_fraction,
            min(self.config.max_kelly_fraction, k),
        )

    def _lanes_from_tca(self) -> list[LaneEdge]:
        lanes: list[LaneEdge] = []
        for card in self.tca.all_scorecards():
            if card.verdict == "INSUFFICIENT_DATA":
                continue
            decaying = (
                card.verdict == "BLEEDING"
                or card.decay_slope_bps < 0
            )
            # Starve MARGINAL: scale net_bps down so Kelly underweights them
            net = card.net_bps
            if (
                self.config.starve_marginal
                and card.verdict == "MARGINAL"
                and net > 0
            ):
                net = net * self.config.marginal_weight_scale
            lanes.append(
                LaneEdge(
                    pipeline_id=card.pipeline_id,
                    net_bps=net,
                    return_std=max(0.01, abs(card.net_bps) / 1e4 * 2),
                    trade_count=card.fill_count,
                    decaying=decaying,
                    cluster="",
                )
            )
        return lanes

    def _tca_window_net_pnl(self) -> float:
        return sum(c.net_pnl_usd for c in self.tca.all_scorecards())

    def run(
        self,
        *,
        equity_usd: float | None = None,
        regime: str = "neutral",
        drawdown_pct: float = 0.0,
        dry_run: bool = False,
        date_utc: str | None = None,
    ) -> DailyCompoundResult:
        notes: list[str] = []
        if not self.config.enabled:
            notes.append("daily_compound.enabled=false — no-op")
            return DailyCompoundResult(
                date_utc=date_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                equity_usd=0.0,
                previous_equity_usd=0.0,
                daily_pnl_usd=0.0,
                daily_pnl_pct=0.0,
                green_day=False,
                green_streak=0,
                red_streak=0,
                ath_usd=0.0,
                new_ath=False,
                phase="GROWTH",
                kelly_fraction=self.config.base_kelly_fraction,
                drawdown_pct=drawdown_pct,
                effective_drawdown_pct=drawdown_pct,
                notes=notes,
                dry_run=dry_run,
            )

        today = date_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state = self._load_state()
        equity = self._resolve_equity(equity_usd)
        if equity <= 0:
            notes.append("equity_usd is zero — seed capital with: titan-safety capital deposit")
            equity = float(equity_usd or 0.0)

        prev_eq = state.get("last_equity_usd")
        first_snapshot = prev_eq is None
        if first_snapshot:
            prev_eq = equity
            notes.append("first snapshot — establishing equity baseline (no streak)")
        prev_eq = float(prev_eq)

        # Optional: fold rolling TCA net into equity (paper / when operator opts in)
        tca_net = self._tca_window_net_pnl()
        if (
            self.config.apply_tca_pnl_to_equity
            and not dry_run
            and abs(tca_net) > 1e-9
            and state.get("last_date_utc") != today
            and not first_snapshot
        ):
            self.capital.apply_realized_pnl(
                tca_net,
                operator="daily_compound",
                reason=f"TCA window net_pnl for {today}",
            )
            equity = float(self.capital.balance()["equity_usd"])
            notes.append(f"applied TCA net PnL ${tca_net:,.2f} to capital equity")

        daily_pnl = round(equity - prev_eq, 2)
        daily_pct = (daily_pnl / prev_eq * 100.0) if prev_eq > 0 else 0.0
        green = daily_pnl >= 0.0

        green_streak = int(state.get("green_streak", 0))
        red_streak = int(state.get("red_streak", 0))
        # Only advance streaks once per calendar day; skip first baseline snapshot
        if first_snapshot:
            green_streak = 0
            red_streak = 0
            green = True  # neutral baseline — not a red day
            daily_pnl = 0.0
            daily_pct = 0.0
        elif state.get("last_date_utc") != today:
            if green:
                green_streak = green_streak + 1
                red_streak = 0
            else:
                red_streak = red_streak + 1
                green_streak = 0
        else:
            notes.append("already ran today — re-using streak counters")

        ath = float(state.get("ath_usd") or 0.0)
        new_ath = equity > ath
        if new_ath:
            ath = equity
            notes.append(f"new ATH ${ath:,.2f}")

        phase = self._phase(equity)
        prior_kelly = float(
            state.get("kelly_fraction") or self.config.base_kelly_fraction
        )
        kelly = self._compute_kelly(
            green=green,
            green_streak=green_streak,
            red_streak=red_streak,
            prior_kelly=prior_kelly,
        )

        # Effective drawdown for allocator: red days force extra de-gross
        eff_dd = drawdown_pct
        if not green and prev_eq > 0:
            day_loss_pct = abs(min(0.0, daily_pct))
            # Map red day into de-gross ladder space
            synthetic = day_loss_pct / max(self.config.red_day_degross_mult, 0.01)
            eff_dd = max(drawdown_pct, synthetic)
            notes.append(
                f"red day — effective drawdown {eff_dd:.2f}% "
                f"(raw {drawdown_pct:.2f}%, day loss {day_loss_pct:.2f}%)"
            )

        max_active = (
            self.config.max_active_on_green
            if green
            else self.config.max_active_on_red
        )

        alloc_cfg = AllocatorConfig(
            kelly_fraction=kelly,
            max_active_pipelines=max_active,
            min_net_bps=self.config.min_net_bps_for_deploy,
            min_trades=self.config.min_trades_for_deploy,
            advisory_mode=False,  # compound plan is actionable when live
            selective_activation=True,
        )
        allocator = self.allocator or CapitalAllocator(alloc_cfg)
        # If external allocator passed, still apply dynamic kelly/max_active
        allocator.config.kelly_fraction = kelly
        allocator.config.max_active_pipelines = max_active
        allocator.config.min_net_bps = self.config.min_net_bps_for_deploy
        allocator.config.min_trades = max(
            allocator.config.min_trades, self.config.min_trades_for_deploy
        )

        loop = ProfitLoop(
            self.tca,
            allocator=allocator,
            safety_dir=self.safety_dir,
            auto_halt_bleeding=self.auto_halt_bleeding and not dry_run,
        )

        if dry_run:
            # Plan without defund side effects
            lanes = self._lanes_from_tca()
            for lane in lanes:
                if loop.is_defunded(lane.pipeline_id):
                    lane.decaying = True
            plan = allocator.allocate(
                equity, lanes, regime=regime, drawdown_pct=eff_dd
            )
            pl_dict = {
                "dry_run": True,
                "would_defund": [
                    c.pipeline_id
                    for c in self.tca.all_scorecards()
                    if c.verdict == "BLEEDING" and not loop.is_defunded(c.pipeline_id)
                ],
                "already_defunded": sorted(loop.defunded_lanes()),
                "plan": plan.to_dict(),
            }
            pl_result: ProfitLoopResult | None = None
        else:
            pl_result = loop.run(
                equity_usd=equity,
                regime=regime,
                drawdown_pct=eff_dd,
                lane_overrides=self._lanes_from_tca(),
            )
            pl_dict = pl_result.to_dict()
            plan = pl_result.plan

        # Growth phase: 100% reinvest — no sweep pressure
        if phase == "GROWTH":
            notes.append(
                f"GROWTH phase — 100% reinvest until "
                f"${self.config.growth_threshold_usd:,.0f}"
            )
        else:
            notes.append(
                "HARVEST phase — weekly 20% profit sweep eligible (Sunday UTC)"
            )

        if green and green_streak >= self.config.min_green_streak_for_boost:
            notes.append(
                f"green streak {green_streak} — Kelly boosted to {kelly:.3f}"
            )
        if not green:
            notes.append(
                f"red streak {red_streak} — Kelly cut to {kelly:.3f}, "
                f"max_active={max_active}"
            )

        # Persist
        plan_dict = plan.to_dict() if plan else None
        if not dry_run:
            new_state = {
                "green_streak": green_streak,
                "red_streak": red_streak,
                "ath_usd": ath,
                "last_date_utc": today,
                "last_equity_usd": equity,
                "kelly_fraction": kelly,
                "last_daily_pnl_usd": daily_pnl,
                "phase": phase,
            }
            self._save_state(new_state)
            self._append_ledger(
                {
                    "date_utc": today,
                    "equity_usd": equity,
                    "previous_equity_usd": prev_eq,
                    "daily_pnl_usd": daily_pnl,
                    "daily_pnl_pct": round(daily_pct, 4),
                    "green_day": green,
                    "green_streak": green_streak,
                    "red_streak": red_streak,
                    "ath_usd": ath,
                    "new_ath": new_ath,
                    "phase": phase,
                    "kelly_fraction": kelly,
                    "drawdown_pct": drawdown_pct,
                    "effective_drawdown_pct": eff_dd,
                    "deployed_usd": (plan_dict or {}).get("deployed_usd", 0),
                    "defunded": (pl_dict or {}).get("defunded", []),
                    "ts": time.time(),
                }
            )
            if plan_dict is not None:
                self.plan_path.write_text(
                    json.dumps(
                        {
                            "date_utc": today,
                            "generated_at": time.time(),
                            "plan": plan_dict,
                            "kelly_fraction": kelly,
                            "phase": phase,
                            "green_day": green,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            # Track weekly profit for harvest sweeps
            if green and daily_pnl > 0:
                cap_state = self.capital.load_state()
                cap_state["weekly_profit_usd"] = round(
                    float(cap_state.get("weekly_profit_usd") or 0.0) + daily_pnl, 2
                )
                self.capital.save_state(cap_state)

        telegram = self.render_telegram(
            DailyCompoundResult(
                date_utc=today,
                equity_usd=equity,
                previous_equity_usd=prev_eq,
                daily_pnl_usd=daily_pnl,
                daily_pnl_pct=round(daily_pct, 4),
                green_day=green,
                green_streak=green_streak,
                red_streak=red_streak,
                ath_usd=ath,
                new_ath=new_ath,
                phase=phase,
                kelly_fraction=kelly,
                drawdown_pct=drawdown_pct,
                effective_drawdown_pct=eff_dd,
                profit_loop=pl_dict,
                allocation_plan=plan_dict,
                notes=notes,
                dry_run=dry_run,
            )
        )

        result = DailyCompoundResult(
            date_utc=today,
            equity_usd=equity,
            previous_equity_usd=prev_eq,
            daily_pnl_usd=daily_pnl,
            daily_pnl_pct=round(daily_pct, 4),
            green_day=green,
            green_streak=green_streak,
            red_streak=red_streak,
            ath_usd=ath,
            new_ath=new_ath,
            phase=phase,
            kelly_fraction=kelly,
            drawdown_pct=drawdown_pct,
            effective_drawdown_pct=eff_dd,
            profit_loop=pl_dict,
            allocation_plan=plan_dict,
            notes=notes,
            dry_run=dry_run,
            telegram_text=telegram,
        )
        return result

    @staticmethod
    def render_telegram(result: DailyCompoundResult) -> str:
        sign = "+" if result.daily_pnl_usd >= 0 else ""
        emoji = "📈" if result.green_day else "📉"
        ath = " 🏆 NEW ATH" if result.new_ath else ""
        lines = [
            f"{emoji} *Daily Compound* — {result.date_utc} UTC{ath}",
            (
                f"Equity: `${result.equity_usd:,.2f}` | "
                f"Day: `{sign}${result.daily_pnl_usd:,.2f}` "
                f"({sign}{result.daily_pnl_pct:.2f}%)"
            ),
            (
                f"Phase: `{result.phase}` | Kelly: `{result.kelly_fraction:.3f}` | "
                f"Streak G{result.green_streak}/R{result.red_streak}"
            ),
            f"ATH: `${result.ath_usd:,.2f}` | Eff DD: `{result.effective_drawdown_pct:.2f}%`",
        ]
        plan = result.allocation_plan or {}
        allocs = plan.get("allocations") or []
        if allocs:
            top = ", ".join(
                f"{a['pipeline_id']}:${a['target_notional_usd']:,.0f}"
                for a in allocs[:4]
            )
            lines.append(f"Deploy: {top}")
        defunded = (result.profit_loop or {}).get("defunded") or []
        if defunded:
            lines.append(f"Auto-defunded: `{', '.join(defunded)}`")
        if result.notes:
            lines.append("_" + " · ".join(result.notes[:4]) + "_")
        if result.dry_run:
            lines.append("_dry-run — no ledger/defund writes_")
        return "\n".join(lines)


def run_daily_compound(
    engine: TCAEngine,
    *,
    safety_dir: Path | None = None,
    equity_usd: float | None = None,
    regime: str = "neutral",
    drawdown_pct: float = 0.0,
    dry_run: bool = False,
    config: DailyCompoundConfig | None = None,
    send_telegram: bool = False,
) -> dict[str, Any]:
    """Convenience entry used by CLI and systemd oneshot."""
    dc = DailyCompoundEngine(
        engine,
        safety_dir=safety_dir,
        config=config,
        auto_halt_bleeding=not dry_run,
    )
    result = dc.run(
        equity_usd=equity_usd,
        regime=regime,
        drawdown_pct=drawdown_pct,
        dry_run=dry_run,
    )
    out = result.to_dict()
    if send_telegram and not dry_run:
        try:
            from .telegram_notify import notify_money_summary

            notify_money_summary(
                period=f"daily_compound {result.date_utc}",
                realized_usd=result.daily_pnl_usd,
                daily_pnl_usd=result.daily_pnl_usd,
                daily_pnl_pct=result.daily_pnl_pct,
                equity_usd=result.equity_usd,
                portfolio={
                    "equity_usd": result.equity_usd,
                    "daily_pnl_usd": result.daily_pnl_usd,
                    "daily_pnl_pct": result.daily_pnl_pct,
                    "ath_usd": result.ath_usd,
                    "phase": result.phase,
                    "kelly_fraction": result.kelly_fraction,
                },
                safety_dir=safety_dir,
            )
            out["telegram_sent"] = True
        except Exception as exc:
            out["telegram_sent"] = False
            out["telegram_error"] = str(exc)
    return out
