"""Control-plane HMAC auth tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

from titan_safety.auth import (
    AUTH_HEADER,
    ensure_control_secret,
    sign_control_command,
    verify_control_auth,
)
from titan_safety.http_server import SafetyHTTPServer


def test_sign_and_verify(tmp_path: Path) -> None:
    token = sign_control_command("FLATTEN", "op", tmp_path)
    ok, operator = verify_control_auth(
        {AUTH_HEADER: token}, "FLATTEN", tmp_path
    )
    assert ok is True
    assert operator == "op"


def test_missing_header_denied(tmp_path: Path) -> None:
    ensure_control_secret(tmp_path)
    ok, reason = verify_control_auth({}, "FLATTEN", tmp_path)
    assert ok is False
    assert "missing" in reason


def test_wrong_command_denied(tmp_path: Path) -> None:
    token = sign_control_command("FLATTEN", "op", tmp_path)
    ok, reason = verify_control_auth({AUTH_HEADER: token}, "HEARTBEAT", tmp_path)
    assert ok is False
    assert "mismatch" in reason


def test_tampered_signature_denied(tmp_path: Path) -> None:
    token = sign_control_command("FLATTEN", "op", tmp_path)
    parts = token.split("|")
    parts[-1] = "0" * 64
    ok, reason = verify_control_auth({AUTH_HEADER: "|".join(parts)}, "FLATTEN", tmp_path)
    assert ok is False
    assert "signature" in reason


def test_expired_token_denied(tmp_path: Path) -> None:
    token = sign_control_command("FLATTEN", "op", tmp_path, ts=int(time.time()) - 9999)
    ok, reason = verify_control_auth({AUTH_HEADER: token}, "FLATTEN", tmp_path)
    assert ok is False
    assert "expired" in reason


def test_http_server_rejects_unauthenticated_mutator(tmp_path: Path) -> None:
    called = {"n": 0}

    def flatten(_body, _headers):
        called["n"] += 1
        return 200, {"ok": True}

    srv = SafetyHTTPServer(
        "127.0.0.1",
        0,
        {"POST /v1/flatten": flatten},
        auth_commands={"POST /v1/flatten": "FLATTEN"},
        safety_dir=tmp_path,
    )
    srv.start(background=True)
    assert srv._httpd is not None
    port = srv._httpd.server_address[1]
    try:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/flatten",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
            body = json.loads(exc.read().decode())
            assert body["decision"] == "DENY"
        assert called["n"] == 0

        token = sign_control_command("FLATTEN", "op", tmp_path)
        req2 = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/flatten",
            data=b"{}",
            headers={"Content-Type": "application/json", AUTH_HEADER: token},
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=2) as resp:
            assert resp.status == 200
            assert called["n"] == 1
    finally:
        srv.stop()
