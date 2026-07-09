# §COMM_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `COMM_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** NATS / Telegram / HERALD communication surface.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Channels

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
