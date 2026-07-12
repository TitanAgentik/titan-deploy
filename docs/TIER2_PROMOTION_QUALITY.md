# Tier 2 Promotion Quality — Items 11–14

> **Scope:** Research / promotion quality gates before scale-up. Complements [`docs/TIER1_CAPITAL_RISK.md`](./TIER1_CAPITAL_RISK.md).  
> **Does not auto-enable live capital** — Phase 5 human YES + operator checklist still required.

**Policy source:** `templates/risk_kernel/policy.yaml` → `tier2_promotion_quality` + `promotion_stats` + `v1_surface_lockdown.yaml`.

---

## Status matrix

| # | Requirement | Enforced (code) | Documented | Notes |
|---|-------------|-----------------|------------|-------|
| 11 | Walk-forward mandatory | **DONE** | **DONE** | `promotion_stats.py` `require_walk_forward` |
| 11 | Purged CV mandatory | **DONE** | **DONE** | `purged_cv_passed` flag in stats gate |
| 11 | Cost model + fat slippage | **DONE** | **DONE** | `min_fat_slippage_bps`, `cost_bps > 0` |
| 11 | Capacity curves | **DONE** | **DONE** | `capacity_curve_ok` in stats gate |
| 11 | Deflated Sharpe (multiple-testing) | **DONE** | **DONE** | `promotion_registry.py` global trial count |
| 11 | Shadow mode N days + divergence bounds | **DONE** | **DONE** | `min_shadow_days`, `max_shadow_divergence_pct` |
| 12 | Micro-live ≤0.05–0.1% equity | **DONE** | **DONE** | `micro_live_caps.py` |
| 12 | No $10–50k jump on short phases | **DONE** | **DONE** | `max_jump_notional_usd: 500` |
| 12 | Calendar is NOT a gate | **DONE** | **DONE** | `calendar_is_gate: false` enforced in code |
| 13 | BLEEDING auto-defund | **DONE** | **DONE** | `profit_loop.py` (pre-existing) |
| 13 | Refund requires promotion YES | **DONE** | **DONE** | `profit_loop.refund()` + audit check |
| 13 | Daily TCA scorecard → Telegram | **DONE** | **DONE** | `tca daily-scorecard` + `notify_tca_daily_scorecard` |
| 14 | v1 disable P22 / flash / honeypots / QI / 5-PoP | **DONE** | **DONE** | `v1_surface_lockdown.yaml` + `v1_surface.py` |
| 14 | One chain, one venue class, ≤2 strategies | **DONE** | **DONE** | Hyperliquid + allocator cap 2 |
| 14 | Catalog ≠ checklist in allocator | **DONE** | **DONE** | `selective_activation` + v1 pipeline blocks |

---

## 11. Promotion as a product

### Statistical evidence gate (`promotion_stats.py`)

Mandatory before `strategy_promotion` / `phase5_go_nogo`:

| Check | Threshold | Metadata field |
|-------|-----------|----------------|
| Deflated Sharpe | ≥ 0.90 | `returns`, `trials` (from registry) |
| PSR | ≥ 0.90 | computed |
| Min trades | ≥ 200 | `num_trades` |
| Walk-forward | ≥ 5 folds pass | `walk_forward_folds_passed` |
| Purged CV | pass | `purged_cv_passed: true` |
| Fat slippage | ≥ 5 bps modeled | `fat_slippage_bps` |
| Capacity curve | validated | `capacity_curve_ok: true` |
| Shadow days | ≥ 3 | `shadow_days` |
| Shadow gas/tip sim | required | `shadow_gas_tip_simulated: true` |
| Shadow divergence | ≤ 15% | `backtest_sharpe` / `shadow_sharpe` |

### Multiple-testing registry (`promotion_registry.py`)

Append-only `~/.openclaw/safety/promotion_registry.jsonl` records every config tried. Global trial count raises the DSR benchmark automatically.

```bash
titan-safety promotion registry summary
titan-safety promotion registry list --strategy-id P5
```

### Walk-forward / purged CV computation

**STUB:** ARBITER / QUANT supply fold results via `strategy_stats` metadata. Gate enforcement is **DONE**; external backtest runner wiring is operator-side.

---

## 12. Paper ≠ live micro (`micro_live_caps.py`)

| Phase | Max % / trade | Max aggregate % | Min fills to scale |
|-------|---------------|-----------------|-------------------|
| `micro_live_conservative` | 0.05% | 0.25% | 50 |
| `micro_live` | 0.10% | 0.50% | 50 |
| `validated_scale` | 0.50% | 2.0% | 200 + YES |

```bash
titan-safety micro-caps --notional 100 --equity 50000 --phase micro_live_conservative
```

`rollout.calendarIsNotAGate: true` in `openclaw.json` — phase clock is advisory only.

---

## 13. TCA closed loop

### Auto-defund BLEEDING

```bash
titan-safety tca profit-loop --equity 10000
```

### Refund gate

Requires literal `YES` reason **and** `strategy_promotion` approval in audit log for that pipeline.

### Daily scorecard

```bash
titan-safety tca daily-scorecard --equity 25000
titan-safety tca daily-scorecard --format-only --no-send
```

Schedule via systemd/cron → HERALD Telegram digest (`event_type: tca_daily_scorecard`).

---

## 14. v1 surface lockdown

Config: `templates/risk_kernel/v1_surface_lockdown.yaml`

| Disabled for v1 | Enforcement |
|-----------------|-------------|
| P22 memecoin | `blocked_pipeline_ids` + `memecoinTrench.enabled: false` |
| Flash loans | `flash_loan_live.enabled: false` + v1 check |
| Predatory honeypots (live lanes) | `predatory_honeypot_live: false` |
| Quantum-inspired live | `quantum_inspired.advisory_only` |
| 5-PoP mesh | `edgeMesh.mode: single_pop` |
| Multi-CEX | venue class `perp_dex` only |

```bash
titan-safety v1-surface --pipeline P22
titan-safety v1-surface --venue hyperliquid
```

---

## v1 operator config checklist

Before first micro-live trade (after Phase 5 YES):

- [ ] `capital_profile: paper` until Phase 5 YES (policy default)
- [ ] `v1SurfaceLockdown.enabled: true` in `openclaw.json`
- [ ] `edgeMesh.mode: single_pop`, `activePops: [EDGE-FRA]`
- [ ] `allocator.maxActivePipelines: 2`
- [ ] `memecoinTrench.enabled: false`, `flashLoanRouter.enabled: false`
- [ ] `quantum.enabled: false`
- [ ] Micro-live phase cap: `--phase micro_live_conservative` (≤0.05% / trade)
- [ ] Promotion registry + stats evidence for each strategy
- [ ] TCA daily scorecard scheduled (`tca daily-scorecard`)
- [ ] Tier 0/1 authority unchanged — kernel DENY, signing gate, drawdown enforce

---

## Code paths

| Module | Role |
|--------|------|
| `promotion_registry.py` | Global multiple-testing ledger |
| `promotion_stats.py` | Walk-forward / purged CV / shadow / DSR gates |
| `promotion_gate.py` | Human YES + stats + registry + micro caps |
| `micro_live_caps.py` | Phase equity caps (not calendar) |
| `profit_loop.py` | BLEEDING defund + YES-gated refund |
| `tca_daily_scorecard.py` | Daily HERALD digest |
| `v1_surface.py` | v1 fantasy surface lockdown |
| `allocator.py` | ≤2 strategies + pipeline blocks |

---

## Tests

```bash
python3 -m pytest tests/test_tier2_promotion_quality.py tests/test_promotion_gate.py tests/test_profit_loop.py -q
```
