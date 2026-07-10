# Archived — Titan Agentik Web Cockpit

**Status:** Decommissioned. **Do not use for production operations.**

The sole operator surface is **Telegram via HERALD**. See [`../../TELEGRAM_OPS_GUIDE.md`](../../TELEGRAM_OPS_GUIDE.md).

This React/Vite UI was moved from `web/` for historical reference only. It is not installed, served, or supported in the current deploy bundle.

## Why archived

- Operator visibility is delivered as institutional-grade Telegram messages (names, severity, timestamps, details, action required).
- The risk kernel (`:19001`), execution gate, and in-process signing remain authoritative — no dashboard overrides them.
- Reduces attack surface (no browser admin console on `:5173`).

## If you need to browse the old UI locally (non-production)

```bash
cd archive/cockpit-web
npm install
npm run dev
```

Open http://127.0.0.1:5173 on localhost only. Fixture data and advisory labels apply; **UI live ≠ capital live**.

## Pointers

- Telegram ops: [`TELEGRAM_OPS_GUIDE.md`](../../TELEGRAM_OPS_GUIDE.md)
- System manual: [`SYSTEM.md`](../../SYSTEM.md)
- CLI: `titan-safety notify test`, `titan-safety kill status`, `curl :19003/health`
