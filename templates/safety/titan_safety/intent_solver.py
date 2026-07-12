"""Intent solver scaffold — stub submit to MEV-shielded solver networks.

Honest STUB until operator wires CoW/UniswapX/Across endpoints.
Does NOT bypass broadcast authority or risk kernel.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .kernel import TradeRequest
from .tier4_gate import tier4_active, tier4_cfg


@dataclass
class IntentSubmission:
    trade: TradeRequest | dict[str, Any]
    solver_network: str = "stub"
    calldata: dict[str, Any] | None = None
    typed_data: dict[str, Any] | None = None
    mev_tip_bps: float = 0.0
    ts: float = field(default_factory=time.time)

    def body(self) -> dict[str, Any]:
        trade = self.trade.__dict__ if isinstance(self.trade, TradeRequest) else self.trade
        return {
            "trade": trade,
            "solver_network": self.solver_network,
            "calldata": self.calldata,
            "typed_data": self.typed_data,
            "mev_tip_bps": self.mev_tip_bps,
        }


@dataclass
class IntentSolverResult:
    decision: str  # ALLOW | DENY | STUB
    reason: str
    code: str = ""
    intent_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntentSolverClient:
    """Stub client — records intent locally; no live solver RPC until wired."""

    def __init__(self, policy_raw: dict[str, Any] | None = None) -> None:
        self.policy_raw = policy_raw or {}
        self.cfg = tier4_cfg(self.policy_raw).get("intent_solver") or {}

    def is_available(self) -> bool:
        if not tier4_active(self.policy_raw):
            return False
        return bool(self.cfg.get("enabled", False))

    def submit(self, submission: IntentSubmission) -> IntentSolverResult:
        if not tier4_active(self.policy_raw):
            return IntentSolverResult(
                decision="DENY",
                reason="tier4_ultimate not active — intent solver gated",
                code="TIER4_INACTIVE",
            )
        if not self.cfg.get("enabled", False):
            return IntentSolverResult(
                decision="DENY",
                reason="intent_solver.enabled is false",
                code="INTENT_SOLVER_DISABLED",
            )

        trade = (
            submission.trade
            if isinstance(submission.trade, TradeRequest)
            else TradeRequest.from_dict(submission.trade)
        )
        networks = [str(n) for n in self.cfg.get("networks") or []]
        network = submission.solver_network
        if networks and network not in networks and network != "stub":
            return IntentSolverResult(
                decision="DENY",
                reason=f"solver network {network!r} not allow-listed",
                code="SOLVER_NETWORK_DENIED",
            )

        intent_id = f"intent-stub-{uuid.uuid4().hex[:12]}"
        if self.cfg.get("stub_submit", True):
            return IntentSolverResult(
                decision="STUB",
                reason="stub submit — no live solver RPC configured",
                code="INTENT_STUB",
                intent_id=intent_id,
                details={
                    "trade_id": trade.trade_id,
                    "solver_network": network,
                    "mev_tip_bps": submission.mev_tip_bps,
                    "note": "Wire solver endpoint in tier4_ultimate.intent_solver before live",
                },
            )

        return IntentSolverResult(
            decision="DENY",
            reason="live solver submit not implemented in scaffold",
            code="INTENT_LIVE_NOT_WIRED",
        )
