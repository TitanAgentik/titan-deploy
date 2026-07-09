---
name: herald_notify
description: HERALD institutional Telegram trade notifications — JSON-first payloads + Markdown alerts (§TGCMD.2 / §TGCMD.3)
metadata:
  openclaw:
    status: active
    agent: HERALD
    tier: T2
  skill_tuple:
    intent: herald_notify
    method: template_render
    difficulty: medium
---

# Herald Notify

Institutional-grade Telegram notifications for trades, PnL, strategies, and hourly digests.

## Contract

Every notification MUST include:

1. **JSON payload** (schema `trade_notification.v1.json`) — machine-parseable
2. **Telegram Markdown** — scannable on mobile
3. **ISO 8601** `timestamp`, `agent_id`, `pipeline_id`, `reason_codes` (≥1)

## Severity Icons

| Icon | Meaning |
|------|---------|
| ✅ | Profit / WIN |
| ❌ | Loss |
| ⚡ | Trade execution |
| 📊 | Hourly / summary digest |

## Routing

| Event | NATS topic | Delivery |
|-------|------------|----------|
| Trade entry/exit | `tgcmd.herald.trade` | Immediate if material (>0.5% equity) |
| PnL realized | `tgcmd.herald.pnl` | Immediate if material |
| Hourly digest | `tgcmd.herald.report.hourly` | `:00 UTC` cron |
| Urgent alert | `tgcmd.herald.alert.urgent` | Immediate (§TGCMD.2a) |
| Drawdown tier cross | `herald_queue.jsonl` → `drawdown_tier` | Immediate CRITICAL/HIGH — **trading continues** |
| Capital deposit/withdraw | operator Telegram → `titan_safety.telegram_capital` | Immediate on large withdraw |

## Operator Capital Commands (Simple)

| Command | Description |
|---------|-------------|
| `/deposit <amount> <asset>` | Record inbound capital |
| `/withdraw <amount> <asset> [address]` | Initiate withdrawal |
| `/withdraw confirm <id>` | Confirm large withdrawal (>20% equity) |
| `/balance` | Portfolio equity / available / reserved |
| `/sweep` | Trezor profit sweep (HARVEST ≥$35K) |
| `/capital deposit\|withdraw\|balance\|sweep` | Alternate prefix |

CLI: `titan-safety capital deposit|withdraw|balance|sweep|telegram --text "..."`

Render capital events: `render_capital(result)` or `notify.py capital` smoke test.

Material threshold: **0.5% portfolio equity** OR severity `CRITICAL` / `HIGH`.

## Assets

```
~/.openclaw/workspace/telegram/
  schema/trade_notification.v1.json
  reason_codes.yaml
  templates/*.md
~/.openclaw/workspace/skills/herald_notify/notify.py
```

## Usage

```python
from notify import render, render_hourly_digest, should_send_immediate

payload = {
    "event_type": "trade_execution",
    "timestamp": "2026-07-02T20:15:33Z",
    "agent_id": "TRENCH-OPS",
    "pipeline_id": "P3",
    "reason_codes": ["SIGNAL_ARB_GAP"],
    "severity": "INFO",
    "trade": { ... },
    "strategy": { ... },
    "risk": { ... },
}

msg = render(payload)
# msg.telegram_text → send via Telegram bot
# msg.immediate → bypass hourly batch if True
```

CLI smoke test:

```bash
python3 ~/.openclaw/workspace/skills/herald_notify/notify.py
python3 ~/.openclaw/workspace/skills/herald_notify/notify.py pnl
python3 ~/.openclaw/workspace/skills/herald_notify/notify.py digest
```

## Reason Codes

See `~/.openclaw/workspace/telegram/reason_codes.yaml`. Examples:

- `SIGNAL_CONFLUENCE`, `SIGNAL_ARB_GAP`, `STOP_LOSS`, `CB_TRIGGER`, `TAKE_PROFIT`

## Integration

- **HERALD agent** owns all Telegram I/O (AGENTS.md)
- **Hermes cron** `hourly_report` → `render_hourly_digest()`
- **TRENCH-OPS / ALCHEMY** publish to `tgcmd.herald.trade` on fill
- **GUARDIAN** may append `CB_TRIGGER` reason codes on risk events
- Config: `~/.hermes/config.yaml` → `notifications.telegram`
- Gateway: `~/.openclaw/openclaw.json` → `gateway.telegram` + `notifications`

## Format Reference

Aligned with §TGCMD.2 hourly report sections and §TGCMD.3 real-time trade notifications (informational mode — no approval queue per USER.md autonomy).
