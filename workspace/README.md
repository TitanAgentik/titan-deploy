# TITAN Agent Workspace

OpenClaw + Hermes context files for TITAN. Regenerated on every `python3 scripts/build.py`.

## Docs

| System | Reference |
|--------|-----------|
| OpenClaw workspace | https://docs.openclaw.ai/concepts/agent-workspace |
| OpenClaw memory | https://docs.openclaw.ai/concepts/memory |
| Hermes SOUL.md | https://hermes-agent.nousresearch.com/docs/user-guide/features/personality |
| Hermes context files | https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files |
| Hermes config | https://hermes-agent.nousresearch.com/docs/user-guide/configuration |

## Required files (OpenClaw)

| File | Purpose |
|------|---------|
| `SOUL.md` | Persona, tone, iron-law boundaries |
| `AGENTS.md` | Operating instructions / multi-agent protocol |
| `USER.md` | Operator (Hyperion) profile |
| `IDENTITY.md` | Name, vibe, framework identity |
| `TOOLS.md` | Local tool conventions |
| `HEARTBEAT.md` | Periodic checklist (keep short) |
| `BOOT.md` | Gateway restart checklist |
| `BOOTSTRAP.md` | First-run ritual (delete after complete) |
| `MEMORY.md` | Curated long-term memory (main session only) |
| `memory/YYYY-MM-DD.md` | Daily logs |
| `iron-laws.md` | Immutable safety constitution |
| `skills/` | Workspace skills (deployed from `output/workspace/skills`) |

## Hermes

| File | Location after deploy |
|------|----------------------|
| `SOUL.md` | `~/.hermes/SOUL.md` (identity slot #1) |
| `.hermes.md` | Project context |
| `config.yaml` | `~/.hermes/config.yaml` |

## Sync rule

**Source of truth for content:** `output/TITAN.reconciled.md` → `scripts/extract_bootstrap.py` → `output/bootstrap/` → this folder + repo root copies.

**Source of truth for configs:** `templates/*` → `configs_detail.md` via `scripts/sync_workspace_docs.py`.

Do not hand-edit generated files expecting them to survive a rebuild — change extractors/templates instead.
