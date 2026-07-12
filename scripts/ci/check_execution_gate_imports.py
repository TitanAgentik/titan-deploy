#!/usr/bin/env python3
"""CI: execution skills must reference ExecutionGate (structural non-bypass)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIRS = [
    ROOT / "templates" / "skills",
]

EXECUTION_SKILL_PATTERNS = (
    "trench_ops",
    "memecoin_trench",
    "flash_loan_router",
    "execution",
)

GATE_MARKERS = (
    re.compile(r"ExecutionGate", re.I),
    re.compile(r"execution_gate", re.I),
    re.compile(r"titan-safety\s+gate\s+(check|sign)", re.I),
    re.compile(r"from\s+titan_safety\.execution_gate\s+import", re.I),
)


def is_execution_skill(path: Path) -> bool:
    name = path.parent.name.lower()
    return any(p in name for p in EXECUTION_SKILL_PATTERNS)


def skill_has_gate_reference(text: str) -> bool:
    return any(p.search(text) for p in GATE_MARKERS)


def main() -> int:
    errors: list[str] = []
    checked = 0
    for base in SKILL_DIRS:
        if not base.exists():
            continue
        for skill_md in base.glob("*/SKILL.md"):
            if not is_execution_skill(skill_md):
                continue
            checked += 1
            text = skill_md.read_text(encoding="utf-8", errors="replace")
            if not skill_has_gate_reference(text):
                errors.append(f"{skill_md}: missing ExecutionGate / gate check reference")

    if checked == 0:
        print("[check_execution_gate_imports] WARN: no execution skills found to check")
        return 0

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"[check_execution_gate_imports] OK: {checked} execution skill(s) reference ExecutionGate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
