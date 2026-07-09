#!/usr/bin/env python3
"""Reconstruct missing TITAN §REF companion files for OpenClaw/Hermes deploy.

The original TITAN.md offloads large YAML/JSON/skill bodies to companion files
(§CONFIGS_detail.md, §SKILLS_full.md, …) that were never shipped with the
source dump. This script builds usable stand-ins under refs/ from:

  - live templates/ (configs, policy, infra)
  - extracted skills / memory / playbooks
  - deploy scripts
  - honest "missing original" notes for narrative-only companions

Run from build.py after reconcile + extract_skills.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT_DIR, PROJECT_ROOT, RECONCILED_PATH, write_text

TEMPLATES = PROJECT_ROOT / "templates"
REFS = PROJECT_ROOT / "refs"


def _header(name: str, purpose: str) -> str:
    return f"""# §{name}

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `{name}` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** {purpose}
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

"""


def write_configs() -> None:
    cfg = (TEMPLATES / "config.yaml").read_text(encoding="utf-8")
    oc = json.dumps(
        json.loads((TEMPLATES / "openclaw.json").read_text(encoding="utf-8")),
        indent=2,
    )
    policy = (TEMPLATES / "risk_kernel" / "policy.yaml").read_text(encoding="utf-8")
    signing = (TEMPLATES / "infra" / "signing_node.yaml").read_text(encoding="utf-8")
    body = _header(
        "CONFIGS_detail.md",
        "Full Hermes config.yaml + OpenClaw openclaw.json + risk policy bodies "
        "that TITAN stubs as `# → see §CONFIGS_detail.md`.",
    )
    body += f"""## Hermes `~/.hermes/config.yaml`

```yaml
{cfg.rstrip()}
```

## OpenClaw `~/.openclaw/openclaw.json`

```json
{oc}
```

## Risk kernel `~/.openclaw/risk_kernel/policy.yaml`

```yaml
{policy.rstrip()}
```

## Signing node `~/.openclaw/infra/signing_node.yaml`

```yaml
{signing.rstrip()}
```
"""
    write_text(REFS / "CONFIGS_detail.md", body)
    # Keep repo-root alias used by operators
    root_cfg = PROJECT_ROOT / "configs_detail.md"
    if root_cfg.exists():
        # Prefer sync_workspace_docs output; still write refs copy above
        pass
    print(f"  refs/CONFIGS_detail.md ({len(body)} chars)")


def write_skills_full() -> None:
    skills_dir = OUTPUT_DIR / "workspace" / "skills"
    lines = [
        _header(
            "SKILLS_full.md",
            "Index of extracted skill directories (full bodies live under "
            "output/workspace/skills/*/SKILL.md).",
        ),
        "## Active skills\n",
    ]
    if skills_dir.exists():
        for d in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("_")):
            skill = d / "SKILL.md"
            desc = ""
            if skill.exists():
                for line in skill.read_text(encoding="utf-8", errors="replace").splitlines()[:30]:
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip("\"'")
                        break
                    if line.startswith("# ") and "SKILL" not in line.upper():
                        desc = line[2:].strip()
                        break
            lines.append(f"- `{d.name}/` — {desc or 'see SKILL.md'}")
        archived = skills_dir / "_archived"
        if archived.exists():
            lines.append("\n## Archived (not loaded at runtime)\n")
            for d in sorted(p for p in archived.rglob("SKILL.md")):
                lines.append(f"- `{d.parent.relative_to(skills_dir)}/`")
    else:
        lines.append("_Run extract_skills.py first._\n")
    lines.append(
        "\n## OpenClaw / Hermes load order\n\n"
        "- OpenClaw workspace skills: `~/.openclaw/workspace/skills/` (highest precedence)\n"
        "- Hermes: symlink or copy to `~/.hermes/skills`\n"
        "- Quantum skills stay under `_archived/quantum/` — dormant for live capital\n"
    )
    body = "\n".join(lines)
    write_text(REFS / "SKILLS_full.md", body)
    print(f"  refs/SKILLS_full.md ({len(body)} chars)")


def write_deploy_scripts() -> None:
    deploy = (PROJECT_ROOT / "deploy.sh").read_text(encoding="utf-8")
    verify = (PROJECT_ROOT / "verify.sh").read_text(encoding="utf-8")
    body = _header(
        "DEPLOY_scripts.md",
        "Deploy / verify / build entrypoints that TITAN referenced as §DEPLOY_scripts.md.",
    )
    body += f"""## Commands

```bash
python3 scripts/build.py          # normalize → reconcile → extract → sync workspace
./deploy.sh                       # build + install to ~/.openclaw and ~/.hermes
./deploy.sh --start-services      # also enable/start titan-* systemd units
./deploy.sh --verify              # bootstrap limits + pytest + chaos harness
```

## deploy.sh

```bash
{deploy.rstrip()}
```

## verify.sh (excerpt — full file in repo)

```bash
{verify[:8000].rstrip()}
# … truncated; see verify.sh in repo root …
```
"""
    write_text(REFS / "DEPLOY_scripts.md", body)
    print(f"  refs/DEPLOY_scripts.md ({len(body)} chars)")


def write_memory_detail() -> None:
    body = _header(
        "MEMORY_detail.md",
        "Memory layout aligned with OpenClaw memory docs "
        "(MEMORY.md curated + memory/YYYY-MM-DD.md daily).",
    )
    body += """## Layout

| File | Role | Loaded when |
|------|------|-------------|
| `MEMORY.md` | Curated long-term facts | Main private session bootstrap |
| `memory/YYYY-MM-DD.md` | Daily working notes | Today + yesterday on `/new` |
| `memory/agents/` | Per-agent sidecars (TITAN) | On demand via memory tools |
| `memory/strategies/` | Pipeline notes | On demand |
| `memory/risk/` | Risk notes (constitutional) | On demand — agents must not rewrite |

## Rules (OpenClaw)

1. Prefer writing durable facts to `MEMORY.md`; details to daily files.
2. Do not put secrets, keys, or wallet seeds in memory files.
3. Action-sensitive notes must include when it is safe to act / expiry.
4. Hermes does not auto-load OpenClaw MEMORY.md as SOUL — keep SOUL identity-only.

## TITAN sidecars (extracted)

See `output/memory/` after build. Deploy copies them to `~/.openclaw/memory/`.
"""
    mem = OUTPUT_DIR / "memory"
    if mem.exists():
        body += "\n### Extracted memory files\n\n"
        for p in sorted(mem.rglob("*")):
            if p.is_file():
                body += f"- `{p.relative_to(mem)}`\n"
    write_text(REFS / "MEMORY_detail.md", body)
    print(f"  refs/MEMORY_detail.md ({len(body)} chars)")


def write_keys_detail() -> None:
    body = _header(
        "KEYS_detail.md",
        "Key custody / signing isolation — no secrets. Points at infra specs.",
    )
    body += """## Principles

1. Never store session keys or seeds in agent memory / workspace markdown.
2. Signing only via isolated signing node `:19010` with fresh `X-Titan-Gate-Receipt`.
3. Mac Mini vault = metadata + Trezor ceremonies; not the live signer.
4. Live capital: `withdrawal_adapter: trezor_signing` (not mock).
5. Control-plane HMAC secret: `~/.openclaw/safety/control_plane.secret` mode 0600.

## Specs

- `templates/infra/signing_node.yaml`
- `templates/infra/power_requirements.yaml` (UPS on signing path)
- `templates/openclaw.json` → `signingNode`

## Operator checklist

- [ ] Trezor / hardware wallet provisioned
- [ ] Signing node systemd unit healthy (`curl :19010/health`)
- [ ] Gate receipt required (`requireGateReceipt: true`)
- [ ] Exchange API keys: trade-only, withdrawal disabled where possible
"""
    write_text(REFS / "KEYS_detail.md", body)
    print(f"  refs/KEYS_detail.md ({len(body)} chars)")


def write_agents_schemas() -> None:
    """Full JSON schema fences externalized from bootstrap AGENTS.md for headroom."""
    body = _header(
        "AGENTS_schemas.md",
        "Structured-output JSON schemas (debate, trader decision, risk debate, "
        "decision log) externalized from AGENTS.md to stay under the 20,000-byte "
        "bootstrap limit.",
    )
    source = RECONCILED_PATH if RECONCILED_PATH.exists() else None
    fences: list[str] = []
    if source is not None:
        text = source.read_text(encoding="utf-8")
        agents_block = text
        marker = "## Inter-Agent Protocol & Consensus Engine"
        if marker in text:
            start = text.index(marker)
            agents_block = text[start : start + 30000]
        fences = re.findall(
            r"(?ms)^[ \t]*```json[ \t]*\n.*?\n[ \t]*```[ \t]*$", agents_block
        )
    if fences:
        body += "\n\n".join(f.strip() for f in fences) + "\n"
    else:
        body += (
            "Schemas not found in reconciled source — see "
            "`output/TITAN.reconciled.md` §Inter-Agent Protocol.\n"
        )
    write_text(REFS / "AGENTS_schemas.md", body)
    print("  refs/AGENTS_schemas.md")


def write_narrative_stub(name: str, purpose: str, see_also: str) -> None:
    body = _header(name, purpose)
    body += f"""## Status

The original companion body was **not included** in the TITAN.md dump shipped to
this machine. Narrative / research content remains in `output/TITAN.reconciled.md`
under related sections.

## See also

{see_also}

## Operator note

Do not block OpenClaw/Hermes startup on this file. Bootstrap context is the
`workspace/*.md` set; this companion is reference-only.
"""
    write_text(REFS / name, body)
    print(f"  refs/{name} (stub)")


def write_au_audit() -> None:
    body = _header(
        "AU_audit.md",
        "Audit / decision-log pointers for TITAN safety services.",
    )
    body += """## Append-only logs (runtime)

| Log | Path |
|-----|------|
| Promotion audit | `~/.openclaw/safety/promotion_audit.jsonl` |
| Capital audit | `~/.openclaw/capital/capital_audit.jsonl` |
| Signing audit | `~/.openclaw/safety/signing_audit.jsonl` |
| Defund ledger | `~/.openclaw/safety/defund_ledger.jsonl` |
| Decision hash chain | `titan_safety.audit_chain` |

## Verify

```bash
titan-safety promotion verify-audit
titan-safety capital audit  # if exposed
```

Constitutional blocks prevent agents from rewriting `risk_kernel/` or `SOUL.md`.
"""
    write_text(REFS / "AU_audit.md", body)
    print(f"  refs/AU_audit.md ({len(body)} chars)")


def write_perf_detail() -> None:
    body = _header(
        "PERF_detail.md",
        "Performance / BIOS / GPU schedule pointers (hardware ops).",
    )
    gpu = ""
    gp = TEMPLATES / "infra" / "gpu_schedule.yaml"
    if gp.exists():
        gpu = gp.read_text(encoding="utf-8")
    bios = ""
    bp = TEMPLATES / "infra" / "titanhome_bios_checklist.md"
    if bp.exists():
        bios = bp.read_text(encoding="utf-8")[:6000]
    body += f"""## GPU schedule

```yaml
{gpu.rstrip() if gpu else "# missing gpu_schedule.yaml"}
```

## BIOS checklist (excerpt)

```markdown
{bios.rstrip() if bios else "# missing"}
```

Full narrative PERF sections remain in `TITAN.reconciled.md` (§PERF).
"""
    write_text(REFS / "PERF_detail.md", body)
    print(f"  refs/PERF_detail.md ({len(body)} chars)")


def write_comm_detail() -> None:
    body = _header(
        "COMM_detail.md",
        "NATS / Telegram / HERALD communication surface.",
    )
    body += """## Channels

| Channel | Config | Notes |
|---------|--------|-------|
| Telegram | `openclaw.json` gateway.telegram + Hermes channels.telegram | Informational; promotion via YES gate |
| HERALD | `workspace/skills/herald_notify` | Trade / PnL / digest templates |
| NATS | `NATS_URL` in `.env` | Internal bus — not required for paper |

## Templates

`templates/telegram/templates/*.md` → `~/.openclaw/workspace/telegram/`

## Heartbeat

OpenClaw `HEARTBEAT.md` must stay short (token budget). Dead-man's switch is
separate (`titan-dead-mans-switch.service` on `:19005`).
"""
    write_text(REFS / "COMM_detail.md", body)
    print(f"  refs/COMM_detail.md ({len(body)} chars)")


def write_cockpit_detail() -> None:
    body = _header(
        "COCKPIT_detail.md",
        "Operator capital deposit/withdraw CLI — not profit attribution.",
    )
    body += """## Capital commands (ledger, not PnL)

```bash
titan-safety capital deposit --amount 2500 --asset USDC --operator YOU
titan-safety capital withdraw --amount 100 --asset USDC --confirm-yes --operator YOU
titan-safety capital balance
```

Telegram: `/deposit 2500 USDC` (parsed by `telegram_capital`).

Deposits credit `equity_usd` / `available_usd`. Trading profit is tracked via
TCA / weekly_profit — **do not confuse with deposits**.

Withdrawals require `--confirm-yes` (or pending `--confirm REQUEST_ID`).
Live withdrawals route through signing node when `withdrawal_adapter: trezor_signing`.
"""
    write_text(REFS / "COCKPIT_detail.md", body)
    print(f"  refs/COCKPIT_detail.md ({len(body)} chars)")


def write_models_detail() -> None:
    body = _header(
        "MODELS_detail.md",
        "Reconciled model tier architecture (critical path unchanged).",
    )
    body += """## Tiers (reconciled)

| Tier | Port | Model | Role |
|------|------|-------|------|
| 1 | `:30000` | Qwen3-30B-A3B FP8 | Signals, risk, execution (critical) |
| 2 | `:30001` | Qwen3-Coder-Next-80B | Orchestration, strategy, code |
| 3a | `:30005` | DeepSeek V4 Pro | Primary R&D / long-horizon |
| 3b | `:30003` | GLM-5.2 | Secondary R&D |
| Embed | `:30004` | Qwen3-Embedding | Memory search / embedder |

**Never** put GLM/DeepSeek on TRENCH-OPS / GUARDIAN / EXECUTOR live path.

Heterogeneous BFT: GUARDIAN→Qwen30B, ARCHON→Qwen-Coder, CORTEX→DeepSeek.
"""
    write_text(REFS / "MODELS_detail.md", body)
    print(f"  refs/MODELS_detail.md ({len(body)} chars)")


def main() -> int:
    REFS.mkdir(parents=True, exist_ok=True)
    print("Reconstructing §REF companions → refs/")
    write_configs()
    write_skills_full()
    write_deploy_scripts()
    write_memory_detail()
    write_keys_detail()
    write_au_audit()
    write_perf_detail()
    write_comm_detail()
    write_cockpit_detail()
    write_models_detail()
    write_agents_schemas()

    # Narrative-only companions — honest stubs with pointers
    write_narrative_stub(
        "GHOST_detail.md",
        "Ghost / stealth / adversarial narrative sections from TITAN.",
        "- Search `TITAN.reconciled.md` for `§GHOST` / stealth / adversarial harness\n"
        "- Runtime: `tests/adversarial/adversarial_harness.py`",
    )
    write_narrative_stub(
        "RESEARCH_detail.md",
        "Research / GRIS / evolution narrative (shadow-only for live capital).",
        "- `TITAN.reconciled.md` §GRIS / R&D sections\n"
        "- Evolution freeze: `titan-safety evolution freeze`",
    )
    write_narrative_stub(
        "MAINT_detail.md",
        "Maintenance / update / ZFS rollback narrative.",
        "- `templates/infra/titanhome_ubuntu_install.md`\n"
        "- Health: `curl :19003/health`",
    )
    write_narrative_stub(
        "MEV_detail.md",
        "MEV pipeline narrative (P29/P30 etc.).",
        "- Pipeline notes in `output/memory/strategies/`\n"
        "- TCA scorecards on `:19007`",
    )
    write_narrative_stub(
        "REAPER_detail.md",
        "Reaper / liquidation narrative.",
        "- See reconciled liquidation pipelines; risk kernel flatten path",
    )
    write_narrative_stub(
        "AEGIS_detail.md",
        "Aegis / defense narrative.",
        "- Kill switch + portfolio risk + dead-man's switch services",
    )
    write_narrative_stub(
        "FORTRESS_detail.md",
        "Fortress / hardening narrative.",
        "- `PRODUCTION_READINESS.md` + safety package under `templates/safety/`",
    )
    write_narrative_stub(
        "EVERGREEN_detail.md",
        "Evergreen / long-horizon research narrative.",
        "- Tier 3 R&D only; never critical path",
    )
    write_narrative_stub(
        "CONDUIT_detail.md",
        "Conduit / bridging narrative.",
        "- Edge mesh Phase 1: EDGE-FRA only (`openclaw.json` edgeMesh)",
    )
    write_narrative_stub(
        "XB_detail.md",
        "Cross-border / XB narrative.",
        "- See reconciled XB sections if present; else N/A for Phase 1",
    )

    # Manifest
    files = sorted(p.name for p in REFS.glob("*.md"))
    manifest = "# refs/ manifest\n\n" + "\n".join(f"- `{f}`" for f in files) + "\n"
    write_text(REFS / "README.md", manifest)
    print(f"Done — {len(files)} companions in {REFS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
