#!/usr/bin/env python3
"""Generate output/TITAN.digest.md — a compact navigation map of the spec.

TITAN.reconciled.md is ~750 KB and can never be loaded into an OpenClaw/Hermes
context window. Agents get their operating context from the bootstrap set
(workspace/*.md); this digest is the on-demand index for everything else:
a section map with line numbers plus pointers to refs/ companions, kept well
under the 20,000-byte per-file bootstrap limit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT_DIR, PROJECT_ROOT, RECONCILED_PATH, ExtractorError, byte_len, extractor_fail, write_text

DIGEST_PATH = OUTPUT_DIR / "TITAN.digest.md"
MAX_BYTES = 18_000

HEADER = """# TITAN Spec Digest (navigation map)

> **Do not load `TITAN.reconciled.md` into context** — it is ~750 KB.
> This digest is the index. Read specific sections with a ranged read
> (line numbers below), or use the `refs/` companions.
>
> Operating context = bootstrap set (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, …).
> This file is reference-only.

## Key invariants (enforced in code, not prose)

- Routine trades <1% equity auto-execute within GUARDIAN limits; promotion to
  live, evolution deploys, leverage changes, flash-loan live, and trades >1%
  equity require explicit human YES. TIMEOUT = HOLD/de-risk, never promote.
- Out-of-process risk kernel `:19001` and portfolio risk `:19004` DENY is
  authoritative; agent votes are advisory.
- In-process SigningNode refuses to sign without a fresh `X-Titan-Gate-Receipt`
  (max 30 s). Mock signer / mock flatten adapters are banned at startup when
  `capital_profile: live`.
- Kill switch deactivation requires an HMAC-signed RESUME. Mutating safety
  POSTs require `X-Titan-Auth`.
- Quantum agents removed from catalog — 100% classical execution.

## Companion files (refs/)

"""


def section_map(text: str) -> list[tuple[int, int, str]]:
    """(line_no, level, title) for #, ##, ### headings outside code fences."""
    out = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,3}) (.+)$", line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def main() -> int:
    if not RECONCILED_PATH.exists():
        return extractor_fail(f"reconciled source missing: {RECONCILED_PATH}")
    try:
        text = RECONCILED_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return extractor_fail(f"reconciled source not valid UTF-8: {RECONCILED_PATH}")
    if not text.strip():
        return extractor_fail(f"reconciled source empty: {RECONCILED_PATH}")
    body = HEADER

    refs_dir = PROJECT_ROOT / "refs"
    if refs_dir.is_dir():
        for p in sorted(refs_dir.glob("*.md")):
            first_para = ""
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("> **Purpose:**"):
                    first_para = line.removeprefix("> **Purpose:**").strip()
                    break
            body += f"- `refs/{p.name}` — {first_para}\n"

    body += (
        "\n## Section map — `output/TITAN.reconciled.md` "
        f"({len(text.splitlines())} lines)\n\n"
        "Read with a ranged read at the given line number.\n\n"
    )

    lines = []
    for line_no, level, title in section_map(text):
        if level == 3:
            continue  # keep digest small; ### headings findable via parent
        indent = "  " * (level - 1)
        lines.append(f"{indent}- L{line_no}: {title}")

    # Trim from the bottom if over budget (top sections are highest-value).
    while lines and byte_len(body + "\n".join(lines) + "\n") > MAX_BYTES:
        lines.pop()
    body += "\n".join(lines) + "\n"

    write_text(DIGEST_PATH, body)
    print(f"Digest -> {DIGEST_PATH} ({byte_len(body)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
