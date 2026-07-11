# Archived copy — Titan Agentik Web Cockpit

**Status:** Backup snapshot. **Do not use for production operations.**

The sole operator surface is **Telegram via HERALD**. See [`../../TELEGRAM_OPS_GUIDE.md`](../../TELEGRAM_OPS_GUIDE.md).

The active dev path is **`web/`** at the repo root (restored for local reference). This `archive/cockpit-web/` directory is a frozen copy from the decommission commit — use `web/` for day-to-day local development.

## Why archived

- Operator visibility is delivered as institutional-grade Telegram messages (names, severity, timestamps, details, action required).
- The risk kernel (`:19001`), execution gate, and in-process signing remain authoritative — no dashboard overrides them.
- Reduces attack surface (no browser admin console on `:5173`).

## If you need to browse the UI locally (non-production)

```bash
cd web
npm install
npm run dev
```

(Equivalent archive copy: `cd archive/cockpit-web` — prefer `web/`.)

Open http://127.0.0.1:5173 on localhost only. Fixture data and advisory labels apply; **UI live ≠ capital live**.

## Pointers

- Telegram ops: [`TELEGRAM_OPS_GUIDE.md`](../../TELEGRAM_OPS_GUIDE.md)
- System manual: [`SYSTEM.md`](../../SYSTEM.md)
- CLI: `titan-safety notify test`, `titan-safety kill status`, `curl :19003/health`
