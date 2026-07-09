# TITAN — Complete Build, Deploy & Go-Live Guide

**Scope:** Everything required to take TITAN from source spec (`source/TITAN.md`) to a
live, bounded-autonomy, profit-focused trading system using the `titan-deploy`
bundle (risk kernel + portfolio risk + capital allocator + TCA + statistical
promotion gates).

**Read this first — honest framing:**
- This bundle ships **real, tested software controls**. It does **not** make live
  trading safe or profitable by itself. Software is necessary, not sufficient.
- Several claims in `TITAN.md` are aspirational or fictional (e.g. `GLM-5.2-753B`,
  `$356,700/day`, quantum "stealth", "23 agents at full autonomy"). Treat the
  spec as **product vision**, and this guide as the **operational reality**.
- The correct posture is **bounded autonomy**: the machine executes freely inside
  a human-set risk envelope; humans own promotions, risk-parameter changes, and
  capital-tier increases. That is what lets you scale capital, not what limits it.
- Ordering matters. Do **not** skip to Section 6 (capital). Sections 1–5, 8–12
  gate it.

Legend: **[HARD GATE]** = must pass before real capital. **[REQUIRED]** = needed
for production. **[RECOMMENDED]** = strongly advised. **[OPTIONAL]** = scale-up.

---

## 1. Hardware & Compute Infrastructure Requirements

TITAN is single-operator, mostly single-host. Concentrate spend on the primary
box and the signing/power path — not on breadth.

### 1.1 Primary compute node — TITANHOME [REQUIRED]
- **CPU:** high-core workstation/server class (spec targets AMD Threadripper PRO
  9995WX-class, 64+ cores). Minimum viable: 32 cores / 64 threads.
- **GPU:** ≥1 large-VRAM accelerator for local inference + REVM simulation. Spec
  targets 2× RTX PRO 6000 Blackwell (192 GB GDDR7 total). Minimum viable for a
  real local MoE + simulation: **48–96 GB VRAM**. Below that, use a smaller model
  or hosted inference (see §4) — do not pretend a 7B model is running a desk.
- **RAM:** 256 GB recommended (128 GB minimum). REVM parallel sweeps + model KV
  cache + feature caches are memory-hungry.
- **Storage:** 2× NVMe — one for OS/models (2 TB+), one for state/logs/audit
  chains (2 TB+). Enable full-disk encryption (LUKS). Separate disk for the
  append-only audit/decision logs is [RECOMMENDED].
- **Roles:** orchestrator inference, safety services (`:19001`–`:19007`), REVM,
  ML training.

### 1.2 Utility node — TITANSPARK [RECOMMENDED]
- Smaller box (spec: GB10-class) for utility inference (Qwen3-30B-class) and
  operator-gateway failover. Offloads the primary and provides a second brain for
  genuine (non-monoculture) risk consensus — see §5.

### 1.3 Signing node [HARD GATE for live capital]
- **Physically/logically isolated** host or hardened VM whose only job is tx
  signing at `:19010`. **No evolution workloads, no agent runtime, no inbound
  internet.** Spec: `~/.openclaw/infra/signing_node.yaml`.
- Blind-signing rejected; every payload human-verifiable or policy-bounded.

### 1.4 Key-custody node — "The Vault" [REQUIRED]
- Dedicated low-power host (spec: Mac Mini) holding hardware-wallet ceremonies
  (Trezor), key metadata, and the profit-sweep signer. Hardware-encrypted disk.

### 1.5 Power & environment [HARD GATE]
- **UPS mandatory** on TITANHOME + signing node + vault: ≥3000 VA, ≥15 min
  runtime. Power loss mid-trade with wrong reconciliation = realized loss.
- Policy `risk_kernel/policy.yaml → power_loss: halt_trading` + flatten +
  revoke session keys on mains/battery loss. Spec:
  `~/.openclaw/infra/power_requirements.yaml` must contain
  `live_capital_requires_ups: true`.
- Verified by `./deploy.sh --verify` (power-loss halt + UPS gate checks).

### 1.6 GPU scheduling [REQUIRED]
- `~/.openclaw/infra/gpu_schedule.yaml`: **P2 inference is never preempted**;
  off-peak jobs (training, backtests, REVM sweeps) yield to live decision
  latency. Kill off-peak jobs on violation.

---

## 2. Networking, Edge Mesh & Latency Requirements

### 2.1 Phase 1 = single PoP [REQUIRED]
- Launch with **one** edge PoP: **EDGE-FRA** (EU/Telegram, Erigon node). Do **not**
  stand up all 5 PoPs at launch — it multiplies attack surface and ops burden for
  no early alpha. Config: `openclaw.json → edgeMesh.phase1: single_pop`,
  `defaultPop: EDGE-FRA` (verified).
- Defer TKY/SIN/USE/AMS to Phase 3+ once a lane's edge is proven latency-bound.

### 2.2 Connectivity [REQUIRED]
- Business fiber with a documented failover (second ISP or LTE/5G). Static IP or
  stable DDNS for the operator gateway.
- Internal service bus: NATS (`nats://localhost:4222`) with the vault as a
  zero-message-loss failover node.

### 2.3 Latency posture — be honest [REQUIRED]
- You will **not** sustainably win pure speed auctions (Arbitrum Timeboost, ePBS
  deadline sniping) against Jump/Wintermute-class infra. **Do not fund lanes whose
  edge is "be the fastest."**
- Concentrate on **reaction** edges where "fast enough" wins: backrunning,
  liquidations, funding carry. Measure real p50/p95/p99 RTT per venue (the TCA
  service records this indirectly via fill quality) before trusting any
  latency-dependent lane.

### 2.4 Private order flow [HARD GATE for MEV/DEX lanes]
- All EVM order submission via private/OFA relays (Flashbots Protect, MEV-Share,
  BuilderNet) and Solana via Jito. `CB_MEV_LEAK` must **halt**, not log.

---

## 3. Operating System & Base Software Environment

### 3.1 OS [REQUIRED]
- Linux (Ubuntu 24.04 LTS / Debian 12 recommended; your host is on a 6.x kernel).
  Headless server profile; no desktop on TITANHOME.
- Dedicated non-root service user (`titan`). Never run agents or signing as root.

### 3.2 Base packages [REQUIRED]
- `python3.12`, `python3-venv`, `git`, `curl`, `jq`, `build-essential`.
- NVIDIA driver + CUDA matching your GPU (spec: CUDA 13.x, sm_120 Blackwell). For
  older GPUs, match the CUDA/driver to the card.
- `node` + `npm` (for OpenClaw), `pip` (for hermes-agent).

### 3.3 Bundle build & install [REQUIRED]
From the repo root (`titan-deploy/`):

```bash
# 1. Create the venv and install safety deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run the test suite (must be green before anything else)
.venv/bin/python -m pytest tests -q            # expect: all passed

# 3. Dry-run to preview what will be installed
./deploy.sh --dry-run

# 4. Build + install to ~/.openclaw and ~/.hermes
./deploy.sh --install-packages

# 5. Install systemd units (needs root)
./deploy.sh --systemd

# 6. Edit secrets, then verify end-to-end
$EDITOR ~/.openclaw/.env      # Telegram token/user id, NATS url
./deploy.sh --verify          # runs verify.sh: limits, config, tests, harnesses
```

`--verify` must end with `Verification PASSED`. It runs unit tests, the chaos
harness, and the adversarial harness, and checks fail-closed/UPS/signing/promotion
config. **Do not proceed on any FAIL.**

### 3.4 Source-of-truth discipline [REQUIRED]
- Edit `templates/` and `tests/`, then `./deploy.sh --build`. **Never** edit
  `output/` (regenerated) or `~/.openclaw/` (deploy target) by hand.
- Keep the whole repo in git; tag each deployed build.

---

## 4. LLM Inference & Model Serving Setup

### 4.1 Reality check on models [REQUIRED]
- Fictional model names in the spec (`GLM-5.2-753B`, `Wukong-180`) must be mapped
  to **real** models you can actually run. Pick from currently available open
  weights that fit your VRAM (e.g. a strong open MoE for the orchestrator tier, a
  ~30B for the utility tier). Record the exact model + revision in
  `audit_chain` fingerprints (§11).

### 4.2 Serving [REQUIRED]
- Serve locally with vLLM / SGLang / llama.cpp server behind a stable localhost
  endpoint. Configure `openclaw.json` / `config.yaml` inference URLs to it.
- Tier split: **orchestrator tier** (ARCHON/CORTEX/GUARDIAN reasoning) on the big
  GPU; **utility tier** (classification, triage) on TITANSPARK.
- Set `preTradeValidationUrl` and `portfolioRiskUrl` so the runtime calls the
  kernel before every execution (verified in `--verify`).

### 4.3 Break the monoculture [HARD GATE for BFT claims]
- The spec's "BFT 2-of-3" voters (AUGUR/PREDATOR/ATLAS + GUARDIAN) all share one
  model → **correlated, not independent**. `verify.sh` requires this be documented
  in `AGENTS.md`. For real consensus on large trades, run the **second risk brain
  on a different model family** (utility tier). Until then, the only
  model-independent guard is the deterministic risk kernel — treat it as the sole
  authority, not the LLM vote.

### 4.4 Determinism & timeouts [REQUIRED]
- Low temperature for risk/execution decisions; generation timeouts fall back to
  DENY, never to "proceed". The kernel never parses LLM output — it enforces
  numeric limits regardless of what the model says.

---

## 5. Security, Key Management & Hardening (Critical)

### 5.1 Key custody [HARD GATE]
- Hardware wallet (Trezor) for the treasury; **withdrawal keys never touch the
  agent runtime**. Session keys (ERC-4337/7702) issued with least privilege, short
  TTL, and auto-revoked by the kernel on kill/power-loss.
- Exchange API keys: **trade-only, withdrawal disabled**, IP-allowlisted, separate
  from any agent write path.

### 5.2 Signing isolation [HARD GATE]
- TRENCH-OPS routes all signing to `signingNode.endpoint` (`:19010`). Verified by
  `--verify` (`signingNode.enabled` + `endpoint`). Blind-sign rejected;
  `on_env_compromised: halt_all_signing`.

### 5.3 Host hardening [REQUIRED]
- Full-disk encryption; SSH key-only, no password; firewall default-deny; safety
  service ports bound to `127.0.0.1` only (they already bind localhost).
- Secrets in `~/.openclaw/.env` (0600), never in git. Rotate Telegram/API tokens.
- `nftables` egress allowlist to only the venues/relays/data feeds you use.

### 5.4 Kill paths [HARD GATE — drill before live]
- Software: `titan-safety kill activate` (global), `kill portfolio`, `kill pipeline
  halt` (per-lane), all fail-closed and independent of NATS/Telegram/LLM.
- Signed remote HALT: `titan-safety kill sign` → operator can halt from anywhere.
- Hardware: USB BusKill lanyard (see `playbooks/kill_switch.yaml`).
- Kill-switch active ⇒ kernel DENIES all trades. Verify:
  ```bash
  ~/.openclaw/safety/bin/titan-safety kill activate --operator YOU --reason drill
  ~/.openclaw/safety/bin/titan-safety kill status
  SIGNED=$(~/.openclaw/safety/bin/titan-safety kill sign --command RESUME --operator YOU)
  ~/.openclaw/safety/bin/titan-safety kill deactivate --operator YOU --signed "$SIGNED"
  ```

### 5.5 Quantum layer [HARD GATE]
- Must be **dormant** for live capital: `openclaw.json`/`config.yaml`
  `quantum.status: dormant`; `quantum_*` skills archived under
  `skills/_archived/quantum/`. No cuQuantum/Tier-3 dispatch. Reclaim that VRAM for
  REVM. (`deploy.sh` removes stale active `quantum_*` skill dirs.)

### 5.6 Self-modification containment [HARD GATE]
- Constitutional paths are **immutable to the agent runtime**: `SOUL.md`,
  `iron-laws.md`, `risk_kernel/`, `safety/titan_safety/`, execution skills.
  Enforced by `promotion_gate.is_constitutionally_blocked` (adversarial-tested).

---

## 6. Capital Requirements & Phased Deployment Plan

> Capital is gated by Sections 1–5, 8–12. Do not deposit real funds until every
> **[HARD GATE]** above is green and `--verify` passes.

### 6.1 Minimums
- `openclaw.json → capital.min_operating_capital_usd` must be set;
  `withdrawal_adapter: mock` until the live signer is wired (verified).
- Practical starting capital: **$2,500–$10,000** (Phase 1). Enough to pay real
  costs and generate statistically meaningful fills; small enough that a bug is
  survivable.

### 6.2 Phased tiers (per operator directive: 2 days/phase — see caveat)
> **CAVEAT:** 2-day phases are **well below** a safe validation window (regime
> shifts/funding cycles/low-liquidity events need weeks). Operator explicitly
> accepts elevated risk. Gate failures pause the clock; nothing auto-advances.

| Phase | Capital | Focus | Exit gate |
|-------|---------|-------|-----------|
| 0 — Infra + Paper (2d) | $0 | services up, paper all lanes, TCA scorecards | harnesses green, kill drill, scorecard per lane |
| 1 — Micro-live (2d) | $2.5–10K | ≤0.1%/trade, allocator advisory | stats gate + Phase-5 YES per lane, DD <5%, zero reconciliation divergence |
| 2 — Validated scale (2d) | $10–50K | allocator enforced, live reconciliation | 48h zero divergence, no BLEEDING lane funded, MRM no drift |
| 3 — Mature (2d) | $50K+ | fund proven lanes on evidence, sweeps ≥$15K | operator sign-off, playbooks exercised |

### 6.3 Deposits / sweeps [REQUIRED]
```bash
titan-safety capital deposit --amount 2500 --asset USDC
titan-safety capital balance
titan-safety capital verify-audit           # audit chain must be valid
# Weekly profit sweep to cold storage once ≥ $15K (R23): 20% of weekly profit
titan-safety capital sweep --weekly-profit <usd>
```

### 6.4 Sizing authority [HARD GATE]
- Humans set the **gross risk envelope** (`allocator.base_gross_pct`, per-lane and
  cluster caps, `kelly_fraction`). The allocator distributes **within** it via
  fractional Kelly. Changing these = `leverage_change`/risk-param promotion → human
  YES required.

---

## 7. Data Feeds, APIs & External Dependencies

### 7.1 Chain data [REQUIRED]
- Own node where it matters: **Erigon** (EVM) on EDGE-FRA; Solana RPC + Jito
  ShredStream for MEV/liq lanes. Public RPCs only as fallback (rate limits kill
  latency-sensitive lanes).
- Mempool: Flashbots MEV-Share node (EVM), ShredStream (Solana).

### 7.2 Market/venue APIs [REQUIRED per funded lane]
- Perps/funding (P5/P18): dYdX v4, Hyperliquid, GMX v2, Vertex, Drift, Aevo.
- DEX/AMM (P3/P29/P34): Uniswap V4, Curve, Balancer, Aerodrome, Raydium/Orca.
- Lending/liquidations (P6/P24/P46): Aave V3, Morpho, Compound V3.
- Only provision feeds for lanes you actually fund (start with ~6, not 46).

### 7.3 Reference/support data [RECOMMENDED]
- Price oracles (Chainlink/Pyth) for reconciliation sanity; gas/tip oracles;
  funding-rate history for the P18 predictor.

### 7.4 Dependency hygiene [REQUIRED]
- Every external feed needs a **health check + failover** and a circuit breaker
  (staleness/divergence → pause the dependent lane, not the whole book).
- Bridge lanes: hard-gate on bridge-safety score < 0.6 (bridges are the #1 loss
  source in DeFi).

---

## 8. Testing, Validation & Pre-Live Pipeline Requirements

### 8.1 Automated suite [HARD GATE]
```bash
.venv/bin/python -m pytest tests -q                       # unit tests
PYTHONPATH=templates/safety .venv/bin/python tests/adversarial/adversarial_harness.py
PYTHONPATH=templates/safety .venv/bin/python tests/chaos/chaos_harness.py
```
All must pass. `--verify` runs these plus config/limit checks.

### 8.2 Deployment lifecycle per strategy [HARD GATE]
Every lane runs the full lifecycle before capital:
1. **Backtest** (cost-realistic: model gas/tips/slippage/reverts).
2. **Paper** (auto-monitored divergence).
3. **Shadow** (private mempool, revert-on-loss) to validate MEV alpha.
4. **Micro-live** ≤0.1% equity with per-trade Telegram + kill switch.
5. **Statistical promotion gate** (see 8.3) — replaces the old "Sharpe≥0, 20
   trades, auto-promote".
6. **Phase-5 human YES** (fail-closed on timeout).

### 8.3 Statistical promotion gate [HARD GATE]
A strategy touching live capital must clear (`promotion_stats.py`, policy
`promotion_stats:`):
- **Deflated Sharpe ≥ 0.90** (corrects for multiple-testing across `trials`),
- **PSR ≥ 0.90**, **≥ 200 real trades**,
- **modeled costs > 0** (zero-cost backtests rejected),
- **net-of-cost expectancy > 0**,
- **shadow/live vs backtest Sharpe divergence ≤ 15%**.

```bash
titan-safety promotion-stats --stats '{"strategy_id":"P5","returns":[...],
  "trials":5,"num_trades":500,"gross_bps":18,"cost_bps":4,
  "backtest_sharpe":1.8,"shadow_sharpe":1.75}'
# exit 0 = pass; the promotion gate refuses stats-gated promotions with no evidence
```

### 8.4 Execution quality (TCA) [REQUIRED before scaling a lane]
Feed fills to the TCA service and require a non-BLEEDING verdict:
```bash
curl -s -X POST http://127.0.0.1:19007/v1/scorecard -d '{"pipeline_id":"P29"}'
# net_bps > 0, tip_efficiency ≤ 0.40, fill_rate ≥ 0.80, decay_slope ≥ 0
```

---

## 9. Monitoring, Observability & Alerting Stack

### 9.1 Service health [REQUIRED]
- Status aggregator at `:19003` rolls up all safety+profit services:
  ```bash
  curl -s http://127.0.0.1:19003/health | jq
  ```
  Ports: risk kernel `19001`, reconciliation `19002`, status `19003`, portfolio
  risk `19004`, dead-man's `19005`, **allocator `19006`**, **TCA `19007`**,
  signing `19010`.

### 9.2 Metrics [REQUIRED]
- Every service exposes Prometheus `/metrics`. Stand up Prometheus + Grafana
  (dashboard stub in `playbooks/observability_grafana_stub.yaml`). Key gauges:
  `allocator_gross_pct`, `allocator_utilization`, `tca_bleeding_lanes`,
  `portfolio_var_95_usd`, `portfolio_risk_deny_total`.

### 9.3 Structured logs & audit [REQUIRED]
- JSON logs from all services; hash-chained decision log (`audit_chain`) with
  model/LoRA/prompt/SOUL fingerprints. Ship logs off-host (append-only).

### 9.4 Operator alerting [REQUIRED]
- HERALD/Telegram for: every material trade (>0.5% or conf>0.8), all DENYs,
  drawdown-tier trips, reconciliation divergence, BLEEDING lane, dead-man's
  warnings, kill-switch events. Alerts must reach a human 24/7.

---

## 10. Risk Management & Circuit Breaker Validation

### 10.1 Independent risk kernel [HARD GATE]
- Out-of-process, deterministic, **fail-closed** (`riskKernel.failClosed: true`).
  If unreachable → all trades DENY. Validate:
  ```bash
  # Stop the kernel, confirm a trade path returns DENY (not bypass), restart.
  ```
- Enforces per-trade notional, aggregate exposure, leverage cap, loss-velocity
  (60s/15m), open-position count, slippage cap, venue/contract allowlist,
  human-approval-above-% .

### 10.2 Portfolio risk [REQUIRED]
- `:19004` VaR/CVaR caps, correlation-cluster caps, regime-scaled gross. Wire the
  **live AUGUR regime feed** (stub by default). Simulate:
  ```bash
  curl -s -X POST http://127.0.0.1:19004/v1/simulate -d '{"equity_usd":10000,
    "pipeline_id":"P29","notional_usd":500,"pipelines":[...]}'
  ```

### 10.3 Drawdown handling [HARD GATE]
- Kernel tiers (2/5/8/10/12% 24h) → alert → soft-pause → cut 50% → critical →
  full halt+flatten. Allocator **de-grossing ladder** (3/5/7/10% → 0.75/0.5/0.25/0)
  cuts gross *before* the hard tiers, while keeping delta-neutral carry running.
- Power-loss = HALT+flatten+revoke keys (verified).

### 10.4 Adversarial validation [HARD GATE]
- `adversarial_harness.py` must pass: data-poisoning→slippage DENY, prompt-
  injection→pipeline halt, correlated-failure cap, self-mod→SOUL blocked,
  black-swan velocity halt, flash-crash 60s velocity.

---

## 11. Self-Improvement & Agent Evolution Safety Controls

### 11.1 Shadow-only by default [HARD GATE]
- All evolution loops (DGM-H, GEPA, HyEvo, SIA-LoRA, EurekAgent, GRIS model-swap)
  run in **air-gapped staging** (`promotion.airGappedStaging: true`) with **zero
  order authority**. They emit *proposals*, not live changes. Verified.

### 11.2 No live code self-mutation [HARD GATE]
- Proposals reach live only via the standard gated pipeline (§8) + human YES.
  Constitutional paths (risk kernel, SOUL, execution) can never be self-modified.

### 11.3 Bounded live tuning [REQUIRED]
- Only non-risk parameters (e.g. signal thresholds) may be auto-tuned, within
  tight per-cycle drift budgets. **Risk/sizing/leverage params are frozen** to the
  loops; changing them is a human-gated promotion.

### 11.4 Serialize + monitor [REQUIRED]
- One change to the live path at a time → bake → measure via TCA/attribution →
  next. Auto-**de-fund** (not silently continue) on live edge decay; notify human
  before re-scaling.

### 11.5 Fingerprinted rollback [REQUIRED]
- Every deployed model/prompt/strategy is fingerprinted in the audit chain;
  1.5× drawdown → instant pause + auto-rollback (Phase 6 watch mode).

---

## 12. Operational Procedures & Human Oversight Model

### 12.1 Bounded-autonomy matrix [HARD GATE]
- `openclaw.json → autonomy.matrix` defines `auto_execute` vs `human_required`
  (verified). Machine trades freely inside the envelope; humans own:
  promotions, risk-param/leverage changes, capital-tier transitions, flash-loan
  go-live.

### 12.2 TIMEOUT = hold/de-risk [HARD GATE]
- Operator absence is **never** implicit approval. `promotion.timeoutPolicy:
  hold_derisk`; SOUL/USER docs must state "never auto-promote on TIMEOUT"
  (verified). This inverts the spec's dangerous `TIMEOUT→auto-promote`.

### 12.3 Dead-man's switch [REQUIRED]
- Heartbeat every ≤48h; miss → de-risk; 72h → flatten. Never auto-promotes.
  ```bash
  titan-safety heartbeat --operator YOU          # cron or manual
  ```

### 12.4 Daily/weekly operator loop [REQUIRED]
- Daily: review `:19003` health, overnight trades, DENYs, TCA scorecards, set the
  day's gross envelope. Weekly: promotion reviews, capital-tier decision, sweep,
  incident review.

### 12.5 Runbooks [REQUIRED]
- `playbooks/`: `kill_switch.yaml`, `circuit_breaker_drawdown.yaml`,
  `promotion.yaml`, `wind_down.yaml`, `red_team_checklist.yaml`. Exercise each at
  least once before Phase 3.

---

## 13. Legal, Regulatory, Tax & Compliance Requirements

> Not legal advice. Engage a crypto-literate lawyer and accountant **before** live
> capital. This is where autonomous crypto desks actually get killed.

### 13.1 Entity & jurisdiction [REQUIRED]
- Trade through an appropriate legal entity; confirm whether your activity implicates
  money-transmission, VASP, or fund-management rules in your jurisdiction.

### 13.2 Prohibited strategies [HARD GATE — do not deploy]
- The spec's manipulative/adversarial lanes (**§APEX** adversarial signal injection
  / "liquidity mirage", retail counter-trading, **§DARKINT**, treasury/vesting
  front-running) carry catastrophic legal + non-market tail risk. **Keep them
  disabled.** They are excluded from this bundle by design.

### 13.3 Market-conduct hygiene [REQUIRED]
- MEV/arb is broadly tolerated; manipulation is not. Keep order flow private,
  avoid spoofing/wash patterns, respect venue ToS (API keys can be revoked).

### 13.4 Tax [REQUIRED]
- `capital/tax_ledger.py` provides FIFO lot tracking + CSV export. Reconcile every
  fill; export for your accountant. Track per-jurisdiction treatment of crypto
  gains, staking/funding income, and cross-chain events.
  ```bash
  # tax ledger CSV export (see capital/tax_ledger.py)
  ```

### 13.5 Records [REQUIRED]
- Retain the hash-chained decision/audit logs, promotion approvals, and capital
  ledger — they double as your compliance and tax evidence.

---

## 14. Performance Benchmarking & Success Criteria

### 14.1 Gate every promotion & capital increase on (beyond Sharpe):
- **Deflated Sharpe ≥ 0.90**, **PSR ≥ 0.90** (multiple-testing-aware).
- **Net-of-cost expectancy (bps) > 0** per lane (TCA `net_bps`).
- **Tip efficiency ≤ 40%**, **fill rate ≥ 80%**, verdict ≠ BLEEDING.
- **Shadow/live vs backtest divergence ≤ 15%**.
- **Capacity holds at target size** (TCA `capacity_pressure` not rising).
- **Edge-decay slope ≥ 0**.
- **Correlation to existing book** within cluster caps.
- Sortino/Calmar and **max drawdown + time-to-recover** trending acceptably.

### 14.2 Portfolio-level success
- Compounding equity with drawdowns inside the de-grossing ladder; allocator
  utilization sensible (fractional-Kelly, not full); no single lane/cluster over
  its cap; delta-neutral carry earning through directional drawdowns.

### 14.3 Anti-goals
- Ignore the spec's fantasy targets (e.g. "$2,500→$1M in 90 days"). Sizing to a
  fantasy over-levers the book. Target high-but-real risk-adjusted returns.

---

## 15. Final Go-Live Checklist [ALL must be TRUE]

**Infra & power**
- [ ] TITANHOME, signing node, vault provisioned; models actually run locally.
- [ ] UPS installed + power-loss drill → HALT confirmed; `live_capital_requires_ups: true`.
- [ ] GPU schedule: P2 inference never preempted.

**Software & config**
- [ ] `./deploy.sh --verify` → `Verification PASSED`.
- [ ] `pytest` + adversarial + chaos harnesses green.
- [ ] All services healthy at `:19003` (incl. allocator `:19006`, TCA `:19007`).
- [ ] Quantum dormant; `quantum_*` skills archived.

**Security**
- [ ] Signing isolated (`:19010`), blind-sign rejected.
- [ ] Withdrawal keys off the agent runtime; exchange keys trade-only, no withdraw.
- [ ] Global/portfolio/pipeline kill switches drilled; signed remote HALT works;
      BusKill installed.
- [ ] Fail-closed verified (kernel down ⇒ DENY).

**Risk & autonomy**
- [ ] TIMEOUT = hold/de-risk (no auto-promote) in kernel + SOUL + USER.
- [ ] Bounded-autonomy matrix set; risk params frozen to evolution loops.
- [ ] Evolution shadow-only (air-gapped staging), zero order authority.
- [ ] Drawdown tiers + allocator de-grossing validated.
- [ ] Dead-man's switch tested; heartbeat scheduled.

**Evidence & money**
- [ ] Each live lane cleared the statistical promotion gate (DSR/PSR/cost/
      shadow/trades) **and** has a Phase-5 human YES on record
      (`titan-safety promotion verify-audit`).
- [ ] No BLEEDING lane funded (TCA).
- [ ] Reconciliation live adapter wired; 48h zero divergence.
- [ ] Capital deposited via ledger; `capital verify-audit` valid; sweep armed.

**Compliance**
- [ ] Legal entity + tax treatment confirmed with professionals.
- [ ] Prohibited (§APEX/§DARKINT/front-running) lanes disabled.
- [ ] Monitoring + off-host audit log shipping live; operator alerting 24/7.

> When — and only when — every box is checked: start at Phase 1 capital, keep the
> operator in the loop for promotions and the daily risk envelope, and let the
> machine execute inside it. Scale by evidence, one ratchet at a time.
