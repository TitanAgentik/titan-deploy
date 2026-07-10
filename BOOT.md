# BOOT.md — Gateway Restart Checklist

> Full system manual: [`SYSTEM.md`](./SYSTEM.md)  
> Telegram operations: [`TELEGRAM_OPS_GUIDE.md`](./TELEGRAM_OPS_GUIDE.md)  
> Real-capital go-live: [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) (Phase 5 YES)

Keep short. Runs on gateway restart when internal hooks are enabled.

1. Confirm safety services healthy: `:19001`–`:19008` (`curl …/health`); signing is in-process (`titan-safety`) — do not require `:19010`
2. Confirm kill switch inactive: `titan-safety kill status`
3. Confirm evolution freeze if live capital: `titan-safety evolution status`
4. Confirm inference tiers up: `:30000` (critical), `:30001` (reasoning)
5. Confirm Telegram path: `titan-safety notify test --dry-run` (or `--format-only`)
6. Do **not** auto-promote or auto-resume halted pipelines
7. Notify HERALD only on CRITICAL/HIGH failures

Outbound alerts: `titan-safety notify` / herald_notify skill — do not spam routine OK.  
**No cockpit:** web UI archived at `archive/cockpit-web/` — Telegram is the sole operator surface.
