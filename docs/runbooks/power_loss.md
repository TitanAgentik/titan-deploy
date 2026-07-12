# Runbook — Power Loss / UPS Event

> **Severity:** CRITICAL  
> **Alert:** `TitanUpsBatteryLow`, `notify_power_ups` (STUB until UPS telemetry wired)  
> **Policy:** `templates/risk_kernel/policy.yaml` → `power_loss`

## Detection

- Eaton UPS SNMP/USB telemetry (operator STUB) → `ups_battery_percent` metric
- Manual: mains failure, UPS beep, FORGE host brownout
- Kernel may auto-HALT on `power_loss.action: halt_trading`

## Immediate actions (0–5 min)

1. **Do not open new risk.** Verify kill switch not required yet.
2. Send Telegram heartbeat if DMS active: `titan-safety dms heartbeat --operator YOU`
3. Check `:19001/health` and `:19005/health` from console (not web cockpit).
4. If battery < 20%: `titan-safety kill portfolio --operator YOU --reason "UPS event"`

## Graceful shutdown (5–15 min)

```bash
titan-safety kill activate --operator YOU --reason "power loss — graceful halt"
systemctl stop titan-risk-kernel titan-reconciliation titan-openclaw-gateway  # order: gate first
```

5. Confirm no in-flight broadcasts: review `hyperliquid_fill_ledger.jsonl` tail.
6. Document event in operator log with ISO timestamp.

## Recovery

1. Restore mains; verify UPS battery charging.
2. Boot TITANHOME per `BOOT.md`; run `./verify.sh`.
3. Reconciliation must PASS before RESUME: `titan-safety recon status`
4. `titan-safety kill deactivate` only after operator root-cause note.
5. Re-enable pipelines individually — not global auto-resume.

## Quarterly drill

See `templates/playbooks/ups_quarterly_drill.yaml`.

## References

- `templates/playbooks/kill_switch.yaml`
- `docs/AGENT_HOST_SECURITY.md` — BusKill checklist
