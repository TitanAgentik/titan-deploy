# Tier 4 Ultimate — What "Ultimate" Looks Like (After Tier 0–3)

> **Scope:** Multi-PoP RTT routing, intent solvers, MEV tip optimization, portfolio construction with borrow/funding/capacity, continuous red-team, formal kernel property tests, shadow twin divergence gating.  
> **Gated:** `tier4_ultimate.enabled: false` by default — operator cannot accidentally enable without Tier 0–3 completion.  
> **Does NOT enable live capital** — Phase 5 human YES + Tier 0 checklist still required. Evolution remains shadow-only.

**Policy source:** `templates/risk_kernel/policy.yaml` → `tier4_ultimate`  
**Prerequisites:** Tiers 0–3 complete (see checklist below)  
**SSOT index:** [`docs/CANONICAL_RUNBOOK.md`](./CANONICAL_RUNBOOK.md)

---

## Prerequisites — Tier 0–3 checklist (must pass before Tier 4)

| Tier | Doc | Operator must verify |
|------|-----|----------------------|
| 0 | [`TIER0_MONEY_PATH.md`](./TIER0_MONEY_PATH.md) | `tier0_money_path.enabled: true`, broadcast authority, recon HALT |
| 1 | [`TIER1_CAPITAL_RISK.md`](./TIER1_CAPITAL_RISK.md) | `capital_profile: live`, drawdown tiers enforced (not notify-only) |
| 2 | [`TIER2_PROMOTION_QUALITY.md`](./TIER2_PROMOTION_QUALITY.md) | Promotion registry, walk-forward, micro-live caps exercised |
| 3 | [`TIER3_INSTITUTIONAL_OPS.md`](./TIER3_INSTITUTIONAL_OPS.md) | Observability deployed, runbooks exercised, security_ops enabled |

Set each `tier4_ultimate.tier_checklist.tierN_complete: true` in policy **only after** the corresponding doc checklist is done. `tier4_gate.tier4_active()` requires both the flag **and** policy preconditions.

---

## Status matrix (DONE / STUB)

| # | Requirement | Code | Status | Notes |
|---|-------------|------|--------|-------|
| 21 | Multi-PoP RTT measurement hooks | `edge_router.measure_rtt` | **STUB** | Returns target p95 until ICMP/HTTP probe wired |
| 21 | RTT-based routing | `edge_router._select_lowest_rtt` | **DONE** | Uses measured health when Tier 4 active |
| 21 | PoP failover on unhealthy | `edge_router.route` | **DONE** | Skips unhealthy PoPs; STUB health until probes |
| 21 | v1 unlock full 5-PoP mesh | `v1_surface.check_edge_pop(tier4_active=)` | **DONE** | Only when `tier4_active` |
| 22 | Intent solver scaffold | `intent_solver.IntentSolverClient` | **STUB** | `stub_submit: true` — no live RPC |
| 22 | MEV tip optimizer advisory | `mev_tip_optimizer.MevTipOptimizer` | **STUB** | Heuristic; integrates with `broadcast_authority` |
| 23 | Borrow rate cap in portfolio risk | `portfolio_risk.simulate_pre_trade` | **DONE** | Tier 4 portfolio_construction caps |
| 23 | Funding rate cap | `portfolio_risk.simulate_pre_trade` | **DONE** | Per-pipeline funding field |
| 23 | Capacity curves | `portfolio_risk` + `allocator` | **DONE** | Gated by `capacity_curve_enabled` |
| 24 | Continuous red-team runner | `red_team_runner.RedTeamRunner` | **DONE** | Subprocess harness; schedule STUB until enabled |
| 25 | Kernel property tests | `tests/test_kernel_properties.py` | **DONE** | Table-driven (no hypothesis dep) |
| 26 | Shadow twin divergence gate | `shadow_twin.ShadowTwin` | **DONE** | Blocks live deploy on divergence |

---

## Policy block

```yaml
tier4_ultimate:
  enabled: false
  requires_tiers: [0, 1, 2, 3]
  tier_checklist:
    tier0_complete: false
    tier1_complete: false
    tier2_complete: false
    tier3_complete: false
  shadow_twin:
    enabled: false
    max_divergence_pct: 15.0
    block_live_on_divergence: true
  multi_pop:
    failover_enabled: true
    unhealthy_rtt_p95_ms: 50.0
  intent_solver:
    enabled: false
    stub_submit: true
  mev_tip_optimizer:
    enabled: false
    advisory_only: true
  red_team_continuous:
    enabled: false
    interval_minutes: 60
  portfolio_construction:
    capacity_curve_enabled: false
```

---

## Operator unlock checklist — Tier 4

1. Complete Tier 0–3 operator checklists (docs linked above).
2. Set `tier_checklist.tier0_complete` … `tier3_complete: true` in policy.
3. Verify preconditions: `python3 -c "from titan_safety.tier4_gate import tier4_prerequisites; ..."` or `pytest tests/test_tier4_ultimate.py`.
4. Wire edge RTT probes on all 5 PoPs (replace STUB in `edge_router.measure_rtt`).
5. Set `tier4_ultimate.enabled: true` — **still does not enable live capital**.
6. Optionally enable sub-features one at a time:
   - `multi_pop.failover_enabled`
   - `intent_solver.enabled` (after solver endpoints wired)
   - `mev_tip_optimizer.enabled`
   - `red_team_continuous.enabled` + systemd timer
   - `shadow_twin.enabled`
   - `portfolio_construction.capacity_curve_enabled`
7. Update `v1_surface_lockdown.yaml` — Tier 4 active lifts `full_edge_mesh_5_pop` at runtime.
8. Run property tests: `pytest tests/test_kernel_properties.py -v`
9. Run continuous red-team once: `RedTeamRunner(policy).run_once()`
10. Confirm shadow twin blocks deploy when divergence > cap (paper test).

**Hard rules unchanged:** Kernel DENY absolute; evolution shadow-only; no closed/cloud models on live path; receipt single-use enforced on broadcast submit.

---

## File index

| File | Role |
|------|------|
| `templates/safety/titan_safety/tier4_gate.py` | Prerequisite gate |
| `templates/safety/titan_safety/edge_router.py` | RTT + failover |
| `templates/safety/titan_safety/intent_solver.py` | Solver stub |
| `templates/safety/titan_safety/mev_tip_optimizer.py` | Tip advisory |
| `templates/safety/titan_safety/red_team_runner.py` | Continuous red-team |
| `templates/safety/titan_safety/shadow_twin.py` | Divergence gate |
| `templates/safety/titan_safety/gate_receipt.py` | Single-use receipts |
| `templates/risk_kernel/v1_surface_lockdown.yaml` | Tier 4 multi-PoP unlock note |
| `tests/test_kernel_properties.py` | Formal property tests |
| `tests/test_tier4_ultimate.py` | Tier 4 scaffold tests |

---

## Tests

```bash
cd /path/to/titan-deploy
PYTHONPATH=templates/safety python3 -m pytest tests/test_kernel_properties.py tests/test_tier4_ultimate.py -v
```
