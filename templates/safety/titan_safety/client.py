"""Fail-closed client for risk kernel pre-trade validation."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .kernel import TradeRequest, ValidationResult


class RiskKernelClient:
    """Client that DENYs all trades when kernel is unreachable."""

    def __init__(self, base_url: str, timeout: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def validate(self, trade: TradeRequest | dict[str, Any]) -> ValidationResult:
        if isinstance(trade, dict):
            trade = TradeRequest.from_dict(trade)
        try:
            body = json.dumps(
                {
                    "trade_id": trade.trade_id,
                    "venue": trade.venue,
                    "contract": trade.contract,
                    "side": trade.side,
                    "notional_usd": trade.notional_usd,
                    "leverage": trade.leverage,
                    "expected_price": trade.expected_price,
                    "worst_price": trade.worst_price,
                    "strategy_id": trade.strategy_id,
                }
            ).encode()
            req = urllib.request.Request(
                f"{self.base_url}/v1/validate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                return ValidationResult(
                    decision=data.get("decision", "DENY"),
                    reason=data.get("reason", ""),
                    code=data.get("code", ""),
                    details=data.get("details", {}),
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return ValidationResult(
                decision="DENY",
                reason=f"Risk kernel unreachable — fail-closed: {exc}",
                code="KERNEL_UNREACHABLE",
            )

    def health(self) -> dict[str, Any] | None:
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/health", timeout=self.timeout
            ) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
