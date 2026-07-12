# Canonical Runbook — Single Source of Truth (SSOT)

> **Purpose:** One index for operator truth. Specialized guides are thin wrappers pointing here.  
> **Policy version:** `templates/risk_kernel/policy.yaml` → `version: "2.2"` (CI-enforced)  
> **Does not enable live capital.**

---

## How to use this document

1. Start here for any operational question.
2. Follow links to tier docs for depth.
3. Beginner guides (`DEPLOYMENT_GUIDE_BEGINNER.md`, etc.) summarize — **this file wins on conflict**.
4. Run `python3 scripts/ci/check_doc_policy_consistency.py` after doc edits.

---

## Tier index

| Tier | Doc | Scope |
|------|-----|-------|
| 0 | [`docs/TIER0_MONEY_PATH.md`](./TIER0_MONEY_PATH.md) | Broadcast authority, recon HALT, Hyperliquid |
| 1 | [`docs/TIER1_CAPITAL_RISK.md`](./TIER1_CAPITAL_RISK.md) | Drawdown, loss velocity, paper default |
| 2 | [`docs/TIER2_PROMOTION_QUALITY.md`](./TIER2_PROMOTION_QUALITY.md) | Walk-forward, micro-live, TCA loop |
| 3 | [`docs/TIER3_INSTITUTIONAL_OPS.md`](./TIER3_INSTITUTIONAL_OPS.md) | Observability, DR, security, BFT honesty |
| 4 | [`docs/TIER4_ULTIMATE.md`](./TIER4_ULTIMATE.md) | Multi-PoP, intent solvers, shadow twin (gated) |

---

## Constitutional (immutable)

| Doc | Role |
|-----|------|
| [`AGENTS.md`](../AGENTS.md) | Agent protocol, bounded autonomy, advisory voting |
| [`iron-laws.md`](../iron-laws.md) | Non-negotiable capital rules |
| [`SOUL.md`](../SOUL.md) | Identity (deployed to `~/.openclaw`) |

---

## Operator surfaces

| Surface | Doc | Production? |
|---------|-----|-------------|
| **Telegram / HERALD** | [`TELEGRAM_OPS_GUIDE.md`](../TELEGRAM_OPS_GUIDE.md) | **YES** |
| CLI `titan-safety` | [`SYSTEM.md`](../SYSTEM.md) | YES |
| Web `web/` | [`BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md`](../BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md) | Dev only — **not** authorization |
| Grafana | [`templates/observability/grafana/dashboards/titan.json`](../templates/observability/grafana/dashboards/titan.json) | Diagnostic — alerts via Telegram |

---

## Runbooks (incident response)

| Incident | Runbook |
|----------|---------|
| Power / UPS | [`docs/runbooks/power_loss.md`](./runbooks/power_loss.md) |
| Host compromise | [`docs/runbooks/host_compromise.md`](./runbooks/host_compromise.md) |
| RPC eclipse | [`docs/runbooks/rpc_eclipse.md`](./runbooks/rpc_eclipse.md) |
| Stuck nonce | [`docs/runbooks/stuck_nonce.md`](./runbooks/stuck_nonce.md) |
| Partial fill | [`docs/runbooks/partial_fill.md`](./runbooks/partial_fill.md) |

Playbooks: `templates/playbooks/` — kill switch, promotion, UPS drill, harvest drill.

---

## Safety services map

| Port | Service | Metrics |
|------|---------|---------|
| :19001 | Risk kernel | `risk_kernel_*`, `execution_gate_p99_ms` |
| :19002 | Reconciliation | `reconciliation_*` |
| :19003 | Status aggregator | `titan_services_degraded` |
| :19004 | Portfolio risk | `portfolio_var_95_usd` |
| :19005 | Dead man's switch | `dms_*` |
| :19006 | Allocator | `allocator_*` |
| :19007 | TCA | `tca_*`, `profit_loop_*` |
| :19008 | Security ops | `security_signing_halted` |

Observability deploy: `templates/observability/prometheus.yml` + `alert_rules.yaml`.

---

## Bounded autonomy (authoritative = policy.yaml)

Human YES still required for: Phase 5 promotion, evolution live, leverage change, new pipeline, trades above policy thresholds when autonomous_signing disabled.

**Autonomous when policy enables:** flash-loan live (`flash_loan_live_requires_approval: false`), routine trades &lt;1% equity, CB tier response.

**Never auto:** promotion TIMEOUT → HOLD/de-risk; kernel DENY is absolute.

---

## Thin wrappers (point here — do not duplicate)

| Wrapper | Points to |
|---------|-----------|
| `DEPLOYMENT_GUIDE_BEGINNER.md` | This file + `TITAN_AGENTIK_COMPLETE_SETUP_GUIDE.md` |
| `BEGINNER_LIVE_CAPITAL_EXPLAINED.md` | `LIVE_CAPITAL_PRODUCTION_GUIDE.md` + Tier 0–4 |
| `BEGINNER_WEB_UI_LIVE_MONEY_GUIDE.md` | § Operator surfaces above |
| `TITAN_CURRENT.md` | Executive snapshot — defers to this SSOT on conflict |

---

## CI / verify

```bash
./verify.sh
python3 scripts/ci/check_execution_gate_imports.py
python3 scripts/ci/check_doc_policy_consistency.py
```

---

## Audit export

```bash
python3 scripts/audit_export_worm.py --dry-run
# Production: set TITAN_AUDIT_EXPORT_BUCKET + credentials
```

---

## Go-live checklist (summary)

**Canonical sequence:** [`docs/GO_LIVE_SEQUENCE.md`](./GO_LIVE_SEQUENCE.md) (7 steps + drills).

See also [`docs/TIER3_INSTITUTIONAL_OPS.md`](./TIER3_INSTITUTIONAL_OPS.md) § Operator checklist.
