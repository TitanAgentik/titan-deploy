"""Gate receipt + signing node tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

from titan_safety.gate_receipt import (
    RECEIPT_HEADER,
    issue_gate_receipt,
    verify_gate_receipt,
)
from titan_safety.kernel import TradeRequest
from titan_safety.signing_service import (
    SigningNode,
    build_signing_node,
    resolve_signing_mode,
)


def _trade(**kwargs) -> TradeRequest:
    defaults = dict(
        trade_id="t1",
        venue="paper",
        contract="0xabc",
        side="buy",
        notional_usd=10.0,
    )
    defaults.update(kwargs)
    return TradeRequest(**defaults)


def test_issue_and_verify_receipt(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    ok, reason = verify_gate_receipt(receipt.token, trade, tmp_path)
    assert ok is True
    assert reason == "ok"


def test_receipt_rejects_tamper(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    parts = receipt.token.split("|")
    parts[-1] = "0" * 64
    ok, reason = verify_gate_receipt("|".join(parts), trade, tmp_path)
    assert ok is False
    assert "signature" in reason


def test_receipt_rejects_wrong_trade(tmp_path: Path) -> None:
    receipt = issue_gate_receipt(_trade(), tmp_path)
    ok, reason = verify_gate_receipt(receipt.token, _trade(trade_id="other"), tmp_path)
    assert ok is False
    assert "trade_id" in reason


def test_receipt_expires(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path, ts=int(time.time()) - 120)
    ok, reason = verify_gate_receipt(receipt.token, trade, tmp_path, max_age_seconds=30)
    assert ok is False
    assert "expired" in reason


def test_signing_denies_without_receipt(tmp_path: Path) -> None:
    node = SigningNode(safety_dir=tmp_path)
    code, body = node.sign(
        {"trade": _trade().__dict__},
        {},
    )
    assert code == 401
    assert body["code"] == "GATE_RECEIPT_INVALID"


def test_signing_allows_with_receipt(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    node = SigningNode(safety_dir=tmp_path)
    code, body = node.sign(
        {"trade": trade.__dict__},
        {RECEIPT_HEADER: receipt.token},
    )
    assert code == 200
    assert body["decision"] == "ALLOW"
    assert "signature" in body


def test_signing_halted(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    node = SigningNode(safety_dir=tmp_path)
    node.halt("test")
    code, body = node.sign(
        {"trade": trade.__dict__},
        {RECEIPT_HEADER: receipt.token},
    )
    assert code == 403
    assert body["code"] == "SIGNING_HALTED"


def test_http_signing_service(tmp_path: Path) -> None:
    import urllib.error
    import urllib.request

    from titan_safety.signing_service import create_app

    # create_app needs a policy for port; use None defaults to 19010 — bind 0 via patch
    # Use SigningNode directly through a tiny server instead
    from titan_safety.http_server import SafetyHTTPServer

    node = SigningNode(safety_dir=tmp_path)

    def sign_route(body, headers):
        return node.sign(body, headers)

    srv = SafetyHTTPServer(
        "127.0.0.1",
        0,
        {"POST /v1/sign": sign_route, "GET /health": lambda _b, _h: (200, node.health())},
        safety_dir=tmp_path,
    )
    srv.start(background=True)
    assert srv._httpd is not None
    port = srv._httpd.server_address[1]
    try:
        trade = _trade()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/sign",
            data=json.dumps({"trade": trade.__dict__}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        receipt = issue_gate_receipt(trade, tmp_path)
        req2 = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/sign",
            data=json.dumps({"trade": trade.__dict__}).encode(),
            headers={
                "Content-Type": "application/json",
                RECEIPT_HEADER: receipt.token,
            },
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=2) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            assert body["decision"] == "ALLOW"
    finally:
        srv.stop()


def test_build_signing_node_in_process(tmp_path: Path) -> None:
    trade = _trade()
    receipt = issue_gate_receipt(trade, tmp_path)
    node = build_signing_node(safety_dir=tmp_path, require_live_signer=False)
    code, body = node.sign(
        {"trade": trade.__dict__},
        {RECEIPT_HEADER: receipt.token},
    )
    assert code == 200
    assert body["decision"] == "ALLOW"
    assert node.health()["mode"] == "in_process"


def test_resolve_signing_mode_default() -> None:
    assert resolve_signing_mode({}) == "in_process"
    assert resolve_signing_mode({"signing": {"mode": "http"}}) == "http"
