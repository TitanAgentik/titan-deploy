"""Single broadcast authority — only TRENCH-OPS / execution daemon may submit txs.

Agents never hold hot keys. Every submission requires:
  1. ALLOW gate receipt bound to trade
  2. Payload hash bound to calldata / typed_data
  3. Caller identity in the broadcast allowlist (agents denied)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .gate_receipt import verify_gate_receipt
from .kernel import TradeRequest
from .observability import setup_logging
from .trade_verifier import compute_payload_hash, verify_receipt_payload_binding

logger = setup_logging("broadcast_authority")

# Only execution paths may broadcast — LLM agents are advisory-only.
DEFAULT_BROADCAST_CALLERS = frozenset(
    {
        "trench-ops",
        "trench_ops",
        "execution_daemon",
        "flatten_executor",
        "broadcast_authority",
    }
)

# Explicit deny — agents must never submit directly.
AGENT_CALLER_DENY = frozenset(
    {
        "archon",
        "cortex",
        "guardian",
        "sentinel",
        "oracle",
        "wraith",
        "predator",
        "augur",
        "narrative",
        "lamarck",
        "darwin_godel",
        "herald",
        "nexus",
        "forge",
        "alchemy",
        "atlas",
        "quant",
        "arbiter",
        "horizon",
        "hyperion",
    }
)

BROADCAST_AUDIT = "broadcast_audit.jsonl"


@dataclass
class BroadcastSubmission:
    caller_id: str
    trade: TradeRequest | dict[str, Any]
    gate_receipt: str
    calldata: dict[str, Any] | None = None
    typed_data: dict[str, Any] | None = None
    venue_adapter: str = ""
    reduce_only: bool = False
    ts: float = field(default_factory=time.time)

    def body(self) -> dict[str, Any]:
        return {
            "trade": self.trade.__dict__ if isinstance(self.trade, TradeRequest) else self.trade,
            "calldata": self.calldata,
            "typed_data": self.typed_data,
            "gate_receipt": self.gate_receipt,
            "reduce_only": self.reduce_only,
        }


@dataclass
class BroadcastResult:
    decision: str  # ALLOW | DENY
    reason: str
    code: str = ""
    submit_status: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def tier0_cfg(policy_raw: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": False,
        "broadcast_authority_enforced": True,
        "venue": "hyperliquid",
        "venue_adapter": "titan_safety.adapters.hyperliquid_live:HyperliquidLiveAdapter",
        "allowed_callers": sorted(DEFAULT_BROADCAST_CALLERS),
        "agent_submit_denied": True,
        "require_payload_hash_binding": True,
    }
    cfg = dict(defaults)
    cfg.update((policy_raw or {}).get("tier0_money_path") or {})
    return cfg


def validate_broadcast_caller(caller_id: str, policy_raw: dict[str, Any]) -> tuple[bool, str]:
    """Return (ok, reason). Agents are always denied when agent_submit_denied."""
    cfg = tier0_cfg(policy_raw)
    if not cfg.get("broadcast_authority_enforced", True):
        return True, "broadcast authority not enforced"

    cid = caller_id.strip().lower().replace("-", "_")
    if cfg.get("agent_submit_denied", True) and cid in AGENT_CALLER_DENY:
        return False, f"agent caller {caller_id!r} denied — advisory only"

    allowed = {c.lower().replace("-", "_") for c in cfg.get("allowed_callers", [])}
    allowed |= {c.lower().replace("-", "_") for c in DEFAULT_BROADCAST_CALLERS}
    if cid not in allowed:
        return False, f"caller {caller_id!r} not in broadcast allowlist"
    return True, "ok"


def validate_submission_bundle(
    submission: BroadcastSubmission,
    policy_raw: dict[str, Any],
    safety_dir: Path | None = None,
    max_receipt_age: int = 30,
) -> tuple[bool, str, str]:
    """Validate gate receipt + payload hash binding. Returns (ok, reason, code)."""
    trade = (
        submission.trade
        if isinstance(submission.trade, TradeRequest)
        else TradeRequest.from_dict(submission.trade)
    )
    cfg = tier0_cfg(policy_raw)

    ok_caller, caller_reason = validate_broadcast_caller(submission.caller_id, policy_raw)
    if not ok_caller:
        return False, caller_reason, "BROADCAST_CALLER_DENIED"

    if not submission.gate_receipt:
        return False, "missing gate receipt", "GATE_RECEIPT_MISSING"

    ok_receipt, receipt_reason = verify_gate_receipt(
        submission.gate_receipt, trade, safety_dir, max_receipt_age
    )
    if not ok_receipt:
        return False, receipt_reason, "GATE_RECEIPT_INVALID"

    body = submission.body()
    if cfg.get("require_payload_hash_binding", True) and trade.venue.lower() != "paper":
        ok_bind, bind_reason = verify_receipt_payload_binding(
            submission.gate_receipt, trade, body, policy_raw
        )
        if not ok_bind:
            return False, bind_reason, "PAYLOAD_HASH_MISMATCH"

    return True, "ok", "OK"


class BroadcastAuthority:
    """Single submitter enforcement — delegates to venue adapter after validation."""

    def __init__(
        self,
        policy_raw: dict[str, Any] | None = None,
        safety_dir: Path | None = None,
        venue_submit: Callable[[BroadcastSubmission, TradeRequest], dict[str, Any]] | None = None,
    ) -> None:
        self.policy_raw = policy_raw or {}
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self._venue_submit = venue_submit
        self._audit_path = self.safety_dir / BROADCAST_AUDIT

    def _audit(self, record: dict[str, Any]) -> None:
        record = {**record, "ts": time.time()}
        with self._audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    def _resolve_venue_submit(
        self,
    ) -> Callable[[BroadcastSubmission, TradeRequest], dict[str, Any]]:
        if self._venue_submit is not None:
            return self._venue_submit
        cfg = tier0_cfg(self.policy_raw)
        spec = str(cfg.get("venue_adapter", "")).strip()
        if not spec:
            raise RuntimeError("tier0_money_path.venue_adapter not configured")

        from .policy_loader import load_component

        loaded = load_component(spec)
        adapter = loaded() if isinstance(loaded, type) else loaded
        if hasattr(adapter, "submit_signed"):
            return adapter.submit_signed
        if callable(adapter):
            return adapter
        raise RuntimeError(f"venue adapter {spec!r} has no submit_signed method")

    def submit(self, submission: BroadcastSubmission, max_receipt_age: int = 30) -> BroadcastResult:
        """Authoritative submit path — DENY on any validation failure."""
        ok, reason, code = validate_submission_bundle(
            submission, self.policy_raw, self.safety_dir, max_receipt_age
        )
        trade = (
            submission.trade
            if isinstance(submission.trade, TradeRequest)
            else TradeRequest.from_dict(submission.trade)
        )
        payload_hash = compute_payload_hash(submission.body())

        if not ok:
            self._audit(
                {
                    "action": "deny",
                    "caller_id": submission.caller_id,
                    "trade_id": trade.trade_id,
                    "code": code,
                    "reason": reason,
                    "payload_hash": payload_hash,
                }
            )
            return BroadcastResult(decision="DENY", reason=reason, code=code)

        try:
            submit_fn = self._resolve_venue_submit()
            venue_result = submit_fn(submission, trade)
        except Exception as exc:
            logger.error(f"venue submit failed: {exc}")
            self._audit(
                {
                    "action": "submit_error",
                    "caller_id": submission.caller_id,
                    "trade_id": trade.trade_id,
                    "error": str(exc),
                    "payload_hash": payload_hash,
                }
            )
            return BroadcastResult(
                decision="DENY",
                reason=str(exc),
                code="VENUE_SUBMIT_ERROR",
                details={"payload_hash": payload_hash},
            )

        status = str(venue_result.get("status", "submitted"))
        self._audit(
            {
                "action": "submit",
                "caller_id": submission.caller_id,
                "trade_id": trade.trade_id,
                "venue": trade.venue,
                "status": status,
                "payload_hash": payload_hash,
                "venue_result": venue_result,
            }
        )
        return BroadcastResult(
            decision="ALLOW",
            reason="submitted via broadcast authority",
            code="OK",
            submit_status=status,
            details={"payload_hash": payload_hash, "venue": venue_result},
        )
