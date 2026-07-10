# Titan Agentik Web UI — Live Production Setup Guide

> **What this document is:** A beginner-friendly but complete walkthrough for putting the **Titan Agentik cockpit** (`web/`) into a **production-style** deployment on TITANHOME (or equivalent operator host).  
> **What this document is not:** A switch that enables live trading. Shipping the UI does **not** authorize capital. Live capital still requires paper → shadow → Phase 5 human YES, UPS, healthy safety units, and the gates in `PRODUCTION_READINESS.md`.

**Related docs (do not skip):**

| Doc | Role |
|-----|------|
| [`web/README.md`](./web/README.md) | Quick start + provider overview |
| [`WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md`](./WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md) | Beginner deep-dive: mock vs live providers, env, proxies, stubs |
| [`SYSTEM.md`](./SYSTEM.md) | Full system manual (cockpit map §11, ports §10) |
| [`PRODUCTION_READINESS.md`](./PRODUCTION_READINESS.md) | Honest go-live gates for **capital** |
| [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) | **Real-capital** paper → shadow → Phase 5 YES → live (not this UI guide) |
| [`BOOT.md`](./BOOT.md) | Short gateway-restart checklist |
| [`BOOTSTRAP.md`](./BOOTSTRAP.md) | First-run ritual |
| [`TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md`](./TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md) | End-to-end stack setup |
| [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) / [`DEPLOYMENT_GUIDE_BEGINNER.md`](./DEPLOYMENT_GUIDE_BEGINNER.md) | Deploy narratives |

---

## Table of contents

1. [What you're building (cockpit vs trading brain)](#1-what-youre-building-cockpit-vs-trading-brain)
2. [Prerequisites](#2-prerequisites)
3. [Mental model: mock → live `/api/*` → titan-safety](#3-mental-model-mock--live-api--titan-safety)
4. [Install Node.js](#4-install-nodejs)
5. [Install web dependencies](#5-install-web-dependencies)
6. [Local verify with mock data](#6-local-verify-with-mock-data)
7. [Configure env for production intent](#7-configure-env-for-production-intent)
8. [Build production assets](#8-build-production-assets)
9. [Serve the production build](#9-serve-the-production-build)
10. [Reverse proxy map (`/api/*` → ports)](#10-reverse-proxy-map-api--ports)
11. [Wire live providers (real stubs + TODOs)](#11-wire-live-providers-real-stubs--todos)
12. [Auth & exposure (never raw public internet)](#12-auth--exposure-never-raw-public-internet)
13. [TLS / certificates](#13-tls--certificates)
14. [systemd unit example](#14-systemd-unit-example)
15. [Health checks & `verify.sh`](#15-health-checks--verifysh)
16. [Go-live checklist (paper → shadow → capital)](#16-go-live-checklist-paper--shadow--capital)
17. [Troubleshooting](#17-troubleshooting)
18. [Security checklist](#18-security-checklist)
19. [Appendix A — Sidebar / route map](#appendix-a--sidebar--route-map)
20. [Appendix B — Port table](#appendix-b--port-table)
21. [Appendix C — Glossary](#appendix-c--glossary)

---

## 1. What you're building (cockpit vs trading brain)

### Cockpit (this guide)

The **Titan Agentik web UI** lives in `web/`. It is a **React** single-page app built with **Vite**. Operators use it to:

- See health of safety services
- Inspect fleet posture (20 classical agents)
- Drive Manual Control / Security Ops / Promotions surfaces
- Toggle mock vs live **data providers**
- Store an operator **HMAC** token in the browser session for mutating calls

Think of it as a **flight deck / instrument panel**. It displays and requests; it does **not** replace the risk kernel.

### Trading brain (not this guide alone)

The actual trading stack is:

| Layer | What it is | Authoritative? |
|-------|------------|----------------|
| OpenClaw / Hermes agents (20 classical) | Propose signals, votes, orchestration | Advisory |
| BFT 2-of-3 (AUGUR + PREDATOR + ATLAS) | Trade authorization votes | Advisory |
| Risk kernel `:19001` + ExecutionGate | Pre-trade DENY / ALLOW + receipt | **Authoritative** |
| Portfolio risk `:19004` | VaR / correlation caps when wired | **Authoritative** |
| In-process `titan_safety.SigningNode` | Signs only after fresh gate receipt | **Authoritative for signing** |
| Edge mesh (5 PoPs) | Broadcast / low-RTT execution workers | Execution path |

> **Critical mental split:** A green cockpit does **not** mean live capital is safe. Fixture/advisory pages can look “healthy” while backends are down (soft-fail). Always read the advisory labels and curl the safety ports yourself.

### Classical-only fleet (do not regress)

- **20 agents** total. Quantum agents **QCC / QSA / QRP are removed**.
- QI Optimizer page = classical simulated annealing, **advisory only** (`live_path=false`).
- Signing default = **in-process** via `titan-safety gate sign`. Legacy HTTP `:19010` is **optional / not required**.

---

## 2. Prerequisites

### Operator skills

You should be comfortable with:

1. Opening a terminal on Linux (Ubuntu 24.04 LTS is the documented TITANHOME OS).
2. Copy-pasting commands and reading error text.
3. Editing a text file (`.env.production`, nginx/Caddy config, systemd unit).

You do **not** need to be a frontend engineer. You **do** need to understand that the UI talks to local HTTP services.

### Software

| Requirement | Why |
|-------------|-----|
| **Node.js 20+** (LTS recommended) + **npm** | Builds and runs the Vite app |
| **Git** clone of this repo | Source of `web/` |
| **titan-safety** stack installed (for live mode) | Serves `:19001`–`:19008` |
| Optional: **nginx** or **Caddy** | Recommended reverse proxy on TITANHOME |
| Optional: **Tailscale** | Safe remote access without public exposure |

### Hardware / network (production intent)

| Item | Notes |
|------|-------|
| **TITANHOME** (or equivalent) | Primary host for safety services + cockpit |
| Loopback / LAN only by default | Bind UI to private network; tunnel for remote |
| **UPS** (Eaton 9SX class) | **Required before live capital** — not required merely to view the UI, but required before treating the stack as production trading. See `templates/infra/power_requirements.yaml` and `PRODUCTION_READINESS.md`. |

> **UPS note:** You can build and serve the cockpit without a UPS. You must **not** move real capital without UPS + power-loss HALT drill. The cockpit’s Power & UPS page is largely fixture until you wire real telemetry.

### What “production web UI” means here

For this repo, production UI means:

1. Built static assets (`web/dist/`) — not forever `npm run dev`.
2. Process supervised (systemd) so it survives reboot.
3. Same-origin (or carefully configured) reverse proxy for `/api/*` → safety ports.
4. Access only via Tailscale / VPN / SSH tunnel — **never** raw public internet without auth.
5. `VITE_DATA_MODE=live` only after you understand soft-fail and have backends (or accept advisory fallbacks).
6. HMAC set in Settings for any mutating control-plane actions.

It does **not** mean “trading is live.”

---

## 3. Mental model: mock → live `/api/*` → titan-safety

```text
┌─────────────────────────────┐
│  Browser (cockpit SPA)      │
│  React routes in web/src    │
└──────────────┬──────────────┘
               │ fetch("/api/...")
               ▼
┌─────────────────────────────┐
│  Dev: Vite proxy            │
│  Prod: nginx/Caddy/preview  │  ← must rewrite /api/* → 127.0.0.1:1900x
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  titan-safety HTTP units    │
│  :19001 … :19008            │
│  Signing: in-process (not   │
│  mandatory :19010)          │
└─────────────────────────────┘
```

### Three data modes you will hear about

| Mode | Where set | Behavior |
|------|-----------|----------|
| **Mock** | Default `VITE_DATA_MODE=mock` or Settings → Mock | Returns fixtures from `web/src/lib/data.ts` via `providers/mock/` |
| **Live** | `VITE_DATA_MODE=live` or Settings → Live | Calls `/api/*` via `providers/live/`; on failure **soft-fails** back to fixtures with `advisory: true` + error string |
| **Session override** | Settings → Data providers | Stored in `sessionStorage` key `titan.dataMode` — **not** written to disk; wins over env until tab closes |

Code: `web/src/lib/providers/mode.ts`, `create.ts`, `live/index.ts`, `mock/index.ts`.

### Soft-fail (important)

Live adapters **never throw into the UI**. If `:19003` is down, Health may still show fixture-looking data with an error / advisory flag. That is intentional so the cockpit stays usable during bring-up — and dangerous if you ignore the advisory labels.

### Env vars baked at build time

Vite embeds `VITE_*` variables **when you build**. Changing `.env.production` after `npm run build` does nothing until you rebuild.

| Variable | Meaning |
|----------|---------|
| `VITE_DATA_MODE` | `mock` (default) or `live` |
| `VITE_API_BASE` | Optional absolute origin (e.g. `https://cockpit.tailnet.ts.net`). Empty = same-origin relative `/api/*` (preferred behind a reverse proxy) |

---

## 4. Install Node.js

### Check if Node is already available

```bash
node -v
npm -v
which node
```

You want Node **v20+** (v22 LTS is fine). If `node: command not found`, install it.

### Ubuntu / Debian (TITANHOME typical)

**Option A — NodeSource (common for current LTS):**

```bash
# Example for Node 22 — adjust if your org pins a version
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v && npm -v
```

**Option B — Ubuntu packages (may be older):**

```bash
sudo apt-get update
sudo apt-get install -y nodejs npm
node -v
```

If the distro Node is &lt; 20, prefer Option A or `nvm`.

### nvm (user-local, good when you lack sudo)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# restart shell or: source ~/.nvm/nvm.sh
nvm install 22
nvm use 22
node -v
```

### PATH missing / Cursor agent / non-interactive shells

Symptoms:

- `npm: command not found` in a Cursor terminal but works in a normal SSH session
- Agent scripts cannot find Node

Fixes:

1. Confirm install location:

   ```bash
   ls -la ~/.nvm/versions/node/*/bin/node 2>/dev/null
   ls -la /usr/bin/node /usr/local/bin/node 2>/dev/null
   ```

2. Export PATH for the current shell:

   ```bash
   export PATH="$HOME/.nvm/versions/node/$(ls $HOME/.nvm/versions/node | tail -1)/bin:$PATH"
   # or, if system Node:
   export PATH="/usr/bin:$PATH"
   ```

3. For systemd units (later), set `Environment=PATH=...` explicitly — do not rely on interactive `.bashrc`.

4. If a Cursor sandbox cannot see your Node, run build commands in a normal host terminal with the PATH above.

> **Do not** commit Node binaries into this repo. Install on the host.

---

## 5. Install web dependencies

From the repo root:

```bash
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy/web"
# or: cd /path/to/titan-deploy/web
```

### Prefer lockfile install

This repo includes `web/package-lock.json`. Prefer:

```bash
npm ci
```

`npm ci` installs **exactly** the locked versions (cleaner for production). If `npm ci` fails because `node_modules` is half-broken:

```bash
rm -rf node_modules
npm ci
```

### Fallback

```bash
npm install
```

### What gets installed

From `web/package.json`:

- **Runtime:** React 19, react-router-dom, recharts, lucide-react, clsx
- **Build:** Vite 6, TypeScript, `@vitejs/plugin-react`

Scripts:

| Script | Command | Purpose |
|--------|---------|---------|
| `npm run dev` | `vite --host 0.0.0.0 --port 5173` | Dev server + API proxy |
| `npm run build` | `tsc -b && vite build` | Typecheck + production bundle → `dist/` |
| `npm run preview` | `vite preview --host 0.0.0.0 --port 5173` | Serve `dist/` locally (limited proxy) |

---

## 6. Local verify with mock data

Before any production build, prove the UI loads.

```bash
cd /path/to/titan-deploy/web
npm run dev
```

Open: **http://127.0.0.1:5173**

### What you should see

- Signal theme (cool slate / cyan) by default; Night theme in Settings
- Sidebar sections (Control / Trading / Intelligence / Build / Governance)
- Dashboard with fixture metrics
- Settings → Data providers → **Mock** active by default

### Confirm mock mode

1. Open **Settings**.
2. Under **Data providers**, leave **Mock** selected (or select it).
3. Open **Health & Verify** and **Agent Manager** — data comes from fixtures; fleet size should be **20** classical agents (no QCC/QSA/QRP).

### Stop the dev server

`Ctrl+C` in the terminal.

> **Dev vs prod:** `npm run dev` is fine for learning and UI work. For production on TITANHOME, continue to build + reverse proxy (sections 8–10). Do not leave an unbound `0.0.0.0:5173` exposed to the public internet.

---

## 7. Configure env for production intent

Create env files **inside `web/`** (Vite loads them automatically).

### Recommended files

| File | When used |
|------|-----------|
| `.env.production` | Applied during `npm run build` (production mode) |
| `.env.local` | Local overrides (gitignored if you add it to ignore; do not commit secrets) |
| `.env` | Optional shared defaults |

### Minimal production intent

Create `web/.env.production`:

```bash
# Production build defaults for Titan Agentik cockpit
# Rebuild after changing these values.

# live = call /api/* stubs (soft-fail to fixtures if backends down)
# mock = fixtures only
VITE_DATA_MODE=live

# Leave empty for same-origin /api/* behind nginx/Caddy (recommended).
# Set only if the browser must call a different absolute origin.
# VITE_API_BASE=https://cockpit.your-tailnet.ts.net
VITE_API_BASE=
```

### When to keep mock in production build

If safety units are **not** up yet, you can ship:

```bash
VITE_DATA_MODE=mock
```

Operators can still flip **Settings → Live** for a session (sessionStorage override). Remember: that override does not change the baked env default for new sessions.

### Absolute API base (advanced)

Set `VITE_API_BASE` only when:

- Static files are served from origin A
- APIs are on origin B

Otherwise prefer **empty** `VITE_API_BASE` and reverse-proxy `/api` on the same host (avoids CORS pain).

Code reference: `live/index.ts` uses:

```ts
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";
```

---

## 8. Build production assets

```bash
cd /path/to/titan-deploy/web
npm run build
```

### What happens

1. `tsc -b` — TypeScript project build / typecheck
2. `vite build` — bundles JS/CSS into `web/dist/`

### What `dist/` is

`dist/` is a folder of **static files** (HTML, JS, CSS, assets). Any static file server can host them. There is **no** Node server required inside the browser bundle — but you still need something to:

1. Serve `index.html` + assets
2. Proxy `/api/*` to localhost safety ports (Vite’s `server.proxy` only exists in **dev**)

```bash
ls -la dist/
# expect: index.html, assets/*.js, assets/*.css, …
```

### Rebuild rule

Any change to `VITE_*` or source → run `npm run build` again → restart the static server / reload proxy.

---

## 9. Serve the production build

You have three practical options. **Recommended default for TITANHOME: Caddy or nginx reverse proxy** serving `dist/` + proxying `/api/*`. Use `vite preview` only for a quick smoke test.

### Option A — Quick smoke: `vite preview` (not full production)

```bash
cd /path/to/titan-deploy/web
npm run preview
# http://127.0.0.1:5173
```

**Limits:**

- Good for “does the bundle load?”
- **Does not** automatically apply the same `server.proxy` map from `vite.config.ts` the way `vite` dev does (preview is a static preview server). For live `/api/*`, put nginx/Caddy in front or call backends another way.
- Still binds `0.0.0.0:5173` per `package.json` — firewall carefully.

### Option B — Recommended: Caddy (simple TLS + reverse proxy)

Install Caddy, then an example Caddyfile (adjust paths/user):

```caddyfile
# /etc/caddy/Caddyfile — TITANHOME cockpit example
# Bind to Tailscale IP or localhost only in real deployments.

:8443 {
        # Prefer Tailscale Serve or bind to 100.x / 127.0.0.1 in production.
        root * /path/to/titan-deploy/web/dist
        encode gzip
        try_files {path} /index.html
        file_server

        handle_path /api/risk* {
                reverse_proxy 127.0.0.1:19001
        }
        handle_path /api/recon* {
                reverse_proxy 127.0.0.1:19002
        }
        handle_path /api/status* {
                reverse_proxy 127.0.0.1:19003
        }
        handle_path /api/portfolio* {
                reverse_proxy 127.0.0.1:19004
        }
        handle_path /api/dms* {
                reverse_proxy 127.0.0.1:19005
        }
        handle_path /api/allocator* {
                reverse_proxy 127.0.0.1:19006
        }
        handle_path /api/tca* {
                reverse_proxy 127.0.0.1:19007
        }
        handle_path /api/security* {
                reverse_proxy 127.0.0.1:19008
        }
        # Signing status via status-agg control plane (in-process signing)
        handle_path /api/signing* {
                reverse_proxy 127.0.0.1:19003
        }
        # Optional legacy HTTP signing_node — only if you deliberately run :19010
        handle_path /api/sign* {
                reverse_proxy 127.0.0.1:19010
        }
}
```

> **Path rewrite note:** Vite’s config **strips** the `/api/risk` prefix before forwarding (so `/api/risk/health` → `http://127.0.0.1:19001/health`). Caddy `handle_path` also strips the matched prefix. Match that behavior. If you use `handle` + `reverse_proxy` without stripping, upstreams will see `/api/risk/...` and return 404.

Reload:

```bash
sudo systemctl reload caddy
```

### Option C — Recommended alternative: nginx

```nginx
# /etc/nginx/sites-available/titan-cockpit
server {
    listen 127.0.0.1:8080;
    server_name localhost;

    root /path/to/titan-deploy/web/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Strip /api/<name> prefix to match vite.config.ts rewrite behavior
    location /api/risk/ {
        proxy_pass http://127.0.0.1:19001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
    location /api/recon/ {
        proxy_pass http://127.0.0.1:19002/;
    }
    location /api/status/ {
        proxy_pass http://127.0.0.1:19003/;
    }
    location /api/portfolio/ {
        proxy_pass http://127.0.0.1:19004/;
    }
    location /api/dms/ {
        proxy_pass http://127.0.0.1:19005/;
    }
    location /api/allocator/ {
        proxy_pass http://127.0.0.1:19006/;
    }
    location /api/tca/ {
        proxy_pass http://127.0.0.1:19007/;
    }
    location /api/security/ {
        proxy_pass http://127.0.0.1:19008/;
    }
    location /api/signing/ {
        proxy_pass http://127.0.0.1:19003/;
    }
    # Optional legacy only
    location /api/sign/ {
        proxy_pass http://127.0.0.1:19010/;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/titan-cockpit /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Why not “just leave Vite dev running”?

| Concern | Dev server | Static + reverse proxy |
|---------|------------|-------------------------|
| HMR / source maps | Yes (extra attack surface) | No |
| Survives reboot | Manual | systemd |
| Matches production asset graph | No | Yes |
| Operator discipline | Easy to forget | Explicit |

---

## 10. Reverse proxy map (`/api/*` → ports)

Source of truth for the **dev** proxy: `web/vite.config.ts`. Production reverse proxies must mirror this map.

| UI path prefix | Upstream | Service | Notes |
|----------------|----------|---------|-------|
| `/api/risk` | `127.0.0.1:19001` | Risk kernel | Authoritative DENY |
| `/api/recon` | `127.0.0.1:19002` | Reconciliation | Pre-trade recon |
| `/api/status` | `127.0.0.1:19003` | Status aggregator | `/health` rollup |
| `/api/portfolio` | `127.0.0.1:19004` | Portfolio risk | VaR / summary |
| `/api/dms` | `127.0.0.1:19005` | Dead-man's switch | Heartbeat / wind-down |
| `/api/allocator` | `127.0.0.1:19006` | Capital allocator | Plans / pipelines |
| `/api/tca` | `127.0.0.1:19007` | TCA / execution quality | Scorecards |
| `/api/security` | `127.0.0.1:19008` | Security Ops | Four pillars |
| `/api/signing` | `127.0.0.1:19003` | Status / control plane | Halt status for **in-process** signing |
| `/api/sign` | `127.0.0.1:19010` | Legacy HTTP signing_node | **Optional — not required** |

### Rewrite rule (same as Vite)

For each prefix, strip the prefix before forwarding:

| Browser requests | Upstream receives |
|------------------|-------------------|
| `GET /api/status/health` | `GET http://127.0.0.1:19003/health` |
| `GET /api/security/v1/status` | `GET http://127.0.0.1:19008/v1/status` |
| `GET /api/risk/v1/validate` | `GET/POST http://127.0.0.1:19001/v1/validate` |

### Manual curl checks (bypass UI)

```bash
curl -sS http://127.0.0.1:19001/health
curl -sS http://127.0.0.1:19002/health
curl -sS http://127.0.0.1:19003/health
curl -sS http://127.0.0.1:19004/health
curl -sS http://127.0.0.1:19005/health
curl -sS http://127.0.0.1:19006/health
curl -sS http://127.0.0.1:19007/health
curl -sS http://127.0.0.1:19008/health
```

Aggregator rollup (preferred single check):

```bash
curl -sS http://127.0.0.1:19003/health | python3 -m json.tool
```

Expect `"status":"ok"` when units are healthy (`PRODUCTION_READINESS.md`).

> **Do not** require `:19010` for health PASS. Default signing is in-process inside `titan-safety`.

---

## 11. Wire live providers (real stubs + TODOs)

### Where the code lives

```text
web/src/lib/providers/
  types.ts          # shared DTOs
  mode.ts           # VITE_DATA_MODE + session override
  http.ts           # soft-fail fetchJson (2.5s timeout default)
  create.ts         # mock vs live factory
  mock/index.ts     # fixtures
  live/index.ts     # /api/* adapters ← wire here
  context.tsx       # React hooks
```

### What is already implemented (honest)

| Provider method | Live call attempted | Status |
|-----------------|---------------------|--------|
| `getHealth()` | `GET /api/status/health` | Implemented mapping; soft-fail to mock |
| `getFleet()` | `GET /api/status/v1/fleet` | **TODO** until registry exists; rejects totals ≠ 20 |
| `getSigning()` | `GET /api/signing/v1/status` | Implemented; forces `mode: "in_process"` |
| `getSecurity()` | `GET /api/security/v1/status` via `securityApi.ts` | Implemented when `:19008` up |
| `getPortfolio()` | `GET /api/portfolio/v1/summary` | Partial; soft-fail; some fields still from mock |
| `getPipelines()` | `GET /api/allocator/v1/pipelines` | **TODO** until allocator exposes catalog |
| `getManualControl()` | `GET /api/status/v1/control` | Partial; soft-fail |

Comments in `live/index.ts` are the source of truth for remaining work. **Do not invent fake backends** — implement real endpoints on status-agg / portfolio / allocator, then map JSON into the DTOs in `types.ts`.

### Checklist per surface

#### Fleet (Agent Manager)

- [ ] Status aggregator (or agent registry) serves `GET /v1/fleet` (proxied as `/api/status/v1/fleet`)
- [ ] Payload includes exactly **20** classical agents (no QCC/QSA/QRP)
- [ ] Map fields into `AgentDto` (`id`, `tierKey`, `runStatus`, BFT roles, etc.)
- [ ] Confirm UI shows `source: live`, `advisory: false` when healthy

#### Health

- [ ] `:19003/health` returns overall status + per-service map
- [ ] Ports match `SERVICE_PORT` in `live/index.ts` (19001–19008)
- [ ] In-process signing row is informational; legacy `:19010` optional

#### Signing status

- [ ] Control-plane status at `/api/signing/v1/status` (→ `:19003`) returns `halted`, optional `audit`
- [ ] UI Signing page shows **in-process**, `daemonRequired: false`
- [ ] Do **not** require a separate signing daemon for PASS

#### Pipelines

- [ ] Allocator (or status) serves pipeline catalog JSON
- [ ] Map into `PipelineDto[]`; keep `dexOnly: true`
- [ ] Until then, accept soft-fail fixtures and treat as advisory

#### Portfolio

- [ ] `:19004` (or capital module) serves `/v1/summary` with `equity_usd`, `drawdown_pct`, etc.
- [ ] Never display fixture equity as live capital without checking advisory/error

#### Security

- [ ] `:19008/v1/status` live
- [ ] Mutating lockdown uses `X-Titan-Auth` (Settings HMAC)
- [ ] Prefer dry-run first (`postSecurityLockdownDryRun`)

### How to add a new provider (from `web/README.md`)

1. Extend DTO in `types.ts`.
2. Implement `getX()` on mock + live (live: soft-fail with `error` + fixture).
3. Export a hook from `context.tsx`.
4. Prefer the hook in the page; keep `data.ts` for charts/static labels only.
5. Show `advisoryLabel(result)` so operators never confuse fixtures with live capital.

### Pages still on fixtures

SYSTEM.md §11 is honest: many pages (PnL charts, Power UPS refresh, Decision Log samples, QI Optimizer) remain fixture/localStorage until wired. **SaveBar always saves to browser localStorage — not the live API.**

---

## 12. Auth & exposure (never raw public internet)

### Hard rule

> **NEVER** expose the cockpit raw on the public internet without an authentication layer in front. This UI can trigger HMAC-gated control-plane actions (kill, lockdown, promotions surfaces). Treat it like an admin console.

### Recommended access patterns

| Method | How | Good for |
|--------|-----|----------|
| **Tailscale Serve / Funnel off** | Install Tailscale on TITANHOME; Serve the Caddy/nginx port only on the tailnet | Daily remote ops |
| **SSH tunnel** | `ssh -L 8080:127.0.0.1:8080 user@titan-host` then open `http://127.0.0.1:8080` | Quick access |
| **WireGuard / corporate VPN** | Same idea as Tailscale | Existing VPN shops |
| **Cloudflare Tunnel + SSO** | Tunnel + IdP in front | Teams with SSO already |

Dev-time tunnel example (from `web/README.md`):

```bash
ssh -L 5173:127.0.0.1:5173 user@titan-host
```

### HMAC for mutating actions

| Concept | Detail |
|---------|--------|
| Header | `X-Titan-Auth` |
| Browser storage | `sessionStorage` key `titan-hmac-token` |
| Code | `web/src/lib/auth.ts` → `authHeaders()` |
| UI | **Settings → Control-plane HMAC** → Save session |
| Backend | `titan_safety` `auth.py` when `control_plane.auth_required: true` |

Without HMAC, mutating POSTs return **401**. The UI shows messages like:  
`401 — HMAC required. Set operator token in Settings (sessionStorage titan-hmac-token).`

> The HMAC token is **session-only** (not written to disk by the app). Closing the browser tab clears sessionStorage. Do not paste production secrets into screenshots or chat logs.

### Optional front-door auth

HMAC protects **mutating API calls** to titan-safety. It does **not** by itself stop a stranger from loading the SPA if the port is public. Add one of:

- Tailscale ACL (preferred)
- HTTP basic auth on Caddy/nginx
- SSO (Authentik / Keycloak / Cloudflare Access) in front of the reverse proxy

### Advisory vs live actions

Many Manual Control / Command Center buttons are **demo/local** until HTTP is up. Labels in the UI call out HMAC + Human YES. Kernel DENY on `:19001` remains authoritative even if the UI looks “armed.”

---

## 13. TLS / certificates

### Local LAN only

If you only open `http://127.0.0.1:8080` on the machine (or via SSH tunnel), TLS is optional. Prefer tunnel over opening LAN ports.

### Tailscale

Tailscale can terminate HTTPS for you (Serve). Certificates are managed by Tailscale — simplest path for a single operator.

### Caddy automatic HTTPS

If you put a real DNS name on a public interface (not recommended without SSO), Caddy can obtain Let’s Encrypt certs. For Titan, prefer **private** HTTPS on the tailnet instead.

### Self-signed (lab)

```bash
# Example only — browsers will warn
openssl req -x509 -newkey rsa:2048 -nodes -keyout cockpit.key -out cockpit.crt -days 365
```

Point nginx/Caddy at those files. Operators must click through trust warnings — fine for lab, awkward for daily ops. Prefer Tailscale.

### Mixed content warning

If the SPA is served as `https://…` but `VITE_API_BASE` points to `http://…`, browsers may block requests. Keep **same-origin** `/api/*` via reverse proxy to avoid this.

---

## 14. systemd unit example

Goal: after reboot, the production static server (or a tiny preview) comes back. Prefer serving via **nginx/Caddy** (already systemd-managed) and only ensuring `dist/` is rebuilt on deploy.

### Pattern A — nginx/Caddy only (recommended)

1. Build on deploy:

   ```bash
   cd /path/to/titan-deploy/web && npm ci && npm run build
   ```

2. Rely on `nginx.service` / `caddy.service`.
3. Optional: a oneshot deploy unit that rebuilds assets.

### Pattern B — `vite preview` under systemd (acceptable for single-operator lab)

> Prefer Pattern A for anything resembling production. Preview does not replace a proper `/api` reverse proxy.

`/etc/systemd/system/titan-cockpit.service`:

```ini
[Unit]
Description=Titan Agentik cockpit (vite preview)
After=network.target
# Optional: wait for status aggregator
# After=network.target titan-status-agg.service
Wants=network-online.target

[Service]
Type=simple
User=hyperion
WorkingDirectory=/path/to/titan-deploy/web
Environment=PATH=/usr/bin:/usr/local/bin
Environment=NODE_ENV=production
# Bind locally; put Tailscale/nginx in front
ExecStart=/usr/bin/npm run preview -- --host 127.0.0.1 --port 5173
Restart=on-failure
RestartSec=5

# Hardening (adjust as needed)
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now titan-cockpit.service
sudo systemctl status titan-cockpit.service
```

### Pattern C — `npx serve` static only

```bash
npm install -g serve
# ExecStart=/usr/bin/serve -s dist -l 127.0.0.1:5173
```

You **must** still run nginx/Caddy for `/api/*` proxying if using live providers.

### Safety services systemd

Cockpit up ≠ safety up. Enable safety units via the deploy bundle:

```bash
cd /path/to/titan-deploy
./deploy.sh --systemd --start-services
```

Confirm `:19001`–`:19008` (see `BOOT.md`). Signing remains in-process — do not require `titan-signing-node.service` unless you deliberately chose legacy HTTP mode.

---

## 15. Health checks & `verify.sh`

### Relationship

| Tool | Scope |
|------|-------|
| **Cockpit Health & Verify page** | Operator-facing view; live when providers work, else fixtures/advisory |
| **`curl :19003/health`** | Ground truth for safety rollup |
| **`./verify.sh`** | Repo bootstrap / config / unit / harness checks — **not** a substitute for “UI looks fine” |
| **`./deploy.sh --verify`** | Invokes `verify.sh` after deploy |

`verify.sh` validates deploy-bundle readiness (limits, templates, systemd unit presence, tests, UPS ack for live-capital paths when configured). It does **not** currently treat “cockpit npm build” as the primary gate — you still build/serve `web/` as an operator step.

### Suggested operator health loop

```bash
# 1) Safety rollup
curl -sS http://127.0.0.1:19003/health | python3 -m json.tool

# 2) Kill switch should be inactive for normal ops
titan-safety kill status

# 3) Evolution freeze if live capital
titan-safety evolution status

# 4) Security posture
titan-safety security status

# 5) Cockpit (via proxy)
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
```

### Inference ports (not the web UI, but related)

| Port | Role |
|------|------|
| `:30000` | Tier 1 critical (signals / GUARDIAN / TRENCH-OPS) |
| `:30001` | Tier 2 reasoning |
| `:30002` | Utility (TITANSPARK) |
| `:30005` / `:30003` | R&D only (DeepSeek / GLM) — not live critical path |

Cockpit Model Tiers page documents this map; it does not start GPUs for you.

---

## 16. Go-live checklist (paper → shadow → capital)

Use this as a **cockpit + stack** gate list. Capital gates are owned by `PRODUCTION_READINESS.md` — summarized here so UI operators do not skip them.

### A. UI production (this guide)

- [ ] Node 20+ installed; `npm ci` succeeds in `web/`
- [ ] `npm run build` produces `web/dist/`
- [ ] Reverse proxy serves `dist/` + `/api/*` map (section 10)
- [ ] Access only via Tailscale / VPN / SSH tunnel
- [ ] TLS or private network path documented
- [ ] systemd (or nginx/Caddy) survives reboot
- [ ] Settings HMAC works (401 without token on mutate)
- [ ] Data mode understood: live soft-fail ≠ live capital truth
- [ ] Fleet shows 20 classical agents when live registry exists

### B. Safety stack

- [ ] `:19001`–`:19008` healthy via `:19003/health`
- [ ] In-process signing path verified (`titan-safety gate sign`); `:19010` not required
- [ ] Fail-closed: stop kernel → trades DENY
- [ ] Kill switch drill + signed RESUME
- [ ] DMS heartbeat path tested
- [ ] Security Ops HARDENED / lockdown dry-run

### C. Capital gates (do not skip)

- [ ] Paper ≥ 3 days per lane + shadow evidence
- [ ] Statistical promotion gates pass where required
- [ ] **Phase 5 human YES** recorded (`titan-safety promotion approve --response YES`)
- [ ] UPS installed + power-loss HALT drill
- [ ] Live keys / adapters — mock banned on live profile
- [ ] Residual risks in `PRODUCTION_READINESS.md` accepted by operator

### Phased reminder

| Phase | Meaning for UI |
|-------|----------------|
| Paper | Cockpit can be live-API against paper backends; no real keys |
| Shadow | Observe; do not treat PnL fixtures as profit |
| Micro-live | Still needs YES + tiny equity caps |
| Full live | Phase 5 YES + UPS + fail-closed proof |

> **TIMEOUT on promotion prompts = HOLD / de-risk — never auto-promote.**

---

## 17. Troubleshooting

### Blank page / white screen

1. Open browser DevTools → Console. Note first red error.
2. Confirm you are hitting the reverse proxy root that serves `dist/index.html`.
3. SPA routing: nginx/Caddy must `try_files … /index.html` (deep links like `/security` must not 404).
4. Rebuild: `npm run build` after pulling new code.
5. Hard refresh (Ctrl+Shift+R) to bust cached assets.

### CORS errors

- Prefer same-origin `/api/*` (empty `VITE_API_BASE`).
- If you set `VITE_API_BASE` to another origin, that origin must send CORS headers — usually worse than proxying.

### Proxy 502 Bad Gateway

| Cause | Fix |
|-------|-----|
| Safety unit down | `curl :1900x/health`; start systemd unit |
| Wrong rewrite (prefix not stripped) | Align with Vite rewrite / nginx `proxy_pass …/` trailing slash |
| Bound to wrong interface | Ensure upstream is `127.0.0.1`, not a remote IP you cannot reach |
| Legacy `/api/sign` → `:19010` | Expected 502 if you never started legacy signing — ignore unless you need HTTP signing |

### Live mode still shows fixtures

1. Soft-fail is working — check advisory / error string in UI.
2. Confirm proxy path with browser Network tab (`/api/status/health`).
3. Confirm `VITE_DATA_MODE=live` was set **before** `npm run build`, or use Settings session override.
4. Fleet endpoint returning `total !== 20` is **rejected** by design — fix registry, do not patch the check away.

### `node: command not found`

See [§4](#4-install-nodejs). Fix PATH for interactive shells **and** systemd `Environment=PATH=…`.

### Theme / “white buttons”

- Settings → Appearance: **Signal** (light) vs **Night** (dark).
- Theme stored in `localStorage` key `titan-theme`.
- If controls look unstyled, CSS failed to load — check Network for `assets/*.css` 404 (wrong `root` path in nginx).

### SaveBar confusion

- SaveBar text: **“Browser localStorage · not live API”**.
- Saving Settings bind prefs does **not** reconfigure the Vite/nginx process.
- Dirty state is per-browser, not cluster state.

### HMAC always 401

1. Settings → paste operator token → **Save session**.
2. Confirm backend `control_plane` secret matches what you paste.
3. sessionStorage blocked (rare private mode) — `auth.ts` silently fails; try a normal window.

### Port 5173 already in use

```bash
ss -ltnp | grep 5173
# stop the old process or choose another port in preview/proxy
```

---

## 18. Security checklist

- [ ] No exchange / wallet **private keys** in the browser, env committed to git, or UI fixtures
- [ ] HMAC secret not committed; session-only in browser
- [ ] Cockpit not on `0.0.0.0` public interface without Tailscale/SSO/basic auth
- [ ] Mutating actions require HMAC; lockdown / kill require operator discipline (+ Human YES where labeled)
- [ ] Treat UI as **advisory** until soft-fail errors are gone and curls match
- [ ] Risk kernel DENY cannot be overridden by the SPA
- [ ] Signing is **in-process** `titan_safety.SigningNode` after gate receipt — not in the React app, not mandatory `:19010`
- [ ] No closed/cloud models on live trading path (infra concern; UI Model Tiers should reflect local tiers)
- [ ] Quantum agents absent; do not re-add QCC/QSA/QRP in fleet payloads
- [ ] Memecoin / flash-loan live remain gated (catalog until Phase 5 YES + config flags)
- [ ] UPS + power-loss policy before live capital
- [ ] Regular kill-switch and fail-closed drills

---

## Appendix A — Sidebar / route map

From `web/src/App.tsx` / `SYSTEM.md` §11:

### Control

| Route | Page |
|-------|------|
| `/` | Dashboard |
| `/command` | Command Center |
| `/manual-control` | Manual Control |
| `/capital` | Capital & Wallets |
| `/wallets` | Wallet Tracker |
| `/pnl` | PnL |
| `/risk` | Risk & CBs |
| `/dms` | Dead Man's Switch |
| `/security` | Security Ops |
| `/ops` | Ops Center |
| `/health` | Health & Verify |
| `/power` | Power & UPS |
| `/forge` | Forge |

### Trading

| Route | Page |
|-------|------|
| `/pipelines` | Pipelines |
| `/qi-optimizer` | QI Optimizer (classical SA, advisory) |
| `/tca` | TCA & Allocator |
| `/promotions` | Promotions |
| `/memecoin` | Memecoin Trench |
| `/edge` | Edge Mesh |
| `/latency` | Latency |
| `/flash-loans` | Flash Loans |
| `/signing` | Signing (in-process) |

### Intelligence

| Route | Page |
|-------|------|
| `/automations` | Automations |
| `/crypto-news` | Crypto News |
| `/crypto-twitter` | Crypto Twitter |
| `/goals` | Goals Lab |
| `/identity` | Identity |
| `/models` | Model Tiers |
| `/ai-log` | AI Log |
| `/decisions` | Decision Log |
| `/questions` | Questions |

### Build

| Route | Page |
|-------|------|
| `/skills` | Skill Factory |
| `/agent-manager` | Agent Manager (20-agent fleet) |
| `/agents` | Agent Teams |
| `/workspace` | Workspace |

### Governance

| Route | Page |
|-------|------|
| `/reports` | Reports |
| `/settings` | Settings |

Unknown paths redirect to `/`.

---

## Appendix B — Port table

### Safety / control plane

| Port | Service |
|------|---------|
| 19001 | Risk kernel |
| 19002 | Reconciliation |
| 19003 | Status aggregator (+ `/api/signing` proxy target) |
| 19004 | Portfolio risk |
| 19005 | Dead-man's switch |
| 19006 | Capital allocator |
| 19007 | TCA / execution quality |
| 19008 | Security Ops |
| 19010 | Legacy HTTP signing (**optional**) |
| 18789 | OpenClaw gateway (Telegram / agents) |
| 19100 | Edge worker (per PoP) |

### Cockpit

| Port | Role |
|------|------|
| 5173 | Vite dev / preview default (`package.json`) |
| 8080 / 8443 | Typical nginx/Caddy local listeners (your choice) |

### Inference (not served by `web/`, documented for operators)

| Port | Tier |
|------|------|
| 30000 | Tier 1 critical |
| 30001 | Tier 2 reasoning |
| 30002 | Utility (TITANSPARK) |
| 30003 | GLM-5.2 R&D |
| 30004 | Embedder |
| 30005 | DeepSeek V4 Pro R&D |
| 30020 | REVM sim |

---

## Appendix C — Glossary

| Term | Plain meaning |
|------|----------------|
| **Vite** | Fast frontend build tool / dev server used by this React app |
| **SPA** | Single-page app — one HTML shell; React Router changes views without full reloads |
| **`dist/`** | Output folder of minified production static files |
| **Env / `.env`** | Files that set `VITE_*` variables baked in at build time |
| **Proxy / reverse proxy** | A server that accepts browser requests and forwards `/api/*` to localhost safety ports |
| **TLS** | HTTPS encryption (certificates) |
| **HMAC** | Shared-secret style auth header (`X-Titan-Auth`) for mutating control-plane calls |
| **Mock providers** | UI data from local fixtures (`data.ts`) — safe, not capital truth |
| **Live providers** | UI data from `/api/*`; soft-fails to mock on error |
| **Soft-fail** | On API error, show fixture data + advisory/error instead of crashing |
| **Advisory** | Informational / non-authoritative — kernel can still DENY |
| **systemd** | Linux service manager — starts programs on boot, restarts on failure |
| **Tailscale** | Private mesh VPN — recommended remote access to the cockpit |
| **TITANHOME** | Primary trading/compute host in the Titan BOM |
| **titan-safety** | Out-of-process Python safety stack (kernel, gate, DMS, security, …) |
| **In-process signing** | `SigningNode` inside titan-safety after gate receipt — default; no `:19010` required |
| **Phase 5 YES** | Explicit human promotion approval before full live capital |
| **UPS** | Battery backup — mandatory before live capital |
| **BFT vote** | 2-of-3 agent votes (advisory); not a kernel bypass |
| **SaveBar** | UI control that persists drafts to **localStorage**, not the API |

---

## Quick command cheat sheet

```bash
# Install + mock dev
cd /path/to/titan-deploy/web
npm ci
npm run dev                    # http://127.0.0.1:5173

# Production build
cp -n .env.production.example .env.production 2>/dev/null || true
# edit VITE_DATA_MODE=live
npm run build
npm run preview                # smoke only

# Safety ground truth
curl -sS http://127.0.0.1:19003/health | python3 -m json.tool
titan-safety security status
titan-safety kill status

# Remote access (example)
ssh -L 8080:127.0.0.1:8080 user@titan-host
```

---

## Document maintenance

When changing ports, provider endpoints, or signing mode:

1. Update `web/vite.config.ts` and this guide’s proxy table together.
2. Update `SYSTEM.md` §10–§11 if architecture changed.
3. Keep classical-only fleet (20) and in-process signing facts accurate.

*Accuracy over marketing. This guide documents the repo as shipped — stubs and TODOs included.*
