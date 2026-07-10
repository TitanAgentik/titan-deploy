# Telegram Operations Guide

> **Sole operator surface:** HERALD delivers institutional-grade Telegram messages for all Titan operational events. The web cockpit has been **archived** (`archive/cockpit-web/`). Do not run it for production operations.

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
titan-safety notify test --format-only        # print message body
```

## CLI reference

| Command | Purpose |
|---------|---------|
| `titan-safety notify test` | Smoke test notification |
| `titan-safety notify test --queue` | Enqueue to `~/.openclaw/safety/herald_queue.jsonl` |
| `titan-safety notify send --title ... --event-type ... --description ...` | Custom alert |
| `titan-safety notify drain` | Flush queued events to Telegram |
| `titan-safety capital balance --telegram` | Capital events (existing HERALD formatter) |

Optional env:

| Variable | Default | Meaning |
|----------|---------|---------|
| `TITAN_TELEGRAM_ENABLED` | `1` | Set `0` to disable sends |
| `TITAN_TELEGRAM_DRY_RUN` | `0` | Set `1` to skip API |
| `TITAN_NOTIFY_GATE_ALLOW` | `0` | Set `1` to notify gate ALLOW (noisy) |

## Message format

Every alert uses the same institutional template (no emoji spam):

```
TITAN — {Title}
Severity: {INFO|LOW|MEDIUM|HIGH|CRITICAL}
Time: {ISO8601 UTC}
Agent: {AGENT_ID}
Event: {event_type}

Description
{plain-language summary}

Details
• key: value
...

Action Required
{operator next step or "None — informational only."}

Reason codes: {CODE1, CODE2}
```

## Severity legend

| Severity | When used |
|----------|-----------|
| **INFO** | Routine state, successful checks, gate ALLOW (if enabled) |
| **LOW** | Minor advisory, non-urgent health |
| **MEDIUM** | Trade lifecycle, signing success |
| **HIGH** | Denied trades, drawdown tiers, pipeline halt, promotion denial |
| **CRITICAL** | Global HALT, lockdown, signing failure, Phase 5 YES, UPS loss (when wired) |

## Events covered

| Event | Source module | Notes |
|-------|---------------|-------|
| Risk kernel ALLOW/DENY | `execution_gate` / `telegram_notify` | DENY always; ALLOW if `TITAN_NOTIFY_GATE_ALLOW=1` |
| Circuit breaker / drawdown tier | `drawdown_notifier` | Trading continues unless HALT tier |
| Trade intent submitted/filled/failed | `notify_trade_intent()` | Call from execution path |
| Signing success/fail | `signing_service` | In-process signing |
| Pipeline halt/resume | `kill_switch` | Per-pipeline and global |
| Agent health up/down | `notify_agent_health()` | Stub hook for FORGE |
| Security / lockdown | `security_ops` + `notify_security_posture()` | Four-pillar changes |
| Power / UPS | `notify_power_ups()` | Stub until UPS telemetry wired |
| Promotion / Phase gates | `promotion_gate` | Includes Phase 5 YES |
| Trezor weekly sweep | `capital.sweep` | HARVEST phase |
| Health / verify failures | `notify_health_failure()` | Call from verify hooks |

Module path: `templates/safety/titan_safety/telegram_notify.py`

## HERALD queue

Events are appended to `~/.openclaw/safety/herald_queue.jsonl` before send. If Telegram is temporarily unavailable, drain later:

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
