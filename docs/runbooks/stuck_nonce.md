# Runbook — Stuck Nonce / Pending Transaction

> **Severity:** HIGH  
> **Venues:** EVM (Erigon), Hyperliquid, Solana (different semantics)

## Detection

- Broadcast succeeds but no fill after timeout
- Subsequent txs fail with nonce too low / already known
- Reconciliation shows ghost position
- `signing_error_total` increment on optional `:19010`

## Immediate actions

1. **Stop broadcasting** for affected wallet: pipeline halt or portfolio kill.
2. Identify stuck tx hash from fill ledger / exchange UI.
3. Do **not** blindly increment nonce — verify pending pool.

## EVM

```bash
# Inspect pending (operator tools — cast/ethers on airgapped workflow)
# Replace nonce only after confirming stuck tx dropped or replaced
```

- Use private builder / Flashbots Protect for replacement if policy allows.
- Kernel must ALLOW replacement intent (notional ≤ caps).

## Hyperliquid

- Check order status via Hyperliquid API (EDGE-TKY).
- Cancel open orders before new nonce sequence.
- See `hyperliquid_live` adapter logs.

## Solana

- Blockhash expiry — rebroadcast with fresh blockhash.
- Jito bundle may need cancel path.

## Recovery

1. Clear pending state; reconciliation PASS.
2. Resume at micro-live cap only until 5 clean fills.
3. Log root cause in decision log reflection.

## References

- `docs/TIER0_MONEY_PATH.md`
- `templates/skills/trench_ops_execution/SKILL.md`
