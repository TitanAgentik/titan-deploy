# Runbook — RPC Eclipse / Stale Chain Data

> **Severity:** HIGH  
> **Risk:** Trades priced on forked or censored state; reconciliation diverge.

## Detection

- Reconciliation denies spike (`TitanReconciliationDiverge` alert)
- Believed position ≠ exchange position
- Block height lag vs independent source (Erigon on EDGE-FRA vs local RPC)
- Fill ledger gaps; nonce stuck (see `stuck_nonce.md`)

## Immediate actions

1. **Halt new entries:** `titan-safety kill portfolio --operator YOU --reason "RPC eclipse"`
2. Compare block heights from ≥3 sources (R17 signal rule applies to infra).
3. Switch edge routing per `edge_router.py` — lowest live p50 RTT **with** health check.
4. Review `openclaw.json` → no public RPC pools on live path.

## Diagnosis

```bash
titan-safety recon status
titan-safety recon pre-trade --dry-run  # if exposed
curl -s http://127.0.0.1:19002/health
```

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Single venue stale | PoP RPC bad | Failover edge per `edge_mesh.yaml` |
| All EVM stale | Local Erigon lag | Pause EVM lanes; use EDGE-FRA archive |
| Solana slot drift | gRPC provider | Switch AMS/FRA redundancy |

## Recovery

1. Confirm canonical chain tip matches exchange.
2. Reconciliation PASS for 3 consecutive checks.
3. Resume pipelines one at a time; micro-live caps apply (`micro_live_caps.py`).

## Prevention

- Cross-validate ≥3 RPC sources before re-enable.
- FORGE edge RTT probes → `memory/infra/rtt.jsonl` (alert `TitanEdgeRttDegraded`).

## References

- `templates/infra/edge_mesh.yaml`
- `docs/TIER0_MONEY_PATH.md`
