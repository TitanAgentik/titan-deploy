"""Deterministic risk kernel — non-LLM trade validation."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .policy_loader import Policy, load_policy
from .stealth_predatory import check_stealth_evasion


@dataclass
class TradeRequest:
    trade_id: str
    venue: str
    contract: str
    side: str
    notional_usd: float
    leverage: float = 1.0
    expected_price: float = 0.0
    worst_price: float = 0.0
    strategy_id: str = ""
    confidence: float = 0.0
    bft_votes: list[dict[str, Any]] = field(default_factory=list)
    uses_flash_loan: bool = False
    flash_loan_source: str = ""
    flash_loan_amount_usd: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TradeRequest:
        votes = data.get("bft_votes") or data.get("bftVotes") or []
        if not isinstance(votes, list):
            votes = []
        return cls(
            trade_id=str(data.get("trade_id", "")),
            venue=str(data.get("venue", "")),
            contract=str(data.get("contract", "")).lower(),
            side=str(data.get("side", "buy")),
            notional_usd=float(data.get("notional_usd", 0)),
            leverage=float(data.get("leverage", 1.0)),
            expected_price=float(data.get("expected_price", 0)),
            worst_price=float(data.get("worst_price", 0)),
            strategy_id=str(data.get("strategy_id", "")),
            confidence=float(data.get("confidence", 0.0)),
            bft_votes=[v for v in votes if isinstance(v, dict)],
            uses_flash_loan=bool(data.get("uses_flash_loan", data.get("usesFlashLoan", False))),
            flash_loan_source=str(data.get("flash_loan_source", data.get("flashLoanSource", ""))),
            flash_loan_amount_usd=float(
                data.get("flash_loan_amount_usd", data.get("flashLoanAmountUsd", 0))
            ),
        )


@dataclass
class ValidationResult:
    decision: str  # ALLOW | DENY
    reason: str
    code: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    venue: str
    contract: str
    notional_usd: float
    leverage: float = 1.0


class RiskKernelState:
    """In-memory kernel state — persisted optionally for restart survival."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path
        self.positions: dict[str, Position] = {}
        self.recent_losses: deque[tuple[float, float]] = deque(maxlen=500)
        self.halted: bool = False
        self.flatten_requested: bool = False
        self.keys_revoked: bool = False
        self.safe_mode_exposure_cap_pct: float | None = None
        self.halt_new_entries: bool = False
        self.drawdown_pct_24h: float = 0.0
        self._load()

    def _load(self) -> None:
        if self.state_path and self.state_path.exists():
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.halted = bool(data.get("halted", False))
            self.flatten_requested = bool(data.get("flatten_requested", False))
            self.keys_revoked = bool(data.get("keys_revoked", False))
            cap = data.get("safe_mode_exposure_cap_pct")
            self.safe_mode_exposure_cap_pct = float(cap) if cap is not None else None
            self.halt_new_entries = bool(data.get("halt_new_entries", False))
            self.drawdown_pct_24h = float(data.get("drawdown_pct_24h", 0.0))
            for k, p in data.get("positions", {}).items():
                self.positions[k] = Position(**p)
            for ts, amt in data.get("recent_losses", []):
                self.recent_losses.append((float(ts), float(amt)))

    def save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "halted": self.halted,
            "flatten_requested": self.flatten_requested,
            "keys_revoked": self.keys_revoked,
            "safe_mode_exposure_cap_pct": self.safe_mode_exposure_cap_pct,
            "halt_new_entries": self.halt_new_entries,
            "drawdown_pct_24h": self.drawdown_pct_24h,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "recent_losses": list(self.recent_losses),
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def aggregate_exposure(self) -> float:
        return sum(abs(p.notional_usd) for p in self.positions.values())

    def record_loss(self, amount_usd: float) -> None:
        self.recent_losses.append((time.time(), abs(amount_usd)))

    def loss_velocity_60s(self) -> float:
        cutoff = time.time() - 60.0
        return sum(amt for ts, amt in self.recent_losses if ts >= cutoff)

    def loss_velocity_window(self, seconds: float) -> float:
        cutoff = time.time() - seconds
        return sum(amt for ts, amt in self.recent_losses if ts >= cutoff)


class RiskKernel:
    """Independent deterministic risk authority."""

    def __init__(
        self,
        policy: Policy,
        state: RiskKernelState | None = None,
        kill_switch_active: bool = False,
        pipeline_halt_checker: Any | None = None,
        portfolio_simulator: Any | None = None,
        safety_dir: Path | None = None,
    ) -> None:
        self.policy = policy
        self.state = state or RiskKernelState()
        self.kill_switch_active = kill_switch_active
        self.pipeline_halt_checker = pipeline_halt_checker
        self.portfolio_simulator = portfolio_simulator
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")

    @classmethod
    def from_policy_path(
        cls,
        policy_path: str | Path,
        state_path: str | Path | None = None,
        kill_switch_active: bool = False,
        safety_dir: str | Path | None = None,
    ) -> RiskKernel:
        policy = load_policy(policy_path)
        sp = Path(str(state_path).replace("~", str(Path.home()))) if state_path else None
        state = RiskKernelState(sp) if sp else RiskKernelState()
        sd = Path(str(safety_dir).replace("~", str(Path.home()))) if safety_dir else None
        return cls(policy, state, kill_switch_active, safety_dir=sd)

    def _deny(self, code: str, reason: str, **details: Any) -> ValidationResult:
        return ValidationResult(decision="DENY", reason=reason, code=code, details=details)

    def _allow(self, reason: str = "within_limits") -> ValidationResult:
        return ValidationResult(decision="ALLOW", reason=reason, code="OK")

    def _validate_flash_loan(self, trade: TradeRequest) -> ValidationResult | None:
        """Return DENY result if flash-loan trade fails policy; None if OK."""
        is_paper = trade.venue.lower() == "paper"
        fl_raw = self.policy.raw.get("flash_loan_live") or {}
        requires_approval = bool(
            self.policy.raw.get("position_limits", {}).get("flash_loan_live_requires_approval", False)
        )

        if not is_paper:
            if not fl_raw.get("enabled", False):
                return self._deny(
                    "FLASH_LOAN_DISABLED",
                    "flash_loan_live.enabled is false — live flash loans blocked",
                )
            if requires_approval:
                from .promotion_gate import PromotionGate

                pg = PromotionGate(self.safety_dir)
                approved = pg.has_approved("flash_loan_live") or (
                    bool(trade.strategy_id) and pg.has_approved("flash_loan_live", trade.strategy_id)
                )
                if not approved:
                    return self._deny(
                        "FLASH_LOAN_NOT_APPROVED",
                        "Live flash loan requires operator YES on flash_loan_live promotion",
                        strategy_id=trade.strategy_id,
                    )

        fl_amount = trade.flash_loan_amount_usd or trade.notional_usd
        max_fl = float(fl_raw.get("max_amount_usd", 500_000.0))
        if fl_amount > max_fl:
            return self._deny(
                "FLASH_LOAN_AMOUNT",
                f"Flash loan amount {fl_amount} exceeds cap {max_fl}",
                amount=fl_amount,
                cap=max_fl,
            )

        if trade.flash_loan_source:
            allowed_sources: set[str] = set()
            for chain_sources in (fl_raw.get("sources") or {}).values():
                if isinstance(chain_sources, list):
                    allowed_sources.update(str(s).lower() for s in chain_sources)
            if allowed_sources and trade.flash_loan_source.lower() not in allowed_sources:
                return self._deny(
                    "FLASH_LOAN_SOURCE",
                    f"Flash loan source not allow-listed: {trade.flash_loan_source}",
                    source=trade.flash_loan_source,
                )

        if trade.strategy_id:
            pipelines = [str(p) for p in fl_raw.get("pipeline_ids", [])]
            if pipelines and trade.strategy_id not in pipelines and not is_paper:
                return self._deny(
                    "FLASH_LOAN_PIPELINE",
                    f"Pipeline {trade.strategy_id} not in flash_loan_live allowlist",
                    strategy_id=trade.strategy_id,
                )

        return None

    def validate_trade(self, trade: TradeRequest) -> ValidationResult:
        if self.kill_switch_active:
            return self._deny("KILL_SWITCH", "Global kill switch active — all trades denied")

        if self.pipeline_halt_checker and trade.strategy_id:
            if self.pipeline_halt_checker(trade.strategy_id):
                return self._deny(
                    "PIPELINE_HALT",
                    f"Pipeline halted: {trade.strategy_id}",
                    pipeline_id=trade.strategy_id,
                )

        if self.state.keys_revoked:
            return self._deny("KEYS_REVOKED", "API keys revoked by risk kernel")

        if self.state.halted:
            return self._deny("HALTED", "Trading halted by risk kernel")

        if not self.policy.enforce:
            return self._allow("policy_monitor_mode")

        stealth_deny = check_stealth_evasion(trade, self.policy)
        if stealth_deny is not None:
            return ValidationResult(
                decision=stealth_deny.decision,
                reason=stealth_deny.reason,
                code=stealth_deny.code,
                details=stealth_deny.details,
            )

        limits = self.policy.trading_limits

        if trade.venue not in self.policy.allowed_venues:
            return self._deny(
                "VENUE_DENIED",
                f"Venue not allow-listed: {trade.venue}",
                venue=trade.venue,
            )

        if self.policy.allowed_contracts and trade.contract not in self.policy.allowed_contracts:
            return self._deny(
                "CONTRACT_DENIED",
                f"Contract not allow-listed: {trade.contract}",
                contract=trade.contract,
            )

        if trade.uses_flash_loan:
            fl_result = self._validate_flash_loan(trade)
            if fl_result is not None:
                return fl_result

        if trade.notional_usd <= 0:
            return self._deny("INVALID_NOTIONAL", "Notional must be positive")

        if trade.notional_usd > limits.max_notional_usd_per_trade:
            return self._deny(
                "NOTIONAL_CAP",
                f"Per-trade notional {trade.notional_usd} exceeds cap {limits.max_notional_usd_per_trade}",
                notional=trade.notional_usd,
                cap=limits.max_notional_usd_per_trade,
            )

        pct = (trade.notional_usd / limits.equity_usd) * 100.0 if limits.equity_usd else 100.0
        max_pct = self.policy.raw.get("position_limits", {}).get("max_equity_pct_per_trade", 2.0)
        if pct > float(max_pct):
            return self._deny(
                "EQUITY_PCT",
                f"Trade {pct:.2f}% equity exceeds {max_pct}% cap",
                pct_equity=pct,
            )

        projected = self.state.aggregate_exposure() + abs(trade.notional_usd)
        if projected > limits.max_aggregate_exposure_usd:
            return self._deny(
                "EXPOSURE_CAP",
                f"Aggregate exposure {projected} would exceed cap {limits.max_aggregate_exposure_usd}",
                projected=projected,
            )

        if trade.leverage > limits.max_leverage:
            return self._deny(
                "LEVERAGE_CAP",
                f"Leverage {trade.leverage} exceeds cap {limits.max_leverage}",
            )

        open_count = len(self.state.positions)
        pos_key = f"{trade.venue}:{trade.contract}"
        if pos_key not in self.state.positions and open_count >= limits.max_open_positions:
            return self._deny(
                "POSITION_COUNT",
                f"Open positions {open_count} at cap {limits.max_open_positions}",
            )

        velocity = self.state.loss_velocity_60s()
        if velocity > limits.max_loss_velocity_usd_per_60s:
            return self._deny(
                "LOSS_VELOCITY",
                f"60s loss velocity {velocity} exceeds cap {limits.max_loss_velocity_usd_per_60s}",
            )

        velocity_15m = self.state.loss_velocity_window(900.0)
        max_15m = float(
            self.policy.raw.get("drawdown_velocity", {}).get(
                "max_loss_usd_per_15m", limits.max_loss_velocity_usd_per_60s * 3
            )
        )
        if velocity_15m > max_15m:
            return self._deny(
                "LOSS_VELOCITY_15M",
                f"15m loss velocity {velocity_15m} exceeds cap {max_15m}",
            )

        human_pct = float(
            self.policy.raw.get("position_limits", {}).get("human_approval_above_pct", 1.0)
        )
        auto_cfg = (self.policy.raw or {}).get("autonomous_signing") or {}
        autonomous = bool(auto_cfg.get("enabled", False))

        if pct > human_pct:
            if autonomous:
                from .trade_verifier import verify_agent_authorization

                v = verify_agent_authorization(
                    trade,
                    self.policy.raw or {},
                    limits.equity_usd,
                    self.safety_dir,
                )
                if not v.ok:
                    return self._deny(
                        v.code or "AGENT_VERIFY_DENIED",
                        v.reason,
                        **v.details,
                    )
            else:
                return self._deny(
                    "HUMAN_APPROVAL_REQUIRED",
                    f"Trade {pct:.2f}% equity exceeds {human_pct}% human-approval threshold",
                    pct_equity=pct,
                )
        elif autonomous and trade.venue.lower() != "paper":
            from .trade_verifier import verify_agent_authorization

            v = verify_agent_authorization(
                trade,
                self.policy.raw or {},
                limits.equity_usd,
                self.safety_dir,
            )
            if not v.ok:
                return self._deny(
                    v.code or "AGENT_VERIFY_DENIED",
                    v.reason,
                    **v.details,
                )

        if self.state.safe_mode_exposure_cap_pct is not None:
            cap_pct = self.state.safe_mode_exposure_cap_pct
            exp_pct = (projected / limits.equity_usd * 100.0) if limits.equity_usd else 100.0
            if exp_pct > cap_pct:
                return self._deny(
                    "SAFE_MODE",
                    f"Safe mode exposure cap {cap_pct}% — projected {exp_pct:.1f}%",
                )

        if trade.expected_price > 0 and trade.worst_price > 0:
            slip_bps = abs(trade.worst_price - trade.expected_price) / trade.expected_price * 10000
            if slip_bps > limits.max_slippage_bps:
                return self._deny(
                    "SLIPPAGE",
                    f"Pre-trade slippage {slip_bps:.1f}bps exceeds cap {limits.max_slippage_bps}bps",
                    slippage_bps=slip_bps,
                )

        if self.portfolio_simulator and trade.strategy_id:
            sim = self.portfolio_simulator(trade)
            if sim and sim.get("decision") == "DENY":
                return self._deny(
                    sim.get("code", "PORTFOLIO_RISK"),
                    sim.get("reason", "Portfolio risk simulation denied"),
                    **{k: v for k, v in sim.items() if k not in ("decision", "reason", "code")},
                )

        from .drawdown_tiers import DrawdownTierEngine

        dd_engine = DrawdownTierEngine(self.policy.raw or {})
        dd_deny = dd_engine.check_trade(
            self.state.drawdown_pct_24h, trade, state=self.state
        )
        if dd_deny is not None:
            code, reason = dd_deny
            return self._deny(code, reason, drawdown_pct=self.state.drawdown_pct_24h)

        return self._allow()

    def apply_fill(self, trade: TradeRequest) -> None:
        key = f"{trade.venue}:{trade.contract}"
        existing = self.state.positions.get(key)
        if existing:
            sign = 1 if trade.side.lower() in ("buy", "long") else -1
            existing.notional_usd += sign * trade.notional_usd
            if abs(existing.notional_usd) < 0.01:
                del self.state.positions[key]
        else:
            self.state.positions[key] = Position(
                venue=trade.venue,
                contract=trade.contract,
                notional_usd=trade.notional_usd,
                leverage=trade.leverage,
            )
        self.state.save()

    def trigger_flatten(self, revoke_keys: bool = True) -> dict[str, Any]:
        self.state.halted = True
        self.state.flatten_requested = True
        if revoke_keys:
            self.state.keys_revoked = True
        self.state.save()
        return {
            "action": "FLATTEN",
            "halted": True,
            "keys_revoked": self.state.keys_revoked,
            "positions": len(self.state.positions),
        }

    def clear_positions(self) -> None:
        self.state.positions.clear()
        self.state.flatten_requested = False
        self.state.save()

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "halted": self.state.halted,
            "kill_switch": self.kill_switch_active,
            "keys_revoked": self.state.keys_revoked,
            "open_positions": len(self.state.positions),
            "aggregate_exposure": self.state.aggregate_exposure(),
            "loss_velocity_60s": self.state.loss_velocity_60s(),
            "loss_velocity_15m": self.state.loss_velocity_window(900.0),
        }
