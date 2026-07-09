"""Unbypassable pre-trade execution gate.

Every live order MUST pass: reconcile → risk kernel → (optional portfolio).
If any service is unreachable or returns non-ALLOW, the trade is DENY.
This is the code-level enforcement that config URLs alone cannot provide.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from pathlib import Path

from .auth import sign_control_command
from .gate_receipt import GateReceipt, issue_gate_receipt
from .kernel import TradeRequest, ValidationResult
from .policy_loader import Policy, load_policy
from .reconciliation import BelievedPosition, ReconciliationResult


@dataclass
class GateDecision:
    decision: str  # ALLOW | DENY
    reason: str
    code: str = ""
    stages: dict[str, Any] = field(default_factory=dict)
    receipt: str = ""  # X-Titan-Gate-Receipt token when ALLOW

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def allowed(self) -> bool:
        return self.decision == "ALLOW"


class ExecutionGate:
    """Fail-closed multi-stage pre-trade gate for TRENCH-OPS / EXECUTOR."""

    def __init__(
        self,
        policy: Policy,
        kernel_url: str | None = None,
        recon_url: str | None = None,
        timeout: float = 2.0,
        auth_operator: str = "execution_gate",
        safety_dir: Path | None = None,
    ) -> None:
        self.policy = policy
        ports = policy.service
        self.kernel_url = (kernel_url or f"http://127.0.0.1:{ports.risk_kernel_port}").rstrip("/")
        self.recon_url = (recon_url or f"http://127.0.0.1:{ports.reconciliation_port}").rstrip("/")
        self.timeout = timeout
        self.auth_operator = auth_operator
        self.safety_dir = safety_dir

    @classmethod
    def from_policy_path(cls, path: str | Any) -> ExecutionGate:
        return cls(load_policy(path))

    def _post(self, url: str, body: dict[str, Any], auth_command: str | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if auth_command:
            headers["X-Titan-Auth"] = sign_control_command(auth_command, self.auth_operator)
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def gate(
        self,
        trade: TradeRequest | dict[str, Any],
        believed: list[BelievedPosition] | list[dict[str, Any]] | None = None,
    ) -> GateDecision:
        if isinstance(trade, dict):
            trade = TradeRequest.from_dict(trade)
        stages: dict[str, Any] = {}

        # --- Stage 0: live-profile mock ban ---
        mock_block = self._check_mock_ban()
        stages["mock_ban"] = mock_block
        if mock_block["decision"] != "ALLOW":
            return GateDecision(
                decision="DENY",
                reason=mock_block["reason"],
                code=mock_block["code"],
                stages=stages,
            )

        # --- Stage 1: reconciliation ---
        believed_list = believed or []
        believed_payload = []
        for p in believed_list:
            if isinstance(p, BelievedPosition):
                believed_payload.append(
                    {
                        "venue": p.venue,
                        "contract": p.contract,
                        "notional_usd": p.notional_usd,
                        "side": p.side,
                    }
                )
            else:
                believed_payload.append(p)
        pending = {
            "venue": trade.venue,
            "contract": trade.contract,
            "notional_usd": trade.notional_usd,
            "side": trade.side,
        }
        try:
            recon = self._post(
                f"{self.recon_url}/v1/pre_trade",
                {"believed": believed_payload, "pending": pending},
            )
            stages["reconciliation"] = recon
            if recon.get("decision") != "ALLOW":
                return GateDecision(
                    decision="DENY",
                    reason=f"Reconciliation gate: {recon.get('reason', 'denied')}",
                    code=str(recon.get("code", "RECON_DENY")),
                    stages=stages,
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            stages["reconciliation"] = {"decision": "DENY", "error": str(exc)}
            return GateDecision(
                decision="DENY",
                reason=f"Reconciliation unreachable — fail-closed: {exc}",
                code="RECON_UNREACHABLE",
                stages=stages,
            )

        # --- Stage 2: risk kernel ---
        try:
            kernel = self._post(
                f"{self.kernel_url}/v1/validate",
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
                    "confidence": trade.confidence,
                    "bft_votes": trade.bft_votes,
                },
            )
            stages["risk_kernel"] = kernel
            if kernel.get("decision") != "ALLOW":
                return GateDecision(
                    decision="DENY",
                    reason=f"Risk kernel: {kernel.get('reason', 'denied')}",
                    code=str(kernel.get("code", "KERNEL_DENY")),
                    stages=stages,
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            stages["risk_kernel"] = {"decision": "DENY", "error": str(exc)}
            return GateDecision(
                decision="DENY",
                reason=f"Risk kernel unreachable — fail-closed: {exc}",
                code="KERNEL_UNREACHABLE",
                stages=stages,
            )

        receipt = issue_gate_receipt(trade, self.safety_dir)
        stages["gate_receipt"] = {
            "issued": True,
            "trade_id": receipt.trade_id,
            "ts": receipt.ts,
        }
        return GateDecision(
            decision="ALLOW",
            reason="passed reconciliation + risk kernel",
            code="OK",
            stages=stages,
            receipt=receipt.token,
        )

    def _check_mock_ban(self) -> dict[str, str]:
        """In enforce mode with non-paper venues, mock adapters are forbidden."""
        adapter = self.policy.reconciliation.adapter
        venues = [v.lower() for v in self.policy.allowed_venues]
        live_venues = [v for v in venues if v not in ("paper", "mock", "test")]
        capital = self.policy.raw.get("capital", {}) if self.policy.raw else {}
        # Also check openclaw-style capital section if embedded in raw
        withdrawal = str(
            capital.get("withdrawal_adapter")
            or self.policy.raw.get("withdrawal_adapter", "mock")
        )
        if self.policy.enforce and live_venues and adapter == "mock":
            return {
                "decision": "DENY",
                "reason": (
                    f"Live venues {live_venues} configured but reconciliation.adapter=mock — "
                    "refusing trades until a live adapter is wired"
                ),
                "code": "MOCK_ADAPTER_FORBIDDEN",
            }
        if self.policy.enforce and live_venues and withdrawal == "mock":
            # Soft warning stage — still allow trade validation but flag
            return {
                "decision": "ALLOW",
                "reason": "withdrawal_adapter still mock (sweeps blocked; trading allowed)",
                "code": "WITHDRAWAL_MOCK_WARN",
            }
        return {"decision": "ALLOW", "reason": "ok", "code": "OK"}
