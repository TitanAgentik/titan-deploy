# BOOT.md — Gateway Restart Checklist

Keep short. Runs on gateway restart when internal hooks are enabled.

1. Confirm safety services healthy: `:19001`–`:19008` (`curl …/health`); signing is in-process — do not require `:19010`
2. Confirm kill switch inactive: `titan-safety kill status`
3. Confirm evolution freeze if live capital: `titan-safety evolution status`
4. Confirm inference tiers up: `:30000` (critical), `:30001` (reasoning)
5. Do **not** auto-promote or auto-resume halted pipelines
6. Notify HERALD only on CRITICAL/HIGH failures

Outbound alerts: use the message tool / herald_notify — do not spam routine OK.
