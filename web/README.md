# TITAN Cockpit

Institutional-grade operator Web UI for the TITAN / OpenClaw / Hermes control plane.

**Design:** [Signal theme](DESIGN.md) — original TITAN palette (cool slate, cyan accent, Sora display). Night dark mode in Settings.

Inspired by [ClawBuddy](https://clawbuddy.help) and the [OpenClaw Control UI](https://docs.openclaw.ai/web/control-ui), adapted to TITAN’s bounded-autonomy trading stack.

## Features

- **Command palette** — `Ctrl+K` / `⌘K` to jump anywhere or run operator actions
- **Activity rail** — bell icon in topbar for recent agent + operator events
- **Status strip** — navy mesh-grid KPI band on Dashboard
- **Interactive UX** — clickable metrics, modals, drawers, confirmation flows, toasts
- **21 sections** — capital, risk, pipelines, promotions, edge mesh, signing, model tiers, and more

## Quick start

```bash
cd web
npm install
npm run dev
```

Open **http://127.0.0.1:5173** (or your machine’s LAN IP — Vite binds `0.0.0.0`).

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
| `/api/sign` | `:19010` |

## Sidebar sections

**Control:** Dashboard · Command Center · Capital & Wallets · Risk & CBs · **Security Ops** · Ops Center · Forge

**Trading:** Pipelines · Promotions · Edge Mesh · Signing Node

**Intelligence:** Automations · Goals Lab · Identity · Model Tiers · AI Log · Questions

**Build:** Skill Factory · Agent Teams · Workspace

**Governance:** Reports · Settings

### Security Ops

Four-pillar defensive/offensive posture UI:

| Pillar | Role |
|--------|------|
| **Impenetrable** | Risk kernel, signing isolation, netns, PCR, DMS, closed-model ban |
| **Evasion** | MEV-shielded intents, edge RTT, Nostr dispatch, fingerprint rotation |
| **Stalking** | PREDATOR/SENTINEL threat hunt — mempool clusters, probes, copy-traders |
| **Predatory** | Honeypots, Red Team gauntlet, counter-copy poison, kill-chain response |

Demo actions only until HMAC-wired to live safety units.

### Capital & Wallets

Dedicated deposit / withdraw / wallet inventory / **Trezor Safe 7 weekly profit sweeps**.
Deposits credit the operator ledger (≠ trading PnL). Sweeps unlock at $35K equity (20% of
weekly profit every Sunday UTC; 100% reinvest below threshold).

Demo data is used until safety systemd units are up; Command Center actions are local session demos (HMAC wiring lives in Settings).
