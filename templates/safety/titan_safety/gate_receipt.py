"""Signed ExecutionGate ALLOW receipts — required by the signing node.

A receipt binds a specific trade_id + notional + venue + contract to a fresh
ALLOW decision. Signing without a valid receipt is refused (fail-closed).

Token format (X-Titan-Gate-Receipt):
  GATE_ALLOW|<trade_id>|<venue>|<contract>|<notional>|<side>|<unix_ts>|<hex_hmac>
  HMAC-SHA256 over the payload before the final |sig, using control_plane.secret.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .auth import ensure_control_secret
from .kernel import TradeRequest

RECEIPT_HEADER = "X-Titan-Gate-Receipt"
RECEIPT_PREFIX = "GATE_ALLOW"
DEFAULT_MAX_AGE_SECONDS = 30

# In-process single-use ledger (persisted optionally via safety_dir).
_consumed_receipt_sigs: set[str] = set()


@dataclass
class GateReceipt:
    trade_id: str
    venue: str
    contract: str
    notional_usd: float
    side: str
    ts: int
    token: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _payload(
    trade_id: str,
    venue: str,
    contract: str,
    notional_usd: float,
    side: str,
    ts: int,
    payload_hash: str = "",
) -> str:
    # Fixed precision so float formatting cannot break HMAC verify.
  # Optional payload_hash binds calldata/typed_data at sign/submit time (Tier 0).
    return (
        f"{RECEIPT_PREFIX}|{trade_id}|{venue}|{contract.lower()}|"
        f"{notional_usd:.8f}|{side.lower()}|{ts}|{payload_hash}"
    )


def issue_gate_receipt(
    trade: TradeRequest | dict[str, Any],
    safety_dir: Path | None = None,
    ts: int | None = None,
    payload_hash: str = "",
) -> GateReceipt:
    if isinstance(trade, dict):
        trade = TradeRequest.from_dict(trade)
    timestamp = int(time.time()) if ts is None else int(ts)
    secret = ensure_control_secret(safety_dir)
    payload = _payload(
        trade.trade_id,
        trade.venue,
        trade.contract,
        trade.notional_usd,
        trade.side,
        timestamp,
        payload_hash,
    )
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}|{sig}"
    return GateReceipt(
        trade_id=trade.trade_id,
        venue=trade.venue,
        contract=trade.contract.lower(),
        notional_usd=trade.notional_usd,
        side=trade.side.lower(),
        ts=timestamp,
        token=token,
    )


def _receipt_signature(token: str) -> str:
    parts = token.strip().split("|")
    return parts[-1] if parts else ""


def reset_consumed_receipts() -> None:
    """Test helper — clear in-process consumed receipt ledger."""
    _consumed_receipt_sigs.clear()


def is_receipt_consumed(token: str) -> bool:
    sig = _receipt_signature(token)
    return bool(sig) and sig in _consumed_receipt_sigs


def consume_gate_receipt(
    token: str,
    trade: TradeRequest | dict[str, Any],
    safety_dir: Path | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Verify and mark receipt single-use. Returns (ok, reason)."""
    ok, reason = verify_gate_receipt(token, trade, safety_dir, max_age_seconds)
    if not ok:
        return False, reason
    sig = _receipt_signature(token)
    if sig in _consumed_receipt_sigs:
        return False, "gate receipt already consumed (single-use)"
    _consumed_receipt_sigs.add(sig)
    return True, "ok"


def verify_gate_receipt(
    token: str,
    trade: TradeRequest | dict[str, Any],
    safety_dir: Path | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Verify receipt binds to this trade and is fresh. Returns (ok, reason)."""
    if isinstance(trade, dict):
        trade = TradeRequest.from_dict(trade)
    if not token or not token.strip():
        return False, "missing gate receipt"
    parts = token.strip().split("|")
    # v1: 8 parts (no payload_hash); v2: 9 parts (payload_hash before sig)
    if len(parts) == 8:
        prefix, trade_id, venue, contract, notional_str, side, ts_str, sig = parts
        receipt_payload_hash = ""
    elif len(parts) == 9:
        prefix, trade_id, venue, contract, notional_str, side, ts_str, receipt_payload_hash, sig = parts
    else:
        return False, "malformed gate receipt"
    if prefix != RECEIPT_PREFIX:
        return False, f"invalid receipt prefix: {prefix}"
    try:
        ts = int(ts_str)
        notional = float(notional_str)
    except ValueError:
        return False, "invalid receipt fields"
    now = time.time()
    if now - ts > max_age_seconds:
        return False, "gate receipt expired"
    if ts > now + 60:
        return False, "gate receipt timestamp in future"
    if trade_id != trade.trade_id:
        return False, "trade_id mismatch"
    if venue != trade.venue:
        return False, "venue mismatch"
    if contract.lower() != trade.contract.lower():
        return False, "contract mismatch"
    if side.lower() != trade.side.lower():
        return False, "side mismatch"
    if abs(notional - trade.notional_usd) > 1e-6:
        return False, "notional mismatch"
    secret = ensure_control_secret(safety_dir)
    payload = _payload(trade_id, venue, contract, notional, side, ts, receipt_payload_hash)
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "invalid receipt signature"
    return True, "ok"


def bind_receipt_to_payload(
    token: str,
    trade: TradeRequest | dict[str, Any],
    payload_hash: str,
    safety_dir: Path | None = None,
) -> GateReceipt:
    """Re-issue receipt with payload_hash bound to calldata/typed_data (Tier 0 sign path)."""
    if isinstance(trade, dict):
        trade = TradeRequest.from_dict(trade)
    parts = token.strip().split("|")
    if len(parts) not in (8, 9):
        raise ValueError("malformed gate receipt for rebinding")
    ts = int(parts[6])
    return issue_gate_receipt(trade, safety_dir, ts=ts, payload_hash=payload_hash)
