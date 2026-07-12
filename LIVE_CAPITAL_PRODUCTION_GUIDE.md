# LIVE CAPITAL PRODUCTION GUIDE

> **What this document is:** A beginner-friendly but complete walkthrough from *current deploy state* → paper → shadow → Phase 5 human YES → **real-capital live trading** on Titan.  
> **What this document is not:** A one-liner that flips live trading on. It does **not** bypass the risk kernel (`:19001`), the ExecutionGate, the Bounded Autonomy Matrix, or Hyperion’s explicit YES gates.  
> Prefer the beginner narrative? See [`BEGINNER_LIVE_CAPITAL_EXPLAINED.md`](./BEGINNER_LIVE_CAPITAL_EXPLAINED.md).

**Last aligned with:** deploy bundle policy `templates/risk_kernel/policy.yaml` v2.1+, `PRODUCTION_READINESS.md`, `SYSTEM.md`, `iron-laws.md`, `SOUL.md`, `AGENTS.md`.

> **Beginner bridge (cockpit UI + data providers + this capital path):** [`BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md`](./BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md). Flipping UI Live mode does **not** authorize capital.

**Related docs (read these too):**

| Doc | Role |
|-----|------|
| [`BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md`](./BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md) | **Beginner:** web UI live + providers + real money (standalone) |
| [`PRODUCTION_READINESS.md`](./PRODUCTION_READINESS.md) | Honest “what software enforces” + residual risks |
| [`SYSTEM.md`](./SYSTEM.md) | Full system manual |
| [`BOOT.md`](./BOOT.md) | Gateway restart checklist (no auto-promote) |
| [`BOOTSTRAP.md`](./BOOTSTRAP.md) | First-run ritual |
| [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md) | Cockpit production serve — **UI live ≠ capital live** |
| [`WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md`](./WEB_UI_DATA_PROVIDERS_LIVE_GUIDE.md) | Mock vs live **data providers** only — does **not** authorize capital |
| [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) / [`DEPLOYMENT_GUIDE_BEGINNER.md`](./DEPLOYMENT_GUIDE_BEGINNER.md) | Deploy narratives |
| [`TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md`](./TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md) | End-to-end stack setup |
| [`templates/playbooks/promotion.yaml`](./templates/playbooks/promotion.yaml) | Promotion ceremony playbook |
| [`templates/infra/live.env.example`](./templates/infra/live.env.example) | Secrets template for `~/.openclaw/.env` |

---

## Table of contents

1. [What “production live capital” means in Titan](#1-what-production-live-capital-means-in-titan)
2. [What you already have vs what is still gated](#2-what-you-already-have-vs-what-is-still-gated)
3. [Non-negotiable prerequisites](#3-non-negotiable-prerequisites)
4. [Capital & risk policy before first live order](#4-capital--risk-policy-before-first-live-order)
5. [Paper trading period (3-day minimum)](#5-paper-trading-period-3-day-minimum)
6. [Shadow / dry-run with live market data](#6-shadow--dry-run-with-live-market-data)
7. [Phase 5 human YES ceremony](#7-phase-5-human-yes-ceremony)
8. [Enabling live profile safely](#8-enabling-live-profile-safely)
9. [First live trade playbook](#9-first-live-trade-playbook)
10. [Ongoing production ops](#10-ongoing-production-ops)
11. [Cockpit + CLI monitoring during live](#11-cockpit--cli-monitoring-during-live)
12. [Rollback / HALT procedures](#12-rollback--halt-procedures)
13. [Security & stealth for live capital](#13-security--stealth-for-live-capital)
14. [Go-live master checklist](#14-go-live-master-checklist)
15. [Troubleshooting live DENY / signing / edge](#15-troubleshooting-live-deny--signing--edge)
16. [Appendix](#16-appendix)

---

## Critical distinctions (read before anything else)

| Concept | Means | Does **not** mean |
|---------|-------|-------------------|
| Cockpit `VITE_DATA_MODE=live` | UI fetches `/api/*` from safety ports | Real capital is authorized |
| `capital_profile: live` in deployed policy | Live *profile* rules apply (mock adapters banned, stealth enforced) | Every pipeline is funded and broadcasting |
| Paper venue | Simulated fills; no broadcast of real txs | Strategy is “proven” |
| Shadow / dry-run | Live market data + full gate path; **no** capital broadcast | Phase 5 already approved |
| BFT 2-of-3 (AUGUR + PREDATOR + ATLAS) | **Advisory** trade authorization | Override of risk kernel DENY |
| Risk kernel `:19001` DENY | **Authoritative** — absolute | Something an LLM can negotiate |
| Phase 5 YES | Explicit Hyperion `YES` in promotion audit | Silence, TIMEOUT, or “looks good” |
| In-process signing | `titan-safety gate sign` after ExecutionGate ALLOW | Separate mandatory `:19010` daemon |
| UPS + power-loss HALT | Required before live capital | Optional nice-to-have for paper UI |

**Iron law:** TIMEOUT on a promotion prompt = **HOLD / de-risk**. Never auto-promote. (`iron-laws.md` §7, Bounded Autonomy Matrix.)

---

## 1. What “production live capital” means in Titan

In Titan, **production live capital** means:

1. Real funds sit in operator-controlled wallets / DEX positions (DEX-only posture — R02 / R46; no CEX-direct live path).
2. Agents may **propose** trades; they cannot force fills.
3. Every live order must clear:
   - Reconciliation (`:19002`)
   - Risk kernel (`:19001`)
   - Portfolio risk when wired (`:19004`)
   - ExecutionGate → fresh `X-Titan-Gate-Receipt`
   - In-process `titan_safety.SigningNode` (`titan-safety gate sign`)
   - Edge broadcast (5-PoP mesh) on a **MEV-shielded** path (`ghost_evasion`)
4. Human YES is still required for: Phase 5 go/no-go, new pipeline activation, evolution→live, leverage change, flash-loan live, and (per matrix) trades / promotions above policy thresholds.
5. Classical-only fleet: **20 agents**. Quantum agents QCC/QSA/QRP are **removed**. `quantum.enabled: false`.
6. Signing is **in-process** on TITANHOME inside `titan-safety` after gate ALLOW. Mac Mini vault = key metadata + **Trezor ceremonies** — not the hot-path signer. Legacy HTTP `:19010` is optional and **not required**.

### What production does *not* mean

- “Deploy script finished” ≠ live capital.
- “Cockpit is green” ≠ live capital (soft-fail fixtures can look healthy).
- “Template has `capital_profile: live`” ≠ you already said YES and wired adapters. **Template defaults to `paper`.**
- “BFT voted ALLOW” ≠ kernel must ALLOW.
- Enabling every pipeline in the catalog ≠ production. **Catalog ≠ checklist.** Fund ≤ `allocator.max_active_pipelines` (default **2**) HEALTHY lanes.

### Mental model (one diagram)

```text
Hyperion (YES gates)
        │
        ▼
Agents propose ──► BFT votes (advisory)
        │
        ▼
ExecutionGate ──► recon :19002 ──► kernel :19001 ──► portfolio :19004
        │
        │ ALLOW + X-Titan-Gate-Receipt
        ▼
titan-safety SigningNode (in-process)
        │
        ▼
Edge PoP (FRA/TKY/SIN/USE/AMS) ──► shielded DEX / intent / Jito / Flashbots
```

If **any** stage fails or is unreachable → **DENY / fail-closed**. There is no “bypass for production urgency.”

---

## 2. What you already have vs what is still gated

### Already in the software bundle (necessary, not sufficient)

| Control | Where | Fail mode |
|---------|-------|-----------|
| Independent risk kernel | `titan_safety.kernel` `:19001` | DENY if unreachable |
| ExecutionGate + receipt | `execution_gate.py` | DENY without fresh receipt |
| In-process signing gate | `SigningNode` / `gate sign` | Reject without receipt |
| Portfolio VaR / correlation | `:19004` | DENY when wired |
| Allocator + TCA + promotion stats | `:19006` / `:19007` / CLI | Stats fail-closed; allocator may be advisory |
| Kill switch / wind-down / DMS | CLI + `:19005` | Halt / derisk / flatten |
| Evolution freeze | `evolution_freeze.py` | Blocks live promotions while frozen |
| Ghost evasion + security ops | policy + `:19008` | DENY public/unshielded paths |
| Promotion audit (explicit YES) | `promotion_gate.py` | TIMEOUT → HOLD |
| Mock adapter ban on live profile | startup assert | Refuse live startup with mocks |

See `PRODUCTION_READINESS.md` §“What Is Enforced in Software” for the full table.

### Still gated / operator-owned (honest blockers)

These are **not** silently finished by this guide or by `deploy.sh`:

| Gap | Status in repo | What you must do |
|-----|----------------|------------------|
| **Live signing RPC** | `live_signer()` raises until Trezor bridge RPC is wired | Install/wire `openclaw-trezor-bridge` per `signing_node.yaml`; set `TITAN_LIVE_SIGNING_READY=1` only after health OK |
| **Position recon aggregator** | Built-in Hyperliquid clearinghouse (`recon_aggregator.py`); EVM indexer STUB | Set `HYPERLIQUID_WALLET_ADDRESS` or `TITAN_RECON_FETCHER_URL` |
| **Key revoke at venue** | `LiveKeyRevoker` returns `revoke_pending` | Manually disable keys at venue UI until revoke RPC exists |
| **Capital withdraw / Trezor sweep adapter** | Often still `mock` until ops wiring | Wire Trezor Safe 7 ceremony path before treating sweeps as production |
| **AUGUR regime feed** | File/stub regime in portfolio risk | Wire live AUGUR feed for production regime limits |
| **P22 memecoin trench** | `memecoin_trench.enabled: false` | Phase 5 / `memecoin_p22` YES + Geyser/Jito + `memecoinTrench.enabled` |
| **Flash-loan live** | `flash_loan_live.enabled: false` | Paper sim ≥3d + `flash_loan_live` YES + router flag |
| **Allocator enforce** | `allocator.advisory_mode: true` in template | Explicitly set `false` only after you accept automated de-fund behavior |
| **Edge PoPs** | Specs + bootstrap scripts exist | Provision WireGuard + `edge_pop_bootstrap.sh` per PoP |
| **Agent skill honor DENY** | Config-level wiring | Code-review execution skills so no path skips `preTradeValidationUrl` |
| **Grafana / BusKill** | Stub / separate hardware | Optional ops hardening — not a substitute for kernel |

**Bottom line:** The bundle gives you a **fail-closed control plane**. Real capital still requires evidence, YES, UPS, live adapters, and residual-risk acceptance.

---

## 3. Non-negotiable prerequisites

Do not skip. If any item fails, stay on paper/shadow.

### 3.1 Hardware & power

| Item | Requirement |
|------|-------------|
| **TITANHOME** | Primary compute + inference + safety services |
| **UPS** | ≥3000VA class (Eaton 9SX documented), ≥15 min runtime on TITANHOME + signing path |
| **Power-loss policy** | `power_loss.on_ups_battery: halt_trading`, `ups_required_for_live_capital: true` |
| **TITANSPARK** | Utility inference (`:30002`) — UPS recommended |
| **Mac Mini vault** | Key metadata + Trezor ceremonies — UPS mandatory for vault duties |
| **Edge mesh** | At least EDGE-FRA for Phase 1 micro-live; full 5-PoP for mature latency |

Specs: `templates/infra/power_requirements.yaml`, `hardware_bom.yaml`, `signing_node.yaml`.

**Drill (required):** Disconnect mains (or simulate UPS battery) → confirm trading **HALT** + CRITICAL alert → resume only with operator ack.

### 3.2 Keys & Trezor

- Hot-path signing: **in-process** `titan-safety` after gate ALLOW — never in agent LLM runtime.
- Cold / harvest: **Trezor Safe 7** ceremonies on Mac Mini vault.
- Session keys / seeds: **never** written to agent memory (`iron-laws.md` §4).
- Withdrawal keys: least privilege; separate from agent-writable paths.
- `TITAN_LIVE_SIGNING_READY=0` until bridge + signing health verified; then `=1`.

### 3.3 RPC / ghost (stealth)

Live capital forbids public RPC / public mempool / unshielded CEX-direct venues (`ghost_evasion.forbidden_venues`). Use shielded venues only (Uniswap / Curve / Aave / Hyperliquid / Jupiter / Jito / Flashbots Protect / intent solvers, etc. per policy allow-list).

Kernel codes you will see if you cheat: `STEALTH_PUBLIC_PATH`, `STEALTH_UNSHIELDED_VENUE`.

### 3.4 Policy & classical-only

Confirm on the **deployed** host (`~/.openclaw/…`), not only in the git template:

```bash
# Policy present
test -f ~/.openclaw/risk_kernel/policy.yaml && echo OK_POLICY

# Quantum off
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home()/".openclaw"/"openclaw.json"
cfg = json.loads(p.read_text()) if p.exists() else {}
q = cfg.get("quantum") or {}
print("quantum.enabled=", q.get("enabled", False))
print("quantum.status=", q.get("status", "n/a"))
PY

# No QCC/QSA/QRP in agent definitions (classical 20)
rg -n 'QCC|QSA|QRP' ~/.openclaw/openclaw.json || echo "OK_NO_QUANTUM_AGENTS"
```

### 3.5 Safety services + verify

```bash
# Aggregate health — expect status ok
curl -s http://127.0.0.1:19003/health | python3 -m json.tool

# Individual ports :19001–:19008
for p in 19001 19002 19003 19004 19005 19006 19007 19008; do
  echo -n ":$p "; curl -sf "http://127.0.0.1:$p/health" >/dev/null && echo OK || echo DOWN
done

# Bundle verify (from repo root on TITANHOME)
./verify.sh
```

**Signing note:** Do **not** require `:19010` healthy. Default is in-process. Only start legacy `titan-signing-node.service` if you deliberately set `signing.mode=http`.

### 3.6 Fail-closed proof (mandatory)

```bash
# 1) Stop risk kernel (systemd unit name may be titan-risk-kernel)
sudo systemctl stop titan-risk-kernel.service   # or: systemctl --user stop …

# 2) Any validate / gate sign attempt must DENY or fail — never ALLOW
curl -s -X POST http://127.0.0.1:19001/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{"trade_id":"failclosed","venue":"paper","contract":"0x0000000000000000000000000000000000000000","notional_usd":10}'
# Expect connection error or DENY — not ALLOW

# 3) Restart kernel
sudo systemctl start titan-risk-kernel.service
curl -sf http://127.0.0.1:19001/health
```

If trades still ALLOW with kernel down, **do not go live** — an execution path is bypassing the gate.

---

## 4. Capital & risk policy before first live order

Edit **deployed** `~/.openclaw/risk_kernel/policy.yaml` deliberately. Template defaults (illustrative — verify yours):

| Knob | Template default | Meaning |
|------|------------------|---------|
| `trading_limits.max_notional_usd_per_trade` | `500` | Hard per-trade notional |
| `trading_limits.max_aggregate_exposure_usd` | `2500` | Aggregate exposure |
| `trading_limits.max_leverage` | `3.0` | Leverage cap (changes still need YES) |
| `trading_limits.equity_usd` | `2500` | Declared equity for % gates |
| `position_limits.max_equity_pct_per_trade` | `2.0` | Max % equity per trade |
| `position_limits.human_approval_above_pct` | `1.0` | Above → BFT path when autonomous signing on |
| `allocator.kelly_fraction` | `0.25` | Quarter-Kelly |
| `allocator.max_active_pipelines` | `4` | Concentration |
| `allocator.advisory_mode` | `true` | Log targets until you enforce |
| `promotion_stats.min_trades` | `200` | Evidence before capital |
| `promotion_stats.min_deflated_sharpe` / `min_psr` | `0.90` | Stats gate |
| `drawdown_tiers` | 2 / 5 / 8 / 10 / 12% | Notify ladder (see note below) |
| `drawdown_velocity` | `$150/60s`, `$400/15m` | Hard velocity breakers |
| `power_loss.ups_required_for_live_capital` | `true` | No UPS → no live |

### Confidence gate (agents)

| Confidence | Action |
|------------|--------|
| ≥ 0.70 | Full size (within caps) |
| 0.50–0.69 | Reduced size ≈ confidence × target |
| 0.30–0.49 | Escalate to ARCHON |
| < 0.30 | Reject |

### Stop-loss mandate (R16)

Every position must have a **hard stop-loss**. Soft “mental stops” are not compliant.

### Drawdown honesty note

- **SOUL / AGENTS operational doctrine** describes a 5-tier CB ladder culminating in halt at 12%.
- **Default template** (`capital_profile: paper`) uses `drawdown_notify_only: true` — tiers alert only.
- **Live profile** (after Phase 5 YES) enforces de-gross / halt / flatten via `tier1_capital_risk.profiles.live` — see [`docs/TIER1_CAPITAL_RISK.md`](./docs/TIER1_CAPITAL_RISK.md).
- **Velocity** breakers still DENY/HALT on all profiles.

### Weekly profit sweep (R23)

| Portfolio value | Sweep behavior |
|-----------------|----------------|
| < **$15K** | Growth phase — **100% reinvest**; sweeps paused |
| ≥ **$15K** | Harvest — **20% of weekly profit** every 7 days to **Trezor Safe 7** |

Capital injections continue regardless. CLI surface: `titan-safety capital …` / Telegram `/sweep` (when wired).

### DEX-only

`live.env.example` is explicit: **no CEX API keys** for the live recon/signing path. CEX names in venue allow-lists are historical/catalog — live posture is DEX + shielded routes.

---

## 5. Paper trading period (3-day minimum)

**Policy:** `promotion_gates.paper_minimum_days: 3`.  
**Lifecycle:** §DEPLOY_LIFECYCLE (ARBITER) — Phases 1–4 can automate evidence collection; **Phase 5 never auto-YES**.

### Goals of paper

1. Same data feeds and order logic as live, **without** broadcasting real txs.
2. Record divergence vs backtest (PnL ±15%, trade count ±25%, win rate ±20% typical thresholds in TOOLS.md).
3. Populate TCA scorecards (`:19007`) and allocator attribution samples.
4. Prove kill switch, DMS heartbeat, and recon paths with **zero** live keys.

### How to run (copy-paste starting point)

```bash
# Ensure paper venue works through kernel
curl -s -X POST http://127.0.0.1:19001/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "trade_id":"paper-smoke-1",
    "venue":"paper",
    "contract":"0x0000000000000000000000000000000000000000",
    "notional_usd":10,
    "strategy_id":"P5"
  }' | python3 -m json.tool

# Capital ledger smoke (paper deposit ≠ trading PnL)
~/.openclaw/safety/bin/titan-safety capital deposit --amount 2500 --asset USDC --operator hyperion
~/.openclaw/safety/bin/titan-safety capital balance
~/.openclaw/safety/bin/titan-safety capital verify-audit

# TCA / promotion-stats examples (replace with your lane returns)
~/.openclaw/safety/bin/titan-safety promotion-stats --stats \
  '{"strategy_id":"P5","returns":[0.02,-0.004,0.03,0.012],"trials":5,"num_trades":500,"gross_bps":12,"cost_bps":3,"backtest_sharpe":1.8,"shadow_sharpe":1.7}'
```

Run candidate pipelines via OpenClaw/Hermes paper mode (see `TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md` and agent skills). Prefer **one or two** lanes — not the whole catalog.

### What to record each day (minimum)

Create a dated note (Telegram digest + local file), e.g. `~/.openclaw/memory/paper/YYYY-MM-DD.json`:

```json
{
  "date": "2026-07-10",
  "operator": "hyperion",
  "pipeline_id": "P5",
  "mode": "paper",
  "trades": 0,
  "pnl_usd": 0.0,
  "max_dd_pct": 0.0,
  "divergence_vs_backtest_pct": 0.0,
  "tca_verdict": "unknown",
  "kernel_denies": 0,
  "incidents": [],
  "confidence": 0.0,
  "notes": "Day N/3"
}
```

**Exit criteria for paper:** ≥3 calendar days **and** enough fills to approach statistical gates (stretch until regime diversity; calendar is **not** an auto-advance — `rollout.calendarIsNotAGate: true`).

---

## 6. Shadow / dry-run with live market data

**Shadow** means: live prices / mempool / routing decisions, full gate path, **no capital broadcast**.

Evolution outputs (DGM-H, GEPA, HyEvo, SIA, EurekAgent, etc.) stay **shadow-only** until a separate evolution YES (`promotion_gates.shadow_only_evolution`).

### Operator checklist for shadow

- [ ] `airGappedStaging: true` for evolution staging (`playbooks/promotion.yaml`)
- [ ] `titan-safety evolution status` — freeze if you are already protecting live capital elsewhere
- [ ] Edge routing latency-faithful (`paper_latency_faithful` / full mesh from paper)
- [ ] Compare shadow Sharpe vs backtest — divergence ≤ **15%** (`promotion_stats.max_shadow_divergence_pct`)
- [ ] Red-team checklist exercised (`playbooks/red_team_checklist.yaml`)

### Micro-live (still not “full live”)

§DEPLOY_LIFECYCLE Phase 3 / PRODUCTION_READINESS Phase 1:

- ≤ **0.1%** equity per trade
- Tiny notional; hard CB on micro-test capital
- Still requires healthy UPS + live adapters for anything that touches real wallets
- Trades >1% equity still need promotion-style YES / BFT path per policy

Do **not** jump from day-1 paper to full size.

---

## 7. Phase 5 human YES ceremony

### What you are saying YES to

You are authorizing **this subject** (strategy / phase5 go-no-go / flash-loan / etc.) to leave `PENDING_PROMOTION_APPROVAL` and touch live capital **within** kernel limits. You are **not**:

- Disabling `:19001`
- Approving every pipeline in the catalog
- Approving evolution forever
- Approving P22 or flash-loans unless those categories are in the approve command
- Approving closed/cloud models on the live path

### Preconditions (all must be true)

- [ ] Paper ≥ 3 days for the subject lane
- [ ] Shadow evidence + red-team review
- [ ] Statistical gate when category is stats-gated (`strategy_promotion`, `evolution_deploy`, `phase5_go_nogo`): ≥200 trades, DSR ≥0.90, PSR ≥0.90, cost realism, shadow divergence ≤15%
- [ ] Safety `:19001`–`:19008` healthy; fail-closed drill done
- [ ] Kill switch drill done (activate → DENY → signed RESUME)
- [ ] UPS + power-loss HALT drill done
- [ ] Live recon URL or equivalent wired; mock recon **not** used on live profile
- [ ] Signing path understood; `TITAN_LIVE_SIGNING_READY` still `0` until you intentionally arm
- [ ] Residual risks in `PRODUCTION_READINESS.md` accepted
- [ ] Evolution frozen if protecting live (`titan-safety evolution freeze`)

### Exact ceremony (copy-paste)

Categories allowed by CLI (`PromotionCategory`):

- `strategy_promotion`
- `evolution_deploy`
- `leverage_change`
- `flash_loan_live`
- `position_over_1pct_equity`
- `phase5_go_nogo`

**Phase 5 go / no-go (full live readiness for a subject):**

```bash
~/.openclaw/safety/bin/titan-safety promotion approve \
  --category phase5_go_nogo \
  --subject P5 \
  --response YES \
  --operator hyperion \
  --request-id "phase5-$(date -u +%Y%m%dT%H%M%SZ)"
```

**Per-strategy promotion:**

```bash
~/.openclaw/safety/bin/titan-safety promotion approve \
  --category strategy_promotion \
  --subject P5 \
  --response YES \
  --operator hyperion \
  --request-id "strat-P5-$(date -u +%Y%m%dT%H%M%SZ)"
```

**Flash-loan live (separate YES):**

```bash
~/.openclaw/safety/bin/titan-safety flashloan sim --count 100
~/.openclaw/safety/bin/titan-safety promotion approve \
  --category flash_loan_live \
  --subject flash_loan_global \
  --response YES \
  --operator hyperion \
  --request-id "fl-live-001"
# Then set flashLoanRouter.enabled + policy flash_loan_live.enabled — only after YES
```

**Anything other than exact `YES`:** not approved. Empty / TIMEOUT / “ok” / “lgtm” → **HOLD / de-risk**.

Audit log (append-only): `~/.openclaw/safety/promotion_audit.jsonl` (path may follow install layout — confirm on host).

### What NOT to do

- Do not script auto-YES from Telegram bots without Hyperion physical confirmation.
- Do not approve while kill switch is confused or kernel is down.
- Do not approve P22 in the same breath as a calm spot lane — use memecoin prerequisites (`memecoin sim`, filter honeypot DENY, Geyser/Jito).

---

## 8. Enabling live profile safely

> **This section documents operator steps that require Hyperion’s explicit intent.**  
> Following these steps without Phase 5 YES + adapters + UPS is an operational error.  
> This guide does **not** change your live host policy for you.

### 8.1 Fill secrets (never commit)

```bash
cp /path/to/titan-deploy/templates/infra/live.env.example ~/.openclaw/.env
chmod 600 ~/.openclaw/.env
${EDITOR:-nano} ~/.openclaw/.env
```

Minimum fields before first live attempt:

| Variable | Purpose |
|----------|---------|
| `TITAN_RECON_FETCHER_URL` | Position truth aggregator (preferred) |
| `ETH_RPC_URL` / `ERIGON_HTTP_URL` | EVM (prefer EDGE-FRA Erigon — not public Alchemy/Infura) |
| `SOLANA_RPC_URL` / `GEYSER_GRPC_URL` | Solana (if used) |
| `JITO_BLOCK_ENGINE_URL` | Jito (P22 / Solana shielded) |
| `TREZOR_BRIDGE_SOCKET` or `OPENCLAW_TREZOR_BRIDGE` | Ceremony / bridge socket |
| `TITAN_LIVE_SIGNING_READY` | Keep `0` until ready; then `1` |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_USER_ID` | Operator alerts |
| `NATS_URL` | Bus |

**Known wiring gap:** Even with bridge env set, `live_signer()` currently fails closed until the Trezor signing RPC is implemented/installed. Treat “arm signing” as a real engineering milestone, not a boolean flip.

### 8.2 Policy / openclaw profile

On the host:

1. Confirm `capital_profile: live` only when you intend live rules (mock banned).
2. Keep `paper` in `allowed_venues` for unpromoted / shadow lanes.
3. Confirm `signing.mode: in_process` and `signingNode.mode: in_process`.
4. Confirm `quantum.enabled: false`.
5. Confirm `ghost_evasion.enabled: true` and `require_shielded_path_live: true`.
6. Leave `memecoin_trench.enabled: false` and `flash_loan_live.enabled: false` until separate YES.
7. Leave `allocator.advisory_mode: true` until you deliberately enforce.

```bash
# Sanity: credentials status (no secret values printed)
python3 - <<'PY'
from titan_safety.adapters.live_bundle import credentials_status
import json
print(json.dumps(credentials_status(), indent=2))
PY
```

(If import path differs, run via `titan-safety` venv / `PYTHONPATH=~/.openclaw/safety`.)

### 8.3 systemd safety units

Typical units (names from `templates/systemd/`):

| Unit | Port |
|------|------|
| `titan-risk-kernel.service` | 19001 |
| `titan-reconciliation.service` | 19002 |
| `titan-status-aggregator.service` | 19003 |
| `titan-portfolio-risk.service` | 19004 |
| `titan-dead-mans-switch.service` | 19005 |
| `titan-allocator.service` | 19006 |
| `titan-tca.service` | 19007 |
| `titan-security-ops.service` | 19008 |
| `titan-signing-node.service` | 19010 **legacy optional only** |

```bash
# Example — adjust user vs system units to your install
sudo systemctl enable --now titan-risk-kernel.service
sudo systemctl enable --now titan-reconciliation.service
sudo systemctl enable --now titan-status-aggregator.service
sudo systemctl enable --now titan-portfolio-risk.service
sudo systemctl enable --now titan-dead-mans-switch.service
sudo systemctl enable --now titan-allocator.service
sudo systemctl enable --now titan-tca.service
sudo systemctl enable --now titan-security-ops.service

curl -s http://127.0.0.1:19003/health | python3 -m json.tool
```

Deploy helpers:

```bash
cd "/home/hyperion/Documents/Cursor Projects/titan-deploy"   # or your clone path
./deploy.sh --systemd --start-services --verify
```

### 8.4 Evolution freeze while live

```bash
~/.openclaw/safety/bin/titan-safety evolution freeze --operator hyperion --reason "live capital armed"
~/.openclaw/safety/bin/titan-safety evolution status
```

### 8.5 Edge bootstrap (at least FRA for Phase 1)

```bash
# After WireGuard peers exist
POP=EDGE-FRA bash ~/.openclaw/infra/edge_pop_bootstrap.sh
~/.openclaw/safety/bin/titan-safety edge route --venue jito --strategy P22
```

---

## 9. First live trade playbook

**Goal:** One tiny real fill (or intentional DENY) with full observability — not profit.

### Pre-flight (same hour)

```bash
curl -sf http://127.0.0.1:19003/health
~/.openclaw/safety/bin/titan-safety kill status          # must be inactive
~/.openclaw/safety/bin/titan-safety heartbeat            # DMS
~/.openclaw/safety/bin/titan-safety security status       # HARDENED preferred
~/.openclaw/safety/bin/titan-safety evolution status      # frozen if live
```

### Size

- Start at **≤ 0.1% equity** (micro-live), notional well under `max_notional_usd_per_trade`.
- Confidence ≥ 0.70 preferred; otherwise reduce size.
- Hard stop-loss attached **before** submit.
- Shielded venue only.

### Path

1. Signal agents propose → optional TradingAgents debate for non-arb lanes.
2. BFT 2-of-3 if required by size / policy.
3. TRENCH-OPS calls ExecutionGate / `titan-safety gate sign` (never signs in LLM process).
4. On ALLOW + receipt → in-process sign → edge broadcast ≤3 ms target.
5. Reconcile believed vs actual positions (`:19002`).
6. Ingest fill into TCA (`:19007`).

Example gate sign shape (from trench skill — adapt fields; do not invent bypass flags):

```bash
~/.openclaw/safety/bin/titan-safety gate sign --fast --trade '{
  "trade_id":"live-micro-001",
  "strategy_id":"P5",
  "venue":"uniswap_v3",
  "notional_usd":5,
  "side":"buy",
  "confidence":0.75
}'
```

If signing is not wired yet, expect **fail-closed** `NotConfiguredError` — that is correct behavior. Fix wiring; do not mock-sign.

### Monitoring during first trade

- HERALD / Telegram for CRITICAL
- `curl :19003/status` (or cockpit Health with advisory labels understood)
- Kernel logs / journald for DENY codes
- Edge RTT / broadcast errors

### Abort immediately if

- Unexpected ALLOW with kernel stopped (bypass)
- Recon divergence > threshold
- Velocity breaker trip
- Stealth DENY ignored by a skill (skill bug)
- UPS on battery
- Any signing without gate receipt

Abort commands: see [§12](#12-rollback--halt-procedures).

---

## 10. Ongoing production ops

### Daily

1. `curl :19003/health` — all green  
2. `titan-safety heartbeat`  
3. Recon divergence check  
4. Drawdown + velocity review  
5. Clear PENDING promotions (YES or explicit NO — never ignore)  
6. TCA scorecards — defund BLEEDING lanes (profit loop may be dry-run until enabled)

### Weekly

1. `titan-safety capital verify-audit`  
2. If equity ≥ $15K: Trezor sweep ceremony (20% of weekly profit)  
3. Review allocator envelope; keep ≤4 active pipelines unless you consciously raise cap  
4. Security posture: `titan-safety security status`

### Circuit breakers (software)

| ID / class | Typical action |
|------------|----------------|
| Loss velocity 60s / 15m | Kernel DENY / HALT |
| Drawdown tiers | Notify (template) / doctrine halt at high tiers — match your policy |
| `CB_RISK_KERNEL_UNREACHABLE` | Fail-closed DENY |
| `CB_KEYS_SIGNING_ENV_COMPROMISED` | Signing halted |
| `CB_STEALTH_PUBLIC_PATH` / `UNSHIELDED_VENUE` | Fail-closed DENY |
| `CB_SECURITY_LOCKDOWN` | Kill + freeze + signing halt + honeypot |
| Memecoin CBs (P22) | Cap / deny / halt lane |

### Dead-man’s switch

- Operator heartbeat miss > **48h** → de-risk  
- > **72h** → flatten  
- Never promotes  

### Selective activation

Do not turn on P22, flash-loans, and every MEV lane “because production.” Fund evidence-backed HEALTHY lanes only.

---

## 11. Cockpit + CLI monitoring during live

### Cockpit (`WEB_UI_LIVE_PRODUCTION_GUIDE.md`)

- `VITE_DATA_MODE=live` = **data providers** call `/api/*`.  
- Soft-fail returns fixtures with `advisory: true` if backends are down — **do not trust green alone**.  
- Useful routes: `/health`, `/promotions`, `/security`, `/signing`, Manual Control.  
- HMAC in Settings required for mutating control-plane calls.

### CLI essentials

```bash
curl -s http://127.0.0.1:19003/health | python3 -m json.tool
~/.openclaw/safety/bin/titan-safety kill status
~/.openclaw/safety/bin/titan-safety security status
~/.openclaw/safety/bin/titan-safety evolution status
~/.openclaw/safety/bin/titan-safety capital balance
~/.openclaw/safety/bin/titan-safety memecoin status   # expect disabled until YES

# Portfolio simulate
curl -s -X POST http://127.0.0.1:19004/v1/simulate \
  -H 'Content-Type: application/json' \
  -d '{"equity_usd":2500,"pipeline_id":"P5","notional_usd":25,"pipelines":[]}'
```

### Inference (live path)

| Port | Role |
|------|------|
| `:30000` | Tier 1 critical — GUARDIAN / TRENCH-OPS / signals |
| `:30001` | Tier 2 — ARCHON / SENTINEL / LAMARCK |
| `:30002` | Utility (TITANSPARK) |
| `:30005` / `:30003` | R&D only — **never** TRENCH-OPS / GUARDIAN live |

No closed/cloud models on live voters or execution.

---

## 12. Rollback / HALT procedures

### A. Global kill (fastest)

```bash
~/.openclaw/safety/bin/titan-safety kill activate --operator hyperion --reason "live abort"
~/.openclaw/safety/bin/titan-safety kill status
# Trades must DENY while active
```

Resume **only** with signed RESUME:

```bash
SIGNED=$(~/.openclaw/safety/bin/titan-safety kill sign --command RESUME --operator hyperion)
~/.openclaw/safety/bin/titan-safety kill deactivate --operator hyperion --signed "$SIGNED"
```

### B. Wind-down / safe mode

```bash
~/.openclaw/safety/bin/titan-safety wind-down safe-mode --operator hyperion --reason "de-risk"
~/.openclaw/safety/bin/titan-safety wind-down status
```

### C. Security lockdown (HMAC)

```bash
~/.openclaw/safety/bin/titan-safety security lockdown --operator hyperion --reason "incident" --dry-run
# Then real lockdown with signed HMAC — never LLM-alone
```

### D. Flatten

```bash
# Control-plane flatten requires X-Titan-Auth HMAC when auth_required
# Prefer documented playbooks/kill_switch.yaml + flatten executor
```

Kernel may request flatten; TRENCH-OPS / on-chain executors must actually close. If flatten adapter is incomplete, **manual close on shielded path** + revoke keys operationally.

### E. Power loss

On UPS battery / mains loss: policy says **halt trading**, flatten open positions, revoke session keys, require operator ack to resume. Do not discretionary-sign during outage.

### F. Promotion rollback

`playbooks/promotion.yaml` → `rollback.on_failure: revert_to_champion`. Keep champion artifacts in air-gapped staging.

---

## 13. Security & stealth for live capital

Four pillars (default armed):

| Pillar | Owner | Live meaning |
|--------|-------|--------------|
| Impenetrable | SENTINEL | Kernel, in-process signing, netns, PCR/CodeQL, DMS, closed-model ban |
| Evasion (Ghost) | TRENCH-OPS | No public RPC; MEV-shield / Jito / intents; fingerprint rotate; traffic jitter |
| Stalking | PREDATOR | Hunt copy-traders / probes |
| Predatory | PREDATOR | Honeypot lattice; poison fills ≤1% equity auto |

```bash
~/.openclaw/safety/bin/titan-safety security status
~/.openclaw/safety/bin/titan-safety security honeypot status
```

**Lockdown** requires operator HMAC — never auto from LLM alone (`iron-laws.md` §11).

**P22:** catalog until Phase 5 / memecoin YES + live profile flags. Toxicity lane — extra sims and filters first.

---

## 14. Go-live master checklist

Print this. Check boxes only when **true on the live host**.

### Constitution & autonomy

- [ ] Read `SOUL.md`, `iron-laws.md`, Bounded Autonomy Matrix
- [ ] Accept: kernel DENY absolute; BFT advisory; TIMEOUT ≠ YES
- [ ] Accept residual risks in `PRODUCTION_READINESS.md`

### Infra

- [ ] TITANHOME inference `:30000` / `:30001` healthy
- [ ] NATS up; Erigon / Solana feeds as needed
- [ ] UPS installed; power-loss HALT drill passed
- [ ] Edge PoP(s) bootstrapped; route check OK
- [ ] `./verify.sh` passes live-capital checks you care about

### Safety stack

- [ ] `:19001`–`:19008` healthy via `:19003`
- [ ] Fail-closed: kernel stop → DENY
- [ ] Kill switch drill + signed RESUME
- [ ] DMS heartbeat path tested
- [ ] Security Ops HARDENED; lockdown dry-run understood
- [ ] In-process signing path verified; `:19010` not required
- [ ] Evolution frozen while live capital armed

### Evidence

- [ ] Paper ≥ 3 days per lane
- [ ] Shadow / micro-live evidence recorded
- [ ] Statistical promotion gate passed (when required)
- [ ] Red-team checklist done

### Human YES

- [ ] `phase5_go_nogo` and/or `strategy_promotion` YES recorded in audit log
- [ ] Separate YES for flash-loan / P22 / leverage if applicable
- [ ] No auto-promote scripts

### Live wiring

- [ ] `~/.openclaw/.env` filled; mode 600
- [ ] `TITAN_RECON_FETCHER_URL` returns positions (or equivalent implemented)
- [ ] Mock recon/withdraw **not** active on live profile
- [ ] Trezor bridge + signing RPC actually wired (not just env vars)
- [ ] `TITAN_LIVE_SIGNING_READY=1` only after signing health OK
- [ ] Ghost shielded venues only
- [ ] First trade size ≤ 0.1% equity with hard stop

### Cockpit (optional but recommended)

- [ ] Production UI served per `WEB_UI_LIVE_PRODUCTION_GUIDE.md`
- [ ] Operator understands UI live ≠ capital live
- [ ] HMAC set for mutating actions

### Explicit non-goals still off

- [ ] P22 disabled unless YES + flags
- [ ] Flash-loan live disabled unless YES + flags
- [ ] Quantum agents absent; `quantum.enabled false`
- [ ] No closed/cloud models on live path
- [ ] Allocator still advisory unless you chose enforce

---

## 15. Troubleshooting live DENY / signing / edge

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| All trades DENY | Kill switch active; kernel down; lockdown | `kill status`; start kernel; check security lockdown |
| `STEALTH_PUBLIC_PATH` | Public RPC venue | Switch to shielded route / Erigon / Jito |
| `HUMAN_APPROVAL_REQUIRED` / promotion pending | >1% or gated category | Explicit YES or reduce size |
| `NotConfiguredError` live signing | `TITAN_LIVE_SIGNING_READY=0` or bridge RPC unwired | Keep fail-closed; finish `openclaw-trezor-bridge` wiring |
| Recon DENY / divergence | Missing `TITAN_RECON_FETCHER_URL` or stale aggregator | Fix aggregator; do not disable recon |
| Gate sign 401 / receipt rejected | Stale or missing `X-Titan-Gate-Receipt` | Re-run full ExecutionGate; receipt max age ~10s |
| Edge broadcast fail | PoP down / WireGuard | `edge route`; bootstrap PoP; failover PoP |
| Cockpit green but capital wrong | Soft-fail fixtures | Curl `:19003` yourself; ignore advisory UI |
| P22 always paper | `memecoin_trench.enabled false` / no YES | Leave off until ceremony + Geyser/Jito |
| Stats promotion DENY | <200 trades / low DSR/PSR | Stay paper/shadow; do not override |
| Power HALT | UPS battery / mains loss | Do not resume until mains + ack |

**Never** “fix” DENY by commenting out kernel calls, pointing to public RPC, or mock-signing on live profile.

---

## 16. Appendix

### A. Safety ports

| Port | Service |
|------|---------|
| 19001 | Risk kernel |
| 19002 | Reconciliation |
| 19003 | Status aggregator |
| 19004 | Portfolio risk |
| 19005 | Dead-man’s switch |
| 19006 | Capital allocator |
| 19007 | TCA / execution quality |
| 19008 | Security ops |
| 19010 | Signing **legacy HTTP only** (optional) |

### B. Inference ports

| Port | Tier |
|------|------|
| 30000 | Tier 1 critical (Qwen3-30B FP8) |
| 30001 | Tier 2 (Qwen3-Coder-80B) |
| 30002 | Utility TITANSPARK |
| 30003 | GLM-5.2 R&D secondary |
| 30005 | DeepSeek V4 Pro R&D primary |
| 30004 | Embeddings |
| 30020 | REVM sim |

### C. 20 classical agents (no quantum)

**Orchestrator / risk / security:** ARCHON, CORTEX, GUARDIAN, SENTINEL  

**Signals:** ORACLE, WRAITH, PREDATOR, AUGUR, NARRATIVE  

**Coding / execution / research:** TRENCH-OPS, LAMARCK, DARWIN_GODEL (shadow R&D)  

**Utility (TITANSPARK):** HERALD, NEXUS, FORGE, ALCHEMY, ATLAS, QUANT, ARBITER, HORIZON  

**Operator interface:** HYPERION  

**Removed:** QCC, QSA, QRP  

### D. Bounded Autonomy Matrix

| Action | Auto-execute | Human YES required |
|--------|--------------|-------------------|
| Routine trade <1% equity | YES | — |
| Trade >1% equity | — | YES (promotion gate) |
| Rebalance <1% equity | YES | — |
| New pipeline activation | — | YES |
| Model/skill promotion to live | — | YES (Phase 5) |
| Evolution deploy (DGM-H, GEPA, etc.) | Shadow only | YES for live |
| Leverage change | — | YES |
| Flash-loan live | YES (when policy + router enabled) | — |
| CB tier response (within policy) | YES | — |
| Drawdown velocity breach | HALT (kernel) | Alert operator |
| TIMEOUT on promotion prompt | HOLD/de-risk | Never auto-promote |

Authoritative enforcement: risk kernel `:19001` + portfolio risk `:19004`.

### E. Edge PoPs

| PoP | Region | Primary targets |
|-----|--------|-----------------|
| EDGE-FRA | Frankfurt | Erigon, Jito-FRA, ETH builders, Solana-EU |
| EDGE-TKY | ap-northeast-1 | Hyperliquid, Jito-TKY |
| EDGE-SIN | ap-southeast-1 | BSC / Pancake / Sui |
| EDGE-USE | us-east-1 | L2 sequencers, Flashbots Protect |
| EDGE-AMS | Amsterdam | Solana gRPC redundancy, Nostr, bridges |

### F. Glossary

| Term | Definition |
|------|------------|
| **Paper** | Simulated execution; no real capital broadcast |
| **Shadow** | Live data / decisions without capital impact (esp. evolution) |
| **Micro-live** | Real capital at ≤0.1% equity |
| **Phase 5 YES** | Explicit human promotion approval before full live |
| **ExecutionGate** | Unbypassable pre-trade pipeline producing a receipt |
| **Gate receipt** | Short-lived proof of ALLOW required for signing |
| **In-process signing** | `SigningNode` inside titan-safety (not agent runtime) |
| **BFT votes** | Advisory 2-of-3; not kernel override |
| **Ghost evasion** | Mandatory shielded execution paths for live |
| **Catalog ≠ checklist** | Spec mention does not mandate enablement |
| **UI live mode** | Cockpit data providers — not capital authorization |
| **Fail-closed** | On error / unreachable safety → DENY |
| **Harvest / R23** | Weekly Trezor sweep unlock at ≥$15K equity |

### G. Phased capital reminder (advisory calendar)

| Phase | Capital | Focus |
|-------|---------|-------|
| 0 | $0 | Infra + paper |
| 1 | ~$2.5K–10K | Micro-live; allocator advisory |
| 2 | ~$10K–50K | Scale; live recon 48h clean; allocator enforce optional |
| 3 | $50K+ | Proven lanes; sweeps at ≥$15K |

Calendar days are **targets**, not gates. Evidence and YES are gates.

---

## Closing statement

Titan’s production posture is **capital-preservation-first**: agents propose, deterministic safety vetoes, Hyperion owns promotion.  

This guide walks you to live capital **honestly**. It does not claim the repo alone makes trading safe or profitable. Software controls are **necessary**; paper/shadow evidence, UPS, live adapter wiring, stealth routes, and explicit **YES** are what make a go-live decision defensible.

When in doubt: stay on paper, keep signing disarmed (`TITAN_LIVE_SIGNING_READY=0`), and leave Phase 5 pending.
