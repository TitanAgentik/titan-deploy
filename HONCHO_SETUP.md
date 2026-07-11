# HONCHO_SETUP.md — Honcho Dialectic User Modeling for TITAN

Beginner guide for integrating [Honcho](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho) (Hermes dialectic memory) into the Titan stack. Honcho models **operator Hyperion** — preferences, communication style, approval patterns — for **HERALD** (Telegram) and **HYPERION** (operator interface). It does **not** authorize trades; the risk kernel (`:19001`) remains authoritative.

---

## What Honcho adds

| Capability | Built-in SQLite memory | Honcho |
|------------|------------------------|--------|
| Cross-session persistence | File-based `MEMORY.md` / `USER.md` | Server-side API |
| User profile | Manual agent curation | Automatic dialectic reasoning |
| Session summary | — | Session-scoped context injection |
| Multi-agent isolation | — | Per-peer profiles (HERALD vs HYPERION) |
| Observation modes | — | `directional` or `unified` |
| Derived insights | — | Conclusions from conversation patterns |

### Dual-layer context (every turn in `hybrid` mode)

1. **Base context** — session summary, user representation, peer cards, AI identity. Refreshed on `contextCadence`.
2. **Dialectic supplement** — LLM reasoning about what matters right now. Refreshed on `dialecticCadence`.

---

## Quick start (5 steps)

### 1. Deploy templates

```bash
cd /path/to/titan-deploy
./deploy.sh
```

This installs:

- `~/.hermes/config.yaml` with `memory.provider: honcho`
- `~/.hermes/honcho.json` — Titan operator peer defaults
- `openclaw.json` `honcho` block — HERALD/HYPERION peer mapping

### 2. Set environment variables

Copy and edit secrets (never commit):

```bash
cp templates/infra/live.env.example ~/.openclaw/.env
# Also create Hermes env (Honcho reads ~/.hermes/.env)
touch ~/.hermes/.env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `HONCHO_API_KEY` | Cloud or auth'd self-host | API key from [honcho.dev](https://honcho.dev) or JWT for self-hosted |
| `HONCHO_BASE_URL` | Self-hosted only | e.g. `http://127.0.0.1:8000` — leave empty for Honcho cloud |
| `HONCHO_PEER_NAME` | Optional | Default `hyperion` — operator user peer name |

For self-hosted Honcho with `AUTH_USE_AUTH=false`, leave `HONCHO_API_KEY` blank.

Mirror keys into both env files (gateway loads both):

```bash
grep HONCHO ~/.openclaw/.env >> ~/.hermes/.env
```

### 3. Activate Honcho in Hermes

```bash
hermes memory setup honcho
# Or non-interactive: templates already set memory.provider: honcho
hermes honcho status
```

### 4. Create operator-facing profiles

```bash
hermes profile create herald --clone --aiPeer herald-telegram --workspace ~/.openclaw/workspace
hermes profile create hyperion --clone --aiPeer hyperion-assistant --workspace ~/.openclaw/workspace
hermes honcho sync
```

### 5. Verify gateway

```bash
sudo systemctl restart hermes-gateway
hermes honcho status
hermes honcho peers
```

Send a Telegram message to HERALD — Honcho persists messages and builds operator context asynchronously.

---

## Titan peer layout

```
                    ┌─────────────────┐
                    │  hyperion       │  ← user peer (operator Hyperion)
                    │  (peer card)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐ ┌───▼───────────────┐
     │ herald-telegram │ │ hyperion-assistant │
     │ (HERALD)        │ │ (HYPERION)         │
     └─────────────────┘ └────────────────────┘
```

- **Gateway identity:** `pinUserPeer: true` — all Telegram users map to `hyperion` (single-operator setup).
- **Session strategy:** `per-repo` — one Honcho session per git repo (`titan-deploy`).

---

## Observation mode: directional vs unified

| Mode | User peer | AI peer | Titan use |
|------|-----------|---------|-----------|
| **`directional`** (default) | observe self + others | observe self + others | HERALD learns from both your messages and its replies — best for rich operator modeling |
| **`unified`** | observe self only | observe user only | Shared pool — AI does not re-model user from its own replies |

Change in `~/.hermes/honcho.json`:

```json
"observationMode": "directional"
```

Or per-peer override:

```json
"observation": {
  "user": { "observeMe": true, "observeOthers": true },
  "ai":   { "observeMe": true, "observeOthers": false }
}
```

---

## Config reference (Titan defaults)

File: `templates/honcho.json` → `~/.hermes/honcho.json`

| Key | Default | Notes |
|-----|---------|-------|
| `recallMode` | `hybrid` | Auto-inject + tools available |
| `observationMode` | `directional` | Full mutual observation |
| `sessionStrategy` | `per-repo` | One session per git repo |
| `contextTokens` | `1200` | Cap injected context per turn |
| `contextCadence` | `1` | Refresh base layer every turn |
| `dialecticCadence` | `3` | Dialectic LLM every 3 turns |
| `dialecticDepth` | `2` | Multi-pass audit/reconcile |
| `pinUserPeer` | `true` | Single operator via Telegram gateway |

Cost knobs are orthogonal — e.g. frequent base refresh (`contextCadence: 1`) with infrequent dialectic (`dialecticCadence: 5`).

---

## Honcho CLI (after `memory.provider: honcho`)

```bash
hermes honcho status          # connection + config
hermes honcho mode            # hybrid / context / tools
hermes honcho strategy        # per-session / per-directory / per-repo / global
hermes honcho peer            # peer names + reasoning level
hermes honcho tokens          # context token budget
hermes honcho identity        # seed AI peer identity
hermes honcho sync            # push honcho.json to all profiles
hermes honcho sessions        # list session mappings
```

---

## How HERALD and HYPERION use Honcho

### HERALD (Telegram — production operator surface)

- Receives operator commands and alerts via Telegram gateway.
- Honcho injects operator context into HERALD's system prompt (preferences from `USER.md` + derived conclusions).
- `honcho_profile` can update peer card when Hyperion states durable preferences (e.g. "always JSON-first for trade alerts").
- **Does not** bypass promotion gates or risk kernel — Honcho is advisory context only.

### HYPERION (operator interface — off-critical path)

- NATS streaming / reporting interface.
- Separate AI peer (`hyperion-assistant`) — isolated from HERALD's Telegram observations.
- Shares user peer `hyperion` so operator facts accumulate across channels.

---

## Self-hosted Honcho

1. Run Honcho server (Docker compose or native).
2. Set `HONCHO_BASE_URL` in `~/.openclaw/.env` and `~/.hermes/.env`.
3. If `AUTH_USE_AUTH=true`, paste JWT signed with server `AUTH_JWT_SECRET` as `HONCHO_API_KEY`.
4. Run `hermes honcho setup` — wizard stores token under `hosts.default.apiKey` in `honcho.json`.

Dialectic LLM calls use **local Hermes inference** (Tier 2 / utility) — no closed/cloud models on the live path.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `hermes honcho` command missing | Set `memory.provider: honcho` in `~/.hermes/config.yaml`, restart shell |
| Empty peer card | Send a few Telegram messages; check `hermes honcho status` connection |
| Wrong operator identity | Verify `pinUserPeer: true` and `peerName: hyperion` in `honcho.json` |
| Gateway user not mapped | Add `userPeerAliases: {"<telegram_id>": "hyperion"}` if not using pin |
| Dialectic too slow/costly | Raise `dialecticCadence` (e.g. 5) or lower `dialecticDepth` to 1 |

---

## Related files

| Path | Role |
|------|------|
| `templates/honcho.json` | Honcho config template |
| `templates/config.yaml` | `memory.provider: honcho` |
| `templates/openclaw.json` | `honcho` agent peer block |
| `templates/skills/honcho_operator/SKILL.md` | Agent skill reference |
| `AGENTS.md` | Multi-peer + dialectic protocol |
| `SYSTEM.md` §11 | Telegram + Honcho operator modeling |
| `TOOLS.md` | Honcho tool matrix |

Official docs: [Honcho Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/honcho)
