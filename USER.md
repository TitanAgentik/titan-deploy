# Hyperion — Operator Profile

**Email:** titan.agentik@protonmail.com  
**Channel:** Telegram (primary — EDGE-FRA bot), Web Dashboard (secondary — LAN-only on workstation)  
**Role:** Sole human operator & decision authority  
**Timezone:** UTC  
**Physical location of workstation:** Hyperion's home (UPS-protected 240V mains, behind firewall)  
**Operating Mode:** Rust+Python hybrid (read code on critical-path PRs; maturin compilation active)

## Preferences

- **Selective activation:** catalog ≠ required set — fund few HEALTHY lanes (allocator `max_active_pipelines` default 4); do not enable every strategy/feature named in specs
- Trade notifications: JSON-first institutional format via HERALD (§TGCMD.3); immediate alert on material trades >0.5% equity or CRITICAL
- Daily brief at 08:00 UTC: portfolio snapshot, top 3 signals, risk flags, edge-mesh health, classical compute status (quantum dormant), Mac Mini vault status + BTC SPV sync height, §MAINT status (pending updates, days since last cycle, next window ETA), §RDSCOUT status (items crawled last 24h, candidates in triage, strategies in paper-trade, last promotion date)  
- Hourly reports at :00 UTC: institutional-grade performance report via §TGCMD.2 (overall summary, per-strategy breakdown with trade-level reason codes, system health, flags/pending actions)  
- Urgent alerts: immediate bypass of hourly schedule for critical errors, drawdown breaches ≥2% (tiered: 2/5/8/10/12%), security threats, hardware alarms (§TGCMD.2a)  
- Require approval: strategy promotion, evolution-touched agents (DGM-H/GEPA/HyEvo/SIA LoRA/EurekAgent), leverage changes, flash-loan live deploy, positions >1% equity
- Auto-execute: routine rebalances <1% equity, weekly profit sweeps (post-$15K), CB auto-responses per tier  
- Require approval: positions >2% equity, new token debuts, first-time strategies, DGM-H candidate promotions  
- Concise, data-first communication. No fluff. JSON before prose.  
- Escalate unusual patterns immediately via Telegram

## Approval Gates (Promotion & High-Risk Only)

- **Require approval:** strategy promotion (§DEPLOY_LIFECYCLE Phase 5 YES), evolution-touched agents (DGM-H, GEPA, HyEvo, SIA LoRA, EurekAgent), §GRIS model swap to live, leverage changes, flash-loan live deploy, positions >1% equity, new pipeline activation, model promotions
- **Auto-execute:** routine rebalances <1% equity, standard pipeline trades within GUARDIAN limits, weekly profit sweeps (post-$15K), CB tier responses (2%/5%/8%/10%/12%), shadow evolution outputs
- **TIMEOUT policy:** silence on promotion = HOLD/de-risk — never auto-promote
- **Dead-man's switch:** no operator heartbeat >48h → de-risk; >72h → flatten

## Risk Tolerance

- Max 2% equity risk per trade  
- Max 12% portfolio drawdown before full halt (2% alert / 5% soft / 8% reduce / 10% CRITICAL / 12% halt)
- 3+ consecutive losses → require manual sign-off for next trade  
- Quantum budget: **N/A** — quantum layer permanently disabled for live capital

## Capital Management (Simple)

Operator capital moves are **one-command** — no multi-agent approval for routine deposits/withdrawals.

| Command | Action |
|---------|--------|
| `/deposit <amount> <asset>` | Record inbound capital → updates `~/.openclaw/capital/portfolio_state.json` |
| `/withdraw <amount> <asset> [address]` | Initiate withdrawal (mock adapter until Trezor wired) |
| `/withdraw confirm <id>` | Confirm large withdrawal (>20% equity) |
| `/balance` | Show equity, available, reserved, phase (GROWTH/HARVEST) |
| `/sweep` | Trezor profit sweep (HARVEST phase ≥$15K only) |

CLI mirror: `~/.openclaw/safety/bin/titan-safety capital deposit|withdraw|balance|sweep`

- **Min operating reserve:** $500 (withdrawals cannot breach)
- **Large withdrawal gate:** >20% equity requires `/withdraw confirm`
- **Growth phase (<$15K):** 100% reinvest — sweeps paused
- **Harvest phase (≥$15K):** `/sweep` moves 20% of weekly profit to Trezor Safe 7
- **Audit:** append-only `~/.openclaw/capital/capital_audit.jsonl`

## Physical Access

- Workstation is under Hyperion's direct physical control  
- OOB: ASUS AST2600 BMC (onboard) — AST2600 BMC removed from BOM; LAN-isolated management only  
- Trezor Safe 7 hardware wallet holds long-term key material (weekly profit sweep per R23: 20% of profit every 7 days once total portfolio value ≥$15K; 100% reinvested below $15K; injections continue regardless)

## Production Rollout Phases

- **Duration:** Phase 0-3 each **3 calendar days** (operator directive — see PRODUCTION_READINESS.md caveat)
- **Gates unchanged:** kill criteria, metrics thresholds, drawdown limits, Phase 5 human YES
- **Does NOT auto-advance:** passing time alone never promotes; explicit operator approval required

## Capital Phase

- Start: Phase 1 (Foundation, $2,500 starting + biweekly $2,500 injections) — few funded lanes (allocator cap)  
- Growth: Phases 2-3 ($10K-$100K) — incremental pipeline activation  
- Full: Phase 4 ($100K+) — more capacity available — still fund HEALTHY lanes only + classical optimization (quantum dormant)  
- Transitions: event-triggered on 3-consecutive-day equity snapshots
