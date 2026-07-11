"""Shared utilities for TITAN deploy pipeline."""

from __future__ import annotations

import re
import sys
from pathlib import Path


class ExtractorError(Exception):
    """Raised when extractor input/output contract is violated (fail-closed)."""

BOOTSTRAP_FILES = [
    "SOUL.md",
    "AGENTS.md",
    "MEMORY.md",
    "USER.md",
    "TOOLS.md",
    "IDENTITY.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
    "BOOT.md",
]

BOOTSTRAP_MAX_CHARS = 20_000
# OpenClaw docs default is 60_000; TITAN AGENTS.md needs a higher ceiling.
# Set agents.defaults.bootstrapTotalMaxChars accordingly in openclaw.json.
BOOTSTRAP_TOTAL_MAX_CHARS = 150_000
MEMORY_MAX_LINES = 100

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
REFS_DIR = PROJECT_ROOT / "refs"
NORMALIZED_PATH = OUTPUT_DIR / "TITAN.normalized.md"
RECONCILED_PATH = OUTPUT_DIR / "TITAN.reconciled.md"


def unescape_markdown(text: str) -> str:
    """Strip backslash escapes used throughout TITAN.md."""
    text = re.sub(r"\\([#*_\-|>\[\]().`+{}!\\])", r"\1", text)
    text = text.replace("\\<", "<").replace("\\>", ">")
    return text


def read_source(path: Path) -> str:
    """Read UTF-8 source; raise ExtractorError on missing, empty, or corrupt input."""
    if not path.exists():
        raise ExtractorError(f"source not found: {path}")
    if path.stat().st_size == 0:
        raise ExtractorError(f"source empty: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractorError(f"source not valid UTF-8: {path}") from exc


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def find_section(text: str, marker: str, end_markers: list[str] | None = None) -> str:
    """Extract content starting at marker until next section marker."""
    idx = text.find(marker)
    if idx < 0:
        return ""
    start = idx
    if end_markers:
        end = len(text)
        for em in end_markers:
            pos = text.find(em, start + len(marker))
            if pos > start:
                end = min(end, pos)
        return text[start:end].strip()
    return text[start:].strip()


def extract_deploy_block(text: str, filename: str) -> str:
    """Extract markdown between 'Deploy to: ~/.openclaw/FILENAME' fences."""
    pattern = rf"Deploy to: `~/.openclaw/{re.escape(filename)}`"
    m = re.search(pattern, text)
    if not m:
        return ""
    rest = text[m.end() :]
    # Skip ```text fence opener
    rest = re.sub(r"^\s*```text\s*\n", "", rest, count=1)
    # Find ```markdown block
    md_match = re.search(r"```markdown\s*\n(.*?)```", rest, re.DOTALL)
    if md_match:
        return md_match.group(1).strip()
    return ""


def byte_len(text: str) -> int:
    return len(text.encode("utf-8"))


def truncate_to_chars(content: str, max_chars: int) -> tuple[str, bool]:
    """Truncate to max UTF-8 bytes (OpenClaw bootstrapMaxChars is byte-oriented).

    Returns (content, was_truncated).
    """
    if byte_len(content) <= max_chars:
        return content, False
    suffix = "\n\n<!-- truncated to bootstrap char limit -->\n"
    budget = max_chars - byte_len(suffix)
    # Binary search cut point by UTF-8 byte length
    lo, hi = 0, len(content)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if byte_len(content[:mid]) <= budget:
            lo = mid
        else:
            hi = mid - 1
    truncated = content[:lo]
    last_nl = truncated.rfind("\n")
    if last_nl > lo // 2:
        truncated = truncated[:last_nl]
    return truncated + suffix, True


def truncate_lines(content: str, max_lines: int) -> tuple[str, bool]:
    """Return (content, was_truncated)."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content, False
    return "\n".join(lines[:max_lines]) + "\n\n<!-- truncated to line limit -->\n", True


# identifierPolicy=strict — detect visibly truncated on-chain identifiers in output
_TRUNCATED_ETH_ADDR = re.compile(r"0x[a-fA-F0-9]{6,39}(?:\.\.\.|…)")
_TRUNCATED_TX_HASH = re.compile(r"0x[a-fA-F0-9]{8,63}(?:\.\.\.|…)")


def find_truncated_identifiers(content: str) -> list[str]:
    """Return human-readable violations of strict identifier policy."""
    issues: list[str] = []
    for m in _TRUNCATED_ETH_ADDR.finditer(content):
        issues.append(f"truncated address at col {m.start()}: {m.group(0)!r}")
    for m in _TRUNCATED_TX_HASH.finditer(content):
        token = m.group(0)
        if len(token) >= 66:
            continue
        issues.append(f"truncated tx hash at col {m.start()}: {token!r}")
    return issues


def fail_on_truncated_identifiers(content: str, context: str) -> None:
    issues = find_truncated_identifiers(content)
    if issues:
        raise ExtractorError(f"{context}: strict identifierPolicy violations: " + "; ".join(issues[:5]))


def extractor_fail(message: str, code: int = 1) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code
