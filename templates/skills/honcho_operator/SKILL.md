---
name: honcho_operator
description: Honcho dialectic user modeling for Hyperion operator context — peer cards, session summary, dual-layer injection
metadata:
  openclaw:
    status: active
    agents: [HYPERION, HERALD]
    tier: T2
  skill_tuple:
    intent: honcho_operator
    method: memory_provider
    difficulty: medium
---

# Honcho Operator Modeling

Hermes **Honcho** memory provider for dialectic user modeling of operator **Hyperion**.
Official docs: [Honcho Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho).

## When to use

| Agent | Role | Honcho peer |
|-------|------|-------------|
| **HERALD** | Telegram operator surface | `herald-telegram` AI peer, user peer `hyperion` |
| **HYPERION** | Operator interface / NATS reporting | `hyperion-assistant` AI peer, user peer `hyperion` |

Honcho is **not** on the trade critical path. It models operator preferences, communication style, and approval patterns — it does not authorize trades (risk kernel `:19001` remains authoritative).

## Dual-layer context (auto-injected in `hybrid` recall mode)

1. **Base context** — session summary, user representation, user peer card, AI self-representation, AI identity card. Refreshed on `contextCadence`.
2. **Dialectic supplement** — LLM-synthesized reasoning about operator state and needs. Refreshed on `dialecticCadence`.

Both layers are truncated to `contextTokens` (default 1200 in TITAN template).

## Observation modes

| Mode | Use in Titan |
|------|----------------|
| `directional` (default) | Full mutual observation — HERALD/HYPERION cross-model operator from Telegram + session replies |
| `unified` | Shared pool — AI observes user messages only; use if AI peer should not re-model from its own replies |

Override per-peer in `~/.hermes/honcho.json` `observation` block. See `HONCHO_SETUP.md`.

## Hermes tools (when `memory.provider: honcho`)

| Tool | Purpose |
|------|---------|
| `honcho_profile` | Read/update peer card (list of facts about Hyperion) |
| `honcho_search` | Semantic search over conclusions — raw excerpts |
| `honcho_context` | Full session context — summary, representation, card, recent messages |
| `honcho_reasoning` | Synthesized answer from Honcho dialectic LLM |
| `honcho_conclude` | Create/delete conclusions (PII cleanup only) |

## Profile setup

```bash
hermes memory setup honcho          # wizard — or use deployed honcho.json
hermes profile create herald --clone --aiPeer herald-telegram --workspace ~/.openclaw/workspace
hermes profile create hyperion --clone --aiPeer hyperion-assistant --workspace ~/.openclaw/workspace
hermes honcho status                # after provider active
hermes honcho sync                  # push honcho.json to all profiles
```

## Operator facts (seed peer card)

HERALD may update via `honcho_profile` when Hyperion states durable preferences:

- JSON-first communication; concise, data-first
- Telegram primary channel; approval gates for promotion / evolution / >1% equity
- TIMEOUT on promotion = HOLD/de-risk — never auto-promote
- Selective activation — catalog ≠ required enable set
- UTC timezone; institutional hourly reports at :00

Static baseline also lives in `USER.md` — Honcho accumulates **derived** insights beyond explicit statements.

## Constraints

- No closed/cloud models on dialectic path — local Hermes inference only
- Sub-agents (minimal prompt mode): session memory only; no Honcho peer card writes
- Trade authorization unchanged — Honcho does not replace BFT votes or kernel DENY
