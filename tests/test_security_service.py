"""HTTP security_ops service smoke tests."""

from __future__ import annotations

from pathlib import Path

from titan_safety.auth import sign_control_command
from titan_safety.security_service import create_app


def test_create_app_routes(tmp_path: Path) -> None:
    server = create_app(tmp_path, port=19088)
    assert "GET /health" in server.routes
    assert "POST /v1/lockdown" in server.routes


def test_health_handler(tmp_path: Path) -> None:
    server = create_app(tmp_path, port=19089)
    code, body = server.routes["GET /health"]({}, {})
    assert code == 200
    assert body.get("status") in ("ok", "halted")
    assert "pillars" in body
    assert len(body.get("layers", [])) == 6


def test_lockdown_requires_auth(tmp_path: Path) -> None:
    server = create_app(tmp_path, port=19090)
    code, body = server.routes["POST /v1/lockdown"](
        {"operator": "t", "reason": "x", "dry_run": True},
        {},
    )
    assert code == 401
    assert body.get("ok") is False


def test_lockdown_with_hmac(tmp_path: Path) -> None:
    server = create_app(tmp_path, port=19091)
    token = sign_control_command("LOCKDOWN", "op", safety_dir=tmp_path)
    code, body = server.routes["POST /v1/lockdown"](
        {"operator": "op", "reason": "drill", "dry_run": True},
        {"X-Titan-Auth": token},
    )
    assert code == 200
    assert body.get("ok") is True
    assert body.get("dry_run") is True
