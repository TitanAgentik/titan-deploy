# §MEMORY_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `MEMORY_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Memory layout aligned with OpenClaw memory docs (MEMORY.md curated + memory/YYYY-MM-DD.md daily).
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Layout

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

### Extracted memory files

- `agents/routing-table.md`
- `hardware/edge-mesh.md`
- `hardware/macmini-vault.md`
- `hardware/titanspark.md`
- `hardware/workstation.md`
- `rd_automation/indicators.md`
- `research/hydra-models.md`
- `research/quantum-inspired.md`
- `research/skill-evolution.md`
- `risk/circuit-breakers.md`
- `security/README.md`
- `security/posture.md`
- `strategies/active-pipelines.md`
- `strategies/endgame.md`
- `strategies/memecoin-trench.md`
- `strategies/selective-activation.md`
- `strategies/signal-catalog.md`
