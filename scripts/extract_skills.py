#!/usr/bin/env python3
"""Extract skills from §K into workspace/skills/ directories."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    OUTPUT_DIR,
    RECONCILED_PATH,
    ExtractorError,
    extractor_fail,
    fail_on_truncated_identifiers,
    read_source,
    unescape_markdown,
    write_text,
)

SKILL_HEADER = re.compile(
    r"^#{1,3}\s+skills/([a-z0-9_]+)/SKILL\.md.*$", re.MULTILINE | re.IGNORECASE
)

STUB_SKILLS = [
    "archon_orchestration",
    "guardian_risk",
    "trench_ops_execution",
    "oracle_signals",
    "cortex_reflection",
    "sentinel_security",
    "herald_notify",
    "nexus_feeds",
    "forge_infra",
    "alchemy_defi",
    "atlas_portfolio",
    "quant_analysis",
    "arbiter_backtest",
    "horizon_rd",
    "lamarck_learning",
    "darwin_godel_research",
    "wraith_onchain",
    "predator_scanner",
    "augur_macro",
    "narrative_catalyst",
]

# Quantum skills archived — not loaded at runtime (classical-only mode)
QUANTUM_SKILLS = [
    "quantum_derivative_pricing",
    "quantum_var_cvar",
    "quantum_counterparty_score",
    "quantum_fraud_detection",
    "quantum_portfolio_rebalance",
    "quantum_gas_prediction",
    "quantum_yield_optimizer",
    "quantum_signal",
    "quantum_qrng",
]


def archived_quantum_skill(name: str, original: str) -> str:
    """Mark extracted quantum skill as removed; preserve stub for audit trail."""
    title = name.replace("_", " ").title()
    return f"""---
name: {name}
description: {title} — REMOVED (quantum layer dormant; classical-only mode)
metadata:
  openclaw:
    status: removed
  skill_tuple:
    intent: {name}
    method: archived
    difficulty: high
---

# {title} (ARCHIVED)

**Status:** `removed` — quantum compute layer is **permanently disabled** for live capital.
Quantum agents removed from catalog. Use classical equivalents (QUANT, ORACLE, GUARDIAN).

This skill is retained under `skills/_archived/quantum/` for spec audit only — not loaded at runtime.

## Original spec (truncated)

{original[:800].strip()}{"..." if len(original) > 800 else ""}
"""


def stub_skill(name: str) -> str:
    title = name.replace("_", " ").title()
    return f"""---
name: {name}
description: {title} — stub skill (full definition pending §SKILLS_full.md)
metadata:
  openclaw:
    status: stub
  skill_tuple:
    intent: {name}
    method: stub
    difficulty: medium
---

# {title}

Status: **stub** — minimal skill placeholder for deploy bundle.

## Integration

- Agent routing: see AGENTS.md
- Full spec: pending extraction from TITAN source
"""


def extract_skills(text: str) -> dict[str, str]:
    text = unescape_markdown(text)
    skills: dict[str, str] = {}

    # Find §K section
    k_start = text.find("# §K — Skills Directory")
    if k_start < 0:
        k_start = text.find("# §K — SKILLS DIRECTORY")
    k_end = text.find("# §L — Memory Directory", k_start)
    if k_end < 0:
        k_end = text.find("# §L — MEMORY", k_start)
    if k_start < 0:
        raise ExtractorError("§K — Skills Directory section not found in source")
    section = text[k_start:k_end]

    headers = list(SKILL_HEADER.finditer(section))
    for i, match in enumerate(headers):
        name = match.group(1)
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
        body = section[start:end].strip()

        # Skip REMOVED skills
        if "REMOVED" in match.group(0):
            continue

        # Extract yaml frontmatter block if present
        content = body
        yaml_match = re.search(r"```yaml\s*\n(.*?)```", body, re.DOTALL)
        if yaml_match:
            front = yaml_match.group(1).strip()
            rest = body[yaml_match.end() :].strip()
            if not rest or rest.startswith("> See"):
                content = f"---\n{front}\n---\n\n# {name.replace('_', ' ').title()}\n\nExtracted from TITAN §K.\n"
            else:
                content = f"---\n{front}\n---\n\n{rest}"
        elif body.startswith("> See"):
            content = stub_skill(name)
        elif len(body) < 20:
            content = stub_skill(name)
        else:
            content = f"# {name.replace('_', ' ').title()}\n\n{body}"

        skills[name] = content

    # Add priority stub skills if missing
    for name in STUB_SKILLS:
        if name not in skills:
            skills[name] = stub_skill(name)

    return skills


def write_skills(
    skills: dict[str, str], quantum_archive: dict[str, str], output_dir: Path
) -> tuple[int, int]:
    """Write active skills; archive quantum_* under _archived/quantum/."""
    import shutil

    archived_dir = output_dir / "_archived" / "quantum"
    active = 0
    archived = 0

    for name, content in sorted(quantum_archive.items()):
        write_text(archived_dir / name / "SKILL.md", archived_quantum_skill(name, content))
        archived += 1
        stale = output_dir / name
        if stale.is_dir():
            shutil.rmtree(stale)

    for name, content in sorted(skills.items()):
        fail_on_truncated_identifiers(content, f"skill:{name}")
        skill_dir = output_dir / name
        write_text(skill_dir / "SKILL.md", content)
        active += 1

    return active, archived


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract skills")
    parser.add_argument("input", type=Path, nargs="?", default=RECONCILED_PATH)
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=OUTPUT_DIR / "workspace" / "skills"
    )
    args = parser.parse_args()

    try:
        text = read_source(args.input)
        all_skills = extract_skills(text)
    except ExtractorError as exc:
        return extractor_fail(str(exc))
    quantum_archive = {
        n: all_skills.pop(n)
        for n in list(all_skills)
        if n in QUANTUM_SKILLS or n.startswith("quantum_")
    }

    active, archived = write_skills(all_skills, quantum_archive, args.output_dir)

    print(
        f"Extracted {active} active + {archived} archived quantum skills -> {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
