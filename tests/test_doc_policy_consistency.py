"""Tests for doc vs policy consistency CI checker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

from check_doc_policy_consistency import (  # noqa: E402
    _parse_policy_flags,
    check_doc,
)


def test_parse_policy_flash_loan_autonomous() -> None:
    text = "flash_loan_live_requires_approval: false\n"
    flags = _parse_policy_flags(text)
    assert flags.get("flash_loan_live_requires_approval") is False


def test_check_doc_flags_flash_loan_contradiction(tmp_path: Path) -> None:
    doc = tmp_path / "AGENTS.md"
    doc.write_text("| Flash-loan live | — | YES |\n", encoding="utf-8")
    flags = {"flash_loan_live_requires_approval": False}
    errors = check_doc(doc, flags)
    assert any("flash" in e.lower() for e in errors)


def test_check_doc_passes_consistent_flash(tmp_path: Path) -> None:
    doc = tmp_path / "AGENTS.md"
    doc.write_text("| Flash-loan live | YES (when enabled) | — |\n", encoding="utf-8")
    flags = {"flash_loan_live_requires_approval": False}
    errors = check_doc(doc, flags)
    assert errors == []


def test_human_yes_pattern_detected(tmp_path: Path) -> None:
    doc = tmp_path / "guide.md"
    doc.write_text("Flash-loan live requires human YES before broadcast.\n", encoding="utf-8")
    flags = {"flash_loan_live_requires_approval": False}
    errors = check_doc(doc, flags)
    assert len(errors) >= 1
