"""Unit tests for decision log rotation, repair, and memory-write validation."""

from __future__ import annotations

import json
from pathlib import Path

from titan_safety.audit_chain import AuditChainWriter, DecisionLogEntry, build_fingerprint
from titan_safety.decision_log import (
    ensure_decision_log_healthy,
    is_pending,
    load_jsonl,
    repair_decision_log,
    rotate_decision_log,
    validate_memory_write,
    write_backup,
)


def _append_chain(log: Path, n: int) -> None:
    writer = AuditChainWriter(log)
    fp = build_fingerprint(prompt_version="test")
    for i in range(n):
        writer.append(
            DecisionLogEntry(
                decision_id=f"d{i}",
                agent_id="GUARDIAN",
                action="validate",
                fingerprint=fp,
                payload={"status": "resolved", "i": i},
            )
        )


def test_validate_memory_write_requires_fields() -> None:
    ok, msg = validate_memory_write(
        {"agent_id": "ARCHON", "rationale": "test", "ts": 1.0}
    )
    assert ok is True
    ok, msg = validate_memory_write({"agent_id": "ARCHON", "ts": 1.0})
    assert ok is False
    assert "rationale" in msg


def test_is_pending_fail_closed() -> None:
    assert is_pending({"status": "pending"}) is True
    assert is_pending({"status": "resolved"}) is False
    assert is_pending({}) is True


def test_rotate_prunes_oldest_resolved_only(tmp_path: Path) -> None:
    log = tmp_path / "decision_log.jsonl"
    records = []
    for i in range(5):
        records.append(
            {
                "ts": float(i),
                "status": "resolved",
                "decision_id": f"old{i}",
                "agent_id": "A",
                "payload": {},
            }
        )
    records.append(
        {
            "ts": 99.0,
            "status": "pending",
            "decision_id": "pending1",
            "agent_id": "A",
            "payload": {},
        }
    )
    log.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    result = rotate_decision_log(log, max_resolved=3, backup=False)
    assert result.rotated is True
    assert result.removed == 2
    assert result.kept_pending == 1

    kept, err = load_jsonl(log)
    assert err is None
    ids = [r["decision_id"] for r in kept]
    assert "pending1" in ids
    assert "old0" not in ids
    assert "old1" not in ids


def test_rotate_aborts_on_corrupt_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "decision_log.jsonl"
    log.write_text('{"ok":true}\n{broken\n', encoding="utf-8")
    result = rotate_decision_log(log, max_resolved=1, backup=False)
    assert result.rotated is False
    assert "parse error" in result.message.lower()


def test_repair_from_backup(tmp_path: Path) -> None:
    log = tmp_path / "decision_log.jsonl"
    backup = tmp_path / "decision_log.jsonl.bak"
    _append_chain(backup, 2)

    log.write_text("not json\n", encoding="utf-8")
    result = repair_decision_log(log, backup)
    assert result.repaired is True

    writer = AuditChainWriter(log)
    ok, _ = writer.verify()
    assert ok is True


def test_ensure_healthy_repairs_corrupt_log(tmp_path: Path) -> None:
    log = tmp_path / "decision_log.jsonl"
    _append_chain(log, 3)
    write_backup(log)
    log.write_text("{bad\n", encoding="utf-8")

    result = ensure_decision_log_healthy(log, max_resolved=500)
    assert result["healthy"] is True
    assert result["repair"]["repaired"] is True

    writer = AuditChainWriter(log)
    ok, _ = writer.verify()
    assert ok is True
