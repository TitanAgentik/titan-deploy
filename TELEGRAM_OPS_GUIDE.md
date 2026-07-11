# Telegram Operations Guide

> **Sole production operator surface:** HERALD delivers institutional-grade Telegram messages for all Titan operational events. The React cockpit (`web/`) is for **local dev/reference** only — do not expose it for production operations. Frozen backup: `archive/cockpit-web/`.

## Quick setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather). Copy the **bot token**.
2. Start a chat with your bot (or add it to an operator group).
3. Obtain your **chat ID** (user or group). Tools: `@userinfobot`, or inspect `getUpdates` after messaging the bot.
4. Set environment variables in `~/.openclaw/.env` (never commit secrets):

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
# Legacy alias also supported:
# TELEGRAM_USER_ID=your_chat_id_here
```

5. Smoke test:

```bash
titan-safety notify test --dry-run          # format only, no API
titan-safety notify test                      # sends if creds set
titan-safety notify test --format-only        # print message body (includes sample PnL)
```

## CLI reference

| Command | Purpose |
|---------|---------|
| `titan-safety notify test` | Smoke test notification (includes sample Financial Summary) |
| `titan-safety notify test --queue` | Enqueue to `~/.openclaw/safety/herald_queue.jsonl` |
| `titan-safety notify send --title ... --event-type ... --description ...` | Custom alert |
| `titan-safety notify pnl --realized 142.88 --pct-equity 0.55 --pipeline P3 --asset WETH/USDC --outcome WIN` | Realized PnL alert |
| `titan-safety notify digest` | Send sample hourly digest via HERALD renderer |
| `titan-safety notify digest --format-only` | Preview hourly digest without sending |
| `titan-safety notify drain` | Flush queued events to Telegram |
| `titan-safety capital balance --telegram` | Capital events (existing HERALD formatter) |

Optional env:

| Variable | Default | Meaning |
|----------|---------|---------|
| `TITAN_TELEGRAM_ENABLED` | `1` | Set `0` to disable sends |
| `TITAN_TELEGRAM_DRY_RUN` | `0` | Set `1` to skip API |
| `TITAN_NOTIFY_GATE_ALLOW` | `0` | Set `1` to notify gate ALLOW (noisy) |

## Message format

Every institutional alert uses the same template (no emoji spam):

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

## Financial fields operators see

| Event | Money fields shown |
|-------|-------------------|
| **Trade fill** (institutional) | `notional_usd`, optional `pnl` block (net, outcome) |
| **Trade fill** (HERALD) | P&L line with `net_usd`, `% equity`, fees; portfolio footer |
| **PnL close** (HERALD `pnl_close.md`) | Entry/exit prices, net P&L, fees, slippage, WIN/LOSS icon |
| **Risk kernel DENY** | Optional portfolio snapshot (equity, exposure, open positions) |
| **Trezor sweep** | Sweep amount prominently in description + Financial Summary |
| **Hourly digest** | Hour P&L, daily P&L, win rate, per-strategy breakdown, gas/fees |
| **Money summary** | Realized + unrealized + daily rollup with win/loss counts |

### Example: institutional trade fill with PnL

```
TITAN — Trade Intent Filled
Severity: MEDIUM
...
Description
Trade tx-20260702-00142 status: filled. Net P&L: +$142.88.

Financial Summary
Realized: +$142.88 (+0.55% equity)
Equity: $261,042.18 | Exposure: 12.40% | Open: 7
Outcome: WIN
```

### Example: HERALD PnL close

```
✅ PROFIT — P3
━━━━━━━━━━━━━━━━━━━━━━━━━━
P3 | flash_loan_arb_eth_mainnet
LONG WETH/USDC | ethereum
Entry 3,860.40 → Exit 3,891.22
P&L: +142.88 (+0.55% equity)
Fees: $5.55 | Slippage: 4.20 bps
```

### Example: hourly digest

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

## Severity legend

| Severity | When used |
|----------|-----------|
| **INFO** | Routine state, successful checks, gate ALLOW (if enabled) |
| **LOW** | Minor advisory, non-urgent health |
| **MEDIUM** | Trade lifecycle, signing success, small PnL closes |
| **HIGH** | Denied trades, drawdown tiers, pipeline halt, material PnL |
| **CRITICAL** | Global HALT, lockdown, signing failure, Phase 5 YES, UPS loss (when wired) |

## Events covered

| Event | Source module | Notes |
|-------|---------------|-------|
| Risk kernel ALLOW/DENY | `execution_gate` / `telegram_notify` | DENY always; portfolio snapshot on DENY |
| Circuit breaker / drawdown tier | `drawdown_notifier` | Trading continues unless HALT tier |
| Trade intent submitted/filled/failed | `notify_trade_intent()` | PnL on filled/failed |
| PnL realized / unrealized | `notify_pnl_realized()` / `notify_pnl_unrealized()` | Financial Summary block |
| Money summary rollup | `notify_money_summary()` | Periodic operator digest |
| Signing success/fail | `signing_service` | In-process signing |
| Pipeline halt/resume | `kill_switch` | Per-pipeline and global |
| Agent health up/down | `notify_agent_health()` | Stub hook for FORGE |
| Security / lockdown | `security_ops` + `notify_security_posture()` | Four-pillar changes |
| Power / UPS | `notify_power_ups()` | Stub until UPS telemetry wired |
| Promotion / Phase gates | `promotion_gate` | Includes Phase 5 YES |
| Trezor weekly sweep | `capital.sweep` / `notify_trezor_sweep()` | Sweep amount in Financial Summary |
| Hourly digest | `notify_hourly_digest()` / HERALD cron | Full P&L + win rate |
| Health / verify failures | `notify_health_failure()` | Call from verify hooks |

Module paths:
- Institutional: `templates/safety/titan_safety/telegram_notify.py`
- HERALD trade format: `templates/skills/herald_notify/notify.py` + `templates/telegram/templates/`

## HERALD queue

Events are appended to `~/.openclaw/safety/herald_queue.jsonl` before send. Records with `pnl` or `portfolio` keys are rendered with Financial Summary. HERALD-format events (`hourly_digest`, `pnl_realized`, `trade_execution`) delegate to the herald renderer on drain.

```bash
titan-safety notify drain
```

## Capital commands (operator → bot)

| Telegram command | Action |
|------------------|--------|
| `/balance` | Equity / available / reserved |
| `/deposit <amount> <asset>` | Record deposit |
| `/withdraw <amount> <asset>` | Initiate withdrawal |
| `/sweep` | Trezor profit sweep (≥ $15K equity) |

## What replaced the cockpit

| Old surface | Replacement |
|-------------|-------------|
| Dashboard / PnL pages | Hourly digest + trade notifications (HERALD) |
| Risk & CBs page | `titan-safety kill status`, drawdown Telegram alerts |
| Health & Verify | `curl :19003/health`, `titan-safety notify` on failures |
| Promotions UI | `titan-safety promotion approve`, Telegram gate messages |
| Manual control UI | CLI + signed commands (`titan-safety kill sign`) |

Archived UI: [`archive/cockpit-web/README.md`](archive/cockpit-web/README.md) (reference only).

## Safety notes

- Telegram is **notify-only**. It cannot override risk kernel DENY or bypass signing.
- No closed/cloud models on the live path.
- Phase 5 live capital still requires explicit operator YES — Telegram does not auto-promote.
