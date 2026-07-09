"""Shared utilities for TITAN deploy pipeline."""

from __future__ import annotations

import re
from pathlib import Path

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
    return path.read_text(encoding="utf-8")


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


def truncate_to_chars(content: str, max_chars: int) -> str:
    """Truncate to max UTF-8 bytes (OpenClaw bootstrapMaxChars is byte-oriented)."""
    if byte_len(content) <= max_chars:
        return content
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
    return truncated + suffix


def truncate_lines(content: str, max_lines: int) -> str:
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    return "\n".join(lines[:max_lines]) + "\n\n<!-- truncated to line limit -->\n"
