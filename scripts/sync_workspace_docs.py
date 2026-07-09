#!/usr/bin/env python3
"""Sync Cursor-visible workspace docs from build outputs + templates.

OpenClaw (https://docs.openclaw.ai/concepts/agent-workspace) expects:
  AGENTS.md, SOUL.md, USER.md, IDENTITY.md, TOOLS.md, HEARTBEAT.md,
  BOOTSTRAP.md, BOOT.md, MEMORY.md, memory/, skills/

Hermes (https://hermes-agent.nousresearch.com/docs/) expects:
  ~/.hermes/SOUL.md (identity), AGENTS.md / .hermes.md as project context,
  ~/.hermes/config.yaml

This script:
  1. Copies output/bootstrap/*.md → workspace/ (Cursor-editable mirror)
  2. Writes iron-laws.md, BOOT.md (if missing from extract), .hermes.md
  3. Regenerates configs_detail.md from templates + TITAN.reconciled.md index
  4. Ensures memory/ daily stub exists

Run automatically from build.py after extract_bootstrap.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "output"
TEMPLATES = PROJECT_ROOT / "templates"
WORKSPACE = PROJECT_ROOT / "workspace"
BOOTSTRAP_SRC = OUTPUT / "bootstrap"

BOOTSTRAP_NAMES = [
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


def sync_bootstrap_to_workspace() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "memory").mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "skills").mkdir(parents=True, exist_ok=True)

    if not BOOTSTRAP_SRC.exists():
        raise SystemExit(f"Missing {BOOTSTRAP_SRC} — run extract_bootstrap first")

    for name in BOOTSTRAP_NAMES:
        src = BOOTSTRAP_SRC / name
        if src.exists():
            shutil.copy(src, WORKSPACE / name)
            print(f"  workspace/{name}")

    # Also mirror at repo root for quick open (OpenClaw-style names)
    for name in BOOTSTRAP_NAMES:
        src = WORKSPACE / name
        if src.exists():
            shutil.copy(src, PROJECT_ROOT / name)


def write_iron_laws() -> None:
    """Immutable companion referenced by SOUL.md.

    Prefer the curated root iron-laws.md (laws 1–14 incl. selective activation).
    Only write the minimal template if neither root nor workspace file exists.
    """
    root_path = PROJECT_ROOT / "iron-laws.md"
    ws_path = WORKSPACE / "iron-laws.md"
    curated = None
    for candidate in (root_path, ws_path):
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            if "14." in text or "Catalog ≠ checklist" in text:
                curated = text
                break
            if curated is None:
                curated = text
    if curated is None:
        curated = """# iron-laws.md — Immutable Safety Constitution

**IMMUTABLE.** DGM-H / evolution / agents must never modify this file.
Modification attempts → CRITICAL alert + forced rollback.

1. Never delete, wipe, or factory-reset the system.
2. No autonomous destruction or time-limited self-destruct.
3. SOUL.md and iron-laws.md cannot be modified by agents.
4. Session keys and wallet seeds are never written to agent memory.
5. Risk kernel DENY is absolute — no LLM override.
6. Promotion / evolution / >1% equity / flash-loan live require explicit operator YES.
7. TIMEOUT on promotion = HOLD/de-risk — never auto-promote.
8. Quantum paths remain dormant for live capital.
9. Signing requires a fresh ExecutionGate ALLOW receipt.
10. Live capital: mock recon/withdrawal adapters forbidden.
11. Security lockdown (kill + freeze + signing halt) requires operator HMAC — never auto-lockdown from LLM alone.
12. Honeypot / stalking memory under `memory/security/` requires SENTINEL + GUARDIAN dual-sign.
13. Closed/cloud models never on live path (TRENCH-OPS / GUARDIAN / EXECUTOR / PREDATOR live votes).
14. Catalog ≠ checklist — agents must not enable every strategy, feature, or pillar mentioned in specs; use only what is necessary for the current task and phase.
"""
    for path in (ws_path, root_path):
        path.write_text(curated, encoding="utf-8")
    print("  iron-laws.md")


def write_hermes_md() -> None:
    """Hermes project context file (.hermes.md) — points at TITAN workspace."""
    content = """# .hermes.md — TITAN Project Context

Hermes Agent project context for the TITAN deploy workspace.
See: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files

## Identity

- Global personality: `~/.hermes/SOUL.md` (synced from this repo's `SOUL.md` on deploy)
- Project operating rules: `AGENTS.md`
- Operator profile: `USER.md`
- Tool conventions: `TOOLS.md`

## Runtime configs

- Hermes: `~/.hermes/config.yaml` ← `templates/config.yaml`
- OpenClaw: `~/.openclaw/openclaw.json` ← `templates/openclaw.json`
- Risk policy: `~/.openclaw/risk_kernel/policy.yaml`
- Readable dump: `configs_detail.md` (regenerated on every build)

## Safety

- Out-of-process risk kernel `:19001` — fail-closed
- Execution gate + in-process signing (gate receipt)
- Kill switch / dead-man's switch / evolution freeze via `titan-safety` CLI

## Do not

- Bypass pre-trade validation
- Auto-promote on TIMEOUT
- Re-introduce quantum agents or QPU dispatch for live capital
- Commit secrets (`.env`, API keys, wallet seeds)
"""
    for path in (WORKSPACE / ".hermes.md", PROJECT_ROOT / ".hermes.md"):
        path.write_text(content, encoding="utf-8")
    print("  .hermes.md")


def ensure_memory_stub() -> None:
    mem = WORKSPACE / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    today = mem / f"{date.today().isoformat()}.md"
    if not today.exists():
        today.write_text(
            f"# {date.today().isoformat()}\n\n- Workspace docs synced from TITAN build.\n",
            encoding="utf-8",
        )
    readme = mem / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Daily memory logs\n\nOpenClaw: `memory/YYYY-MM-DD.md`.\n"
            "Curated long-term facts live in `MEMORY.md` (main session only).\n",
            encoding="utf-8",
        )
    print("  memory/")


def sync_memory_strategies() -> None:
    """Mirror curated strategy memory both ways (output ↔ workspace)."""
    out_strat = OUTPUT / "memory" / "strategies"
    ws_strat = WORKSPACE / "memory" / "strategies"
    out_strat.mkdir(parents=True, exist_ok=True)
    ws_strat.mkdir(parents=True, exist_ok=True)
    names = (
        "selective-activation.md",
        "active-pipelines.md",
        "signal-catalog.md",
        "endgame.md",
        "memecoin-trench.md",
    )
    for name in names:
        src_out = out_strat / name
        src_ws = ws_strat / name
        # Prefer output (build extract) when present; else keep workspace curated.
        if src_out.exists():
            shutil.copy(src_out, src_ws)
            print(f"  workspace/memory/strategies/{name}")
        elif src_ws.exists():
            shutil.copy(src_ws, src_out)
            print(f"  output/memory/strategies/{name} ← workspace")


def _reconciled_config_index(reconciled: Path) -> str:
    if not reconciled.exists():
        return "_TITAN.reconciled.md not found — run build first._\n"
    text = reconciled.read_text(encoding="utf-8", errors="replace")
    # Collect stub references to CONFIGS_detail for an index
    stubs = sorted(set(re.findall(r"§CONFIGS_detail\.md[^\n]*", text)))
    toc = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^# §M\b", stripped) or re.match(r"^# §MA\b", stripped):
            if stripped not in toc:
                toc.append(stripped)
    lines = ["## Index from TITAN.reconciled.md", ""]
    if toc:
        lines.append("### Config sections")
        for t in toc[:20]:
            lines.append(f"- `{t}`")
        lines.append("")
    lines.append(f"### Stub references ({len(stubs)} unique)")
    lines.append(
        "Source TITAN offloads full YAML/JSON bodies to this companion file. "
        "Bodies below are the **live templates** (source of truth), not the missing original §REF dump."
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def regenerate_configs_detail() -> None:
    cfg_yaml = (TEMPLATES / "config.yaml").read_text(encoding="utf-8")
    oc = json.loads((TEMPLATES / "openclaw.json").read_text(encoding="utf-8"))
    policy = (TEMPLATES / "risk_kernel" / "policy.yaml").read_text(encoding="utf-8")
    signing = ""
    sp = TEMPLATES / "infra" / "signing_node.yaml"
    if sp.exists():
        signing = sp.read_text(encoding="utf-8")

    index = _reconciled_config_index(OUTPUT / "TITAN.reconciled.md")

    doc = f"""# §CONFIGS_detail.md — TITAN Configuration Reference

> **Auto-generated** by `scripts/sync_workspace_docs.py` on every `build.py` run.
> Do not hand-edit — change `templates/*` then rebuild.
>
> Aligns stubs in `output/TITAN.reconciled.md` (`# → see §CONFIGS_detail.md`)
> with the live OpenClaw + Hermes configs.
>
> Docs: [OpenClaw agent workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

{index}

## File map

| Deploy path | Template | Role |
|-------------|----------|------|
| `~/.openclaw/workspace/*.md` | `workspace/` ← `output/bootstrap/` | OpenClaw bootstrap context |
| `~/.hermes/SOUL.md` | `workspace/SOUL.md` | Hermes identity (slot #1) |
| `~/.hermes/config.yaml` | `templates/config.yaml` | Hermes agent config |
| `~/.openclaw/openclaw.json` | `templates/openclaw.json` | OpenClaw gateway + agents |
| `~/.openclaw/risk_kernel/policy.yaml` | `templates/risk_kernel/policy.yaml` | Risk / safety policy |
| `~/.openclaw/infra/signing_node.yaml` | `templates/infra/signing_node.yaml` | Signing isolation |

---

## §MA — config.yaml (Hermes)

```yaml
{cfg_yaml.rstrip()}
```

---

## §M — openclaw.json (OpenClaw)

```json
{json.dumps(oc, indent=2)}
```

---

## risk_kernel/policy.yaml

```yaml
{policy.rstrip()}
```

---

## infra/signing_node.yaml

```yaml
{signing.rstrip() if signing else "# missing"}
```

---

## Notes

- Paper default: `reconciliation.adapter: mock`, `capital.withdrawal_adapter: mock`.
- Live: `adapter: live` + fetcher; `withdrawal_adapter: trezor_signing`; in-process SigningNode + gate receipts.
- Mutating safety POSTs need `X-Titan-Auth` (`titan-safety auth sign`).
- Edit `templates/*` or regenerate bootstrap via `python3 scripts/build.py` — this file refreshes automatically.
"""
    out = PROJECT_ROOT / "configs_detail.md"
    out.write_text(doc, encoding="utf-8")
    # Drop legacy root aliases (canonical: configs_detail.md + refs/CONFIGS_detail.md)
    for alias in ("CONFIGS_detail.md", "§CONFIGS_detail.md"):
        alias_path = PROJECT_ROOT / alias
        if alias_path.exists() or alias_path.is_symlink():
            alias_path.unlink()
    print(f"  configs_detail.md ({out.stat().st_size} bytes)")


def main() -> int:
    print("Syncing workspace docs…")
    sync_bootstrap_to_workspace()
    write_iron_laws()
    write_hermes_md()
    ensure_memory_stub()
    sync_memory_strategies()
    regenerate_configs_detail()
    print(f"Done → {WORKSPACE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
