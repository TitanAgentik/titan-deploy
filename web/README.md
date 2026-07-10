# Titan Agentik

Crypto-native operator Web UI for the Titan Agentik / OpenClaw / Hermes control plane.

**Design:** [Signal theme](DESIGN.md) — original Titan palette (cool slate, cyan accent, Sora display). Night dark mode in Settings.

Inspired by [ClawBuddy](https://clawbuddy.help) and the [OpenClaw Control UI](https://docs.openclaw.ai/web/control-ui), adapted to Titan Agentik’s bounded-autonomy trading stack.

## Features

- **Command palette** — `Ctrl+K` / `⌘K` to jump anywhere or run operator actions
- **Activity rail** — bell icon in topbar for recent agent + operator events
- **Status strip** — light translucent KPI band on Dashboard
- **DEX-only** — no CEX venues; Uniswap / Curve / Hyperliquid / Solana / L2 DEX
- **Interactive UX** — clickable metrics, modals, drawers, confirmation flows, toasts
- **Data providers** — mock fixtures by default; live `/api/*` stubs soft-fail until backends exist
- **Operator sections** — capital, risk, pipelines, promotions, memecoin trench, edge mesh, flash loans, in-process signing, Agent Manager (20 classical agents), and more

**Production go-live (build, reverse proxy, TLS, systemd, HMAC):** see [`../WEB_UI_LIVE_PRODUCTION_GUIDE.md`](../WEB_UI_LIVE_PRODUCTION_GUIDE.md).  
**Data providers deep-dive (mock vs live, env, stubs):** see [`../WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md`](../WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md).

## Quick start

```bash
cd web
npm install
npm run dev
```

Open **http://127.0.0.1:5173** (or your machine’s LAN IP — Vite binds `0.0.0.0`).

Optional env (`.env` / `.env.local`):

```bash
# mock (default) | live
VITE_DATA_MODE=mock

# Optional absolute API origin; empty = same-origin Vite proxy
# VITE_API_BASE=http://127.0.0.1:5173
```

Session override: **Settings → Data providers** (mock / live). Does not persist to disk.

## Access from anywhere

Do **not** expose this UI raw on the public internet without auth.

Recommended:

1. **Tailscale Serve** (same pattern as OpenClaw dashboard)
2. **SSH tunnel**: `ssh -L 5173:127.0.0.1:5173 user@titan-host`
3. **Cloudflare Tunnel** / reverse proxy with SSO in front

Vite proxies safety services:

| UI path | Upstream |
|---------|----------|
| `/api/risk` | `:19001` |
| `/api/recon` | `:19002` |
| `/api/status` | `:19003` |
| `/api/portfolio` | `:19004` |
| `/api/dms` | `:19005` |
| `/api/allocator` | `:19006` |
| `/api/tca` | `:19007` |
| `/api/security` | `:19008` Security Ops |
| `/api/signing` | Status / control plane (in-process signing halt via titan-safety) |
| `/api/sign` | Optional legacy HTTP signing_node `:19010` (not required) |

## Data providers

Cockpit pages should not hard-wire fetches forever. High-traffic surfaces use `web/src/lib/providers/`:

```
providers/
  types.ts          # shared DTOs (fleet, health, signing, …)
  mode.ts           # VITE_DATA_MODE + session override
  http.ts           # soft-fail fetchJson
  create.ts         # createProviders({ mode })
  mock/index.ts     # fixtures from data.ts
  live/index.ts     # /api/* stubs — soft-fail to mock
  context.tsx       # DataProvider + useFleet / useHealth / …
  index.ts          # public exports
```

### How to add a data provider

1. Add or extend a DTO in `types.ts`.
2. Implement `getX()` on **mock** (return fixtures from `data.ts`) and **live** (call `/api/...`, map JSON, soft-fail with `error` + fixture data).
3. Export a hook from `context.tsx` (`useX`) that calls `providers.getX()`.
4. Prefer the hook in the page; keep `data.ts` imports only for charts / static labels if needed.
5. Show `advisoryLabel(result)` so operators never confuse fixtures with live capital.

Migrated today: Dashboard, Health, Agent Manager, Manual Control, Signing, Security, Pipelines, Settings (mode toggle). Other pages may still import `data.ts` directly — that file remains the fixture source of truth.

**System truth (do not regress):** 20 classical agents (no QCC/QSA/QRP); signing in-process (no mandatory `:19010`); QI Optimizer = classical SA advisory only.

## Sidebar sections

**Control:** Dashboard · Command Center · Manual Control · Capital & Wallets · Wallet Tracker · PnL · Risk & CBs · Dead Man's Switch · Security Ops · Ops Center · Health & Verify · Power & UPS · Forge

**Trading:** Pipelines · QI Optimizer · TCA & Allocator · Promotions · Memecoin Trench · Edge Mesh · Latency · Flash Loans · Signing

**Intelligence:** Automations · Crypto News · Crypto Twitter · Goals Lab · Identity · Model Tiers · AI Log · Decision Log · Questions

**Build:** Skill Factory · Agent Manager · Agent Teams · Workspace

**Governance:** Reports · Settings

### Security Ops

Four-pillar defensive/offensive posture UI:

| Pillar | Role |
|--------|------|
| **Impenetrable** | Risk kernel, in-process signing isolation, netns, PCR, DMS, closed-model ban |
| **Evasion** | MEV-shielded intents, edge RTT, Nostr dispatch, fingerprint rotation |
| **Stalking** | PREDATOR/SENTINEL threat hunt — mempool clusters, probes, copy-traders |
| **Predatory** | Honeypots, Red Team gauntlet, counter-copy poison, kill-chain response |

Advisory / HMAC-gated until live safety units are up.

### Capital & Wallets

Dedicated deposit / withdraw / wallet inventory / **Trezor Safe 7 weekly profit sweeps**.
Deposits credit the operator ledger (≠ trading PnL). Sweeps unlock at $15K equity (20% of
weekly profit every Sunday UTC; 100% reinvest below threshold).

Fixture data is used until safety systemd units are up; Command Center actions are local session demos (HMAC wiring lives in Settings).
