# TITAN CURRENT — Titan Agentik System State (July 2026)

> **What this document is:** A comprehensive, long-form snapshot of **Titan Agentik** as deployed from this repository in **July 2026** — architecture, operator surfaces, safety posture, recent evolution, and go-live path.  
> **What this document is not:** A replacement for immutable constitutions (`SOUL.md`, `iron-laws.md`) or the enforceable agent protocol (`AGENTS.md` / `TOOLS.md`).  
> **Historical reference:** `source/TITAN.md` (June 2026) describes an earlier catalog posture (23 agents, quantum agents, Phase 5 removed, mandatory `:19010`). **This file is the current truth for operator-facing evolution.**

**Operator contact:** [titan.agentik@protonmail.com](mailto:titan.agentik@protonmail.com)

**Companion docs (read next):**

| Document | Role |
|----------|------|
| [`SYSTEM.md`](./SYSTEM.md) | Primary system manual — ports, agents, CLI, bounded autonomy |
| [`TELEGRAM_OPS_GUIDE.md`](./TELEGRAM_OPS_GUIDE.md) | Production operator surface (HERALD) |
| [`HONCHO_SETUP.md`](./HONCHO_SETUP.md) | Dialectic operator modeling |
| [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) | Paper → shadow → Phase 5 YES → live capital |
| [`TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md`](./TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md) | End-to-end hardware + software setup |
| [`BOOT.md`](./BOOT.md) | Gateway restart checklist |
| [`BOOTSTRAP.md`](./BOOTSTRAP.md) | First-run ritual |
| [`docs/MEMORY_AND_EXTRACTORS.md`](./docs/MEMORY_AND_EXTRACTORS.md) | Extractor contract, memory layout, shadow evolution boundary |

---

## Table of contents

1. [Executive summary — what Titan is now](#1-executive-summary--what-titan-is-now)
2. [Architecture overview](#2-architecture-overview)
3. [20-agent fleet and model tiers](#3-20-agent-fleet-and-model-tiers)
4. [Edge mesh and execution path](#4-edge-mesh-and-execution-path)
5. [In-process signing (no mandatory :19010)](#5-in-process-signing-no-mandatory-19010)
6. [Operator surface — Telegram primary](#6-operator-surface--telegram-primary)
7. [Institutional Telegram + Financial Summary / PnL](#7-institutional-telegram--financial-summary--pnl)
8. [Honcho dialectic operator modeling](#8-honcho-dialectic-operator-modeling)
9. [Web cockpit — local dev vs archive](#9-web-cockpit--local-dev-vs-archive)
10. [Flash loans — autonomous live path](#10-flash-loans--autonomous-live-path)
11. [Live capital path and blockers](#11-live-capital-path-and-blockers)
12. [Bounded autonomy matrix (July 2026)](#12-bounded-autonomy-matrix-july-2026)
13. [Security four pillars + ghost evasion](#13-security-four-pillars--ghost-evasion)
14. [Safety services and ports](#14-safety-services-and-ports)
15. [CLI reference](#15-cli-reference)
16. [Deploy and go-live checklist](#16-deploy-and-go-live-checklist)
17. [Daily operator routine](#17-daily-operator-routine)
18. [What changed from source/TITAN.md](#18-what-changed-from-sourcetitanmd)
19. [Beginner sections](#19-beginner-sections)
20. [Appendix A — commit changelog](#appendix-a--commit-changelog)
21. [Appendix B — glossary](#appendix-b--glossary)
22. [Appendix C — specialized guide index](#appendix-c--specialized-guide-index)

---

## 1. Executive summary — what Titan is now

**Titan Agentik** (the Titan) is a **local-first, capital-preservation-first** crypto trading control plane built on **OpenClaw** (nervous system) + **Hermes Agent** (cognitive runtime). It runs on operator-owned hardware with **all inference local** on the live path — no closed/cloud models on TRENCH-OPS, GUARDIAN, or execution-critical votes.

### July 2026 at a glance

| Dimension | Current state |
|-----------|---------------|
| **Agents** | **20** classical LLM agents + **5** stateless edge workers (no LLM on edge) |
| **Quantum** | **Removed** — QCC/QSA/QRP agents deleted; `quantum.enabled: false`; classical-only live path |
| **Signing** | **In-process** `titan_safety.SigningNode` inside `titan-safety` after ExecutionGate ALLOW; legacy HTTP `:19010` optional only |
| **Operator surface (production)** | **Telegram via HERALD** — institutional alerts, PnL, capital commands |
| **Operator modeling** | **Honcho** dialectic memory for HERALD + HYPERION (advisory context only) |
| **Web UI** | **`web/`** restored for **local dev / reference**; frozen backup at `archive/cockpit-web/` |
| **Flash loans** | **Autonomous** when `flash_loan_live.enabled` + `flashLoanRouter.enabled` — **no human YES**; kernel still DENY-authoritative |
| **Phase 5 live capital** | **Human YES still required** — TIMEOUT = HOLD/de-risk, never auto-promote |
| **Contact** | **titan.agentik@protonmail.com** |
| **Compute** | TITANHOME (Threadripper PRO 9995WX, 2× RTX PRO 6000 96 GB) + TITANSPARK (GB10 utility) |
| **Models (live)** | Tier 1 `:30000` Qwen3-30B-A3B FP8; Tier 2 `:30001` Qwen3-Coder-80B; Utility `:30002` Qwen3-30B-A3B-Instruct-2507 FP4 |

### What Titan does

- Runs twenty specialized AI agents that **propose** trades, debate risk, and orchestrate DeFi operations.
- Enforces every live order through an **out-of-process risk kernel** (`:19001`) and **ExecutionGate** with fresh `X-Titan-Gate-Receipt`.
- Signs transactions only via **in-process SigningNode** after gate ALLOW — never inside the LLM runtime.
- Broadcasts via a **5-PoP global edge mesh** (Tokyo, Singapore, Frankfurt, N. Virginia, Amsterdam) for sub-millisecond RTT to target venues.
- Notifies the operator through **institutional-grade Telegram** messages with severity, timestamps, Financial Summary blocks, and action-required fields.
- Models operator preferences via **Honcho** for HERALD/HYPERION — without bypassing safety gates.

### What Titan does not do

- Auto-promote strategies on calendar timeout or operator silence.
- Let any LLM override risk kernel **DENY**.
- Use public RPC pools or unshielded CEX-direct venues on live capital.
- Require a separate `:19010` signing daemon on the hot path (default).
- Treat a green web cockpit or `VITE_DATA_MODE=live` as authorization for real capital.
- Enable every pipeline in the catalog — **catalog ≠ checklist**; allocator funds ≤4 HEALTHY lanes by default.

### Mental model (one diagram)

```text
Hyperion (Telegram + Honcho context + Phase 5 YES gates)
        │
        ▼
20 Agents propose ──► BFT 2-of-3 votes (advisory: AUGUR + PREDATOR + ATLAS)
        │
        ▼
ExecutionGate ──► recon :19002 ──► kernel :19001 ──► portfolio :19004
        │
        │ ALLOW + X-Titan-Gate-Receipt (~10s max age)
        ▼
titan-safety SigningNode (in-process on TITANHOME)
        │
        ▼
Edge PoP (FRA/TKY/SIN/USE/AMS) ──► MEV-shielded DEX / Jito / Flashbots / intents
        │
        ▼
HERALD ──► Telegram (institutional alerts + PnL + digests)
```

**Authoritative layer:** Risk kernel DENY wins over every agent vote, Honcho conclusion, and Telegram command.

---

## 2. Architecture overview

### Framework stack

| Layer | Technology | Role |
|-------|------------|------|
| **Runtime** | OpenClaw gateway `:18789` | Agent orchestration, Telegram ingress, NATS |
| **Cognition** | Hermes Agent + local llama-server / SGLang | Multi-agent reasoning on local GPUs |
| **Safety** | `titan-safety` Python stack `:19001`–`:19008` | Fail-closed enforcement — kernel, gate, recon, DMS |
| **Signing** | `titan_safety.SigningNode` (in-process) | EIP-712 / calldata signing after gate receipt |
| **Edge** | Stateless workers `:19100` per PoP | Broadcast, latency-faithful routing |
| **Memory** | Honcho (operator) + Memanto/decision log (trading) | Cross-session operator modeling + trade audit |
| **Operator** | HERALD (Telegram) + optional `web/` (local) | Production notify-only + dev instrument panel |

### Node topology

| Node | Role | Key services |
|------|------|--------------|
| **TITANHOME** | Primary brain | Inference `:30000`/`:30001`, safety `:19001`–`:19008`, in-process signing, OpenClaw gateway |
| **TITANSPARK** | Utility inference | SGLang `:30002` — HERALD, NEXUS, FORGE, ALCHEMY, ATLAS, QUANT, ARBITER, HORIZON |
| **Mac Mini vault** | Key metadata + Trezor ceremonies | Weekly profit sweeps; **does not** execute hot-path signing |
| **EDGE-FRA** | Frankfurt bare metal | Erigon archive, Jito-FRA, ETH builders, Telegram relay |
| **EDGE-TKY** | AWS `ap-northeast-1` | Hyperliquid DEX, Jito-TKY |
| **EDGE-SIN** | AWS `ap-southeast-1` | BSC DEX, PancakeSwap, Sui |
| **EDGE-USE** | AWS `us-east-1` | L2 sequencers, Flashbots Protect |
| **EDGE-AMS** | Amsterdam bare metal | Solana gRPC redundancy, Nostr, bridges |

Specs: `templates/infra/hardware_bom.yaml`, `edge_mesh.yaml`, `power_requirements.yaml`, `signing_node.yaml`.

### Classical-only posture

Quantum-coordination agents **QCC**, **QSA**, and **QRP** were removed from the agent catalog. The QI Optimizer remains as **classical simulated annealing only** (`advisory_only`, `live_path=false`) — it is not a quantum agent.

```yaml
# policy.yaml excerpt
quantum:
  enabled: false
  note: "Classical-only — quantum agents removed"
```

Randomness for live operations uses OS CSPRNG. REVM simulation runs on `:30020` (classical EVM sim, not quantum dispatch).

---

## 3. 20-agent fleet and model tiers

### Agent count

| Category | Count | Hosting |
|----------|-------|---------|
| Orchestrator / risk / security | 4 | TITANHOME Tier 1–2 |
| Signal / on-chain / macro | 5 | TITANHOME Tier 1 `:30000` |
| Coding / execution / research | 3 | TITANHOME Tier 1–2 / R&D Tier 3 |
| Utility | 8 | TITANSPARK `:30002` |
| Edge workers (stateless) | 5 | Cloud PoPs — no LLM |
| **Named LLM agents** | **20** | — |

### Model tier table (July 2026)

| Tier | Port | Host / GPU | Model | Role |
|------|------|------------|-------|------|
| **1 Critical** | `:30000` | TITANHOME GPU 0 | **Qwen3-30B-A3B FP8** | ORACLE, WRAITH, PREDATOR, AUGUR, NARRATIVE, GUARDIAN, TRENCH-OPS |
| **2 Reasoning** | `:30001` | TITANHOME GPU 1 | **Qwen3-Coder-Next-80B** | ARCHON, SENTINEL, LAMARCK, orchestration |
| **3a R&D** | `:30005` | Off-peak offload | DeepSeek V4 Pro | CORTEX deep votes (preferred); never live critical path |
| **3b R&D** | `:30003` | Off-peak offload | GLM-5.2 | Secondary R&D only |
| **Utility** | `:30002` | **TITANSPARK** | **Qwen3-30B-A3B-Instruct-2507 FP4** | HERALD, NEXUS, FORGE, ALCHEMY, ATLAS, QUANT, ARBITER, HORIZON |
| **Embedder** | `:30004` | TITANHOME | Qwen3-Embedding-8B | Memory / retrieval |
| **Reranker** | cuda:0 ride-along | TITANHOME | Qwen3-Reranker-0.6B | Retrieval quality |
| **REVM sim** | `:30020` | TITANHOME | Classical EVM sim | Pre-trade simulation |

**Constraints:** No closed/cloud models on the live path. TRENCH-OPS / GUARDIAN / EXECUTOR stay on Tier 1/2 only.

### Agent roster

| Agent | Tier | Role |
|-------|------|------|
| **HYPERION** | Operator interface | Reporting / NATS off-critical path; Honcho peer `hyperion-assistant` |
| **ARCHON** | Tier 2 | Orchestrator + A2A coordinator |
| **CORTEX** | `:30005` → fallback `:30001` | Meta-cognitive / GEPA / PRM judge |
| **GUARDIAN** | Tier 1 | Risk validation / Kelly sizing (critical path) |
| **SENTINEL** | Tier 2 | Security audit / CodeQL / TPM PCR drift |
| **ORACLE** | Tier 1 | Signal generation (classical-only, 108+ signals) |
| **WRAITH** | Tier 1 | On-chain analysis |
| **PREDATOR** | Tier 1 | Scanner / mempool / stalking / P22 filter |
| **AUGUR** | Tier 1 | Macro regime detection |
| **NARRATIVE** | Tier 1 | Catalyst / news ingestion |
| **TRENCH-OPS** | Tier 1 | Execution + edge dispatch; signs via in-process titan-safety |
| **LAMARCK** | Tier 2 | Post-trade learning / OPD / GEPA |
| **DARWIN_GODEL** | Tier 2 / R&D | Auto-research / DGM-H (**shadow only** until YES) |
| **HERALD** | Utility `:30002` | **Telegram notifications**; Honcho peer `herald-telegram` |
| **NEXUS** | Utility | Data feeds / funding / AVS registry |
| **FORGE** | Utility | Infra / strategy-health / inference health |
| **ALCHEMY** | Utility | DeFi ops / liquidations / **flash-loan compose** |
| **ATLAS** | Utility | Portfolio / sweeps / BFT voter |
| **QUANT** | Utility | Stats / pairs / prediction-market models |
| **ARBITER** | Utility | Backtest gate / Red Team / deploy lifecycle |
| **HORIZON** | Utility | R&D metrology (observer only — cannot trade) |

### Trade BFT (advisory)

**Voters:** AUGUR + PREDATOR + ATLAS  
**Threshold:** 2-of-3 cryptographically signed pre-commitment votes  
**Authority:** Advisory only — risk kernel DENY is absolute

Orchestrator-tier heterogeneous BFT (ARCHON / CORTEX / GUARDIAN) uses distinct model families for meaningful disagreement; votes remain advisory.

### Confidence gate

| Confidence | Action | Human required |
|------------|--------|----------------|
| 0.00–0.29 | Auto-reject | No |
| 0.30–0.49 | Auto-escalate to ARCHON | No |
| 0.50–0.69 | Auto-execute at reduced size (size = confidence × target) | No |
| 0.70–1.00 | Auto-execute full size | No |

---

## 4. Edge mesh and execution path

### 5-PoP global mesh

Each edge PoP is placed in the **same AWS region/AZ** as target DEX / sequencer / builder where applicable — traffic stays on provider backbone for **sub-1ms RTT**.

| Worker | PoP | Provider / region | Primary targets |
|--------|-----|-------------------|-----------------|
| TRENCH-OPS-TKY | EDGE-TKY | AWS `c7i.metal-24xl`, `ap-northeast-1` | Hyperliquid DEX, Jito-TKY |
| TRENCH-OPS-SIN | EDGE-SIN | AWS `c7i.4xlarge`, `ap-southeast-1` | BSC DEX, PancakeSwap, Sui |
| TRENCH-OPS-FRA | EDGE-FRA | Vultr BM Frankfurt (DE-CIX) | Erigon, Jito-FRA, ETH builders, Solana-EU |
| TRENCH-OPS-USE | EDGE-USE | AWS `c7i.2xlarge`, `us-east-1` | L2 sequencers, Flashbots Protect |
| TRENCH-OPS-AMS | EDGE-AMS | Vultr BM Amsterdam (AMS-IX) | Solana gRPC redundancy, Nostr, bridges |

**Routing policy:** Lowest live p50 RTT (`edge_mesh.yaml`).  
**Dispatch path:** TRENCH-OPS → Nostr NIP-44 (Kind 1059) → edge worker → broadcast within ~3 ms.

### Trade lifecycle (end-to-end)

1. **Signal / debate** — Multi-analyst evidence pipeline (fundamentals, sentiment, news, technical) → bull/bear adversarial debate → trader decision → risk debate → GUARDIAN gate.
2. **Confidence + BFT** — Size by confidence; attach 2-of-3 votes when equity threshold requires.
3. **Stealth check** — Deny public RPC / unshielded venues (`STEALTH_*` kernel codes).
4. **Reconciliation** — Believed vs adapter positions at `:19002`; divergence → HALT.
5. **Risk kernel** — Notional, leverage, velocity, venue allow-list, kill switch, power-loss, flash-loan caps, etc. at `:19001`.
6. **Portfolio risk** — VaR/CVaR/correlation at `:19004` when wired.
7. **Gate receipt** — Binds `trade_id` + notional + venue; max age ~10 seconds.
8. **Signing** — In-process `SigningNode` rejects blind sign / missing receipt.
9. **Edge** — Route by venue/strategy; Nostr dispatch to lowest-RTT PoP.
10. **Notify** — HERALD → Telegram with institutional format + Financial Summary when applicable.

---

## 5. In-process signing (no mandatory :19010)

### July 2026 signing architecture

TRENCH-OPS and LAMARCK route all transaction signing to **in-process** `titan_safety.SigningNode` via `titan-safety gate sign`. Default `signingNode.mode: in_process` in `openclaw.json`.

| Aspect | Current | Prior (source/TITAN.md era) |
|--------|---------|----------------------------|
| Hot-path signer | `titan-safety` library on TITANHOME | Separate `:19010` HTTP daemon |
| Network hop | Zero extra hop | HTTP round-trip to signing node |
| Mac Mini vault | Key metadata + Trezor ceremonies only | Sometimes described as signing executor |
| Legacy HTTP | Optional `signing.mode=http` | Often documented as required |

```yaml
# policy.yaml
signing:
  mode: in_process
  isolated_module_required: true
  blind_sign_rejected: true
  require_gate_receipt: true
  max_receipt_age_seconds: 10
```

**Signing isolation:** Deterministic safety process only — no LLM, no evolution workloads. Logically isolated module inside `titan_safety`; not a separate daemon on the critical path.

**Every live sign requires:**

1. Fresh `X-Titan-Gate-Receipt` from ExecutionGate ALLOW
2. EIP-712 `typed_data` or explicit calldata (never blind-sign)
3. Kill switch inactive; evolution freeze respected when live capital

CLI:

```bash
titan-safety gate check --trade-json '...'
titan-safety gate sign --trade-json '...'
```

---

## 6. Operator surface — Telegram primary

### Production: HERALD on Telegram

As of commit `7eb4694` (cockpit decommission) and reaffirmed in `f285328` (web restore for dev), **Telegram is the sole production operator surface**.

| Surface | Status | Use |
|---------|--------|-----|
| **Telegram (HERALD)** | **Production** | Alerts, PnL, capital commands, promotion gates |
| **`web/` cockpit** | Local dev / reference | `npm run dev` → `http://127.0.0.1:5173` |
| **`archive/cockpit-web/`** | Frozen backup | Snapshot from decommission; prefer `web/` for dev |

**Telegram is notify-only.** It cannot override risk kernel DENY, bypass signing, or auto-promote on Phase 5 timeout.

### Quick Telegram setup

1. Create bot via [@BotFather](https://t.me/BotFather) → copy **bot token**.
2. Start chat with bot (or operator group).
3. Obtain **chat ID** (`@userinfobot` or `getUpdates`).
4. Set in `~/.openclaw/.env` (never commit):

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

5. Smoke test:

```bash
titan-safety notify test --dry-run
titan-safety notify test
```

### Telegram capital commands

| Command | Action |
|---------|--------|
| `/balance` | Equity / available / reserved |
| `/deposit <amount> <asset>` | Record deposit |
| `/withdraw <amount> <asset>` | Initiate withdrawal |
| `/sweep` | Trezor profit sweep (≥ $15K equity) |

### What replaced cockpit pages

| Old cockpit page | Telegram / CLI replacement |
|------------------|---------------------------|
| Dashboard / PnL | Hourly digest + trade fill notifications |
| Risk & CBs | `titan-safety kill status`, drawdown Telegram alerts |
| Health & Verify | `curl :19003/health`, `titan-safety notify` on failures |
| Promotions UI | `titan-safety promotion approve`, Telegram gate messages |
| Manual control | CLI + signed commands (`titan-safety kill sign`) |

Full reference: [`TELEGRAM_OPS_GUIDE.md`](./TELEGRAM_OPS_GUIDE.md).

---

## 7. Institutional Telegram + Financial Summary / PnL

Commit `f3e9eea` added **Financial Summary** and **PnL fields** to all operator Telegram alerts.

### Message template (institutional)

Every alert uses a consistent template — no emoji spam on institutional path:

```
TITAN — {Title}
Severity: {INFO|LOW|MEDIUM|HIGH|CRITICAL}
Time: {ISO8601 UTC}
Agent: {AGENT_ID}
Event: {event_type}

Description
{plain-language summary}

Financial Summary          ← when PnL/portfolio data present
Realized: +$142.88 (+0.55% equity)
Unrealized: +$156.20
Daily P&L: +$842.33 (+0.32%)
Equity: $261,042.18 | Exposure: 12.4% | Open: 7
Outcome: WIN

Details
• key: value
...

Action Required
{operator next step or "None — informational only."}

Reason codes: {CODE1, CODE2}
```

### HERALD trade format (PnL close example)

```
✅ PROFIT — P3
━━━━━━━━━━━━━━━━━━━━━━━━━━
P3 | flash_loan_arb_eth_mainnet
LONG WETH/USDC | ethereum
Entry 3,860.40 → Exit 3,891.22
P&L: +142.88 (+0.55% equity)
Fees: $5.55 | Slippage: 4.20 bps
```

### Hourly digest

```
📊 HOURLY REPORT — 2026-07-02T19:00–2026-07-02T20:00 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
P&L Hour: +127.45 (+0.05%)
P&L Daily: +842.33 (+0.32%)
Trades: 4 (W:3 L:1)
Win Rate: 75.00%
Exposure: 12.40% (7 open)
Unrealized: +156.20
Gas/Fees: $28.50
```

### CLI for PnL notifications

```bash
titan-safety notify pnl --realized 142.88 --pct-equity 0.55 --pipeline P3 --asset WETH/USDC --outcome WIN
titan-safety notify digest
titan-safety notify digest --format-only
titan-safety notify drain    # flush herald_queue.jsonl
```

### Module paths

| Component | Path |
|-----------|------|
| Institutional formatter | `templates/safety/titan_safety/telegram_notify.py` |
| HERALD trade templates | `templates/skills/herald_notify/notify.py` |
| Template files | `templates/telegram/templates/` |
| Queue file | `~/.openclaw/safety/herald_queue.jsonl` |

### Severity legend

| Severity | When used |
|----------|-----------|
| **INFO** | Routine state, successful checks |
| **LOW** | Minor advisory, non-urgent health |
| **MEDIUM** | Trade lifecycle, signing success, small PnL closes |
| **HIGH** | Denied trades, drawdown tiers, pipeline halt, material PnL |
| **CRITICAL** | Global HALT, lockdown, signing failure, Phase 5 YES prompt, UPS loss |

### Events covered

Risk kernel ALLOW/DENY, circuit breakers, trade fills, PnL realized/unrealized, signing success/fail, kill switch, agent health, security lockdown, promotion gates, Trezor sweeps, hourly digest, health verify failures.

---

## 8. Honcho dialectic operator modeling

Commit `a07b8e8` integrated **Hermes Honcho** for dialectic user modeling of operator **Hyperion** — for HERALD (Telegram) and HYPERION (operator interface).

### What Honcho does (and does not do)

| Does | Does not |
|------|----------|
| Cross-session operator preference modeling | Authorize trades |
| Session summary + peer cards injection | Override risk kernel DENY |
| Dialectic LLM supplement ("what matters now") | Bypass Phase 5 promotion gates |
| Per-peer isolation (HERALD vs HYPERION) | Replace `SOUL.md` / `iron-laws.md` |

### Peer layout

```
                    ┌─────────────────┐
                    │  hyperion       │  ← user peer (operator)
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐ ┌───▼───────────────┐
     │ herald-telegram │ │ hyperion-assistant │
     │ (HERALD)        │ │ (HYPERION)         │
     └─────────────────┘ └────────────────────┘
```

### Quick start (5 steps)

```bash
# 1. Deploy templates
./deploy.sh

# 2. Set env (never commit)
# HONCHO_API_KEY=...        # cloud or JWT for self-hosted
# HONCHO_BASE_URL=...       # self-hosted only
# HONCHO_PEER_NAME=hyperion

# 3. Activate Honcho
hermes memory setup honcho
hermes honcho status

# 4. Create profiles
hermes profile create herald --clone --aiPeer herald-telegram --workspace ~/.openclaw/workspace
hermes profile create hyperion --clone --aiPeer hyperion-assistant --workspace ~/.openclaw/workspace
hermes honcho sync

# 5. Restart gateway
sudo systemctl restart hermes-gateway
```

### Config defaults (`templates/honcho.json`)

| Key | Default | Notes |
|-----|---------|-------|
| `recallMode` | `hybrid` | Auto-inject + tools |
| `observationMode` | `directional` | Full mutual observation for HERALD |
| `sessionStrategy` | `per-repo` | One session per git repo |
| `contextTokens` | `1200` | Cap injected context |
| `contextCadence` | `1` | Refresh base layer every turn |
| `dialecticCadence` | `3` | Dialectic LLM every 3 turns |
| `pinUserPeer` | `true` | Single operator via Telegram gateway |

Dialectic LLM calls use **local Hermes inference** (Tier 2 / utility) — no closed/cloud models on the live path.

Full guide: [`HONCHO_SETUP.md`](./HONCHO_SETUP.md).

---

## 9. Web cockpit — local dev vs archive

### Timeline

| Commit | Change |
|--------|--------|
| `7eb4694` | Decommission `web/` → `archive/cockpit-web/`; Telegram sole ops surface |
| `f285328` | Restore `web/` for local dev; keep archive as frozen backup |

### Current policy

| Path | Purpose |
|------|---------|
| **`web/`** | Active dev copy — `cd web && npm install && npm run dev` |
| **`archive/cockpit-web/`** | Frozen snapshot from decommission — reference only |

**Production operations use Telegram.** Do not expose `web/` on the public internet without auth (Tailscale Serve, SSH tunnel, or SSO reverse proxy).

### Web UI features (local reference)

- Command palette (`Ctrl+K`), activity rail, status strip
- Agent Manager (20 classical agents)
- Data providers: mock (default) vs live `/api/*` stubs
- Sections: capital, risk, pipelines, promotions, memecoin trench, edge mesh, flash loans, signing, security ops

### Critical distinction

| Concept | Means | Does **not** mean |
|---------|-------|-------------------|
| `VITE_DATA_MODE=live` | UI fetches `/api/*` from safety ports | Real capital authorized |
| Green cockpit health | Fixtures or soft-fail may look healthy | Kernel ALLOW for trades |
| Cockpit "Live" toggle | Data provider mode | Phase 5 YES |

Guides (reference): [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md), [`WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md`](./WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md), [`BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md`](./BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md).

### Vite API proxy map

| UI path | Upstream |
|---------|----------|
| `/api/risk` | `:19001` |
| `/api/recon` | `:19002` |
| `/api/status` | `:19003` |
| `/api/portfolio` | `:19004` |
| `/api/dms` | `:19005` |
| `/api/allocator` | `:19006` |
| `/api/tca` | `:19007` |
| `/api/security` | `:19008` |
| `/api/signing` | In-process signing status |
| `/api/sign` | Optional legacy `:19010` |

---

## 10. Flash loans — autonomous live path

Commit `cfcec3c` **removed the human approval gate** for flash-loan live execution.

### July 2026 flash-loan policy

| Gate | Required? |
|------|-----------|
| Human YES (`flash_loan_live` promotion) | **No** (removed) |
| `flash_loan_live.enabled: true` in policy | **Yes** |
| `flashLoanRouter.enabled: true` in openclaw.json | **Yes** |
| Paper sim evidence (`flashloan sim --count 100`) | **Yes** (≥3 days recommended) |
| Risk kernel ALLOW | **Yes** — authoritative |
| Kill switch inactive | **Yes** |
| Amount / source / pipeline caps | **Yes** — kernel enforced |

```yaml
# policy.yaml
human_gates:
  flash_loan_live_requires_approval: false

flash_loan_live:
  enabled: false  # set true + flashLoanRouter.enabled for live
  max_amount_usd: 500000.0
  max_fee_bps: 9.0
  paper_sim_required_days: 3
  pipeline_ids: [P1, P2, P3, P5, P6, P7, P8, P12, P15, P16, P17]
```

### Execution flow

1. **ALCHEMY** composes via `titan-safety flashloan compose` → calldata + typed_data
2. Trade payload sets `uses_flash_loan: true`, `flash_loan_source`, `flash_loan_amount_usd`
3. Kernel DENY unless `flash_loan_live.enabled` + `flashLoanRouter.enabled`
4. `titan-safety gate check/sign` with fresh receipt
5. In-process sign → edge broadcast
6. HERALD notifies with PnL on fill

### CLI

```bash
titan-safety flashloan sim --count 100
titan-safety flashloan status
titan-safety flashloan route --asset WETH --amount-usd 10000 --chain ethereum --strategy P3
titan-safety flashloan compose --request-json '{...}'
```

### Kernel DENY codes (flash-loan)

Kernel enforces: amount caps, allowed sources per chain, pipeline allow-list, kill switch, circuit breakers, stealth venue policy. No LLM can override DENY.

### Remaining gates (not human YES)

- Enable flags in policy + openclaw.json
- Paper simulation evidence
- Positive expected profit from compose step
- Full gate + signing path
- Ghost evasion (shielded venues only on live)

---

## 11. Live capital path and blockers

### What "production live capital" means

1. Real funds in operator-controlled wallets / DEX positions (DEX-only — no CEX-direct live path).
2. Agents **propose**; deterministic safety services **veto**.
3. Every live order clears: recon → kernel → portfolio → gate receipt → in-process sign → edge broadcast on MEV-shielded path.
4. **Phase 5 human YES** still required for strategy promotion to live capital.
5. **20 classical agents**; quantum removed; signing in-process.

### Phased rollout

| Phase | Description | Human gate |
|-------|-------------|------------|
| **Paper** | Simulated fills; no broadcast | Auto-run |
| **Shadow** | Live market data; full gate path; no capital broadcast | Evidence accumulation |
| **Micro-live** | ≤0.1% equity test | After Phase 5 YES |
| **Scale** | 25% → 50% → 75% → 100% over sessions | Operator monitoring |

**Iron law:** `TIMEOUT` on promotion prompt = **HOLD / de-risk**. Never auto-promote.

### Phase 5 YES ceremony

```bash
titan-safety promotion approve --response YES --operator hyperion --pipeline P3 ...
```

Telegram delivers HIGH/CRITICAL alerts on promotion gate events. Silence does not approve.

### Honest blockers (July 2026)

Software controls are necessary but not sufficient. Operator-owned gaps:

| Gap | Status | Action required |
|-----|--------|-----------------|
| Live signing RPC | `live_signer()` raises until Trezor bridge wired | Wire `openclaw-trezor-bridge`; set `TITAN_LIVE_SIGNING_READY=1` after health OK |
| Position recon aggregator | Needs `TITAN_RECON_FETCHER_URL` | Run aggregator HTTP endpoint or extend fetcher |
| Key revoke at venue | `LiveKeyRevoker` returns `revoke_pending` | Manual venue key disable until RPC exists |
| Capital withdraw / Trezor sweep | Often mock until ops wiring | Wire Trezor Safe 7 ceremony path |
| AUGUR regime feed | File/stub in portfolio risk | Wire live feed for production regime limits |
| P22 memecoin trench | `memecoin_trench.enabled: false` | Phase 5 YES + Geyser/Jito + enable flag |
| Edge PoPs | Specs exist | Provision WireGuard + `edge_pop_bootstrap.sh` per PoP |
| UPS | Required for live | Eaton 9SX class; power-loss HALT drill |

Full walkthrough: [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md).  
Beginner narrative: [`BEGINNER_LIVE_CAPITAL_EXPLAINED.md`](./BEGINNER_LIVE_CAPITAL_EXPLAINED.md).

### Capital policy highlights

- Weekly profit sweep: 20% of weekly profit to Trezor Safe 7 when portfolio ≥ $15K; 100% reinvest below threshold.
- Allocator `max_active_pipelines`: default **4** — fund few HEALTHY lanes.
- Drawdown tiers (2/5/8/10/12%): notify by default; velocity breakers still HALT.
- Dead-man's switch: 48h miss → de-risk; 72h → flatten.

---

## 12. Bounded autonomy matrix (July 2026)

Enforced in `AGENTS.md` and `templates/risk_kernel/policy.yaml`.

| Action | Auto-execute | Human YES |
|--------|--------------|-----------|
| Routine trade <1% equity | YES | — |
| Trade >1% equity | BFT path when `autonomous_signing` enabled | — |
| Rebalance <1% equity | YES | — |
| New pipeline activation | — | YES |
| Model/skill promotion to live | — | YES (Phase 5) |
| Evolution deploy (DGM-H, GEPA, …) | Shadow only | YES for live |
| Leverage change | — | YES |
| **Flash-loan live** | **YES** (when policy + router enabled) | — |
| CB tier response (within policy) | YES | — |
| Drawdown velocity breach | HALT (kernel) | Alert operator |
| TIMEOUT on promotion prompt | HOLD/de-risk | **Never auto-promote** |
| Security lockdown | — | YES (HMAC) |
| Withdrawal >20% equity | — | YES |

### Confidence gates (unchanged)

See §3. Agents below 0.30 confidence are auto-rejected without human escalation.

### Circuit breaker autonomy

```yaml
circuit_breaker_autonomy:
  global_policy: "auto_respond"
  severity_responses:
    CRITICAL:
      action: "auto_pause + auto_failover + telegram_critical_alert"
      human_required: true  # six CRITICAL conditions only
    HIGH:
      action: "auto_pause_affected + informational_alert"
      human_required: false
    MEDIUM:
      action: "auto_adjust + informational_log"
    LOW:
      action: "auto_log"
```

### Memory, extractors, and shadow evolution (July 2026)

- **DGM-H / Darwin-Godel** remain **shadow-only** — `evolution_freeze.py` + `promotion_gate.py` + `policy.yaml` `shadow_only_evolution`; Tier 3 off-peak only; never auto-promote on TIMEOUT.
- **Deploy extractors** (`scripts/extract_*.py`, `make_digest.py`) are **fail-closed**: corrupt/missing input, bootstrap truncation, or `identifierPolicy=strict` violations exit non-zero.
- **Decision log** at `/data/openclaw/memory/decision_log.jsonl` uses hash-chained JSONL; rotation at 500 resolved entries; corrupt log repair from `.bak` via `titan-safety audit ensure`.
- **Honcho** (`~/.hermes/`) is advisory operator modeling only — does not replace local audit logs or promotion gate.

Full contract: [`docs/MEMORY_AND_EXTRACTORS.md`](./docs/MEMORY_AND_EXTRACTORS.md).

---

## 13. Security four pillars + ghost evasion

Always-on posture. Doctrine: **invisible to them, visible to us**.

| Pillar | Owner | Core controls |
|--------|-------|---------------|
| **Impenetrable** | SENTINEL | Kernel, in-process signing isolation, netns, PCR/CodeQL, DMS, closed-model ban |
| **Evasion (Ghost)** | TRENCH-OPS | MEV-shield / intents, edge RTT, Nostr NIP-44, fingerprint rotate |
| **Stalking** | PREDATOR | Hunt mode default; mempool / copy-trade / RPC probe feeds |
| **Predatory** | PREDATOR | Honeypot lattice armed; poison fills ≤1% equity auto |

**Forbidden live paths:** public RPC pools, public mempool, unshielded CEX-direct → `STEALTH_PUBLIC_PATH` / `STEALTH_UNSHIELDED_VENUE`.

**Lockdown:** `titan-safety security lockdown` — requires operator **HMAC**; never LLM-alone.

```bash
titan-safety security status
titan-safety security lockdown --dry-run
```

---

## 14. Safety services and ports

### Safety services

| Port | Service | Key endpoints |
|------|---------|---------------|
| **19001** | Risk kernel | `/v1/validate`, `/health`, `/metrics` |
| **19002** | Reconciliation | `/v1/pre_trade`, `/health` |
| **19003** | Status aggregator | `/health`, `/status`, `/metrics` |
| **19004** | Portfolio risk | `/v1/simulate`, `/v1/var`, `/health` |
| **19005** | Dead-man's switch | `/v1/heartbeat`, `/health` |
| **19006** | Capital allocator | `/v1/allocate`, `/v1/plan`, `/health` |
| **19007** | TCA / execution quality | `/v1/ingest`, `/v1/scorecard`, `/health` |
| **19008** | Security ops | `/v1/status`, `/health` |
| **19010** | Signing (legacy optional) | HTTP `/v1/sign` only if `signing.mode=http` — **not required** |

### Inference ports

| Port | Service |
|------|---------|
| **30000** | Tier 1 critical — Qwen3-30B-A3B FP8 |
| **30001** | Tier 2 reasoning — Qwen3-Coder-80B |
| **30002** | Utility — Qwen3-30B-A3B-Instruct-2507 (TITANSPARK) |
| **30003** | GLM-5.2 R&D (off-peak) |
| **30004** | Qwen3-Embedding |
| **30005** | DeepSeek V4 Pro R&D (off-peak) |
| **30020** | REVM classical sim |

### Gateway and edge

| Port | Service |
|------|---------|
| **18789** | OpenClaw / Hermes gateway (Telegram) |
| **19100** | Edge worker (per PoP) |

Control-plane mutating POSTs require `X-Titan-Auth` HMAC when `control_plane.auth_required: true`.

---

## 15. CLI reference

Binary: `titan-safety` (after `./deploy.sh` → `~/.openclaw/safety/bin/`).

### Health and status

```bash
curl -s http://127.0.0.1:19003/health | python3 -m json.tool
titan-safety kill status
titan-safety evolution status
titan-safety security status
```

### Kill switch and wind-down

```bash
titan-safety kill activate --operator YOU --reason "drill"
titan-safety kill sign --command RESUME --operator YOU
titan-safety kill deactivate --operator YOU --signed "$SIGNED"
titan-safety wind-down safe-mode|derisk|flatten|status
```

### Gate and signing

```bash
titan-safety gate check --trade-json '...'
titan-safety gate sign --trade-json '...'
titan-safety bft vote --voter AUGUR --trade-id ...
```

### Capital and allocator

```bash
titan-safety capital balance
titan-safety capital balance --telegram
titan-safety capital sweep
titan-safety allocator plan ...
titan-safety tca scorecard
titan-safety tca profit-loop
```

### Telegram (HERALD)

```bash
titan-safety notify test
titan-safety notify test --dry-run
titan-safety notify send --title "Drill" --event-type notify_test --description "..."
titan-safety notify pnl --realized 142.88 --pct-equity 0.55 --pipeline P3 --asset WETH/USDC --outcome WIN
titan-safety notify digest
titan-safety notify drain
```

### Flash loans

```bash
titan-safety flashloan sim --count 100
titan-safety flashloan status
titan-safety flashloan compose --request-json '...'
```

### Edge and gated strategies

```bash
titan-safety edge route --venue jito --strategy P22
titan-safety memecoin filter|evaluate|sim|status
titan-safety qi demo   # advisory classical SA only
```

### Promotion

```bash
titan-safety promotion approve --response YES ...
titan-safety promotion-stats --stats '...'
```

### Dead-man's switch

```bash
titan-safety heartbeat
```

### Hermes / Honcho

```bash
hermes honcho status
hermes honcho peers
hermes honcho sync
```

---

## 16. Deploy and go-live checklist

### First-time deploy

```bash
# 1. Bootstrap hardware (see TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md)
# 2. Deploy software
./deploy.sh
# Optional: ./deploy.sh --systemd --start-services --verify --edge-bootstrap

# 3. Secrets
cp templates/infra/live.env.example ~/.openclaw/.env
# Edit: TELEGRAM_*, HONCHO_*, RPC keys, HMAC secrets

# 4. Verify
./verify.sh

# 5. Inference
# Start llama-server :30000, :30001; SGLang :30002 on TITANSPARK

# 6. Telegram smoke test
titan-safety notify test --dry-run
titan-safety notify test

# 7. Honcho (optional but recommended)
hermes memory setup honcho
hermes profile create herald --clone --aiPeer herald-telegram --workspace ~/.openclaw/workspace
```

### Go-live sequence (do not skip)

1. **`BOOTSTRAP.md`** — first-run ritual
2. **`./deploy.sh`** — install templates
3. **`./verify.sh`** — config + safety checks
4. **`PRODUCTION_READINESS.md`** — fail-closed drills
5. **Paper trading** — minimum 3 days
6. **Shadow** — live data, no broadcast
7. **Phase 5 YES** — explicit operator approval
8. **Micro-live** — ≤0.1% equity
9. **Scale** — session-based sizing

**Gateway restart:** [`BOOT.md`](./BOOT.md) — health `:19001`–`:19008`; in-process signing; **no auto-promote**.

### Master pre-live checklist

- [ ] Safety units healthy via `:19003`
- [ ] Kernel DENY when stopped (fail-closed drill)
- [ ] Kill switch drill completed
- [ ] DMS heartbeat configured
- [ ] Signing receipt gate verified
- [ ] UPS installed + power-loss HALT drill
- [ ] Telegram credentials set + `notify test` passed
- [ ] Honcho connected (if using operator modeling)
- [ ] Paper ≥3 days + statistical promotion evidence
- [ ] Phase 5 YES recorded in promotion audit
- [ ] `TITAN_LIVE_SIGNING_READY=1` only after Trezor bridge health OK
- [ ] Mock recon/withdraw adapters **not** present on live profile
- [ ] `quantum.enabled: false` confirmed
- [ ] Ghost evasion — no public RPC on live path

---

## 17. Daily operator routine

### Morning

```bash
curl -s http://127.0.0.1:19003/health | python3 -m json.tool
titan-safety kill status
titan-safety evolution status
titan-safety capital balance
titan-safety heartbeat
```

Review Telegram overnight digest and CRITICAL/HIGH alerts.

### During session

- Monitor HERALD trade fills and Financial Summary blocks
- Respond to Phase 5 / promotion prompts explicitly (YES / NO / EXTEND — never silence)
- `/balance`, `/sweep` via Telegram as needed

### Weekly

- Review TCA scorecards: `titan-safety tca scorecard`
- Profit loop: `titan-safety tca profit-loop`
- Trezor sweep when equity ≥ $15K (Sunday UTC policy)
- Verify edge PoP RTT and inference tier health

### On gateway restart

Follow [`BOOT.md`](./BOOT.md):

1. Safety `:19001`–`:19008` healthy
2. Kill switch inactive
3. Evolution freeze if live capital
4. Inference `:30000`, `:30001` up
5. Telegram path: `titan-safety notify test --dry-run`
6. **Do not** auto-promote or auto-resume halted pipelines
7. HERALD alerts on CRITICAL/HIGH failures only

---

## 18. What changed from source/TITAN.md

`source/TITAN.md` (June 2026) remains in the repo as historical reference. **July 2026 current state differs materially:**

| Topic | source/TITAN.md (June) | TITAN_CURRENT (July) |
|-------|------------------------|------------------------|
| **Agent count** | 23 agents (+ QCC/QSA/QRP) | **20** agents; quantum removed |
| **Quantum dispatch** | QCC → NATS JetStream | **Removed**; classical-only |
| **Phase 5** | "REMOVED" — auto-promote on Phase 1–4 | **Human YES required**; TIMEOUT = HOLD |
| **Signing** | `:19010` signing node emphasized | **In-process** SigningNode; `:19010` optional |
| **Operator UI** | Cockpit + Telegram | **Telegram production**; `web/` local dev only |
| **Flash loans** | Human YES implied in matrix | **Autonomous** when flags enabled |
| **Models** | GLM-5.2-753B primary emphasis | **Qwen3-30B** Tier 1 + **Qwen3-Coder-80B** Tier 2 + utility **Qwen3-30B-Instruct-2507** |
| **Telegram format** | Emoji taxonomy | **Institutional** template + Financial Summary / PnL |
| **Honcho** | Mentioned in AGENTS.md | **Fully wired** — templates, setup guide, tests |
| **Contact email** | Various | **titan.agentik@protonmail.com** |
| **Autonomy narrative** | "Zero human gates" broadly | **Bounded matrix** — Phase 5, pipeline activation, evolution, leverage still gated |

### Decommissioned / archived

- Quantum agents QCC, QSA, QRP
- Mandatory `:19010` HTTP signing daemon on hot path
- Production reliance on browser cockpit (`archive/cockpit-web/` frozen)
- `flash_loan_live` human promotion YES requirement
- Phase 5 auto-promote on timeout (contradicts `iron-laws.md` — current policy restores human YES)

### Added / restored

- `telegram_notify.py` institutional module + tests
- Financial Summary and PnL in Telegram alerts
- `HONCHO_SETUP.md` + `templates/honcho.json`
- `web/` restored for local development
- `SYSTEM.md` as primary manual
- `LIVE_CAPITAL_PRODUCTION_GUIDE.md` and beginner companions
- In-process signing fold (`ee75558`)
- Agent Manager ops console (20-agent fleet)

---

## 19. Beginner sections

### "I just cloned the repo — what do I read?"

1. **This file** (`TITAN_CURRENT.md`) — current state overview
2. [`SYSTEM.md`](./SYSTEM.md) — architecture and CLI
3. [`TELEGRAM_OPS_GUIDE.md`](./TELEGRAM_OPS_GUIDE.md) — set up Telegram first
4. [`TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md`](./TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md) — full hardware + software path
5. [`BEGINNER_LIVE_CAPITAL_EXPLAINED.md`](./BEGINNER_LIVE_CAPITAL_EXPLAINED.md) — real money concepts before going live

### "Will Telegram let me trade?"

No. Telegram is **notify-only**. You receive alerts and can run capital **commands** that go through the same safety stack. You cannot override a kernel DENY from chat.

### "Can I use the web UI for production?"

No. Use Telegram for production operations. The web UI is for **local development and reference** on `http://127.0.0.1:5173`. UI live data mode ≠ capital live.

### "Do flash loans need my YES?"

Not anymore (July 2026). When `flash_loan_live.enabled` and `flashLoanRouter.enabled` are true, and paper sim evidence exists, flash loans execute autonomously subject to kernel caps. **Phase 5 YES is still required for general live capital promotion.**

### "What if I don't respond to a promotion prompt?"

**TIMEOUT = HOLD / de-risk.** The system never auto-promotes. This is an iron law.

### "Who do I contact?"

**titan.agentik@protonmail.com** — operator contact for Titan Agentik.

---

## Appendix A — commit changelog

Key commits from `7eb4694` through HEAD (July 2026 evolution):

| Commit | Date (approx) | Summary | Files / impact |
|--------|---------------|---------|----------------|
| `7eb4694` | Jul 2026 | **Decommission web cockpit** — Telegram sole ops surface | Archive `web/` → `archive/cockpit-web/`; add `telegram_notify.py`, `TELEGRAM_OPS_GUIDE.md`, HERALD hooks |
| `f285328` | Jul 2026 | **Restore web/** for local dev | Reinstate `web/` from history; archive remains frozen backup; SYSTEM.md updated |
| `cfcec3c` | Jul 2026 | **Flash-loan autonomous** — remove human YES | `policy.yaml`, `openclaw.json`, kernel, CLI, tests; bounded matrix updated |
| `f3e9eea` | Jul 2026 | **Financial Summary + PnL** in Telegram | `telegram_notify.py` +447 lines; HERALD templates; tests |
| `f574a33` | Jul 2026 | **Contact email** → titan.agentik@protonmail.com | `USER.md`, `source/TITAN.md`, `workspace/USER.md` |
| `a07b8e8` | Jul 2026 | **Honcho integration** | `HONCHO_SETUP.md`, `templates/honcho.json`, openclaw honcho block, tests |
| `c26145a` | Jul 2026 | Live capital production guide | `LIVE_CAPITAL_PRODUCTION_GUIDE.md` |
| `064aded` | Jul 2026 | Web UI live production guide | `WEB_UI_LIVE_PRODUCTION_GUIDE.md` |
| `2f80b69` | Jul 2026 | SYSTEM.md primary manual | Architecture synthesis |
| `ee75558` | Jul 2026 | In-process signing | Fold signing into titan-safety; drop `:19010` hot-path hop |
| `c64849c` | Jul 2026 | Remove quantum agents | QCC/QSA/QRP deleted from catalog |
| `6ce76e1` | Jul 2026 | Agent Manager console | 20-agent classical fleet UI |
| `30f0385` | Jul 2026 | Cockpit align in-process signing | 20-agent catalog in web UI |

Earlier related commits: beginner guides (`7b067df`, `5df53ed`, `0c3189a`), cockpit data providers (`36ba3e4`), production readiness polish.

---

## Appendix B — glossary

| Term | Definition |
|------|------------|
| **Agent** | Specialized LLM worker with a defined role (20 in fleet) |
| **ARCHON** | Orchestrator agent; delegates to all others |
| **ATLAS** | Portfolio agent; BFT voter |
| **AUGUR** | Macro regime agent; BFT voter |
| **BFT** | Byzantine fault tolerant voting — here, 2-of-3 advisory trade votes |
| **Bounded autonomy** | Auto-execute within matrix limits; human YES for promotion, leverage, new pipelines |
| **CB** | Circuit breaker — drawdown / velocity / pipeline halt |
| **DEX-only** | Live capital trades only on decentralized exchange paths |
| **DMS** | Dead-man's switch — heartbeat miss → de-risk / flatten |
| **ExecutionGate** | Pre-sign gate producing `X-Titan-Gate-Receipt` |
| **Ghost evasion** | Stealth posture — no public RPC / unshielded venues on live |
| **GUARDIAN** | Risk validation agent; Kelly sizing |
| **HERALD** | Telegram notification agent |
| **Honcho** | Hermes dialectic operator memory — models Hyperion preferences |
| **HYPERION** | Operator interface agent (off-critical path) |
| **Kernel** | Risk kernel `:19001` — authoritative DENY/ALLOW |
| **LAMARCK** | Post-trade learning agent |
| **Phase 5** | Human YES gate before live capital promotion |
| **PREDATOR** | Scanner / mempool agent; BFT voter |
| **REVM** | Rust EVM simulator for pre-trade checks |
| **SigningNode** | In-process signer inside titan-safety |
| **TITANHOME** | Primary compute node |
| **TITANSPARK** | Utility inference node (GB10) |
| **TRENCH-OPS** | Trade execution agent |
| **TIMEOUT** | Promotion prompt expiry → HOLD/de-risk, never auto-promote |

---

## Appendix C — specialized guide index

| Guide | Audience | Topic |
|-------|----------|-------|
| [`SYSTEM.md`](./SYSTEM.md) | All operators | Primary system manual |
| [`TELEGRAM_OPS_GUIDE.md`](./TELEGRAM_OPS_GUIDE.md) | Production ops | Telegram / HERALD |
| [`HONCHO_SETUP.md`](./HONCHO_SETUP.md) | All operators | Dialectic operator modeling |
| [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) | Go-live | Paper → Phase 5 → live |
| [`BEGINNER_LIVE_CAPITAL_EXPLAINED.md`](./BEGINNER_LIVE_CAPITAL_EXPLAINED.md) | Beginners | Real money concepts |
| [`TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md`](./TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md) | New installs | BIOS to first paper trade |
| [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md) | DevOps | Cockpit serve (archived header; web/ dev) |
| [`WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md`](./WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md) | Developers | Mock vs live providers |
| [`BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md`](./BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md) | Beginners | UI + providers + capital path |
| [`BOOT.md`](./BOOT.md) | Daily ops | Gateway restart |
| [`BOOTSTRAP.md`](./BOOTSTRAP.md) | First run | Initial ritual |
| [`PRODUCTION_READINESS.md`](./PRODUCTION_READINESS.md) | Go-live | Honest enforced vs residual risk |
| [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) | Technical | Deploy narrative |
| [`AGENTS.md`](./AGENTS.md) | Agents | Protocol + bounded autonomy |
| [`TOOLS.md`](./TOOLS.md) | Agents | Capability matrix |
| [`SOUL.md`](./SOUL.md) | Immutable | Identity constitution |
| [`iron-laws.md`](./iron-laws.md) | Immutable | Operational constitution |
| [`source/TITAN.md`](./source/TITAN.md) | Historical | June 2026 catalog reference |
| [`web/README.md`](./web/README.md) | Developers | Local web UI quick start |
| [`archive/cockpit-web/README.md`](./archive/cockpit-web/README.md) | Reference | Frozen cockpit backup |

---

## Document metadata

| Field | Value |
|-------|-------|
| **File** | `TITAN_CURRENT.md` |
| **Version** | July 2026 (aligned with commits through `a07b8e8`) |
| **Maintainer contact** | titan.agentik@protonmail.com |
| **Update policy** | Revise when architecture ports, operator surfaces, or bounded autonomy matrix change |
| **Does not modify** | `SOUL.md`, `iron-laws.md` |

---

*Generated for the titan-deploy bundle. Prefer `TITAN_CURRENT.md` for July 2026 operator truth; use `source/TITAN.md` only as historical catalog reference.*
