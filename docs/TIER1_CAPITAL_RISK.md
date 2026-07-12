# Tier 1 Capital Risk — Items 6–10

> **Scope:** Risk that actually preserves capital. Complements [`docs/TIER0_MONEY_PATH.md`](./TIER0_MONEY_PATH.md) (broadcast authority, Hyperliquid depth-first).  
> **Does not auto-enable live capital** — Phase 5 human YES + operator checklist still required.

**Policy source:** `templates/risk_kernel/policy.yaml` → `tier1_capital_risk` profile overrides merged by `load_policy()`.

---

## Status matrix

| # | Requirement | Enforced (code) | Documented | Notes |
|---|-------------|-----------------|------------|-------|
| 6 | Drawdown tiers de-gross / halt / flatten (live) | **DONE** | **DONE** | `drawdown_tiers.py`, `kernel.py`, allocator `advisory_mode: false` in live profile |
| 6 | Paper/shadow notify-only | **DONE** | **DONE** | `drawdown_notify_only: true` paper profile |
| 7 | Default template = paper | **DONE** | **DONE** | `capital_profile: paper`, `autonomous_signing.enabled: false` |
| 7 | DEX-only venue allow-list | **DONE** | **DONE** | CEX venues stripped from default `allowed_venues` |
| 8 | ExecutionGate structural non-bypass | **DONE** | **DONE** | `scripts/ci/check_execution_gate_imports.py` + `verify.sh` |
| 8 | Agent netns cannot RPC submit | **STUB** | **DONE** | `ghost_evasion.yaml` `network_topology` + `apply_agent_netns_policy.sh.stub` |
| 9 | MTM from chain/recon | **DONE** | **DONE** | `risk_inputs.mark_to_market_equity()` + `recon_aggregator` |
| 9 | Loss velocity from fills | **DONE** | **DONE** | `risk_inputs.loss_velocity_from_fills()` |
| 9 | VaR from real returns | **DONE** | **DONE** | `portfolio_risk_service` enriches from fill ledger |
| 9 | Kill augur stub on live | **DONE** | **DONE** | `detect_live_risk_stubs()` → `LIVE_RISK_STUB` DENY |
| 10 | Gate p99 observability | **DONE** | **DONE** | `execution_gate` → `execution_gate_p99_ms` gauge |
| 10 | Dual-control kill RESUME (live) | **DONE** | **DONE** | `kill_switch.verify_dual_resume()` + CLI `--signed-secondary` |
| 10 | SLO documentation | **DONE** | **DONE** | This file § SLOs |

---

## 6. Drawdown enforcement (live profile)

### Ladder (live — enforced)

| Drawdown | Action | Kernel / allocator |
|----------|--------|-------------------|
| 2% | `soft_de_gross` | `safe_mode_exposure_cap_pct = 75%` |
| 5% | `hard_de_gross` | `safe_mode_exposure_cap_pct = 50%` |
| 8–10% | `halt_new_risk` | DENY risk-increasing trades; de-risk allowed |
| 12% | `full_halt_flatten` | `trigger_flatten()` + DENY all |

Allocator `degross_ladder` aligned: `[2→0.75, 5→0.5, 8→0.25, 10→0]`. With `advisory_mode: false` (live), targets are **enforced** before scaling capital.

### Paper profile

`drawdown_notify_only: true` — HERALD alerts only; `check_trade()` never DENY on tier.

### Code paths

- `templates/safety/titan_safety/drawdown_tiers.py` — tier parse, enforce, `check_trade`
- `templates/safety/titan_safety/drawdown_notifier.py` — alerts + `apply_tier_enforcement`
- `templates/safety/titan_safety/kernel.py` — drawdown DENY in `validate_trade`
- `templates/safety/titan_safety/allocator.py` — `degross_multiplier`, `is_enforced()`

---

## 7. Default template = paper

Deploy bundle defaults:

```yaml
capital_profile: paper
autonomous_signing:
  enabled: false
allowed_venues: [paper]
flash_loan_live:
  enabled: false
allocator:
  advisory_mode: true
  max_active_pipelines: 2
```

Live profile overrides (after Phase 5 YES) via `tier1_capital_risk.profiles.live`. See [`docs/GO_LIVE_SEQUENCE.md`](./GO_LIVE_SEQUENCE.md).

**DEX-only:** No CEX venues in live profile allow-list (R02/R46). Paper profile is `allowed_venues: [paper]` only.

---

## 8. Structural non-bypass

### CI: ExecutionGate in execution skills

```bash
python3 scripts/ci/check_execution_gate_imports.py
```

Fails if `trench_ops_execution`, `memecoin_trench`, or `flash_loan_router` skills lack `ExecutionGate` / `titan-safety gate` references.

### Network policy (STUB)

Spec: `templates/infra/ghost_evasion.yaml` → `network_topology.agent_netns`

- Agent LLM netns: **no** chain RPC submit egress
- Allowed submitters: `trench-ops-edge`, `execution_daemon`, `flatten_executor`, `titan-safety`
- Bootstrap stub: `scripts/ci/apply_agent_netns_policy.sh.stub`

Full eBPF/netns enforcement is **operator deploy step** — honest STUB until wired on TITANHOME.

---

## 9. Independent risk inputs

| Input | Source | Module |
|-------|--------|--------|
| Mark-to-market | `recon_aggregator` / Hyperliquid clearinghouse | `risk_inputs.mark_to_market_equity` |
| Loss velocity | `hyperliquid_fill_ledger.jsonl` | `risk_inputs.loss_velocity_from_fills` |
| VaR returns | Fill ledger per pipeline | `portfolio_risk_service` + `pipeline_returns_from_fills` |
| AUGUR regime | File feed (`augur_regime.json`) — **not stub** on live | `augur_feed.py` |

Live profile blocks simulate/var when stubs detected (`LIVE_RISK_STUB`).

---

## 10. Latency and kill-path SLOs

### Gate latency budgets

| Path | SLO (p99) | Metric |
|------|-----------|--------|
| Standard gate | 250 ms | `execution_gate_p99_ms` |
| Fast gate (P22/P29/P12/P30) | 150 ms | same gauge (hot path) |

Observed via `GET :19001/metrics` / gate `METRICS.observe_latency("execution_gate", ...)`.

Policy reference: `tier1_capital_risk.slo.gate_p99_ms` / `gate_fast_p99_ms`.

### Kill switch deactivate (live)

Single signed `RESUME` is insufficient on **live** profile.

```bash
# Operator A
titan-safety kill sign --command RESUME --operator hyperion

# Operator B (distinct)
titan-safety kill sign --command RESUME --operator backup-op

titan-safety kill deactivate --operator hyperion \
  --signed '<primary>' --signed-secondary '<secondary>'
```

`kill_switch.dual_control_resume: true` in live profile.

---

## Operator checklist — enabling live profile

1. Complete paper minimum (`promotion_stats`, 3-day paper per playbook).
2. Phase 5 explicit **YES** (never on TIMEOUT).
3. Set `capital_profile: live` in deployed `~/.openclaw/risk_kernel/policy.yaml` (or use profile merge).
4. Confirm `drawdown_notify_only: false` and enforced `drawdown_tiers` (live block).
5. Set `allocator.advisory_mode: false` — de-gross ladder enforced.
6. Wire live recon: `HYPERLIQUID_WALLET_ADDRESS` or `TITAN_RECON_FETCHER_URL`.
7. AUGUR regime file feed — **no** `augur_regime_stub` on live (`augur_feed: file`).
8. UPS + power-loss HALT verified.
9. `tier0_money_path.enabled` only after Tier 0 checklist (separate doc).
10. Dual-control kill RESUME tested with two operators.
11. Run `verify.sh` + `pytest tests/test_tier1_capital_risk.py`.
12. Evolution remains shadow-only; kernel DENY stays authoritative.

---

## Related files

| File | Role |
|------|------|
| `templates/risk_kernel/policy.yaml` | `tier1_capital_risk` profiles |
| `templates/safety/titan_safety/policy_loader.py` | Profile merge |
| `templates/safety/titan_safety/risk_inputs.py` | Independent inputs + stub detection |
| `scripts/ci/check_execution_gate_imports.py` | Item 8 CI |
| `iron-laws.md` | Immutable constitution |
| `LIVE_CAPITAL_PRODUCTION_GUIDE.md` | Paper → live ceremony |
