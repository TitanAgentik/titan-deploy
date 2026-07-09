# §COCKPIT_detail.md

> **Reconstructed companion** for OpenClaw + Hermes deploy.
> Original `COCKPIT_detail.md` was referenced by TITAN.md but never present on disk.
>
> **Purpose:** Operator capital deposit/withdraw CLI — not profit attribution.
>
> **Runtime source of truth:** live files under `templates/`, `output/`, and
> `~/.openclaw` / `~/.hermes` after `./deploy.sh` — not this markdown dump.
>
> Docs: [OpenClaw workspace](https://docs.openclaw.ai/concepts/agent-workspace) ·
> [Hermes context files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)

---

## Capital commands (ledger, not PnL)

```bash
titan-safety capital deposit --amount 2500 --asset USDC --operator YOU
titan-safety capital withdraw --amount 100 --asset USDC --confirm-yes --operator YOU
titan-safety capital balance
```

Telegram: `/deposit 2500 USDC` (parsed by `telegram_capital`).

Deposits credit `equity_usd` / `available_usd`. Trading profit is tracked via
TCA / weekly_profit — **do not confuse with deposits**.

Withdrawals require `--confirm-yes` (or pending `--confirm REQUEST_ID`).
Live withdrawals route through signing node when `withdrawal_adapter: trezor_signing`.
