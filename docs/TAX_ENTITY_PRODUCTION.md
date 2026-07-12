# Tax, Entity & Compliance — Production Requirements

> **Current code:** `templates/capital/tax_ledger.py` — **STUB** (FIFO lots, CSV export)  
> **Does not constitute tax advice.** Engage qualified counsel for jurisdiction-specific filing.

---

## Stub vs production

| Capability | Stub (repo) | Production requirement |
|------------|-------------|------------------------|
| Lot tracking | FIFO JSONL | FIFO + LIFO election per entity; wash-sale rules |
| Cost basis | USD at acquisition | Multi-currency FX at trade time; fee allocation |
| Disposal matching | Single wallet | Per-entity, per-account, per-chain |
| Jurisdiction | None | US / EU / SG entity map — separate ledgers |
| Entity separation | None | Trading LLC vs holdco vs personal — firewalled books |
| Audit trail | capital events hook | Immutable tie to `audit_chain` + exchange statements |
| Retention | Local JSONL | 7+ years WORM (`scripts/audit_export_worm.py`) |

---

## Production ledger requirements

### Lot tracking

- Every acquisition: `lot_id`, `asset`, `quantity`, `cost_basis_usd`, `acquired_at`, `venue`, `tx_hash`, `entity_id`
- Every disposal: matched lots, gain/loss, holding period (short/long)
- Staking rewards, airdrops, gas as separate lot types

### Jurisdiction

- Operator entity determines reporting currency and forms
- DeFi yield may be ordinary income at receipt — counsel decides
- Cross-chain bridges: document transfer vs taxable event

### Entity separation

```text
Entity A (trading)  → ~/.openclaw/capital/entity_a/tax_lots.jsonl
Entity B (treasury) → ~/.openclaw/capital/entity_b/tax_lots.jsonl
```

No commingling between entity ledgers. Sweeps to Trezor (R23) tag `entity_id` and `sweep_type`.

---

## Compliance notes

| Topic | Guidance |
|-------|----------|
| Best execution | TCA scorecard (`tca_daily_scorecard.py`) — document venue selection |
| Audit trail | Decision log hash chain + WORM export monthly |
| Retention | Policy `version` field versioned; align with `docs/CANONICAL_RUNBOOK.md` |
| AML/KYC | Off-chain operator responsibility — not automated in stub |
| Market manipulation | Red Team gauntlet + promotion registry for strategy changes |

---

## Wiring stub → production

1. Extend `TaxLedger` with `entity_id` and `jurisdiction` fields
2. Hook `sync_from_capital_event` to all fill ledger writes
3. Export monthly CSV + GL import format (operator ERP)
4. Run `harvest_dust_monthly.yaml` to validate sweep → disposal path

---

## References

- `templates/capital/tax_ledger.py`
- `tests/test_tax_ledger.py`
- `docs/TIER3_INSTITUTIONAL_OPS.md` §19
