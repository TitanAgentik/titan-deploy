# Runbook — Partial Fill / Leg Risk

> **Severity:** MEDIUM–HIGH  
> **TCA:** `tca_bleeding_lanes`, fill rate collapse alert

## Detection

- Order partially filled; remainder cancelled or resting
- TCA `fill_rate` below `min_fill_rate` (policy default 0.80)
- Profit loop marks lane BLEEDING
- Multi-leg arb: one leg filled, hedge failed

## Immediate actions

1. **Assess exposure:** GUARDIAN portfolio sim via `:19004/v1/simulate`
2. If unhedged delta: flatten or hedge per pipeline playbook — fresh gate receipt required.
3. Halt pipeline if leg risk uncapped: `titan-safety kill pipeline halt --pipeline PX`

## TCA response

```bash
titan-safety tca daily-scorecard
titan-safety profit-loop status
```

- Auto-defund may trigger — refund requires promotion YES (`profit_loop.py`).

## Operator decisions

| Scenario | Action |
|----------|--------|
| Single partial, within Kelly | Monitor; adjust size down |
| Arb leg miss | Flatten immediately |
| Repeated partials | Defund lane; walk-forward review |

## Recovery

1. Root-cause: slippage model, venue liquidity, gas/tip budget.
2. Shadow re-run ≥3 days before re-promotion (`docs/TIER2_PROMOTION_QUALITY.md`).
3. Micro-live cap on re-entry.

## References

- `templates/safety/titan_safety/tca.py`
- `docs/TIER2_PROMOTION_QUALITY.md` §13
