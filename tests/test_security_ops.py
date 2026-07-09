"""Tests for four-pillar security_ops module."""

from __future__ import annotations

from pathlib import Path

from titan_safety.security_ops import SecurityOps


def test_status_default(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    st = ops.status()
    assert st["overall"] in ("HARDENED", "LOCKDOWN")
    assert "impenetrable" in st["pillars"]
    assert len(st["layers"]) == 6


def test_honeypot_arm_disarm(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    assert ops.honeypot_armed() is True
    ops.honeypot_disarm("test")
    assert ops.honeypot_armed() is False
    ops.honeypot_arm("test")
    assert ops.honeypot_armed() is True


def test_lockdown_dry_run(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    result = ops.lockdown("op", "drill", dry_run=True)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert len(result["executed"]) == 6
    assert all(e["status"] == "planned" for e in result["executed"])


def test_lockdown_executes(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    result = ops.lockdown("op", "breach")
    assert result["ok"] is True
    assert ops._ks.health().get("kill_switch_active") is True
    assert ops._evo.is_frozen() is True
    assert ops.signing_halted() is True
    assert ops.honeypot_armed() is True
    assert ops.edge_fail_closed() is True
    assert (tmp_path / "EDGE_FAIL_CLOSED").exists()
    herald = (tmp_path / "herald_queue.jsonl").read_text(encoding="utf-8")
    assert "CRITICAL" in herald
    assert "security_lockdown" in herald
    audit = (tmp_path / "security_lockdown.jsonl").read_text(encoding="utf-8")
    assert "kill_switch_activate" in audit
    edge_step = next(e for e in result["executed"] if e["step"] == "edge_fail_closed")
    assert edge_step["status"] == "ok"
    herald_step = next(e for e in result["executed"] if e["step"] == "herald_critical")
    assert herald_step["status"] == "ok"


def test_edge_fail_closed_flag(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    assert ops.edge_fail_closed() is False
    assert ops.status()["edge_fail_closed"] is False
    payload = ops.set_edge_fail_closed("op", "test arm")
    assert payload["armed"] is True
    flag = tmp_path / "EDGE_FAIL_CLOSED"
    assert flag.exists()
    data = __import__("json").loads(flag.read_text(encoding="utf-8"))
    assert data["armed"] is True
    assert data["operator"] == "op"
    assert data["reason"] == "test arm"
    assert "ts" in data
    assert ops.edge_fail_closed() is True
    assert ops.status()["edge_fail_closed"] is True


def test_lockdown_sets_signing_flag_for_node(tmp_path: Path) -> None:
    from titan_safety.signing_service import SigningNode

    ops = SecurityOps(tmp_path)
    ops.lockdown("op", "breach")
    assert (tmp_path / "SIGNING_HALTED").exists()
    node = SigningNode(safety_dir=tmp_path)
    code, body = node.sign({"request_id": "t"}, {})
    assert code == 403
    assert body["code"] == "SIGNING_HALTED"


def test_layer_check(tmp_path: Path) -> None:
    ops = SecurityOps(tmp_path)
    all_layers = ops.layer_check()
    assert all_layers["ok"] is True
    one = ops.layer_check("L1")
    assert len(one["layers"]) == 1
    assert one["layers"][0]["id"] == "L1"
    assert one["layers"][0]["status"] in ("UP", "DOWN")
    # Non-socket layers stay armed; pcr_drift false unless file exists
    l4 = ops.layer_check("L4")
    assert l4["layers"][0]["status"] == "armed"
    assert l4["layers"][0]["pcr_drift"] is False
    assert ops.pcr_drift() is False
