# HEARTBEAT — Scheduled Tasks

Natural-language scheduling for Hermes cron + OpenClaw heartbeat.

## Daily

- **08:00 UTC — Daily Brief (HERALD → Telegram)**
  Portfolio snapshot, top 3 signals, risk flags, edge-mesh health, vault status,
  §MAINT status, §GRIS digest (5-15 candidates from 800+ daily triage).

## Hourly

- **:00 UTC — Performance Report (§TGCMD.2)**
  Institutional digest via `herald_notify` skill: JSON payload + Markdown summary.
  Overall summary, per-strategy breakdown with trade-level reason codes,
  system health, flags/pending actions. Informational only — no per-trade approval queue.

## Operator Heartbeat (Dead-Man's Switch)

- **Daily ping:** Operator `OK` or any Telegram command resets heartbeat timer
- **>48h miss:** De-risk — reduce positions 50%, pause new entries, CRITICAL alert
- **>72h miss:** Flatten to stable collateral; halt non-routine pipelines
- **Never:** Auto-promote strategies or evolution on operator absence
- **Recovery:** Operator sends `RESUME` after restoring heartbeat

## Real-Time Trade Notifications (§TGCMD.3)

- **HERALD → Telegram** on every trade fill (entry/exit)
- **Immediate alert** when material: >0.5% equity impact OR severity CRITICAL/HIGH
- **Portfolio footer** appended on material events
- Templates: `~/.openclaw/workspace/telegram/templates/`
- Formatter: `~/.openclaw/workspace/skills/herald_notify/notify.py`

## Continuous Heartbeats

- **ARCHON:** orchestration loop — delegate tasks, monitor agent health (30s)
- **GUARDIAN:** risk scan — position sizing, drawdown tiers, CB triggers (15s)
- **NEXUS:** data feed health — RPC latency, feed staleness (60s)
- **FORGE:** infrastructure — service health, GPU inference schedule, NATS bus, UPS telemetry (60s)
- **SENTINEL:** security scan — CodeQL gate, dissent review queue (5m)

## Weekly

- **Monday 09:00 UTC — HORIZON R&D Brief**
  Compute ledger, skill evolution summary, dissent log review.

- **Sunday 22:00 UTC — Profit Sweep Check (ATLAS)**
  If portfolio ≥$35K: sweep 20% of weekly profit to Trezor Safe 7.

## GPU Schedule (TITANHOME)

- **Priority 1-2 inference:** GLM-5.2 orchestrator + REVM — **NEVER preempted** during market hours
- **Off-peak only:** CuEVM fuzzing, Monte Carlo backtest, skill evolution training (06:00-10:00 UTC or 22:00-06:00)
- Spec: `~/.openclaw/infra/gpu_schedule.yaml` — enforced by FORGE heartbeat

## Phase-Dependent

- **Phase 1 ($2,500):** Few funded lanes only (e.g. P1/P3/P7/P8/P11 as capital allows) — not the full catalog
- **Phase 2 ($10K+):** Add lanes only when TCA/allocator funds them (e.g. P29/P6/P18 when healthy)
- **Phase 3 ($50K+):** Optional expansion (P34/P40/P41) — still capped by `max_active_pipelines`
- **Phase 4 ($100K+):** More capacity available — still **not** "run every pipeline"; fund HEALTHY lanes only

Catalog size ≠ required set. Allocator `max_active_pipelines` (default 4) is the hard concentration cap.

## CRITICAL Alert Bypass

Immediate Telegram alert (bypasses hourly schedule) for:
1. 12% drawdown in 24h
2. Hardware failure (GPU/CPU/NVMe)
3. Security breach
4. DGM-H SOUL.md modification attempt
5. Exchange API failure >5min
6. Unknown smart contract interaction
