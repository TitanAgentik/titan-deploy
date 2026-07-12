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
FLATTEN_RESUME_STATE = "flatten_resume_state.json"


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


class SigningNodeCloser(PositionCloser):
    """Closes positions via in-process SigningNode (default) or legacy HTTP.

    Each close order gets a fresh gate receipt (issued locally — the flatten
    path is the emergency exit, so it must not depend on recon/kernel being
    healthy), then signs in-process. Set mode=http + endpoint for legacy :19010.
    """

    def __init__(
        self,
        endpoint: str = "",
        safety_dir: Path | None = None,
        timeout: float = 10.0,
        mode: str = "in_process",
        policy_path: Path | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> None:
        self.endpoint = (endpoint or "").rstrip("/")
        self.safety_dir = safety_dir
        self.timeout = timeout
        self.mode = mode
        self.policy_path = policy_path
        self.policy_raw = policy_raw or {}

    def close(self, order: FlattenOrder) -> dict[str, Any]:
        import uuid

        from .gate_receipt import RECEIPT_HEADER, issue_gate_receipt
        from .signing_service import build_signing_node

        trade = {
            "trade_id": f"flatten-{uuid.uuid4().hex[:12]}",
            "venue": order.venue,
            "contract": order.contract,
            "side": order.side,
            "notional_usd": order.notional_usd,
            "leverage": 1.0,
            "expected_price": 0.0,
            "worst_price": 0.0,
        }
        receipt = issue_gate_receipt(trade, self.safety_dir)
        body = {"trade": trade, "reduce_only": True, "gate_receipt": receipt.token}
        headers = {RECEIPT_HEADER: receipt.token}

        if self.mode == "http" and self.endpoint:
            import urllib.request

            req = urllib.request.Request(
                f"{self.endpoint}/v1/sign",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    RECEIPT_HEADER: receipt.token,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return {"status": payload.get("status", "submitted"), **payload}

        node = build_signing_node(
            policy_path=self.policy_path,
            safety_dir=self.safety_dir,
            policy_raw=self.policy_raw,
            require_live_signer=False,
        )
        _code, payload = node.sign(body, headers)
        return {"status": payload.get("status", "submitted"), **payload}


class BroadcastAuthorityCloser(PositionCloser):
    """Close positions via single broadcast authority path (Tier 0)."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        policy_raw: dict[str, Any] | None = None,
        policy_path: Path | None = None,
    ) -> None:
        from .broadcast_authority import BroadcastAuthority, BroadcastSubmission
        from .signing_service import build_signing_node

        self.safety_dir = safety_dir
        self.policy_raw = policy_raw or {}
        self.policy_path = policy_path
        self._BroadcastSubmission = BroadcastSubmission
        self._authority = BroadcastAuthority(policy_raw=self.policy_raw, safety_dir=safety_dir)
        self._signing_node = build_signing_node(
            policy_path=policy_path,
            safety_dir=safety_dir,
            policy_raw=self.policy_raw,
            require_live_signer=False,
        )

    def close(self, order: FlattenOrder) -> dict[str, Any]:
        import uuid

        from .adapters.hyperliquid_live import HyperliquidLiveAdapter, HyperliquidOrder
        from .gate_receipt import RECEIPT_HEADER, issue_gate_receipt

        trade = {
            "trade_id": f"flatten-{uuid.uuid4().hex[:12]}",
            "venue": order.venue,
            "contract": order.contract,
            "side": order.side,
            "notional_usd": order.notional_usd,
            "leverage": 1.0,
            "expected_price": 0.0,
            "worst_price": 0.0,
            "reduce_only": True,
        }
        receipt = issue_gate_receipt(trade, self.safety_dir)
        adapter = HyperliquidLiveAdapter(safety_dir=self.safety_dir)
        if order.venue.lower() == "hyperliquid":
            hl_order = HyperliquidOrder(
                trade_id=trade["trade_id"],
                venue=order.venue,
                contract=order.contract,
                side=order.side,
                notional_usd=order.notional_usd,
                reduce_only=True,
            )
            quote = adapter.quote(hl_order)
            sim = adapter.simulate(hl_order, quote)
            signed = adapter.sign(hl_order, sim, self._signing_node, receipt.token)
            submission = self._BroadcastSubmission(
                caller_id="flatten_executor",
                trade=trade,
                gate_receipt=receipt.token,
                typed_data=signed.get("typed_data"),
                reduce_only=True,
            )
            body = submission.body()
            body["signed"] = signed
            submission.typed_data = signed.get("typed_data")
            result = self._authority.submit(submission)
            return {
                "status": result.submit_status or result.decision.lower(),
                "broadcast": result.to_dict(),
                "signed": {k: v for k, v in signed.items() if k != "typed_data"},
            }

        # Non-HL venues: sign + broadcast stub
        body = {"trade": trade, "gate_receipt": receipt.token, "reduce_only": True}
        headers = {RECEIPT_HEADER: receipt.token}
        _code, payload = self._signing_node.sign(body, headers)
        submission = self._BroadcastSubmission(
            caller_id="flatten_executor",
            trade=trade,
            gate_receipt=receipt.token,
            reduce_only=True,
        )
        result = self._authority.submit(submission)
        return {"status": result.submit_status or payload.get("status", "submitted"), **result.to_dict()}


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


def validate_flatten_config_for_live(policy: Any) -> None:
    """Fail-closed startup check: live profile must not rely on mock closer/revoker.

    Call at service startup (risk kernel) so a live deployment refuses to come
    up until flatten.closer / flatten.revoker are wired to real adapters.
    """
    from .policy_loader import capital_profile_of

    if capital_profile_of(policy) != "live":
        return
    cfg = (policy.raw or {}).get("flatten", {})
    closer = str(cfg.get("closer", "mock")).lower()
    revoker = str(cfg.get("revoker", "mock")).lower()
    if closer == "mock":
        raise ValueError(
            "capital_profile=live requires flatten.closer (signing_node / "
            "in_process or module:attr) — mock closer banned for live"
        )
    if revoker == "mock":
        raise ValueError(
            "capital_profile=live requires flatten.revoker (module:attr) — "
            "mock revoker banned for live"
        )


class FlattenExecutor:
    """Reads kernel/kill flatten intent and enqueues close + revoke actions."""

    @classmethod
    def from_policy(cls, policy: Any, safety_dir: Path | None = None) -> "FlattenExecutor":
        """Build closer/revoker from policy `flatten:` section.

        closer: mock | signing_node | in_process | "module.path:ClassOrFactory"
        revoker: mock | "module.path:ClassOrFactory"
        """
        from .policy_loader import load_component
        from .signing_service import resolve_signing_mode

        cfg = (policy.raw or {}).get("flatten", {}) if getattr(policy, "raw", None) else {}
        closer_spec = str(cfg.get("closer", "mock"))
        revoker_spec = str(cfg.get("revoker", "mock"))
        raw = getattr(policy, "raw", None) or {}
        mode = resolve_signing_mode(raw)
        if str(cfg.get("signing_mode", "")).strip().lower() in ("http", "legacy"):
            mode = "http"

        closer: PositionCloser
        if closer_spec.lower() == "mock":
            closer = MockPositionCloser()
        elif closer_spec.lower() in ("broadcast_authority", "broadcast"):
            closer = BroadcastAuthorityCloser(
                safety_dir=safety_dir,
                policy_raw=raw,
                policy_path=getattr(policy, "source_path", None),
            )
        elif closer_spec.lower() in ("signing_node", "in_process"):
            endpoint = str(cfg.get("signing_endpoint", "") or "")
            use_mode = "http" if mode == "http" else "in_process"
            if use_mode == "http" and not endpoint:
                endpoint = "http://127.0.0.1:19010"
            closer = SigningNodeCloser(
                endpoint=endpoint,
                safety_dir=safety_dir,
                mode=use_mode,
                policy_path=getattr(policy, "source_path", None),
                policy_raw=raw,
            )
        else:
            loaded = load_component(closer_spec)
            closer = loaded() if isinstance(loaded, type) else loaded

        revoker: KeyRevoker
        if revoker_spec.lower() == "mock":
            revoker = MockKeyRevoker()
        else:
            loaded = load_component(revoker_spec)
            revoker = loaded() if isinstance(loaded, type) else loaded

        return cls(safety_dir=safety_dir, closer=closer, revoker=revoker)

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
        self.resume_path = self.safety_dir / FLATTEN_RESUME_STATE

    def _save_resume_state(
        self,
        run_id: str,
        orders: list[FlattenOrder],
        completed: list[int],
        status: str,
        reason: str,
    ) -> None:
        state = {
            "run_id": run_id,
            "reason": reason,
            "status": status,
            "completed_indices": completed,
            "orders": [o.to_dict() for o in orders],
            "ts": time.time(),
        }
        self.resume_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _load_resume_state(self) -> dict[str, Any] | None:
        if not self.resume_path.exists():
            return None
        try:
            return json.loads(self.resume_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _clear_resume_state(self) -> None:
        if self.resume_path.exists():
            self.resume_path.unlink()

    def resume_flatten(
        self,
        kernel: RiskKernel | None = None,
        operator: str = "flatten_executor",
    ) -> dict[str, Any]:
        """Idempotent resume after mid-flatten kill — continues pending close orders."""
        state = self._load_resume_state()
        if not state or state.get("status") == "completed":
            return {"ok": True, "status": "nothing_to_resume"}

        run_id = str(state.get("run_id", ""))
        completed = list(state.get("completed_indices", []))
        orders_raw = state.get("orders", [])
        reason = str(state.get("reason", "resume flatten"))
        results: list[dict[str, Any]] = []

        for idx, raw in enumerate(orders_raw):
            if idx in completed:
                continue
            order = FlattenOrder(
                venue=str(raw["venue"]),
                contract=str(raw["contract"]),
                side=str(raw["side"]),
                notional_usd=float(raw["notional_usd"]),
                reason=reason,
                status=str(raw.get("status", "pending")),
            )
            try:
                close_result = self.closer.close(order)
                order.status = str(close_result.get("status", "closed"))
                completed.append(idx)
                self._save_resume_state(run_id, [order], completed, "in_progress", reason)
                self._append(
                    self.queue_path,
                    {"action": "resume_close", **order.to_dict(), "result": close_result},
                )
                results.append(close_result)
            except Exception as exc:
                logger.error(f"resume close failed {order.venue}:{order.contract}: {exc}")
                self._save_resume_state(run_id, [], completed, "failed", reason)
                return {
                    "ok": False,
                    "status": "failed",
                    "completed": len(completed),
                    "error": str(exc),
                    "results": results,
                }

        self._save_resume_state(run_id, [], completed, "completed", reason)
        if kernel is not None:
            kernel.trigger_flatten(revoke_keys=False)
        return {"ok": True, "status": "completed", "results": results, "completed": len(completed)}

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
        import uuid

        flatten_result = kernel.trigger_flatten(revoke_keys=revoke_keys)
        orders = self.build_orders_from_kernel(kernel, reason)
        run_id = uuid.uuid4().hex[:16]
        completed: list[int] = []
        self._save_resume_state(run_id, orders, completed, "in_progress", reason)
        results: list[dict[str, Any]] = []
        for idx, order in enumerate(orders):
            self._append(self.queue_path, {"action": "enqueue", **order.to_dict()})
            try:
                close_result = self.closer.close(order)
                order.status = str(close_result.get("status", "closed"))
                completed.append(idx)
                self._save_resume_state(run_id, orders, completed, "in_progress", reason)
                self._append(
                    self.queue_path,
                    {"action": "close", **order.to_dict(), "result": close_result},
                )
                results.append(close_result)
            except Exception as exc:
                logger.error(f"close failed {order.venue}:{order.contract}: {exc}")
                order.status = "failed"
                self._save_resume_state(run_id, orders, completed, "failed", reason)
                self._append(
                    self.queue_path,
                    {"action": "close_failed", **order.to_dict(), "error": str(exc)},
                )
                return {
                    "ok": False,
                    "flatten": flatten_result,
                    "orders": [o.to_dict() for o in orders],
                    "close_results": results,
                    "resume": True,
                    "run_id": run_id,
                    "error": str(exc),
                }

        self._save_resume_state(run_id, orders, completed, "completed", reason)

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
