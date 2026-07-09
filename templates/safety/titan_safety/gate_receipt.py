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
) -> str:
    # Fixed precision so float formatting cannot break HMAC verify.
    return (
        f"{RECEIPT_PREFIX}|{trade_id}|{venue}|{contract.lower()}|"
        f"{notional_usd:.8f}|{side.lower()}|{ts}"
    )


def issue_gate_receipt(
    trade: TradeRequest | dict[str, Any],
    safety_dir: Path | None = None,
    ts: int | None = None,
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
    if len(parts) != 8:
        return False, "malformed gate receipt"
    prefix, trade_id, venue, contract, notional_str, side, ts_str, sig = parts
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
    payload = _payload(trade_id, venue, contract, notional, side, ts)
    expected = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False, "invalid receipt signature"
    return True, "ok"
