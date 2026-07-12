# Tier 3 Institutional Ops — Items 15–20

> **Scope:** Observability, disaster recovery, host security, voting honesty, tax/entity, documentation SSOT.  
> **Does not auto-enable live capital** — Phase 5 human YES + operator checklist still required.  
> **Operator surface:** Telegram via HERALD (not Grafana cockpit).

**Policy source:** `templates/risk_kernel/policy.yaml` `version: "2.2"`  
**SSOT index:** [`docs/CANONICAL_RUNBOOK.md`](./CANONICAL_RUNBOOK.md)

---

## Status matrix

| # | Requirement | Enforced (code) | Documented | Notes |
|---|-------------|-----------------|------------|-------|
| 15 | Prometheus scrape :19001–:19008 | **DONE** (config) | **DONE** | `templates/observability/prometheus.yml` |
| 15 | Real Grafana dashboard | **DONE** (JSON) | **DONE** | `templates/observability/grafana/dashboards/titan.json` |
| 15 | Alert rules → HERALD/Telegram | **DONE** (rules) | **DONE** | `alert_rules.yaml` + Alertmanager example STUB |
| 15 | Kernel down alert | **DONE** | **DONE** | `TitanRiskKernelDown` |
| 15 | Recon diverge alert | **DONE** | **DONE** | `TitanReconciliationDiverge` |
| 15 | Signing halt alert | **DONE** | **DONE** | `TitanSigningHalt` |
| 15 | Loss velocity alert | **DONE** | **DONE** | `TitanLossVelocityBreach` |
| 15 | UPS battery alert | **STUB** | **DONE** | Metric `ups_battery_percent` — wire Eaton telemetry |
| 15 | Edge RTT alert | **STUB** | **DONE** | Textfile collector from `edge_rtt_probe.yaml` |
| 15 | Fill rate collapse alert | **DONE** | **DONE** | `TitanFillRateCollapse` via TCA metrics |
| 15 | Gate p99 panel/alert | **DONE** | **DONE** | `execution_gate_p99_ms` |
| 15 | Audit WORM export | **DONE** | **DONE** | `scripts/audit_export_worm.py` |
| 16 | UPS quarterly drill | **DONE** (playbook) | **DONE** | `templates/playbooks/ups_quarterly_drill.yaml` |
| 16 | Runbooks (5 incidents) | **DONE** | **DONE** | `docs/runbooks/*.md` |
| 16 | Cold wallet harvest monthly | **DONE** (playbook) | **DONE** | `harvest_dust_monthly.yaml` — dust only |
| 17 | Agent FS isolation | **DONE** (doc) | **DONE** | `docs/AGENT_HOST_SECURITY.md` |
| 17 | Separate users + capabilities | **DONE** (doc) | **DONE** | systemd template in security doc |
| 17 | BusKill checklist | **STUB** | **DONE** | Manual install — udev not in bundle |
| 18 | BFT honesty in AGENTS.md | **DONE** | **DONE** | Advisory voting; kernel DENY absolute |
| 18 | Independent voter documentation | **DONE** | **DONE** | Partial heterogeneity documented |
| 19 | Tax ledger stub | **DONE** (code) | **DONE** | `templates/capital/tax_ledger.py` |
| 19 | Production tax requirements | **DONE** (doc) | **DONE** | `docs/TAX_ENTITY_PRODUCTION.md` |
| 20 | Canonical runbook SSOT | **DONE** | **DONE** | `docs/CANONICAL_RUNBOOK.md` |
| 20 | Doc/policy CI consistency | **DONE** | **DONE** | `scripts/ci/check_doc_policy_consistency.py` |

---

## 15. Observability that pages humans

### Deploy (operator infra STUB)

```bash
mkdir -p ~/.openclaw/observability
cp templates/observability/prometheus.yml ~/.openclaw/observability/
cp templates/observability/alert_rules.yaml ~/.openclaw/observability/
cp templates/observability/alertmanager_herald.yaml.example ~/.openclaw/observability/alertmanager.yml
# Install prometheus + alertmanager via distro packages or docker
# Import grafana/dashboards/titan.json — diagnostic only; pages go to Telegram
```

### Audit export (immutable)

```bash
python3 scripts/audit_export_worm.py --dry-run
export TITAN_AUDIT_EXPORT_BUCKET=titan-audit-worm
export TITAN_AUDIT_EXPORT_ENDPOINT=https://s3.example.com  # optional
python3 scripts/audit_export_worm.py
```

Cron suggestion: `0 4 * * *` daily export after chain verify.

---

## 16. Disaster recovery

| Playbook | Schedule | Max capital at risk |
|----------|----------|---------------------|
| `ups_quarterly_drill.yaml` | Quarterly | $0 (halt drill) |
| `harvest_dust_monthly.yaml` | Monthly | ≤ $5 dust |

Runbooks cover power loss, compromise, RPC eclipse, stuck nonce, partial fill.

---

## 17. Security model

See [`docs/AGENT_HOST_SECURITY.md`](./AGENT_HOST_SECURITY.md).

---

## 18. BFT honesty

Trade path uses **advisory** 2-of-3 from AUGUR + PREDATOR + ATLAS — not Byzantine fault tolerant.

| Voter | Model | Host |
|-------|-------|------|
| AUGUR | Qwen3-30B FP8 Tier 1 | TITANHOME GPU 0 |
| PREDATOR | Qwen3-30B FP8 Tier 1 | TITANHOME GPU 0 (correlated with AUGUR) |
| ATLAS | Qwen3-30B utility | TITANSPARK |

Orchestrator tier (ARCHON / CORTEX / GUARDIAN) uses distinct model families when available — still advisory.

**Authoritative:** risk kernel `:19001` DENY. Agents never override DENY.

---

## 19. Legal / tax / entity

Stub: `tax_ledger.py`. Production: [`docs/TAX_ENTITY_PRODUCTION.md`](./TAX_ENTITY_PRODUCTION.md).

---

## 20. Documentation SSOT

[`docs/CANONICAL_RUNBOOK.md`](./CANONICAL_RUNBOOK.md) — beginner guides are thin wrappers.

CI: `check_doc_policy_consistency.py` fails if docs claim human YES for flash loans when policy auto-allows.

---

## Operator checklist — Tier 3 go-live

- [ ] Prometheus scraping all `:19001–:19008` targets (`up==1`)
- [ ] Alertmanager → HERALD webhook tested (CRITICAL fires Telegram)
- [ ] Grafana imported (optional diagnostic)
- [ ] `audit_export_worm.py` uploaded to WORM bucket; manifest retained 7y
- [ ] UPS quarterly drill executed once on calendar
- [ ] Harvest dust drill executed once (`--dry-run` minimum)
- [ ] All 5 runbooks read by operator
- [ ] `titan-agent` cannot read `~/.openclaw/secrets/` (permission test)
- [ ] BusKill installed OR documented waiver signed
- [ ] `check_doc_policy_consistency.py` passes in CI
- [ ] AGENTS.md bounded autonomy matches `policy.yaml`
- [ ] Tax production plan filed with counsel (if live entity)

**Still required for live capital:** Phase 5 human YES, `capital_profile: live`, `./verify.sh` green, Tier 0–2 complete.
