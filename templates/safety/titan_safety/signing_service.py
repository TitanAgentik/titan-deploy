"""Signing node HTTP service — refuses to sign without a fresh gate receipt.

This is the server-side enforcement that agent skill docs cannot provide.
POST /v1/sign requires X-Titan-Gate-Receipt matching the trade body.
Actual cryptographic signing is pluggable (mock by default); live wires
Trezor / hardware via signing_node.yaml.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .gate_receipt import RECEIPT_HEADER, verify_gate_receipt
from .http_server import SafetyHTTPServer
from .kernel import TradeRequest
from .observability import METRICS, setup_logging
from .policy_loader import expand_path, load_policy

logger = setup_logging("signing_node")

SignerFn = Callable[[dict[str, Any]], dict[str, Any]]


def mock_signer(request: dict[str, Any]) -> dict[str, Any]:
    """Paper/mock signer — no keys; returns a deterministic mock signature."""
    return {
        "status": "mock_signed",
        "signature": f"0xmocksig{uuid.uuid4().hex[:48]}",
        "signed_at": time.time(),
        "note": "Mock signer — wire Trezor/hardware via signing_node.yaml for live",
        "request_id": request.get("request_id", ""),
    }


class SigningNode:
    """Fail-closed signing gate: receipt → optional halt checks → signer."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        signer: SignerFn | None = None,
        max_receipt_age: int = 30,
        halt_checker: Callable[[], bool] | None = None,
    ) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.signer = signer or mock_signer
        self.max_receipt_age = max_receipt_age
        self.halt_checker = halt_checker
        self._halted = False
        self._sign_log = self.safety_dir / "signing_audit.jsonl"

    def halt(self, reason: str = "") -> None:
        self._halted = True
        logger.critical(f"Signing halted: {reason}")

    def resume(self) -> None:
        self._halted = False

    def is_halted(self) -> bool:
        if self._halted:
            return True
        if self.halt_checker and self.halt_checker():
            return True
        # File flag from kill / compromise
        return (self.safety_dir / "SIGNING_HALTED").exists()

    def _audit(self, record: dict[str, Any]) -> None:
        record = {**record, "ts": time.time()}
        with self._sign_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")

    def sign(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any]]:
        if self.is_halted():
            METRICS.inc("signing_deny_total")
            return 403, {
                "decision": "DENY",
                "code": "SIGNING_HALTED",
                "reason": "signing node halted",
            }

        receipt = ""
        for k, v in headers.items():
            if k.lower() == RECEIPT_HEADER.lower():
                receipt = v.strip()
                break
        # Also accept body.gate_receipt for clients that cannot set custom headers
        if not receipt:
            receipt = str(body.get("gate_receipt", "")).strip()

        trade = TradeRequest.from_dict(body.get("trade") or body)
        if not trade.trade_id:
            return 400, {"decision": "DENY", "code": "MISSING_TRADE", "reason": "trade_id required"}

        ok, reason = verify_gate_receipt(
            receipt, trade, self.safety_dir, self.max_receipt_age
        )
        if not ok:
            METRICS.inc("signing_deny_total")
            self._audit(
                {
                    "action": "deny",
                    "code": "GATE_RECEIPT_INVALID",
                    "reason": reason,
                    "trade_id": trade.trade_id,
                }
            )
            return 401, {
                "decision": "DENY",
                "code": "GATE_RECEIPT_INVALID",
                "reason": reason,
            }

        try:
            result = self.signer(
                {
                    "request_id": body.get("request_id", trade.trade_id),
                    "trade": trade.__dict__,
                    "calldata": body.get("calldata"),
                    "typed_data": body.get("typed_data"),
                }
            )
        except Exception as exc:
            METRICS.inc("signing_error_total")
            logger.error(f"signer failed: {exc}")
            return 500, {"decision": "DENY", "code": "SIGNER_ERROR", "reason": str(exc)}

        METRICS.inc("signing_allow_total")
        self._audit(
            {
                "action": "sign",
                "trade_id": trade.trade_id,
                "status": result.get("status"),
            }
        )
        return 200, {"decision": "ALLOW", **result}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if not self.is_halted() else "halted",
            "halted": self.is_halted(),
            "receipt_required": True,
            "max_receipt_age_seconds": self.max_receipt_age,
        }


def create_app(
    policy_path: Path | None = None,
    safety_dir: Path | None = None,
    signer: SignerFn | None = None,
) -> SafetyHTTPServer:
    from .kill_switch import KillSwitch

    safety = safety_dir or (Path.home() / ".openclaw" / "safety")
    port = 19010
    max_age = 30
    if policy_path and Path(policy_path).exists():
        policy = load_policy(policy_path)
        port = policy.service.signing_node_port
        signing_cfg = (policy.raw or {}).get("signing", {})
        max_age = int(signing_cfg.get("max_receipt_age_seconds", 30))

    ks = KillSwitch(safety)
    node = SigningNode(
        safety_dir=safety,
        signer=signer,
        max_receipt_age=max_age,
        halt_checker=ks.is_active,
    )

    def sign_route(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return node.sign(body, headers)

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return 200, node.health()

    def halt(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        node.halt(str(body.get("reason", "operator halt")))
        (safety / "SIGNING_HALTED").write_text(
            json.dumps({"ts": time.time(), "reason": body.get("reason", "")}),
            encoding="utf-8",
        )
        return 200, {"ok": True, "halted": True}

    routes = {
        "POST /v1/sign": sign_route,
        "POST /v1/halt": halt,
        "GET /health": health,
        "GET /metrics": lambda _b, _h: (200, METRICS.to_json()),
    }
    return SafetyHTTPServer(
        "127.0.0.1",
        port,
        routes,
        auth_commands={"POST /v1/halt": "SIGN_HALT"},
        safety_dir=safety,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TITAN Signing Node")
    parser.add_argument(
        "--policy",
        default=os.environ.get(
            "TITAN_POLICY_PATH",
            str(Path.home() / ".openclaw" / "risk_kernel" / "policy.yaml"),
        ),
    )
    parser.add_argument(
        "--safety-dir",
        default=os.environ.get("TITAN_SAFETY_DIR", str(Path.home() / ".openclaw" / "safety")),
    )
    args = parser.parse_args(argv)
    server = create_app(expand_path(args.policy), Path(args.safety_dir))
    logger.info("Signing node listening (receipt-required)")
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
