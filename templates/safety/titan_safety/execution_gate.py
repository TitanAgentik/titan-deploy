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
from http.client import HTTPConnection
from typing import Any
from urllib.parse import urlparse

from pathlib import Path

from .auth import sign_control_command
from .gate_receipt import GateReceipt, issue_gate_receipt
from .kernel import TradeRequest, ValidationResult
from .policy_loader import Policy, load_policy
from .stealth_predatory import check_stealth_evasion
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

    _HTTP_POOL: dict[str, HTTPConnection] = {}

    def __init__(
        self,
        policy: Policy,
        kernel_url: str | None = None,
        recon_url: str | None = None,
        timeout: float | None = None,
        fast_timeout: float | None = None,
        auth_operator: str = "execution_gate",
        safety_dir: Path | None = None,
    ) -> None:
        self.policy = policy
        ports = policy.service
        self.kernel_url = (kernel_url or f"http://127.0.0.1:{ports.risk_kernel_port}").rstrip("/")
        self.recon_url = (recon_url or f"http://127.0.0.1:{ports.reconciliation_port}").rstrip("/")
        latency = (policy.raw or {}).get("latency", {})
        hot = latency.get("hot_path", {})
        self.timeout = timeout if timeout is not None else float(hot.get("gate_timeout_s", 0.25))
        self.fast_timeout = fast_timeout if fast_timeout is not None else float(
            hot.get("fast_gate_timeout_s", 0.15)
        )
        self.auth_operator = auth_operator
        self.safety_dir = safety_dir

    @classmethod
    def from_policy_path(cls, path: str | Any) -> ExecutionGate:
        return cls(load_policy(path))

    def _hot_path_enabled(self, trade: TradeRequest) -> bool:
        latency = (self.policy.raw or {}).get("latency", {})
        hot = latency.get("hot_path", {})
        if not hot.get("enabled", False):
            return False
        pipelines = {str(p) for p in hot.get("pipelines", [])}
        if pipelines and trade.strategy_id and trade.strategy_id not in pipelines:
            return False
        return bool(hot.get("combined_validate", True))

    def _conn(self, url: str) -> HTTPConnection:
        parsed = urlparse(url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        key = f"{host}:{port}"
        conn = self._HTTP_POOL.get(key)
        if conn is None:
            conn = HTTPConnection(host, port, timeout=self.timeout)
            self._HTTP_POOL[key] = conn
        return conn

    def _post(self, url: str, body: dict[str, Any], auth_command: str | None = None, timeout: float | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
        if auth_command:
            headers["X-Titan-Auth"] = sign_control_command(auth_command, self.auth_operator)
        data = json.dumps(body).encode()
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        use_timeout = self.timeout if timeout is None else timeout
        if parsed.hostname in ("127.0.0.1", "localhost"):
            conn = self._conn(url)
            conn.timeout = use_timeout
            try:
                conn.request("POST", path, body=data, headers=headers)
                resp = conn.getresponse()
                raw = resp.read().decode()
                if resp.status >= 400:
                    raise urllib.error.HTTPError(url, resp.status, raw, resp.headers, None)
                return json.loads(raw)
            except (ConnectionError, TimeoutError, OSError):
                self._HTTP_POOL.pop(f"{parsed.hostname}:{parsed.port or 80}", None)
                raise
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=use_timeout) as resp:
            return json.loads(resp.read().decode())

    def gate(
        self,
        trade: TradeRequest | dict[str, Any],
        believed: list[BelievedPosition] | list[dict[str, Any]] | None = None,
        fast_path: bool | None = None,
    ) -> GateDecision:
        if isinstance(trade, dict):
            trade = TradeRequest.from_dict(trade)
        use_fast = fast_path if fast_path is not None else self._hot_path_enabled(trade)
        if use_fast:
            decision = self._gate_fast(trade, believed)
        else:
            decision = self._gate_standard(trade, believed)
        try:
            from .telegram_notify import notify_gate_decision

            notify_gate_decision(trade, decision, safety_dir=self.safety_dir)
        except Exception:
            pass
        return decision

    def _gate_standard(
        self,
        trade: TradeRequest,
        believed: list[BelievedPosition] | list[dict[str, Any]] | None,
    ) -> GateDecision:
        stages: dict[str, Any] = {}

        # --- Stage 0: ghost evasion (public path / unshielded live deny) ---
        stealth = check_stealth_evasion(trade, self.policy)
        if stealth is not None:
            stages["stealth_evasion"] = stealth.to_dict()
            return GateDecision(
                decision="DENY",
                reason=stealth.reason,
                code=stealth.code,
                stages=stages,
            )
        stages["stealth_evasion"] = {"decision": "ALLOW", "code": "OK"}

        # --- Stage 0.5: live-profile mock ban ---
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

    def _gate_fast(
        self,
        trade: TradeRequest,
        believed: list[BelievedPosition] | list[dict[str, Any]] | None,
    ) -> GateDecision:
        """Millisecond hot path — single localhost hop (recon + kernel combined)."""
        stages: dict[str, Any] = {}
        stealth = check_stealth_evasion(trade, self.policy)
        if stealth is not None:
            stages["stealth_evasion"] = stealth.to_dict()
            return GateDecision(
                decision="DENY",
                reason=stealth.reason,
                code=stealth.code,
                stages=stages,
            )
        stages["stealth_evasion"] = {"decision": "ALLOW", "code": "OK"}

        mock_block = self._check_mock_ban()
        stages["mock_ban"] = mock_block
        if mock_block["decision"] != "ALLOW":
            return GateDecision(
                decision="DENY",
                reason=mock_block["reason"],
                code=mock_block["code"],
                stages=stages,
            )

        believed_payload = []
        for p in believed or []:
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
        body = {
            "believed": believed_payload,
            "pending": pending,
            "trade": {
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
        }
        try:
            result = self._post(
                f"{self.kernel_url}/v1/fast_validate",
                body,
                timeout=self.fast_timeout,
            )
            stages["fast_validate"] = result
            if result.get("decision") != "ALLOW":
                stage = result.get("stage", "fast_validate")
                return GateDecision(
                    decision="DENY",
                    reason=f"{stage}: {result.get('reason', 'denied')}",
                    code=str(result.get("code", "FAST_GATE_DENY")),
                    stages=stages,
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            stages["fast_validate"] = {"decision": "DENY", "error": str(exc)}
            return GateDecision(
                decision="DENY",
                reason=f"Fast validate unreachable — fail-closed: {exc}",
                code="FAST_GATE_UNREACHABLE",
                stages=stages,
            )

        receipt = issue_gate_receipt(trade, self.safety_dir)
        stages["gate_receipt"] = {"issued": True, "trade_id": receipt.trade_id, "ts": receipt.ts}
        return GateDecision(
            decision="ALLOW",
            reason="passed fast_validate (recon + kernel)",
            code="OK_FAST",
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
