"""Hyperliquid live venue adapter — Tier 0 money path (quote → confirm).

Real interfaces with STUB markers where operator keys / exchange RPC required.
Solana/Jito/P22 explicitly deferred.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..broadcast_authority import BroadcastSubmission
from ..kernel import TradeRequest
from ..observability import setup_logging

logger = setup_logging("hyperliquid_live")

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
HYPERLIQUID_EXCHANGE_URL = "https://api.hyperliquid.xyz/exchange"
FILL_LEDGER = "hyperliquid_fill_ledger.jsonl"


class NotConfiguredError(RuntimeError):
    """Operator must arm keys before live submit."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class HyperliquidOrder:
    trade_id: str
    venue: str
    contract: str
    side: str
    notional_usd: float
    reduce_only: bool = False
    expected_price: float = 0.0
    sz: float = 0.0
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HyperliquidLiveAdapter:
    """End-to-end skeleton: quote → simulate → sign → submit → confirm → fill ledger."""

    VENUE = "hyperliquid"

    def __init__(self, safety_dir: Path | None = None) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self._fill_ledger = self.safety_dir / FILL_LEDGER

    def _require_armed(self) -> None:
        if _env("TITAN_LIVE_SIGNING_READY").lower() not in ("1", "true", "yes"):
            raise NotConfiguredError(
                "Hyperliquid live not armed — set TITAN_LIVE_SIGNING_READY=1 after Phase 5 YES"
            )
        if not _env("HYPERLIQUID_WALLET_ADDRESS"):
            raise NotConfiguredError("HYPERLIQUID_WALLET_ADDRESS required")

    def quote(self, order: HyperliquidOrder | dict[str, Any]) -> dict[str, Any]:
        """Fetch mid price via public info API."""
        o = order if isinstance(order, HyperliquidOrder) else HyperliquidOrder(**order)
        coin = o.contract.upper()
        body = json.dumps({"type": "allMids"}).encode()
        import urllib.request

        req = urllib.request.Request(
            HYPERLIQUID_INFO_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            mids = json.loads(resp.read().decode())
        mid = float(mids.get(coin, 0) or 0)
        if mid <= 0:
            return {"status": "quote_failed", "reason": f"no mid for {coin}", "mid": 0.0}
        sz = o.notional_usd / mid if mid else 0.0
        return {
            "status": "quoted",
            "venue": self.VENUE,
            "contract": coin,
            "mid": mid,
            "sz": sz,
            "notional_usd": o.notional_usd,
            "side": o.side,
        }

    def simulate(self, order: HyperliquidOrder | dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
        """Pre-trade simulation — slippage / margin check stub."""
        o = order if isinstance(order, HyperliquidOrder) else HyperliquidOrder(**order)
        mid = float(quote.get("mid", 0) or 0)
        if mid <= 0:
            return {"status": "sim_failed", "reason": "invalid quote", "ok": False}
        worst_bps = 50
        worst_px = mid * (1 + worst_bps / 10000.0) if o.side.lower() == "buy" else mid * (1 - worst_bps / 10000.0)
        return {
            "status": "simulated",
            "ok": True,
            "mid": mid,
            "worst_price": worst_px,
            "sz": quote.get("sz", 0),
            "reduce_only": o.reduce_only,
        }

    def build_typed_data(self, order: HyperliquidOrder, sim: dict[str, Any]) -> dict[str, Any]:
        """Policy-bound typed data for session-key signing."""
        return {
            "domain": {"name": "Hyperliquid", "version": "1", "chainId": 0},
            "types": {
                "Order": [
                    {"name": "coin", "type": "string"},
                    {"name": "side", "type": "string"},
                    {"name": "sz", "type": "string"},
                    {"name": "reduceOnly", "type": "bool"},
                ]
            },
            "primaryType": "Order",
            "message": {
                "coin": order.contract.upper(),
                "side": order.side.upper(),
                "sz": str(sim.get("sz", 0)),
                "reduceOnly": order.reduce_only,
            },
        }

    def sign(
        self,
        order: HyperliquidOrder | dict[str, Any],
        sim: dict[str, Any],
        signing_node: Any,
        gate_receipt: str,
    ) -> dict[str, Any]:
        """Sign via in-process SigningNode — typed_data required."""
        from ..gate_receipt import RECEIPT_HEADER

        o = order if isinstance(order, HyperliquidOrder) else HyperliquidOrder(**order)
        typed_data = self.build_typed_data(o, sim)
        trade = {
            "trade_id": o.trade_id,
            "venue": self.VENUE,
            "contract": o.contract.lower(),
            "side": o.side.lower(),
            "notional_usd": o.notional_usd,
            "leverage": 1.0,
            "expected_price": float(sim.get("mid", 0)),
            "worst_price": float(sim.get("worst_price", 0)),
        }
        body = {
            "trade": trade,
            "typed_data": typed_data,
            "gate_receipt": gate_receipt,
            "reduce_only": o.reduce_only,
        }
        code, payload = signing_node.sign(body, {RECEIPT_HEADER: gate_receipt})
        if code != 200:
            return {"status": "sign_denied", "code": payload.get("code"), "reason": payload.get("reason")}
        return {"status": "signed", "signature": payload.get("signature"), "typed_data": typed_data}

    def submit(self, signed: dict[str, Any]) -> dict[str, Any]:
        """STUB — live exchange POST requires operator session key + bridge."""
        self._require_armed()
        if not _env("HYPERLIQUID_PRIVATE_KEY") and not _env("TREZOR_BRIDGE_SOCKET"):
            raise NotConfiguredError(
                "Hyperliquid submit STUB — wire HYPERLIQUID_PRIVATE_KEY (session) or Trezor bridge"
            )
        # STUB: operator implements exchange POST to HYPERLIQUID_EXCHANGE_URL
        return {
            "status": "submit_stub",
            "tx_id": f"hl-stub-{uuid.uuid4().hex[:16]}",
            "note": "STUB — exchange POST not wired; interfaces validated through sign",
            "exchange_url": HYPERLIQUID_EXCHANGE_URL,
        }

    def submit_signed(self, submission: BroadcastSubmission, trade: TradeRequest) -> dict[str, Any]:
        """BroadcastAuthority venue hook — expects signed payload in submission body."""
        signed = submission.body().get("signed") or {}
        if not signed:
            order = HyperliquidOrder(
                trade_id=trade.trade_id,
                venue=trade.venue,
                contract=trade.contract,
                side=trade.side,
                notional_usd=trade.notional_usd,
                reduce_only=bool(submission.reduce_only),
            )
            quote = self.quote(order)
            sim = self.simulate(order, quote)
            return {
                "status": "submit_denied",
                "reason": "signed payload missing — run quote/sim/sign first",
                "quote": quote,
                "sim": sim,
            }
        return self.submit(signed)

    def confirm(self, submit_result: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
        """STUB — poll fill status from exchange."""
        tx_id = submit_result.get("tx_id", "")
        if submit_result.get("status") == "submit_stub":
            return {
                "status": "confirm_stub",
                "tx_id": tx_id,
                "filled": False,
                "note": "STUB — fill confirmation requires live exchange wiring",
            }
        return {"status": "pending", "tx_id": tx_id, "timeout_s": timeout_s}

    def record_fill(self, confirm_result: dict[str, Any], trade_id: str) -> dict[str, Any]:
        """Append to local fill ledger."""
        record = {**confirm_result, "trade_id": trade_id, "ts": time.time()}
        with self._fill_ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")
        return {"status": "recorded", "ledger": str(self._fill_ledger)}

    def execute_path(
        self,
        trade: dict[str, Any],
        gate_receipt: str,
        signing_node: Any,
    ) -> dict[str, Any]:
        """Full path: quote → simulate → sign → submit → confirm → fill ledger."""
        order = HyperliquidOrder(
            trade_id=str(trade.get("trade_id", uuid.uuid4().hex[:12])),
            venue=self.VENUE,
            contract=str(trade.get("contract", "")).lower(),
            side=str(trade.get("side", "buy")),
            notional_usd=float(trade.get("notional_usd", 0)),
            reduce_only=bool(trade.get("reduce_only", False)),
        )
        quote = self.quote(order)
        if quote.get("status") != "quoted":
            return {"status": "failed", "stage": "quote", **quote}
        sim = self.simulate(order, quote)
        if not sim.get("ok"):
            return {"status": "failed", "stage": "simulate", **sim}
        signed = self.sign(order, sim, signing_node, gate_receipt)
        if signed.get("status") != "signed":
            return {"status": "failed", "stage": "sign", **signed}
        submitted = self.submit(signed)
        confirmed = self.confirm(submitted)
        ledger = self.record_fill(confirmed, order.trade_id)
        return {
            "status": "path_complete",
            "quote": quote,
            "sim": sim,
            "signed": {k: v for k, v in signed.items() if k != "typed_data"},
            "submitted": submitted,
            "confirmed": confirmed,
            "ledger": ledger,
        }
