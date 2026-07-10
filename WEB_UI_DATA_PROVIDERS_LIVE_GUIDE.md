# Titan Agentik Cockpit — Data Providers & Live UI Guide

> **What this document is:** A long, beginner-friendly tutorial that explains — from first principles — how the **Titan Agentik web cockpit** (`web/`) gets **production-level live data**. It focuses on the **data provider** architecture (mock vs live), environment variables, Vite proxies, reverse proxies, auth, page-by-page wiring status, and troubleshooting.  
> **What this document is not:** A switch that enables **live capital trading**. Turning on `VITE_DATA_MODE=live` only tells the UI to *try* fetching real safety APIs. It does **not** authorize Phase 5 capital, bypass the risk kernel, or fund pipelines.

**Related docs (read these too):**

| Doc | Role |
|-----|------|
| [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md) | Build, serve, TLS, systemd, reverse proxy for the cockpit |
| [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) | Paper → shadow → Phase 5 YES → **real capital** (UI live ≠ capital live) |
| [`web/README.md`](./web/README.md) | Quick start + short provider overview |
| [`SYSTEM.md`](./SYSTEM.md) | Full system manual (cockpit map §11, ports §10) |
| [`PRODUCTION_READINESS.md`](./PRODUCTION_READINESS.md) | Honest go-live gates for capital |

**Code sources of truth for this guide:**

- `web/src/lib/providers/` — mode, types, mock, live, React hooks
- `web/src/lib/data.ts` — fixture source of truth
- `web/src/lib/auth.ts` — session HMAC for mutating calls
- `web/vite.config.ts` — dev proxy map
- `web/package.json` — scripts

---

## Table of contents

1. [Big picture: cockpit vs trading brain](#1-big-picture-cockpit-vs-trading-brain)
2. [Critical distinction: UI live ≠ capital live](#2-critical-distinction-ui-live--capital-live)
3. [What a “data provider” is (beginner definition)](#3-what-a-data-provider-is-beginner-definition)
4. [Tour of every provider module](#4-tour-of-every-provider-module)
5. [How mode switching works](#5-how-mode-switching-works)
6. [Environment variables](#6-environment-variables)
7. [Vite proxy map (full table)](#7-vite-proxy-map-full-table)
8. [Step-by-step: local mock first](#8-step-by-step-local-mock-first)
9. [Step-by-step: enable live mode for development](#9-step-by-step-enable-live-mode-for-development)
10. [Step-by-step: implement / wire each live provider](#10-step-by-step-implement--wire-each-live-provider)
11. [JSON shapes / response contracts](#11-json-shapes--response-contracts)
12. [Production build + serve + reverse proxy](#12-production-build--serve--reverse-proxy)
13. [Auth: HMAC, what the browser can hold](#13-auth-hmac-what-the-browser-can-hold)
14. [Checklist: page-by-page fixtures vs providers](#14-checklist-page-by-page-fixtures-vs-providers)
15. [Troubleshooting](#15-troubleshooting)
16. [Security rules for the frontend](#16-security-rules-for-the-frontend)
17. [Glossary](#17-glossary)
18. [Appendix A — Route map](#appendix-a--route-map)
19. [Appendix B — Honest stub vs ready matrix](#appendix-b--honest-stub-vs-ready-matrix)
20. [Appendix C — Copy-paste command cheatsheet](#appendix-c--copy-paste-command-cheatsheet)

---

## 1. Big picture: cockpit vs trading brain

### Analogy: airplane cockpit vs engines

Imagine a commercial airliner.

- The **cockpit** has instruments, switches, and screens. Pilots *see* altitude, fuel, and engine status. They *request* actions (flaps, autopilot modes).
- The **engines, flight computers, and safety interlocks** actually move the plane. A green “engine OK” light on a *simulator* screen does not mean a real engine is running.

In Titan:

| Layer | What it is | Analogy |
|-------|------------|---------|
| **Web UI (`web/`)** | React single-page app (SPA) operators open in a browser | Cockpit instruments |
| **OpenClaw / Hermes agents (20 classical)** | Propose signals, votes, orchestration | Co-pilots making suggestions |
| **BFT 2-of-3 (AUGUR + PREDATOR + ATLAS)** | Advisory trade authorization votes | Co-pilot consensus checklist |
| **Risk kernel `:19001` + ExecutionGate** | Pre-trade DENY / ALLOW + receipt | Flight computer that can refuse takeoff |
| **Portfolio risk `:19004`** | VaR / correlation caps when wired | Weight & balance computer |
| **In-process `titan_safety.SigningNode`** | Signs only after fresh gate receipt | Ignition key that only turns after clearance |
| **Edge mesh (5 PoPs)** | Low-RTT broadcast workers | Radio / dispatch to airports |

The cockpit **displays and requests**. It does **not** replace the risk kernel. Agents propose; deterministic safety services veto.

### What the web UI actually is

- A **React** app under `web/`.
- Built and served by **Vite** (a modern frontend toolchain).
- In development: `npm run dev` → http://127.0.0.1:5173
- In production: `npm run build` → static files in `web/dist/`, then served by nginx/Caddy/`vite preview` + reverse proxy.

### Classical-only fleet (do not regress)

- **20 agents** total.
- Quantum agents **QCC / QSA / QRP are removed**.
- QI Optimizer page = classical simulated annealing, **advisory only** (`live_path=false`).
- Signing default = **in-process** via `titan-safety gate sign`. Legacy HTTP `:19010` is **optional / not required**.

---

## 2. Critical distinction: UI live ≠ capital live

This is the single most important idea in this entire guide. Read it twice.

| Phrase | What it means | What it does **not** mean |
|--------|---------------|---------------------------|
| `VITE_DATA_MODE=live` | The UI’s **data providers** call `/api/*` against safety services | Real money can trade |
| Settings → **Live** | Session override: same as above for this browser tab | Phase 5 YES happened |
| Green Health page | Status aggregator (or soft-fail fixtures) look healthy | Capital profile is live |
| `capital_profile: live` in policy | Live *profile rules* in the risk template | You already said YES and funded lanes |
| Soft-fail “LIVE” badge missing / “ADVISORY” | Fixtures or fallback data | Backend is authoritative |

> **Iron law for operators:** A beautiful green cockpit can still be showing **fixture** (fake demo) numbers because live adapters **soft-fail** when backends are down. Always read the advisory chip (`ADVISORY · mock`, `ADVISORY · live fallback`, or `LIVE`) and verify with `curl` against `127.0.0.1:1900x`.

### Two different “go live” journeys

```text
Journey A — UI data live (THIS GUIDE)
  mock fixtures → VITE_DATA_MODE=live → /api/* → safety ports :19001–:19008
  Goal: operators see real health / security / portfolio summaries in the browser

Journey B — Capital live (OTHER GUIDE)
  paper → shadow → Phase 5 human YES → capital_profile live → real txs
  Goal: real funds move under risk kernel + ExecutionGate + in-process signing
  See: LIVE_CAPITAL_PRODUCTION_GUIDE.md
```

**This guide is Journey A only.** Completing Journey A does not start Journey B.

---

## 3. What a “data provider” is (beginner definition)

### Plain English

A **data provider** is a small piece of TypeScript that answers: *“Give me the Health snapshot / Fleet roster / Portfolio numbers.”*

Pages should **not** hard-code `fetch("http://127.0.0.1:19003/...")` forever. Instead they call a hook like `useHealth()`, and the hook asks the active provider set.

Think of it like a **power outlet standard**:

- The **wall socket shape** = the TypeScript interface (`getHealth()`, `getFleet()`, …).
- The **mock plug** = returns pre-written numbers from `data.ts` (fixtures).
- The **live plug** = calls real HTTP APIs, then maps JSON into the same shapes.
- You can swap plugs without rewriting every page.

### Interface + two implementations

```text
TitanProviders (same methods on both)
├── mockProviders   ← always advisory=true, data from data.ts
└── liveProviders   ← try /api/*; on failure soft-fail to mock + error string
```

Factory: `createProviders({ mode })` in `web/src/lib/providers/create.ts`.

React wrapper: `<DataProvider>` in `web/src/main.tsx` wraps the whole app. Pages use hooks from `context.tsx`.

### Key types (from `types.ts`)

**`ProviderResult<T>`** — every provider method returns this envelope:

| Field | Meaning |
|-------|---------|
| `data` | The actual snapshot (health, fleet, …) |
| `source` | `"mock"` or `"live"` — which adapter ran |
| `advisory` | `true` = treat as non-authoritative / fixture / fallback |
| `error?` | Soft-fail reason (e.g. `HTTP 502`, `unreachable`) |
| `fetchedAt` | ISO 8601 timestamp |

**`DataMode`** — `"mock" | "live"`.

### Soft-fail (why the UI never “crashes” when APIs are down)

Live adapters wrap `fetchJson` (2.5s timeout by default). If the call fails:

1. They still return `data` (usually the mock fixture).
2. They set `source: "live"`, `advisory: true`, and `error: "..."`.
3. The UI shows an **ADVISORY** label via `advisoryLabel(result)`.

This is intentional for bring-up — and dangerous if you ignore the label.

### Fixture

A **fixture** is canned sample data checked into the repo (`web/src/lib/data.ts`). Like a flight simulator’s fake altitude. Useful for UI development when backends are offline.

---

## 4. Tour of every provider module

Directory layout:

```text
web/src/lib/providers/
  index.ts          # public exports (hooks, types, mode helpers)
  types.ts          # shared DTOs (HealthSnapshot, FleetSnapshot, …)
  mode.ts           # VITE_DATA_MODE + sessionStorage override
  http.ts           # fetchJson soft-fail helper + nowIso()
  create.ts         # createProviders / getProviders / resetProviders
  mock/index.ts     # mockProviders — wraps data.ts
  live/index.ts     # liveProviders — /api/* + soft-fail
  context.tsx       # DataProvider + useHealth / useFleet / …
```

### 4.1 `types.ts` — the contract

Defines the shapes pages expect. Mock and live must both produce these. Important snapshots:

| Snapshot | Used for |
|----------|----------|
| `HealthSnapshot` | Health & Verify, Dashboard health strip |
| `FleetSnapshot` | Agent Manager (exactly 20 classical agents) |
| `SigningSnapshot` | Signing page (`mode: "in_process"`, no mandatory daemon) |
| `SecuritySnapshot` | Security Ops |
| `PortfolioSnapshot` | Dashboard equity strip (when wired) |
| `PipelinesSnapshot` | Pipelines page catalog |
| `ManualControlSnapshot` | Manual Control posture |

### 4.2 `mode.ts` — how mock/live is chosen

1. Read `sessionStorage["titan.dataMode"]` if set (`live` or `mock`).
2. Else read build-time `import.meta.env.VITE_DATA_MODE`.
3. Else default **`mock`**.

Session override **wins** over env until the tab closes (not written to disk).

### 4.3 `http.ts` — safe fetch

`fetchJson(path)` returns `{ ok: true, data }` or `{ ok: false, error }` — never throws into React. Default timeout **2500 ms**.

### 4.4 `create.ts` — factory + singleton

```text
resolveDataMode() → "live" ? liveProviders : mockProviders
```

`getProviders()` caches the set; `resetProviders()` clears cache when Settings toggles mode.

### 4.5 `mock/index.ts` — what mock returns

| Method | Source of truth | Notes |
|--------|-----------------|-------|
| `getHealth()` | Tries `probeHealth()` first; if unreachable, uses `services` fixture | Still `advisory: true` |
| `getFleet()` | `agents` array in `data.ts` | Forces `total: 20` |
| `getSigning()` | `manualControl.signingHalted` + `signingAudit` | Always `mode: "in_process"` |
| `getSecurity()` | `securityPosture` + portfolio kill flags | `live: false` |
| `getPortfolio()` | `portfolio` object | Fixture equity |
| `getPipelines()` | `pipelinesCatalog` | `maxFundedHealthy: 4`, `dexOnly: true` |
| `getManualControl()` | `manualControl` + safety service rows | `quantumEnabled: false`, `agentCount: 20` |

### 4.6 `live/index.ts` — what live *attempts*

| Method | HTTP call | Honest status |
|--------|-----------|---------------|
| `getHealth()` | `GET {API_BASE}/api/status/health` | **Ready to map** when `:19003` is up; soft-fail otherwise |
| `getFleet()` | `GET …/api/status/v1/fleet` | **Stub / TODO** — endpoint often missing; rejects `total ≠ 20` |
| `getSigning()` | `GET …/api/signing/v1/status` | **Partial / ready when control plane exposes it**; forces in-process |
| `getSecurity()` | via `fetchSecurityPosture()` → `/api/security/v1/status` | **Ready when `:19008` is up** |
| `getPortfolio()` | `GET …/api/portfolio/v1/summary` | **Partial** — maps some fields; DMS/evolution may stay mock |
| `getPipelines()` | `GET …/api/allocator/v1/pipelines` | **Stub / TODO** until allocator catalog exists |
| `getManualControl()` | `GET …/api/status/v1/control` | **Partial** — maps halt/kill/profile fields when present |

`VITE_API_BASE` (optional) prefixes all paths. Empty = same-origin relative `/api/*` (preferred).

### 4.7 `context.tsx` — React hooks pages should use

| Hook | Provider method |
|------|-----------------|
| `useHealth()` | `getHealth` |
| `useFleet()` | `getFleet` |
| `useSigning()` | `getSigning` |
| `useSecurityProvider()` | `getSecurity` |
| `usePortfolioProvider()` | `getPortfolio` |
| `usePipelinesProvider()` | `getPipelines` |
| `useManualControlProvider()` | `getManualControl` |
| `useDataMode()` | `{ mode, setMode, providers }` |

`advisoryLabel(result)` returns:

- `"…"` while loading
- `"ADVISORY · live fallback"` if `error` set
- `"ADVISORY · mock"` if mock / advisory
- `"LIVE"` only when live succeeded without advisory

### 4.8 Related files outside `providers/`

| File | Role |
|------|------|
| `web/src/lib/data.ts` | Huge fixture library + `probeHealth()` |
| `web/src/lib/auth.ts` | Session HMAC → `X-Titan-Auth` header |
| `web/src/lib/securityApi.ts` | Live security GET/POST helpers |
| `web/src/lib/manualControlApi.ts` | Manual Control mutating calls (HMAC / demo) |
| `web/src/pages/Settings.tsx` | Mode toggle + HMAC form |

---

## 5. How mode switching works

### Build-time vs session override

```text
┌─────────────────────────────────────────────────────────┐
│  Effective mode = sessionStorage override ?? env ?? mock │
└─────────────────────────────────────────────────────────┘

  Settings → Mock / Live
       │
       ▼
  sessionStorage["titan.dataMode"] = "mock" | "live"
       │  (tab lifetime only — NOT localStorage, NOT disk)
       ▼
  resetProviders() + React re-render
       │
       ▼
  createProviders({ mode }) → mockProviders | liveProviders
```

### What Settings actually does

From `Settings.tsx` + `mode.ts` + `context.tsx`:

1. **Env default** is shown as `VITE_DATA_MODE=…` (whatever was baked at build / loaded by Vite for `npm run dev`).
2. Clicking **Mock** or **Live** calls `setMode(next)` → writes `sessionStorage`, resets provider singleton, updates React state.
3. UI text: *“session override (not persisted to disk)”*.
4. Closing the tab clears the override (sessionStorage). Next visit falls back to env again.

> **Note:** `web/README.md` says the Settings toggle “Does not persist to disk” — that is correct. It *does* persist for the **browser tab session** via `sessionStorage`.

### Production builds bake the env

Vite replaces `import.meta.env.VITE_*` **at build time**.

- Changing `.env.production` **after** `npm run build` does nothing until you rebuild.
- A production bundle built with `VITE_DATA_MODE=mock` stays mock until rebuild **or** until an operator uses Settings → Live (session override still works at runtime because mode resolution reads sessionStorage first).

### Dev server env

For `npm run dev`, put vars in `web/.env` or `web/.env.local`:

```bash
VITE_DATA_MODE=mock
# VITE_API_BASE=
```

Restart Vite after changing env files.

---

## 6. Environment variables

Declared in `web/src/vite-env.d.ts`:

| Variable | Values | Default | Purpose |
|----------|--------|---------|---------|
| `VITE_DATA_MODE` | `mock` \| `live` | `mock` | Which provider set to use (unless session override) |
| `VITE_API_BASE` | URL string or empty | empty | Absolute API origin; empty = same-origin `/api/*` |

### Recommended files (inside `web/`)

| File | When |
|------|------|
| `.env` | Shared local defaults |
| `.env.local` | Machine-specific (prefer gitignore; never commit secrets) |
| `.env.production` | Applied during `npm run build` |

### Example `web/.env.local` for live development

```bash
VITE_DATA_MODE=live
# Leave empty to use Vite proxy on same origin:
# VITE_API_BASE=
```

### Example `web/.env.production` for production UI intent

```bash
VITE_DATA_MODE=live
# Prefer empty behind nginx/Caddy same-origin proxy:
VITE_API_BASE=
```

> **Never** put private keys, wallet seeds, Trezor PINs, or `control_plane.secret` into `VITE_*` variables. Anything `VITE_` is embedded into the JavaScript bundle and is visible to anyone who can load the UI.

HMAC tokens belong in **sessionStorage** via Settings (see §13), not in env files committed to git.

---

## 7. Vite proxy map (full table)

Source of truth: `web/vite.config.ts`.

In **development**, the browser calls relative paths like `/api/status/health`. Vite’s dev server **proxies** them to local safety ports and **rewrites** (strips) the prefix.

| UI path prefix | Target | Rewrite | Upstream example |
|----------------|--------|---------|------------------|
| `/api/risk` | `http://127.0.0.1:19001` | strip `/api/risk` | `/api/risk/health` → `:19001/health` |
| `/api/recon` | `http://127.0.0.1:19002` | strip `/api/recon` | → `:19002/...` |
| `/api/status` | `http://127.0.0.1:19003` | strip `/api/status` | `/api/status/health` → `:19003/health` |
| `/api/portfolio` | `http://127.0.0.1:19004` | strip `/api/portfolio` | → `:19004/...` |
| `/api/dms` | `http://127.0.0.1:19005` | strip `/api/dms` | → `:19005/...` |
| `/api/allocator` | `http://127.0.0.1:19006` | strip `/api/allocator` | → `:19006/...` |
| `/api/tca` | `http://127.0.0.1:19007` | strip `/api/tca` | → `:19007/...` |
| `/api/security` | `http://127.0.0.1:19008` | strip `/api/security` | `/api/security/v1/status` → `:19008/v1/status` |
| `/api/signing` | `http://127.0.0.1:19003` | strip `/api/signing` | Control-plane halt status (in-process signing) |
| `/api/sign` | `http://127.0.0.1:19010` | strip `/api/sign` | **Optional legacy** HTTP signing_node — **not required** |

### Why a proxy exists (CORS + same-origin)

**CORS** (Cross-Origin Resource Sharing) is a browser security rule: a page at `http://127.0.0.1:5173` cannot freely call `http://127.0.0.1:19003` unless the API sends special headers.

The Vite proxy makes the browser think everything is **same-origin** (`5173` talks to `5173/api/...`), while Vite secretly forwards to `:1900x`. That avoids CORS pain in development.

In production, your **reverse proxy** (nginx/Caddy) must do the same job.

### Safety service ports (remember)

| Port | Service |
|------|---------|
| `:19001` | Risk kernel (authoritative DENY) |
| `:19002` | Reconciliation |
| `:19003` | Status aggregator (+ signing status path) |
| `:19004` | Portfolio risk |
| `:19005` | Dead-man's switch |
| `:19006` | Allocator |
| `:19007` | TCA |
| `:19008` | Security Ops |
| `:19010` | Optional legacy signing HTTP — **not on hot path** |

Signing execution is **in-process** inside `titan-safety` (`titan-safety gate sign`). No separate `:19010` daemon is required for a healthy stack.

---

## 8. Step-by-step: local mock first

Do this before chasing live APIs. Prove the SPA loads.

### Step 1 — Prerequisites

```bash
node -v   # want v20+
npm -v
```

If missing, install Node 20+ (see `WEB_UI_LIVE_PRODUCTION_GUIDE.md` §4).

### Step 2 — Install dependencies

```bash
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy/web"
# Prefer lockfile:
npm ci
# Fallback if needed:
# npm install
```

### Step 3 — Ensure mock mode

Create or edit `web/.env.local`:

```bash
VITE_DATA_MODE=mock
```

### Step 4 — Start the dev server

```bash
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy/web"
npm run dev
```

Open: **http://127.0.0.1:5173**

### Step 5 — Verify mock behavior

1. Go to **Settings → Data providers**.
2. Confirm **Mock** is active (or click Mock).
3. Open **Health & Verify** — you should see advisory / fixture-style health (or a probe if something happens to answer on `:19003`).
4. Open **Agent Manager** — fleet size **20**, no quantum agents.
5. Look for advisory chips (`ADVISORY · mock`).

### Step 6 — Stop

`Ctrl+C` in the terminal.

> **Success criteria for §8:** UI loads, navigation works, Settings mode toggle works, fleet shows 20 classical agents. You have **not** enabled capital trading.

---

## 9. Step-by-step: enable live mode for development

### Step 1 — Start (or confirm) safety services

Live mode is only meaningful if something listens on the ports. On TITANHOME, that is typically systemd units for `titan-safety` components. Minimum useful set for UI live:

```bash
# From the host — adjust unit names to your install
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:19003/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:19008/v1/status
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:19001/health
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:19004/health
```

Expect `200` when up. `000` / connection refused = service down → live providers will soft-fail.

### Step 2 — Point the UI at live providers

**Option A — Settings (fastest for learning):**

1. `npm run dev`
2. Settings → Data providers → **Live**
3. Watch toast: `Data mode → LIVE (API stubs)`

**Option B — Env (survives tab close):**

```bash
# web/.env.local
VITE_DATA_MODE=live
```

Restart Vite.

### Step 3 — Confirm proxy path works

With Vite running:

```bash
curl -sS http://127.0.0.1:5173/api/status/health | head
curl -sS http://127.0.0.1:5173/api/security/v1/status | head
```

If direct `:19003` works but `/api/status/...` fails, the proxy config is wrong (should not happen with stock `vite.config.ts`).

### Step 4 — Read advisory labels honestly

| What you see | Interpretation |
|--------------|----------------|
| `LIVE` on Health / Security | Live fetch succeeded; `advisory: false` |
| `ADVISORY · live fallback` | Live path ran but soft-failed; showing fixture + error |
| `ADVISORY · mock` | Still in mock mode |

### Step 5 — Optional absolute API base

Only if you deliberately serve APIs on another origin (usually **avoid** — CORS hell):

```bash
VITE_API_BASE=https://cockpit.example.ts.net
```

Prefer empty `VITE_API_BASE` + same-origin reverse proxy.

> **Reminder:** Live UI data ≠ live capital. Do not change `capital_profile` or run Phase 5 ceremonies from this section.

---

## 10. Step-by-step: implement / wire each live provider

This section is for developers extending the cockpit. Be honest: several endpoints are **stubs** until backends exist. Do **not** invent fake “success” backends in the UI.

### General recipe (from `web/README.md`)

1. Add or extend a DTO in `types.ts`.
2. Implement `getX()` on **mock** (fixtures from `data.ts`) and **live** (`fetchJson` + map + soft-fail).
3. Export a hook from `context.tsx`.
4. Prefer the hook in the page; keep `data.ts` for charts / static labels if needed.
5. Show `advisoryLabel(result)` so operators never confuse fixtures with live capital.

### 10.1 Health — mostly ready

**UI call:** `GET /api/status/health` → `:19003/health`

**Expected JSON (as mapped today):**

```json
{
  "status": "ok",
  "services": {
    "risk_kernel": { "status": "ok" },
    "reconciliation": { "status": "ok" },
    "status_agg": { "status": "ok" },
    "portfolio_risk": { "status": "ok" },
    "dead_mans_switch": { "status": "ok" },
    "allocator": { "status": "ok" },
    "tca": { "status": "ok" },
    "security_ops": { "status": "ok" }
  }
}
```

**Wire checklist:**

- [ ] `:19003` returns overall + per-service map
- [ ] Keys match `SERVICE_PORT` in `live/index.ts` (19001–19008)
- [ ] In-process signing row stays informational; do not require `:19010` for PASS
- [ ] Confirm Health page shows `LIVE` when curl works

### 10.2 Fleet — stub / TODO

**UI call:** `GET /api/status/v1/fleet`

**Today:** If the endpoint is missing or `total !== 20`, live soft-fails to the mock roster.

**Backend work remaining:**

- [ ] Status aggregator (or agent registry) serves `/v1/fleet`
- [ ] Payload includes exactly **20** classical agents (no QCC/QSA/QRP)
- [ ] Fields map into `AgentDto` (`id`, `tierKey`, `runStatus`, BFT roles, …)
- [ ] UI shows `source: live`, `advisory: false` when healthy

### 10.3 Signing — partial / control-plane

**UI call:** `GET /api/signing/v1/status` → proxied to `:19003` (not `:19010`)

**Mapped fields:** `halted`, optional `audit[]`. Always forces:

- `mode: "in_process"`
- `daemonRequired: false`
- `optionalLegacyPort: 19010`

**Wire checklist:**

- [ ] Control plane exposes halt + optional audit
- [ ] Signing page never claims a mandatory HTTP signing daemon
- [ ] Mutating sign operations stay on `titan-safety gate sign` (server-side), not in the browser

### 10.4 Security — ready when `:19008` is up

**UI call:** `GET /api/security/v1/status` via `securityApi.ts`

**Mutating:** `POST /api/security/v1/lockdown` with `X-Titan-Auth` (HMAC). Prefer dry-run first.

**Wire checklist:**

- [ ] `:19008/v1/status` live
- [ ] Operator HMAC set in Settings for mutate
- [ ] Prefer `postSecurityLockdownDryRun` before execute

### 10.5 Portfolio — partial

**UI call:** `GET /api/portfolio/v1/summary`

**Mapped when present:** `equity_usd`, `available_usd`, `drawdown_pct`, `capital_profile`, `kill_active`.

**Still often from mock:** `evolutionFrozen`, `dmsHoursSinceHeartbeat`.

**Wire checklist:**

- [ ] `:19004` (or capital module) serves `/v1/summary`
- [ ] Never treat fixture equity as live capital without checking advisory/error
- [ ] Optionally extend mapping for DMS / evolution freeze from authoritative sources

### 10.6 Pipelines — stub / TODO

**UI call:** `GET /api/allocator/v1/pipelines`

**Today:** Soft-fail to `pipelinesCatalog` fixtures until allocator exposes catalog JSON.

**Wire checklist:**

- [ ] Allocator serves pipeline list
- [ ] Map into `PipelineDto[]`; keep `dexOnly: true`
- [ ] Remember catalog ≠ funded — max healthy funded lanes is policy (default 4)

### 10.7 Manual Control — partial

**UI call:** `GET /api/status/v1/control`

**Mapped when present:** `trading_halted`, `kill_active`, `signing_halted`, `capital_profile`.

Always forces classical posture: `quantumEnabled: false`, `agentCount: 20`.

Mutating actions go through `manualControlApi.ts` (HMAC / demo paths) — separate from the read provider.

---

## 11. JSON shapes / response contracts

These are the **TypeScript contracts** the UI expects after mapping. Backends may use snake_case on the wire; live adapters convert.

### ProviderResult envelope

```ts
type ProviderResult<T> = {
  data: T;
  source: "mock" | "live";
  advisory: boolean;
  error?: string;
  fetchedAt: string; // ISO 8601
};
```

### HealthSnapshot

```ts
type HealthSnapshot = {
  overall: "ok" | "degraded" | "halted" | "unreachable";
  reachable: boolean;
  services: ServiceRow[];
  optionalLegacySigning: ServiceRow; // :19010 optional
  inProcessSigning: ServiceRow;      // port null, kind in_process
};
```

### FleetSnapshot

```ts
type FleetSnapshot = {
  total: number; // must be 20 for live accept
  agents: AgentDto[];
  byStatus: Record<"UP" | "DOWN" | "DORMANT" | "IDLE", number>;
  byTier: { t1: number; t2: number; t3a: number; u: number };
  tradeVoters: { id: string; vote: string; signed: boolean; note: string }[];
  bftThreshold: string;
  authoritativeGate: string;
};
```

### Portfolio live wire (snake_case)

```json
{
  "equity_usd": 12500.0,
  "available_usd": 4200.0,
  "drawdown_pct": 1.2,
  "capital_profile": "paper",
  "kill_active": false
}
```

### Signing live wire

```json
{
  "halted": false,
  "mode": "in_process",
  "audit": [
    { "ts": "2026-07-10T00:00:00Z", "action": "sign", "code": "ALLOW", "trade": "…" }
  ]
}
```

### Security live wire (subset)

```json
{
  "overall": "HARDENED",
  "threat_level": "elevated",
  "hunt_mode": true,
  "honeypot_armed": true,
  "pcr_drift": false,
  "signing_halted": false,
  "kill_active": false,
  "evolution_frozen": false,
  "pillars": {},
  "layers": []
}
```

If your backend JSON differs, **change the mapper in `live/index.ts`**, not every page.

---

## 12. Production build + serve + reverse proxy

For full TLS / systemd detail, follow [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md). Here is the data-provider-focused path.

### Step 1 — Build with live intent

```bash
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy/web"

cat > .env.production <<'EOF'
VITE_DATA_MODE=live
VITE_API_BASE=
EOF

npm ci
npm run build
# Output: web/dist/
```

### Step 2 — Understand what `dist/` is

**`dist/`** = compiled static assets (HTML, JS, CSS). There is **no** Vite proxy inside `dist/`. Production **must** put a reverse proxy in front that mirrors `vite.config.ts`.

### Step 3 — Serve static files + proxy `/api/*`

**Caddy sketch** (prefix strip via `handle_path`):

```caddy
# See WEB_UI_LIVE_PRODUCTION_GUIDE.md for full unit + TLS
handle_path /api/status* {
    reverse_proxy 127.0.0.1:19003
}
handle_path /api/security* {
    reverse_proxy 127.0.0.1:19008
}
handle_path /api/portfolio* {
    reverse_proxy 127.0.0.1:19004
}
handle_path /api/allocator* {
    reverse_proxy 127.0.0.1:19006
}
handle_path /api/signing* {
    reverse_proxy 127.0.0.1:19003
}
# … risk, recon, dms, tca, optional /api/sign → :19010
```

**nginx sketch** (trailing slash on `proxy_pass` strips prefix):

```nginx
location /api/status/ {
    proxy_pass http://127.0.0.1:19003/;
}
location /api/security/ {
    proxy_pass http://127.0.0.1:19008/;
}
# … mirror vite.config.ts for all prefixes
```

### Step 4 — SPA fallback

Single-page apps need unknown paths to return `index.html`:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

### Step 5 — Access safely

Do **not** expose the cockpit raw on the public internet without auth.

Recommended:

1. Tailscale Serve
2. SSH tunnel: `ssh -L 5173:127.0.0.1:5173 user@titan-host`
3. Cloudflare Tunnel / reverse proxy with SSO in front

### Step 6 — Verify production live providers

```bash
curl -sS http://127.0.0.1:8080/api/status/health
curl -sS http://127.0.0.1:8080/api/security/v1/status
```

Then open the UI, confirm Settings mode / advisory chips, and compare numbers to curl.

> **`vite preview` note:** `npm run preview` serves `dist/` but does **not** automatically include the full production reverse-proxy story. Prefer nginx/Caddy for real TITANHOME production.

---

## 13. Auth: HMAC, what the browser can hold

### What HMAC means here

**HMAC** (Hash-based Message Authentication Code) in this cockpit context is an **operator shared secret** sent as HTTP header:

```http
X-Titan-Auth: <token from Settings>
```

Mutating control-plane POSTs (lockdown execute, some Manual Control actions) return **401** without it when `control_plane.auth_required: true`.

### Where the token lives

| Storage | Key | Lifetime |
|---------|-----|----------|
| `sessionStorage` | `titan-hmac-token` | Until tab closes |
| Code | `web/src/lib/auth.ts` | `getHmacToken` / `setHmacToken` / `authHeaders()` |

Settings → **Control-plane HMAC** → Save session.

### What the browser **can** hold

- Operator HMAC token (session only) for control-plane mutate
- UI prefs (`localStorage` cockpit drafts, theme)
- Data mode session override (`titan.dataMode`)

### What the browser **must never** hold

- Hot wallet private keys / seed phrases
- Trezor PINs / passphrases
- Long-lived production secrets in `VITE_*` env
- Anything that could blind-sign trades

Signing is **server-side in-process** after ExecutionGate ALLOW. The UI may request halt status; it must not become a signer.

### Advisory badges

Always trust:

1. `advisoryLabel` on provider-backed pages
2. Direct `curl` to safety ports
3. Risk kernel DENY as authoritative for capital

Ignore “green looking” fixture dashboards when `ADVISORY` is showing.

---

## 14. Checklist: page-by-page fixtures vs providers

### Migrated to providers (hooks)

| Route | Page | Provider hook(s) | Still also uses `data.ts`? |
|-------|------|------------------|----------------------------|
| `/` | Dashboard | `useHealth`, `usePortfolioProvider` | Yes — charts / extras |
| `/health` | Health & Verify | `useHealth` | Yes — verify checklist fixture |
| `/agent-manager` | Agent Manager | `useFleet` | Yes — alerts / labels |
| `/manual-control` | Manual Control | `useManualControlProvider` | Yes — rich demo controls |
| `/signing` | Signing | `useSigning` | Minimal |
| `/security` | Security Ops | `useSecurityProvider` | Yes — pillar copy / events |
| `/pipelines` | Pipelines | `usePipelinesProvider` | Yes — fallback catalog import |
| `/settings` | Settings | `useDataMode` | Mode + HMAC UI |

### Still primarily fixtures / localStorage (honest)

| Route | Page | Data source today |
|-------|------|-------------------|
| `/command` | Command Center | `portfolio` fixture + local demos |
| `/capital` | Capital & Wallets | `data.ts` ledger / wallets |
| `/wallets` | Wallet Tracker | fixtures + localStorage watchlist |
| `/pnl` | PnL | fixtures / charts |
| `/risk` | Risk & CBs | fixtures (kernel live path separate) |
| `/dms` | Dead Man's Switch | fixtures |
| `/power` | Power & UPS | fixtures |
| `/ops` | Ops Center | fixtures |
| `/tca` | TCA & Allocator | fixtures |
| `/promotions` | Promotions | fixtures |
| `/edge` | Edge Mesh | fixtures |
| `/latency` | Latency | fixtures |
| `/qi-optimizer` | QI Optimizer | fixtures; **advisory only** |
| `/flash-loans` | Flash Loans | fixtures; live gated elsewhere |
| `/memecoin` | Memecoin Trench | fixtures; Phase 5 gated |
| `/automations` | Automations | fixtures |
| `/crypto-twitter` | Crypto Twitter | fixtures |
| `/crypto-news` | Crypto News | fixtures |
| `/goals` | Goals Lab | fixtures |
| `/identity` | Identity | fixtures |
| `/models` | Model Tiers | fixtures |
| `/ai-log` | AI Log | fixtures |
| `/decisions` | Decision Log | fixtures |
| `/questions` | Questions | fixtures |
| `/skills` | Skill Factory | fixtures |
| `/agents` | Agent Teams | fixtures (`agents`) |
| `/workspace` | Workspace | fixtures |
| `/reports` | Reports | fixtures |
| `/forge` | Forge | fixtures |

**SaveBar** always writes **browser localStorage** — never the live API.

---

## 15. Troubleshooting

### Blank / empty looking data

1. Open browser DevTools → Network. Do `/api/...` calls appear?
2. Check Settings mode: mock vs live.
3. Check advisory chip — soft-fail may show fixtures that look “fine” but stale.
4. `curl` the upstream port directly.

### 502 Bad Gateway

Proxy is up; upstream is down or crashing.

```bash
curl -v http://127.0.0.1:19003/health
journalctl -u titan-status-agg -n 50   # unit name may differ
```

Fix the safety service, not the React code.

### CORS errors in the console

You pointed the browser at a **different origin** without CORS headers (often `VITE_API_BASE` misuse).

**Fix:** Set `VITE_API_BASE=` empty and use same-origin Vite/nginx proxy.

### Wrong mode baked into production build

Symptom: always mock after deploy, Settings shows env `mock`.

```bash
# Rebuild after editing web/.env.production
cd web && npm run build
```

Or use Settings → Live for a session override without rebuild.

### Live mode but always `ADVISORY · live fallback`

Endpoint missing or JSON shape wrong. Check `error` string in React state / network response. For fleet, confirm `total === 20`.

### Health green but capital still paper

Expected. UI health ≠ capital profile. See `LIVE_CAPITAL_PRODUCTION_GUIDE.md`.

### HMAC 401 on mutate

Settings → paste operator token → Save session. Confirm header `X-Titan-Auth` on the POST.

### Preview works but `/api` 404

`vite preview` / static server without reverse proxy. Add nginx/Caddy map from §12.

---

## 16. Security rules for the frontend

1. **Never** put private keys or signing material in the frontend bundle.
2. Treat all UI numbers as **advisory** until soft-fail errors are gone and curls match.
3. HMAC in sessionStorage is for **control-plane mutate**, not for trading signatures.
4. Do not expose `0.0.0.0` cockpit ports to the public internet without Tailscale/SSO/auth.
5. Lockdown execute: prefer dry-run; require HMAC + human YES patterns in Manual Control.
6. Signing: in-process on TITANHOME; Mac Mini vault = metadata + Trezor ceremonies — not hot-path browser signing.
7. Classical-only: do not reintroduce quantum agents into fleet payloads.
8. UI live ≠ Phase 5 capital live. Separate ceremonies, separate docs.

---

## 17. Glossary

| Term | Beginner definition |
|------|---------------------|
| **SPA** | Single-Page Application — one HTML shell; React swaps views without full page reloads |
| **Vite** | Frontend build tool + dev server used by `web/` |
| **dist** | Production build output folder (`web/dist/`) |
| **Env / environment variable** | Config value injected at build/dev time (`VITE_*`) |
| **Provider** | Adapter that supplies a typed snapshot (mock or live) |
| **Fixture** | Checked-in sample data (`data.ts`) |
| **Mock mode** | Providers return fixtures; always advisory |
| **Live mode** | Providers call `/api/*`; soft-fail to fixtures on error |
| **Soft-fail** | Return fallback data + error instead of crashing the UI |
| **Proxy** | Middleman that forwards `/api/foo` to `127.0.0.1:1900x` |
| **Reverse proxy** | Production proxy (nginx/Caddy) in front of static UI + APIs |
| **CORS** | Browser rule blocking cross-origin fetches without permission headers |
| **HMAC** | Shared secret proving the operator is allowed to mutate control plane |
| **sessionStorage** | Browser storage cleared when the tab closes |
| **localStorage** | Browser storage that persists across visits (prefs only — not live API) |
| **DTO** | Data Transfer Object — typed shape crossing API → UI |
| **Advisory** | Non-authoritative; do not treat as live capital truth |
| **Risk kernel** | Out-of-process service on `:19001` that can DENY trades |
| **In-process signing** | Signing inside `titan-safety` after gate ALLOW — no required `:19010` |
| **Phase 5 YES** | Explicit human approval for live capital promotion — not a UI toggle |

---

## Appendix A — Route map

From `web/src/App.tsx`:

| Path | Page |
|------|------|
| `/` | Dashboard |
| `/command` | Command Center |
| `/manual-control` | Manual Control |
| `/capital` | Capital & Wallets |
| `/wallets` | Wallet Tracker |
| `/pnl` | PnL |
| `/risk` | Risk & CBs |
| `/dms` | Dead Man's Switch |
| `/security` | Security Ops |
| `/forge` | Forge |
| `/health` | Health & Verify |
| `/power` | Power & UPS |
| `/ops` | Ops Center |
| `/tca` | TCA & Allocator |
| `/pipelines` | Pipelines |
| `/promotions` | Promotions |
| `/edge` | Edge Mesh |
| `/latency` | Latency |
| `/qi-optimizer` | QI Optimizer (advisory) |
| `/flash-loans` | Flash Loans |
| `/memecoin` | Memecoin Trench |
| `/signing` | Signing |
| `/automations` | Automations |
| `/crypto-twitter` | Crypto Twitter |
| `/crypto-news` | Crypto News |
| `/goals` | Goals Lab |
| `/identity` | Identity |
| `/models` | Model Tiers |
| `/ai-log` | AI Log |
| `/decisions` | Decision Log |
| `/questions` | Questions |
| `/skills` | Skill Factory |
| `/agents` | Agent Teams |
| `/agent-manager` | Agent Manager |
| `/workspace` | Workspace |
| `/reports` | Reports |
| `/settings` | Settings |

---

## Appendix B — Honest stub vs ready matrix

| Live provider | Endpoint attempted | Status | Notes |
|---------------|-------------------|--------|-------|
| `getHealth()` | `/api/status/health` | **Ready when `:19003` up** | Mapping implemented |
| `getSecurity()` | `/api/security/v1/status` | **Ready when `:19008` up** | Mutate needs HMAC |
| `getSigning()` | `/api/signing/v1/status` | **Partial / ready if control plane serves it** | Always in-process |
| `getPortfolio()` | `/api/portfolio/v1/summary` | **Partial** | Some fields still mock |
| `getManualControl()` | `/api/status/v1/control` | **Partial** | Halt/kill/profile only |
| `getFleet()` | `/api/status/v1/fleet` | **Stub / TODO** | Soft-fail until registry; must be 20 agents |
| `getPipelines()` | `/api/allocator/v1/pipelines` | **Stub / TODO** | Soft-fail until allocator catalog |

Pages not listed in the provider hooks table (§14) remain **fixture-first**.

---

## Appendix C — Copy-paste command cheatsheet

```bash
# --- Mock local ---
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy/web"
npm ci
echo 'VITE_DATA_MODE=mock' > .env.local
npm run dev
# open http://127.0.0.1:5173

# --- Live local (after safety units up) ---
echo 'VITE_DATA_MODE=live' > .env.local
npm run dev
curl -sS http://127.0.0.1:5173/api/status/health
curl -sS http://127.0.0.1:5173/api/security/v1/status

# --- Direct backend probes ---
curl -sS http://127.0.0.1:19001/health
curl -sS http://127.0.0.1:19002/health
curl -sS http://127.0.0.1:19003/health
curl -sS http://127.0.0.1:19004/health
curl -sS http://127.0.0.1:19005/health
curl -sS http://127.0.0.1:19006/health
curl -sS http://127.0.0.1:19007/health
curl -sS http://127.0.0.1:19008/v1/status

# --- Production build ---
cat > .env.production <<'EOF'
VITE_DATA_MODE=live
VITE_API_BASE=
EOF
npm run build
ls -la dist/
```

---

*Accuracy over marketing. This guide documents the repo as shipped — stubs, soft-fail, and TODOs included. UI live data is not live capital.*
