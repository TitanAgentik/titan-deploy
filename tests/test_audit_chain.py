"""Unit tests for version-fingerprint audit chain."""

from __future__ import annotations

from pathlib import Path

from titan_safety.audit_chain import (
    AuditChainWriter,
    DecisionLogEntry,
    VersionFingerprint,
    build_fingerprint,
)


def test_fingerprint_composite() -> None:
    fp = VersionFingerprint("a", "b", "v1", "c")
    assert len(fp.composite_hash()) == 64


def test_append_and_verify_chain(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    writer = AuditChainWriter(log)
    fp = build_fingerprint(prompt_version="test-v1")
    for i in range(3):
        entry = DecisionLogEntry(
            decision_id=f"d{i}",
            agent_id="GUARDIAN",
            action="validate_trade",
            fingerprint=fp,
            payload={"i": i},
        )
        writer.append(entry)
    ok, msg = writer.verify()
    assert ok is True


def test_tamper_detection(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    writer = AuditChainWriter(log)
    fp = build_fingerprint(prompt_version="v1")
    writer.append(
        DecisionLogEntry("d1", "ARCHON", "propose", fp, {"x": 1})
    )
    lines = log.read_text().strip().splitlines()
    bad = lines[0].replace("propose", "execute")
    log.write_text(bad + "\n")
    ok, msg = writer.verify()
    assert ok is False
