# TITAN Cockpit

Institutional-grade operator Web UI for the TITAN / OpenClaw / Hermes control plane.

Inspired by [ClawBuddy](https://clawbuddy.help) (dashboard + human-in-the-loop Q&A) and the [OpenClaw Control UI](https://docs.openclaw.ai/web/control-ui) (gateway admin surface), adapted to TITAN’s bounded-autonomy trading stack.

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
| `/api/sign` | `:19010` |

## Sidebar sections

Dashboard · Command Center · Forge · Ops Center · Automations · Goals Lab · Identity · AI Log · Questions · Skill Factory · Agent Teams · Workspace · Reports · Settings

Demo data is used until safety systemd units are up; Command Center actions are local session demos (HMAC wiring lives in Settings).
