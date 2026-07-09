"""Position reconciliation — believed vs exchange truth gate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from .policy_loader import Policy, ReconciliationConfig


@dataclass
class BelievedPosition:
    venue: str
    contract: str
    notional_usd: float
    side: str = "long"


@dataclass
class ReconciliationResult:
    decision: str  # ALLOW | DENY | HALT
    reason: str
    code: str = ""
    divergences: list[dict[str, Any]] = field(default_factory=list)
    halted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "code": self.code,
            "divergences": self.divergences,
            "halted": self.halted,
        }


class PositionAdapter(ABC):
    """Pluggable adapter for on-chain / exchange position truth."""

    @abstractmethod
    def fetch_positions(self) -> list[BelievedPosition]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class MockPaperAdapter(PositionAdapter):
    """Paper/mock adapter for testing without live keys."""

    def __init__(self, positions: list[BelievedPosition] | None = None) -> None:
        self._positions = positions or []

    @property
    def name(self) -> str:
        return "mock"

    def fetch_positions(self) -> list[BelievedPosition]:
        return list(self._positions)

    def set_positions(self, positions: list[BelievedPosition]) -> None:
        self._positions = list(positions)


class LiveExchangeAdapter(PositionAdapter):
    """Live exchange/on-chain position truth adapter.

    Wire a concrete fetcher (REST/RPC) via ``fetcher`` callable that returns
    list[BelievedPosition] or list[dict]. Until wired, construction succeeds
    but fetch raises — forcing fail-closed rather than silent mock matches.
    """

    def __init__(
        self,
        fetcher: Any = None,
        venues: list[str] | None = None,
        name: str = "live",
    ) -> None:
        self._fetcher = fetcher
        self._venues = venues or []
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def fetch_positions(self) -> list[BelievedPosition]:
        if self._fetcher is None:
            raise RuntimeError(
                "LiveExchangeAdapter has no fetcher wired — refuse to invent positions. "
                "Set reconciliation.adapter=mock only for paper, or provide a fetcher."
            )
        raw = self._fetcher(self._venues)
        out: list[BelievedPosition] = []
        for p in raw:
            if isinstance(p, BelievedPosition):
                out.append(p)
            else:
                out.append(
                    BelievedPosition(
                        venue=str(p["venue"]),
                        contract=str(p["contract"]).lower(),
                        notional_usd=float(p["notional_usd"]),
                        side=str(p.get("side", "long")),
                    )
                )
        return out


def assert_adapter_allowed_for_policy(adapter_name: str, policy: Policy) -> None:
    """Raise if enforce mode + live venues still use mock reconciliation."""
    venues = [v.lower() for v in policy.allowed_venues]
    live = [v for v in venues if v not in ("paper", "mock", "test")]
    if policy.enforce and live and adapter_name == "mock":
        raise ValueError(
            f"MOCK_ADAPTER_FORBIDDEN: mode=enforce with live venues {live} "
            "but reconciliation.adapter=mock. Wire a live adapter before trading."
        )


def get_adapter(name: str, **kwargs: Any) -> PositionAdapter:
    if name == "mock":
        return MockPaperAdapter(kwargs.get("positions"))
    if name in ("live", "exchange", "onchain", "live_exchange"):
        return LiveExchangeAdapter(
            fetcher=kwargs.get("fetcher"),
            venues=kwargs.get("venues"),
            name=name if name != "live_exchange" else "live",
        )
    raise ValueError(f"Unknown reconciliation adapter: {name}")


class ReconciliationService:
    """Blocking pre-trade gate comparing believed vs actual positions."""

    def __init__(
        self,
        policy: Policy,
        adapter: PositionAdapter | None = None,
    ) -> None:
        self.config: ReconciliationConfig = policy.reconciliation
        self.adapter = adapter or get_adapter(self.config.adapter)
        self._halted = False

    def reconcile(
        self,
        believed: list[BelievedPosition],
        pending_notional: float = 0.0,
    ) -> ReconciliationResult:
        if self._halted:
            return ReconciliationResult(
                decision="DENY",
                reason="Reconciliation service halted due to prior divergence",
                code="RECON_HALTED",
                halted=True,
            )

        actual = self.adapter.fetch_positions()
        divergences: list[dict[str, Any]] = []

        believed_map = {(p.venue, p.contract): p for p in believed}
        actual_map = {(p.venue, p.contract): p for p in actual}
        all_keys = set(believed_map) | set(actual_map)

        for key in all_keys:
            b = believed_map.get(key)
            a = actual_map.get(key)
            b_notional = abs(b.notional_usd) if b else 0.0
            a_notional = abs(a.notional_usd) if a else 0.0
            diff = abs(b_notional - a_notional)
            if diff <= 0.01:
                continue
            pct = (diff / max(b_notional, a_notional, 1.0)) * 100.0
            divergences.append(
                {
                    "venue": key[0],
                    "contract": key[1],
                    "believed_usd": b_notional,
                    "actual_usd": a_notional,
                    "diff_usd": diff,
                    "diff_pct": pct,
                }
            )

        for d in divergences:
            if d["diff_usd"] > self.config.divergence_threshold_usd:
                self._halted = True
                return ReconciliationResult(
                    decision="HALT",
                    reason=f"Position divergence ${d['diff_usd']:.2f} exceeds threshold",
                    code="DIVERGENCE_USD",
                    divergences=divergences,
                    halted=True,
                )
            if d["diff_pct"] > self.config.divergence_threshold_pct:
                self._halted = True
                return ReconciliationResult(
                    decision="HALT",
                    reason=f"Position divergence {d['diff_pct']:.2f}% exceeds threshold",
                    code="DIVERGENCE_PCT",
                    divergences=divergences,
                    halted=True,
                )

        return ReconciliationResult(
            decision="ALLOW",
            reason="positions reconciled",
            code="OK",
            divergences=divergences,
        )

    def pre_trade_gate(
        self,
        believed: list[BelievedPosition],
        pending: BelievedPosition,
    ) -> ReconciliationResult:
        result = self.reconcile(believed, pending.notional_usd)
        if result.decision != "ALLOW":
            return result
        return ReconciliationResult(decision="ALLOW", reason="pre-trade reconciliation passed")

    def reset_halt(self) -> None:
        self._halted = False

    def health(self) -> dict[str, Any]:
        return {
            "status": "halted" if self._halted else "ok",
            "adapter": self.adapter.name,
            "halted": self._halted,
        }
