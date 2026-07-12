#!/usr/bin/env python3
"""CI: fail when docs claim human YES for paths policy auto-allows.

Scans markdown docs against templates/risk_kernel/policy.yaml bounded-autonomy fields.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "templates" / "risk_kernel" / "policy.yaml"

DOC_GLOBS = (
    "AGENTS.md",
    "TITAN_CURRENT.md",
    "DEPLOYMENT_GUIDE*.md",
    "BEGINNER*.md",
    "LIVE_CAPITAL*.md",
    "docs/**/*.md",
    "iron-laws.md",
)

# Patterns that claim human approval is required (contradicts policy when auto-allowed)
# Negative lookahead avoids "no human YES" autonomous statements.
HUMAN_YES_PATTERNS = [
    re.compile(r"flash[- ]loan(?!.*\bno human YES\b).*human\s+YES", re.I),
    re.compile(r"flash[- ]loan\s+live.*\|\s*—\s*\|\s*YES", re.I),
    re.compile(r"(?<!no )Human\s+YES\s+required.*flash", re.I),
    re.compile(r"flash[- ]loan.*requires?\s+human(?!\s+YES\s+is\s+not)", re.I),
]

POLICY_AUTO_ALLOW_KEYS = {
  "flash_loan_live_requires_approval": False,
  "leverage_change_requires_approval": True,
  "new_pipeline_requires_approval": True,
}


def _parse_policy_flags(text: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for key in POLICY_AUTO_ALLOW_KEYS:
        m = re.search(rf"^\s*{re.escape(key)}:\s*(true|false)\s*", text, re.M | re.I)
        if m:
            flags[key] = m.group(1).lower() == "true"
    return flags


def _collect_docs() -> list[Path]:
    docs: list[Path] = []
    for pattern in DOC_GLOBS:
        docs.extend(ROOT.glob(pattern))
    return sorted({p.resolve() for p in docs if p.is_file()})


def _line_claims_human_yes_required(line: str) -> bool:
    lower = line.lower()
    if "no human yes" in lower or "remove human yes" in lower:
        return False
    if "autonomous" in lower and "flash" in lower:
        return False
    if "human yes implied" in lower:
        return False  # historical comparison rows
    return True


def check_doc(path: Path, policy_flags: dict[str, bool]) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path.name
    lines = text.splitlines()

    # Flash loans: policy false = autonomous when enabled
    if policy_flags.get("flash_loan_live_requires_approval") is False:
        for pat in HUMAN_YES_PATTERNS:
            for match in pat.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                line = lines[line_no - 1] if line_no <= len(lines) else ""
                if not _line_claims_human_yes_required(line):
                    continue
                errors.append(
                    f"{rel}:{line_no}: claims human YES for flash loans but "
                    f"policy flash_loan_live_requires_approval=false"
                )

    # Bounded autonomy matrix row check in AGENTS.md
    if path.name == "AGENTS.md":
        if re.search(r"Flash-loan live\s*\|\s*—\s*\|\s*YES", text):
            if policy_flags.get("flash_loan_live_requires_approval") is False:
                errors.append(
                    f"{rel}: bounded autonomy matrix lists flash-loan live as human YES "
                    f"but policy allows autonomous path"
                )

    return errors


def main() -> int:
    if not POLICY_PATH.exists():
        print(f"FAIL: missing policy at {POLICY_PATH}", file=sys.stderr)
        return 1

    policy_text = POLICY_PATH.read_text(encoding="utf-8")
    policy_flags = _parse_policy_flags(policy_text)
    if not policy_flags:
        print("WARN: could not parse policy approval flags", file=sys.stderr)

    all_errors: list[str] = []
    docs = _collect_docs()
    for doc in docs:
        if doc.name == "TIER3_INSTITUTIONAL_OPS.md":
            continue  # documents contradictions intentionally
        all_errors.extend(check_doc(doc, policy_flags))

    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"[check_doc_policy_consistency] OK: {len(docs)} doc(s) consistent with policy.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
