"""Flatten / key-revoke side-effect executor.

Kernel flags (flatten_requested, keys_revoked) are necessary but not sufficient.
This module turns those flags into actionable work items for TRENCH-OPS /
exchange adapters, and optionally invokes a pluggable closer.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .kernel import Position, RiskKernel
from .kill_switch import KillSwitch
from .observability import setup_logging

logger = setup_logging("flatten_executor")

FLATTEN_QUEUE = "flatten_queue.jsonl"
KEY_REVOKE_LOG = "key_revoke.jsonl"


@dataclass
class FlattenOrder:
    venue: str
    contract: str
    notional_usd: float
    side: str  # close side
    reason: str
    ts: float = field(default_factory=time.time)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PositionCloser(ABC):
    @abstractmethod
    def close(self, order: FlattenOrder) -> dict[str, Any]:
        ...


class MockPositionCloser(PositionCloser):
    def close(self, order: FlattenOrder) -> dict[str, Any]:
        return {
            "status": "mock_closed",
            "venue": order.venue,
            "contract": order.contract,
            "notional_usd": order.notional_usd,
            "note": "Mock closer — wire exchange/DEX closer for live",
        }


class KeyRevoker(ABC):
    @abstractmethod
    def revoke(self, venues: list[str], operator: str, reason: str) -> dict[str, Any]:
        ...


class MockKeyRevoker(KeyRevoker):
    def revoke(self, venues: list[str], operator: str, reason: str) -> dict[str, Any]:
        return {
            "status": "mock_revoked",
            "venues": venues,
            "operator": operator,
            "reason": reason,
            "note": "Mock revoke — disable exchange API keys operationally",
        }


class FlattenExecutor:
    """Reads kernel/kill flatten intent and enqueues close + revoke actions."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        closer: PositionCloser | None = None,
        revoker: KeyRevoker | None = None,
    ) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.closer = closer or MockPositionCloser()
        self.revoker = revoker or MockKeyRevoker()
        self.queue_path = self.safety_dir / FLATTEN_QUEUE
        self.revoke_path = self.safety_dir / KEY_REVOKE_LOG

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        record = {**record, "ts": time.time()}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    def build_orders_from_kernel(self, kernel: RiskKernel, reason: str) -> list[FlattenOrder]:
        orders: list[FlattenOrder] = []
        for pos in kernel.state.positions.values():
            close_side = "sell" if pos.notional_usd >= 0 else "buy"
            orders.append(
                FlattenOrder(
                    venue=pos.venue,
                    contract=pos.contract,
                    notional_usd=abs(pos.notional_usd),
                    side=close_side,
                    reason=reason,
                )
            )
        return orders

    def execute(
        self,
        kernel: RiskKernel,
        operator: str = "flatten_executor",
        reason: str = "flatten requested",
        revoke_keys: bool = True,
    ) -> dict[str, Any]:
        """Trigger kernel flatten flags, enqueue closes, optionally revoke keys."""
        flatten_result = kernel.trigger_flatten(revoke_keys=revoke_keys)
        orders = self.build_orders_from_kernel(kernel, reason)
        results: list[dict[str, Any]] = []
        for order in orders:
            self._append(self.queue_path, {"action": "enqueue", **order.to_dict()})
            try:
                close_result = self.closer.close(order)
                order.status = str(close_result.get("status", "closed"))
                self._append(
                    self.queue_path,
                    {"action": "close", **order.to_dict(), "result": close_result},
                )
                results.append(close_result)
            except Exception as exc:
                logger.error(f"close failed {order.venue}:{order.contract}: {exc}")
                order.status = "failed"
                self._append(
                    self.queue_path,
                    {"action": "close_failed", **order.to_dict(), "error": str(exc)},
                )

        revoke_result: dict[str, Any] | None = None
        if revoke_keys:
            venues = sorted({o.venue for o in orders}) or list(
                set(kernel.policy.allowed_venues)
            )
            revoke_result = self.revoker.revoke(venues, operator, reason)
            self._append(
                self.revoke_path,
                {"action": "revoke", "operator": operator, "reason": reason, **revoke_result},
            )
            # Halt signing node via file flag
            (self.safety_dir / "SIGNING_HALTED").write_text(
                json.dumps({"ts": time.time(), "reason": f"keys_revoked:{reason}"}),
                encoding="utf-8",
            )

        return {
            "ok": True,
            "flatten": flatten_result,
            "orders": [o.to_dict() for o in orders],
            "close_results": results,
            "revoke": revoke_result,
        }

    def pending_from_kill(self, ks: KillSwitch | None = None) -> bool:
        ks = ks or KillSwitch(self.safety_dir)
        if not ks.is_active():
            return False
        return bool(ks.load_state().flatten_requested)
