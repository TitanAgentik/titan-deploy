"""Tests for audit WORM export script."""

from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "templates" / "safety"))

from audit_export_worm import (  # noqa: E402
    build_manifest,
    create_archive,
    export_audit,
    verify_chain,
)
from titan_safety.audit_chain import (  # noqa: E402
    AuditChainWriter,
    DecisionLogEntry,
    build_fingerprint,
)


def _write_chain(path: Path, n: int = 2) -> None:
    writer = AuditChainWriter(path)
    fp = build_fingerprint(prompt_version="test-export")
    for i in range(n):
        writer.append(
            DecisionLogEntry(
                decision_id=f"exp-{i}",
                agent_id="GUARDIAN",
                action="validate",
                fingerprint=fp,
                payload={"i": i},
            )
        )


def test_verify_chain_valid(tmp_path: Path) -> None:
    log = tmp_path / "chain.jsonl"
    _write_chain(log)
    ok, msg = verify_chain(log)
    assert ok is True
    assert "valid" in msg


def test_create_archive_contains_manifest(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    _write_chain(log)
    archive, manifest = create_archive(decision_log=log, audit_log=log, out_dir=tmp_path)
    assert archive.exists()
    assert manifest["chain_verified"] is True
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "manifest.json" in names
    assert "decision_log.jsonl" in names


def test_export_dry_run(tmp_path: Path) -> None:
    log = tmp_path / "audit.jsonl"
    _write_chain(log)
    result = export_audit(
        decision_log=log,
        audit_log=log,
        dry_run=True,
        out_dir=tmp_path,
    )
    assert result["ok"] is True
    assert result["uploaded"] is False
    assert Path(result["local_archive"]).exists()


def test_build_manifest_hashes(tmp_path: Path) -> None:
    log = tmp_path / "d.jsonl"
    log.write_text('{"x":1}\n', encoding="utf-8")
    m = build_manifest(decision_log=log, audit_log=log, chain_ok=True, chain_msg="ok")
    assert m["chain_verified"] is True
    assert len(m["files"]) == 1
    assert len(m["files"][0]["sha256"]) == 64
