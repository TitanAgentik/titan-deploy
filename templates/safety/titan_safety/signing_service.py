"""In-process signing gate — refuses to sign without a fresh gate receipt.

Hot path (default): ``build_signing_node()`` + ``SigningNode.sign()`` inside
``titan-safety gate sign`` / flatten / capital — same process as the gate,
no HTTP hop to :19010.

Optional legacy: ``create_app()`` / ``python -m titan_safety.signing_service``
still exposes POST /v1/sign for compatibility; not required for deploy.

Actual cryptographic signing is pluggable (mock by default); live wires
Trezor / hardware via signing_node.yaml + signing.signer_module.
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
from .policy_loader import capital_profile_of, expand_path, load_component, load_policy

logger = setup_logging("signing")

SignerFn = Callable[[dict[str, Any]], dict[str, Any]]

# Default mode for gate sign / flatten / capital — in-process, no :19010.
DEFAULT_SIGNING_MODE = "in_process"


def mock_signer(request: dict[str, Any]) -> dict[str, Any]:
    """Paper/mock signer — no keys; returns a deterministic mock signature."""
    return {
        "status": "mock_signed",
        "signature": f"0xmocksig{uuid.uuid4().hex[:48]}",
        "signed_at": time.time(),
        "note": "Mock signer — wire Trezor/hardware via signing.signer_module for live",
        "request_id": request.get("request_id", ""),
    }


def resolve_signing_mode(policy_raw: dict[str, Any] | None = None) -> str:
    """Return ``in_process`` (default) or ``http`` (legacy :19010)."""
    env = os.environ.get("TITAN_SIGNING_MODE", "").strip().lower()
    if env in ("in_process", "http", "legacy"):
        return "http" if env == "legacy" else env
    signing = (policy_raw or {}).get("signing") or {}
    mode = str(signing.get("mode") or DEFAULT_SIGNING_MODE).strip().lower()
    if mode in ("http", "legacy", "signing_node"):
        return "http"
    return "in_process"


class SigningNode:
    """Fail-closed signing gate: receipt → optional halt checks → signer."""

    def __init__(
        self,
        safety_dir: Path | None = None,
        signer: SignerFn | None = None,
        max_receipt_age: int = 30,
        halt_checker: Callable[[], bool] | None = None,
        policy_raw: dict[str, Any] | None = None,
    ) -> None:
        self.safety_dir = safety_dir or (Path.home() / ".openclaw" / "safety")
        self.safety_dir.mkdir(parents=True, exist_ok=True)
        self.signer = signer or mock_signer
        self.max_receipt_age = max_receipt_age
        self.halt_checker = halt_checker
        self.policy_raw = policy_raw or {}
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
                "reason": "signing halted",
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
            try:
                from .telegram_notify import notify_signing

                notify_signing("fail", trade.trade_id, code="GATE_RECEIPT_INVALID", reason=reason, safety_dir=self.safety_dir)
            except Exception:
                pass
            return 401, {
                "decision": "DENY",
                "code": "GATE_RECEIPT_INVALID",
                "reason": reason,
            }

        from .trade_verifier import verify_sign_payload

        ok_payload, payload_reason = verify_sign_payload(trade, body, self.policy_raw)
        if not ok_payload:
            METRICS.inc("signing_deny_total")
            self._audit(
                {
                    "action": "deny",
                    "code": "BLIND_SIGN_REJECTED",
                    "reason": payload_reason,
                    "trade_id": trade.trade_id,
                }
            )
            return 403, {
                "decision": "DENY",
                "code": "BLIND_SIGN_REJECTED",
                "reason": payload_reason,
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
        try:
            from .telegram_notify import notify_signing

            notify_signing(
                "success",
                trade.trade_id,
                code="OK",
                reason="In-process sign completed",
                safety_dir=self.safety_dir,
            )
        except Exception:
            pass
        return 200, {"decision": "ALLOW", **result}

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if not self.is_halted() else "halted",
            "halted": self.is_halted(),
            "mode": "in_process",
            "receipt_required": True,
            "max_receipt_age_seconds": self.max_receipt_age,
        }


def build_signing_node(
    policy_path: Path | None = None,
    safety_dir: Path | None = None,
    signer: SignerFn | None = None,
    policy_raw: dict[str, Any] | None = None,
    *,
    require_live_signer: bool = True,
) -> SigningNode:
    """Construct a SigningNode for in-process use (no HTTP server).

    Loads ``signing.signer_module`` from policy when present. Live capital
    profiles refuse the mock signer when ``require_live_signer`` is True.
    """
    from .kill_switch import KillSwitch

    safety = safety_dir or (Path.home() / ".openclaw" / "safety")
    safety = Path(safety)
    safety.mkdir(parents=True, exist_ok=True)
    max_age = 30
    raw: dict[str, Any] = dict(policy_raw or {})
    policy = None
    if policy_path and Path(policy_path).exists():
        policy = load_policy(policy_path)
        raw = policy.raw or raw
    signing_cfg = raw.get("signing", {}) or {}
    max_age = int(signing_cfg.get("max_receipt_age_seconds", max_age))

    if signer is None:
        signer_spec = str(
            signing_cfg.get("signer_module")
            or os.environ.get("TITAN_SIGNER_MODULE", "")
        ).strip()
        if signer_spec:
            signer = load_component(signer_spec)
            logger.info(f"Loaded signer from {signer_spec}")

    if require_live_signer and policy is not None:
        if capital_profile_of(policy) == "live" and signer is None:
            raise ValueError(
                "capital_profile=live requires signing.signer_module "
                "(mock signer banned for live)"
            )

    ks = KillSwitch(safety)
    return SigningNode(
        safety_dir=safety,
        signer=signer,
        max_receipt_age=max_age,
        halt_checker=ks.is_active,
        policy_raw=raw,
    )


def create_app(
    policy_path: Path | None = None,
    safety_dir: Path | None = None,
    signer: SignerFn | None = None,
) -> SafetyHTTPServer:
    """Optional legacy HTTP wrapper around SigningNode (not required for deploy)."""
    safety = safety_dir or (Path.home() / ".openclaw" / "safety")
    port = 19010
    if policy_path and Path(policy_path).exists():
        policy = load_policy(policy_path)
        port = int(getattr(policy.service, "signing_node_port", 19010) or 19010)

    node = build_signing_node(
        policy_path=policy_path,
        safety_dir=Path(safety),
        signer=signer,
        require_live_signer=True,
    )

    def sign_route(body: dict[str, Any], headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        return node.sign(body, headers)

    def health(_body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        h = node.health()
        h["mode"] = "http_legacy"
        return 200, h

    def halt(body: dict[str, Any], _headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        node.halt(str(body.get("reason", "operator halt")))
        (Path(safety) / "SIGNING_HALTED").write_text(
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
        safety_dir=Path(safety),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TITAN Signing (legacy HTTP — prefer in-process via titan-safety gate sign)"
    )
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
    logger.warning(
        "Legacy HTTP signing listener started — prefer mode=in_process "
        "(titan-safety gate sign); :19010 is optional"
    )
    server.start(background=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
