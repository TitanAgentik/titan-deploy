"""Unit tests for deploy extractors — fail-closed contracts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import (  # noqa: E402
    ExtractorError,
    byte_len,
    find_truncated_identifiers,
    read_source,
    truncate_lines,
    truncate_to_chars,
)
from extract_bootstrap import extract_all  # noqa: E402
from extract_skills import extract_skills  # noqa: E402


def test_read_source_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ExtractorError, match="not found"):
        read_source(tmp_path / "missing.md")


def test_read_source_empty_raises(tmp_path: Path) -> None:
    p = tmp_path / "empty.md"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ExtractorError, match="empty"):
        read_source(p)


def test_truncate_to_chars_reports_truncation() -> None:
    content = "x" * 500
    out, was = truncate_to_chars(content, 200)
    assert was is True
    assert byte_len(out) <= 200
    assert "truncated" in out


def test_truncate_lines_reports_truncation() -> None:
    content = "\n".join(f"line {i}" for i in range(10))
    out, was = truncate_lines(content, 3)
    assert was is True
    assert out.startswith("line 0")
    assert "truncated to line limit" in out


def test_find_truncated_identifiers_detects_ellipsis() -> None:
    issues = find_truncated_identifiers("wallet 0xabcdef123456...")
    assert issues


def test_extract_skills_requires_section_k() -> None:
    with pytest.raises(ExtractorError, match="§K"):
        extract_skills("# No skills here\n")


def test_extract_all_shadow_evolution_language(reconciled_text: str) -> None:
    files = extract_all(reconciled_text)
    agents = files["AGENTS.md"]
    assert "DARWIN_GODEL" in agents
    assert "shadow" in agents.lower()
    assert "Evolution deploy" in agents or "evolution deploy" in agents.lower()


def test_extract_all_bounded_autonomy_matrix(reconciled_text: str) -> None:
    files = extract_all(reconciled_text)
    soul = files["SOUL.md"]
    assert "Shadow only" in soul or "shadow-only" in soul.lower()
    assert "Never auto-promote" in soul or "never auto-promote" in soul.lower()


@pytest.fixture
def reconciled_text() -> str:
    path = Path(__file__).resolve().parent.parent / "output" / "TITAN.reconciled.md"
    if not path.exists():
        pytest.skip("output/TITAN.reconciled.md missing — run scripts/build.py first")
    return read_source(path)
