# TITAN Production Readiness

**Last updated:** deploy bundle v2.3 — bounded autonomy + portfolio risk + MRM + **profit engine** (capital allocator, execution-quality/TCA, statistical promotion gates)  
**Honest assessment:** This bundle adds real, tested software controls for both **capital preservation** and **profit compounding**. It does **not** make live trading with real capital safe or profitable by itself. Treat everything below as necessary but not sufficient.

**Operator walkthrough for real capital:** [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](./LIVE_CAPITAL_PRODUCTION_GUIDE.md) — beginner-complete path from paper/shadow → Phase 5 human YES → first live trade. Does **not** bypass `:19001` or auto-promote on TIMEOUT. Cockpit `VITE_DATA_MODE=live` is UI data mode only (see [`WEB_UI_LIVE_PRODUCTION_GUIDE.md`](./WEB_UI_LIVE_PRODUCTION_GUIDE.md)).

**v2.3 profit-engine additions (all deterministic, out-of-process, unit-tested):**
- **Capital allocator** (`allocator.py`, `:19006`) — turns per-lane cost-adjusted edge into forward fractional-Kelly allocation within a human-set gross envelope; per-lane / correlation-cluster / capacity caps; regime scaling; drawdown de-grossing ladder. Winners get fed, losers starved — automatically, inside bounds.
- **Execution-quality / TCA** (`tca.py`, `:19007`) — per-lane net-of-cost scorecards: realized slippage, gas+tip drag, revert/fill rate, tip efficiency, edge-decay slope, capacity pressure. Converts *claimed* edge into *measured* edge and flags bleeding lanes.
- **Statistical promotion gate** (`promotion_stats.py`) — deflated Sharpe (multiple-testing correction), probabilistic Sharpe, cost-realism, shadow-divergence, and minimum-trade-count gates now block overfit strategies **before** capital, in addition to the human YES. Fail-closed: a stats-gated promotion with no evidence is denied.

---

## Infrastructure Roles (Clarified)

| Node | Role | Live capital requirement |
|------|------|--------------------------|
| **TITANHOME** | Primary compute + orchestrator inference + safety services (risk kernel, REVM) | UPS mandatory |
| **TITANSPARK** | Utility inference (Qwen3-30B) + operator gateway failover | UPS recommended |
| **Mac Mini vault** | Key metadata + Trezor ceremonies + profit workloads | UPS mandatory |
| **Signing (in-process)** | `titan_safety.SigningNode` after gate ALLOW — no separate `:19010` daemon | UPS mandatory (TITANHOME) |
| **Edge mesh** | Full 5-PoP: FRA + TKY + SIN + USE + AMS (paper + live, latency-faithful) | Cloud provider redundancy per PoP |

Specs: `~/.openclaw/infra/power_requirements.yaml`, `signing_node.yaml`, `gpu_schedule.yaml`

---

## What Is Enforced in Software (Now)

| Control | Implementation | Fail mode |
|---------|----------------|-----------|
| Independent risk kernel | `titan_safety.kernel` + HTTP `:19001` | **DENY** if unreachable |
| Per-trade notional cap | `policy.yaml` → `trading_limits` | DENY |
| Aggregate exposure cap | Kernel state tracking | DENY |
| Leverage cap | Pre-trade validation | DENY |
| 60s + 15m loss-velocity limiters | Rolling loss windows in kernel | DENY |
| Human-approval gate >1% equity | Kernel `HUMAN_APPROVAL_REQUIRED` | DENY |
| Portfolio VaR/CVaR + correlation caps | `portfolio_risk.py` + HTTP `:19004` | DENY |
| Regime-aware exposure (AUGUR stub) | Portfolio risk engine | DENY |
| MRM signal drift throttle | `mrm.py` per-pipeline/regime | Throttle |
| Explainability layer | `explainability.py` + HERALD for >0.5% / conf>0.8 | Notify |
| Layered kill switches | Global, portfolio, per-pipeline + signed CLI | Halt |
| Constitutional promotion blocks | `promotion_gate.py` path guards | DENY |
| Statistical promotion gate | `promotion_stats.py` (deflated Sharpe/PSR/cost/shadow) | DENY (fail-closed) |
| Forward capital allocator | `allocator.py` + HTTP `:19006` | Fractional-Kelly within envelope |
| Execution-quality / TCA | `tca.py` + HTTP `:19007` | Scorecard + bleeding-lane flag |
| TCA→allocator profit loop | `profit_loop.py` + `POST /v1/profit_loop` | Auto-defund BLEEDING; refund needs human |
| Unbypassable execution gate | `execution_gate.py` (recon→kernel→receipt) | DENY if any stage fails / unreachable |
| Signing receipt gate | `signing_service.SigningNode` (in-process) | 401 without fresh `X-Titan-Gate-Receipt` |
| Flatten / key-revoke executor | `flatten_executor.py` | Enqueues closes + mock revoke + SIGNING_HALTED |
| DMS → wind-down | `dead_mans_service` → `WindDownController` | 48h derisk / 72h flatten side effects |
| Evolution freeze | `evolution_freeze.py` + CLI | Blocks live promotions while frozen |
| Mock adapter ban (live) | `assert_adapter_allowed_for_policy` | DENY / refuse live profile startup |
| Control-plane HMAC auth | `auth.py` `X-Titan-Auth` on mutating POSTs | 401 unauthorized |
| Pipeline concentration | `allocator.max_active_pipelines` (default 4) | Cap funded lanes |
| Selective activation | `autonomy.selectiveActivation` + allocator advisory | Catalog ≠ all-on |
| Security Ops four pillars | `security_ops.py` + HTTP `:19008` | Lockdown / honeypot / posture |
| P22 memecoin trench | `memecoin_filter.py` + six-gate + `memecoin sim` | Catalog until YES; real SOL gated |
| Air-gapped staging flag | `openclaw.json` `promotion.airGappedStaging` | Config |
| Safe mode / wind-down | `wind_down.py` + CLI | De-risk |
| Tax ledger stub | `capital/tax_ledger.py` FIFO + CSV export | Audit |
| Adversarial harness | `tests/adversarial/adversarial_harness.py` | CI/regression |
| Prometheus `/metrics` | All safety services + status aggregator | Scrape |
| Position-count cap | Open position tracking | DENY |
| Venue/contract allow-list | Policy-driven | DENY |
| Pre-trade slippage check | expected vs worst price | DENY |
| FLATTEN + key revocation | `POST /v1/flatten`, kill switch | Halt |
| Global kill switch | File flag + CLI + HMAC-signed command | Halt (no NATS/Telegram/LLM required) |
| Position reconciliation | `:19002` with pluggable adapter | HALT on divergence |
| Dead-man's switch | Daemon, 48h de-risk / 72h flatten | De-risk/flatten; never promotes |
| Promotion gate | CLI + append-only audit log | Requires explicit `YES` |
| Version-fingerprint audit | Hash-chain decision log | Tamper detection |
| Capital ledger | `titan_safety.capital` + audit chain | Deposit/withdraw logged; min reserve enforced |
| Observability | JSON logs, `/health`, `/metrics`, status aggregator `:19003` | Degraded status |
| Power-loss halt | `policy.yaml` → `power_loss` + UPS spec | **HALT** on mains loss |
| Chaos harness | `tests/chaos/chaos_harness.py` | CI/regression |
| Signing isolation | `signing_node.yaml` + openclaw.json `signingNode.mode: in_process` | In-process module; never agent runtime |
| GPU schedule | `gpu_schedule.yaml` — P2 inference never preempted | Kill off-peak jobs on violation |

---

## DO NOT Deploy Real Capital Until

1. **Paper + shadow minimum:** Each strategy completes full §DEPLOY_LIFECYCLE (3+ days paper, shadow execution, micro-live ≤0.1% equity) with documented results.
2. **Phase 5 human YES:** Recorded in promotion audit log via `titan-safety promotion approve --response YES`.
3. **Safety + profit services running:** All systemd units healthy (`curl :19003/health` → `"status":"ok"`), including allocator (`:19006`) and TCA (`:19007`).
4. **Fail-closed verified:** Stop risk kernel; confirm all trade paths return DENY (not bypass).
5. **Kill switch drill:** Activate via CLI; deactivate only with signed `RESUME` (`kill sign --command RESUME` then `kill deactivate --signed ...`); confirm kernel denies trades while active.
5a. **Security Ops four pillars:** `titan-safety security status` shows HARDENED; `security lockdown --dry-run` plans kill+freeze+signing halt+honeypot; skills `sentinel_security` / `predator_scanner` non-stub; refs AEGIS/GHOST/REAPER present; Titan Agentik `/security` matches CLI posture.
6. **Reconciliation with real adapter:** Replace `mock` adapter with exchange/on-chain adapter wired to real keys; verify zero divergence over 48h paper.
7. **Operator heartbeat:** Dead-man's switch tested; heartbeat cron or manual `titan-safety heartbeat` scheduled.
8. **Live infrastructure:** NATS, inference endpoints, Erigon on EDGE-FRA (Phase 1 single PoP), Solana feeds — production SLOs met.
9. **UPS installed and tested:** ≥3000VA, ≥15 min runtime on TITANHOME + signing path; power-loss drill → HALT confirmed.
10. **Signing isolation:** TRENCH-OPS uses `titan-safety gate sign` (in-process); no signing in agent runtime; `signing_node.yaml` deployed; `:19010` not required.
11. **Exchange/wallet keys:** Provisioned with least privilege; withdrawal disabled; separate from agent write paths.
12. **Capital module smoke-tested:** `titan-safety capital deposit|withdraw|balance` and audit verify pass; Trezor/on-chain adapter still `mock` until ops wiring.
13. **Residual risk review:** Operator reads and accepts risks in the next section.
14. **Quantum classical-only:** QCC/QSA/QRP absent from `openclaw.json` agent definitions; `quantum.status: dormant` / `quantum.enabled: false`; no Wukong/cuQuantum/Tier 3 paths active; `quantum_*` skills archived under `skills/_archived/quantum/`.

---

## What Still Requires Human / Operational Steps

- **Real exchange and wallet API keys** — not included; mock/paper adapter only in this bundle.
- **Capital execution adapter** — `withdrawal_adapter: mock` in config; wire Trezor Safe 7 + in-process SigningNode for live sweeps/withdrawals.
- **Paper + shadow trading duration** — software gates exist; calendar time and performance evidence do not.
- **Production infra** — GPU inference on TITANHOME (P2 never preempted), NATS, chain nodes, firewall, **UPS on all signing paths**.
- **Edge mesh** — full 5-PoP from paper; bootstrap via `edge_pop_bootstrap.sh` per PoP after WireGuard.
- **BFT independence** — orchestrator agents share GLM-5.2; correlated consensus is documented, not fixed.
- **Agent runtime integration** — OpenClaw/Hermes must call `preTradeValidationUrl` before every execution; wiring is config-level; execution skills must honor DENY.
- **Key revocation side effects** — kernel sets `keys_revoked` flag; actual API key disable at exchange must be operationalized.
- **Flatten execution** — kernel requests flatten; TRENCH-OPS/on-chain executors must implement flatten handler.
- **BusKill / hardware kill** — documented in `playbooks/kill_switch.yaml`; operator installs USB BusKill separately.
- **Grafana dashboards** — stub only (`playbooks/observability_grafana_stub.yaml`); Prometheus scrape targets documented, not deployed.
- **AUGUR regime feed** — portfolio risk uses stub regime; wire live AUGUR macro feed for production.
- **MRM challenger promotion** — stub only; requires promotion gate YES for live swap.
- **P22 real Solana** — Geyser creds (`GEYSER_GRPC_URL`), Jito tip wallet, live recon module, `capital_profile: live`, venues `solana_pumpfun`/`jito`, promotion YES, then `memecoinTrench.enabled: true` (see `infra/solana_memecoin.yaml` checklist).
- **Flash-loan live** — `titan-safety flashloan sim` + promotion `flash_loan_live` YES, then `flashLoanRouter.enabled: true` + `flash_loan_live.enabled` in policy (see `infra/flash_loan.yaml`).

---

## Honest Residual Risks

1. **Same-model BFT** — GUARDIAN/ARCHON/CORTEX/SENTINEL share weights; only the out-of-process kernel is model-independent.
2. **Quantum layer removed** — QCC/QSA/QRP are **not in the agent catalog**. No cuQuantum, Wukong-180, or Tier 3 cloud QPU dispatch for live capital. Classical GPU only (REVM, CuEVM, ML). Do not re-introduce quantum agents or QPU paths without a full re-audit and operator sign-off.
3. **Config-only agent wiring** — If an execution path bypasses pre-trade HTTP call, capital is exposed. Code review of execution skills required.
4. **Mock reconciliation** — Until live adapter is implemented and tested, position truth is not verified against chain/exchange.
5. **No formal verification** — Limits are unit-tested, not mathematically proven.
6. **Multi-region edge** — 5 PoP mesh configured; operator must provision WireGuard + bootstrap each PoP for live colo paths.
7. **Power dependency** — Without UPS, mains loss can corrupt in-flight trades; UPS + HALT policy mitigates but does not eliminate risk.
8. **Signed kill switch secret** — Stored locally; compromise of host compromises kill switch.
9. **LLM prompt injection** — Kernel does not parse LLM output; but poisoned data feeds can still cause bad proposals (blocked by slippage/limits if configured correctly).
10. **Flash crashes / gaps** — 60s and 15m velocity breakers help; sub-second gaps may still exceed reactive limits.

---

## Phased Rollout (2 Days Per Phase — Operator Directive, roadmap cut ⅓ from 3→2 days)

> **OPERATOR CAVEAT:** Phase durations are **advisory calendar targets**, not auto-advance timers. `openclaw.json` `rollout.calendarIsNotAGate: true`. Stretch until you have regime diversity and ≥200 real fills per lane. Gate failures pause the clock; short duration does **NOT** auto-advance.

### Phase 0 — Infrastructure + Paper (2 Days)

- Deploy bundle; enable safety systemd units (`19001`–`19008`; signing is in-process — no `:19010` required)
- Complete BOOTSTRAP.md checklist including UPS drill
- Run `./deploy.sh --verify` and adversarial harness PASS
- Paper trade all candidate pipelines; zero live keys
- TCA service ingesting paper fills; per-lane scorecards populating
- Shadow evolution only (`airGappedStaging: true`)

**Exit criteria:** 2+ days paper per strategy; chaos + adversarial harness green; operator kill-switch drill; TCA scorecard produced for every candidate lane.

### Phase 1 — Micro-Live ($2–10K, 2 Days)

- Single PoP (EDGE-FRA); capital $2,500–$10,000
- Micro-live ≤0.1% equity per trade; trades >1% require explicit YES
- Portfolio risk service enforcing VaR/correlation caps
- **Capital allocator live in advisory mode** — target notionals logged, human confirms envelope
- Daily reconciliation with mock→live adapter migration plan
- MRM baselines recorded per pipeline/regime

**Exit criteria:** 2+ days micro-live; max drawdown <5%; zero reconciliation divergence >threshold; each live pipeline passes the **statistical promotion gate** (deflated Sharpe ≥0.90, PSR ≥0.90, modeled costs, ≥200 trades, shadow divergence ≤15%) AND Phase 5 YES.

### Phase 2 — Validated Scale ($10–50K, 2 Days)

- Increase equity gradually; drawdown tiers at 2/5/8/10/12% + allocator de-grossing ladder (3/5/7/10%)
- Enable additional pipelines per promotion playbook + red-team checklist
- **Capital allocator moves from advisory to enforced** within the operator-set gross envelope
- Wire live reconciliation adapter; 48h zero divergence
- Trezor sweep config armed (still growth phase if <$15K)

**Exit criteria:** 2+ days combined paper+live track record; MRM no unmitigated drift; explainability on all material trades; no lane flagged BLEEDING by TCA carrying capital.

### Phase 3 — Mature Production ($50K+, 2 Days)

- Optional additional PoPs (Phase 3+ edge mesh)
- Concentrated activation of proven lanes per capital phase gates (fund on TCA/allocator evidence, not breadth)
- Harvest phase sweeps when ≥$15K
- Quarterly red-team re-run; promotion playbook for all model changes

**Exit criteria:** Operator sign-off; residual risks accepted; incident playbooks exercised at least once.

### Profit-Gating Metrics (gate every capital increase, beyond Sharpe)

Every promotion and every capital-tier increase must clear, per lane, at the proposed size:

- **Deflated Sharpe ≥ 0.90** and **PSR ≥ 0.90** (statistical significance after multiple-testing correction)
- **Net-of-cost expectancy > 0** (TCA `net_bps`, after gas/tips/slippage/reverts)
- **Tip efficiency ≤ 40%** and **fill rate ≥ 80%** (TCA verdict not BLEEDING)
- **Shadow/live vs. backtest Sharpe divergence ≤ 15%**
- **≥ 200 real trades** of evidence
- **Capacity pressure not rising** (edge holds at target size)
- **Non-negative edge-decay slope** (edge not fading)

---

## Quick Verification Commands

```bash
# Health aggregate
curl -s http://127.0.0.1:19003/health | python3 -m json.tool

# Pre-trade test (should ALLOW small paper trade)
curl -s -X POST http://127.0.0.1:19001/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{"trade_id":"test","venue":"paper","contract":"0x0000000000000000000000000000000000000000","notional_usd":10}'

# Kill switch
~/.openclaw/safety/bin/titan-safety kill activate --operator YOU --reason "drill"
~/.openclaw/safety/bin/titan-safety kill status
~/.openclaw/safety/bin/titan-safety kill sign --command RESUME --operator YOU
~/.openclaw/safety/bin/titan-safety kill deactivate --operator YOU --signed "$SIGNED"

# Tests
python3 -m pytest /path/to/titan-deploy/tests -q
python3 /path/to/titan-deploy/tests/adversarial/adversarial_harness.py

# P22 memecoin trench (paper filter + sim)
titan-safety memecoin filter --mint-json '{"mint":"test","mint_authority_revoked":true,"freeze_authority_revoked":true,"top10_holder_pct":15,"curve_progress_pct":30,"curve_fill_minutes":60,"sell_sim_ok":true}'
titan-safety memecoin sim --count 100 --seed 42
titan-safety memecoin status

# Portfolio risk simulation
curl -s -X POST http://127.0.0.1:19004/v1/simulate \
  -H 'Content-Type: application/json' \
  -d '{"equity_usd":2500,"pipeline_id":"P30","notional_usd":50,"pipelines":[]}'

# Prometheus metrics
curl -s -H 'Accept: text/plain' http://127.0.0.1:19003/metrics

# Wind-down safe mode
~/.openclaw/safety/bin/titan-safety wind-down safe-mode --operator YOU --reason "drill"
~/.openclaw/safety/bin/titan-safety wind-down status

# Capital allocator plan (attribution -> fractional-Kelly within envelope)
curl -s -X POST http://127.0.0.1:19006/v1/allocate \
  -H 'Content-Type: application/json' \
  -d '{"equity_usd":10000,"regime":"neutral","drawdown_pct":0,
       "lanes":[{"pipeline_id":"P5","net_bps":15,"return_std":0.01,"trade_count":800,"cluster":"funding"},
                {"pipeline_id":"P29","net_bps":30,"return_std":0.03,"trade_count":1200,"cluster":"mev_arb"}]}'

# TCA scorecard (net-of-cost execution quality per lane)
curl -s -X POST http://127.0.0.1:19007/v1/scorecard \
  -H 'Content-Type: application/json' -d '{"pipeline_id":"P29"}'

# Statistical promotion gate (deflated Sharpe / PSR / cost realism)
~/.openclaw/safety/bin/titan-safety promotion-stats --stats \
  '{"strategy_id":"P5","returns":[0.02,-0.004,0.03,0.012],"trials":5,"num_trades":500,"gross_bps":12,"cost_bps":3,"backtest_sharpe":1.8,"shadow_sharpe":1.7}'

# Capital (mock adapter)
~/.openclaw/safety/bin/titan-safety capital deposit --amount 2500 --asset USDC
~/.openclaw/safety/bin/titan-safety capital balance
~/.openclaw/safety/bin/titan-safety capital verify-audit
```

---

## Service Ports

| Service | Port | Endpoint |
|---------|------|----------|
| Risk kernel | 19001 | `/v1/validate`, `/health` |
| Reconciliation | 19002 | `/v1/pre_trade`, `/health` |
| Status aggregator | 19003 | `/health`, `/status` |
| Portfolio risk | 19004 | `/v1/simulate`, `/v1/var`, `/health` |
| Dead-man's switch | 19005 | `/v1/heartbeat`, `/health` |
| Capital allocator | 19006 | `/v1/allocate`, `/v1/budget`, `/health` |
| Execution-quality / TCA | 19007 | `/v1/ingest`, `/v1/scorecard`, `/health` |
| Signing node | 19010 | isolated tx signing |

---

**Bottom line:** Capital preservation requires the safety services **running**, **fail-closed**, **operationally drilled**, and **backed by paper/shadow evidence** (minimum 3 days per phase per operator directive — see caveat above). This bundle provides the software layer; go-live is an operator decision, not a deploy-script side effect.
