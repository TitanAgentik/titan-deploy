# Go-Live Sequence

> **Authority:** Operator checklist — enforced in software where noted.  
> **Policy defaults:** `templates/risk_kernel/policy.yaml` (`capital_profile: paper`).  
> **Related:** [`TIER0_MONEY_PATH.md`](./TIER0_MONEY_PATH.md), [`TIER1_CAPITAL_RISK.md`](./TIER1_CAPITAL_RISK.md), [`LIVE_CAPITAL_PRODUCTION_GUIDE.md`](../LIVE_CAPITAL_PRODUCTION_GUIDE.md)

Do **not** skip steps. Memecoins (P22), flash loans, and multi-PoP mesh stay **off** until boring profit on one venue.

---

## Policy defaults (template root)

```yaml
capital_profile: paper
autonomous_signing:
  enabled: false
drawdown_notify_only: true          # paper; live profile → false via tier1 merge
allowed_venues: [paper]
flash_loan_live:
  enabled: false
allocator:
  advisory_mode: true
  max_active_pipelines: 2
```

Live profile (`tier1_capital_risk.profiles.live`) merges stricter rules: enforced drawdown, live recon, `autonomous_signing.enabled: true`, DEX `allowed_venues`, `allocator.advisory_mode: false`. Kernel **refuses** `capital_profile: live` at startup unless `TITAN_LIVE_SIGNING_READY=1` and `live_signer` does not raise.

---

## Step 1 — Paper only

| Check | Action |
|-------|--------|
| `capital_profile: paper` | Deployed `~/.openclaw/risk_kernel/policy.yaml` |
| `autonomous_signing.enabled: false` | No autonomous hot-path signing |
| `allowed_venues: [paper]` | No live venue broadcast |
| CEX removed | No `binance_*`, `okx_*`, `cex_api_direct` in allow-list |
| `flash_loan_live.enabled: false` | Flash router off |

```bash
./verify.sh
python3 scripts/ci/check_live_config.py
```

---

## Step 2 — Verify + fail-closed drills

### 2a. Bootstrap / policy verify

```bash
./verify.sh "$HOME/.openclaw" "$HOME/.hermes"
pytest tests/test_go_live_integration.py -q
```

### 2b. Risk kernel fail-closed drill

Stop `:19001` (or block port). Any trade proposal must **DENY** (`CB_RISK_KERNEL_UNREACHABLE` / fail-closed).

```bash
sudo systemctl stop titan-risk-kernel.service
# Attempt validate via CLI or agent — expect DENY
sudo systemctl start titan-risk-kernel.service
```

### 2c. Kill-switch RESUME drill (live profile)

On **live** profile only: dual-control RESUME requires **two distinct operators**.

```bash
titan-safety kill-switch status
titan-safety kill-switch activate --operator op_a --reason drill
titan-safety kill-switch resume --signed-primary ... --signed-secondary ...  # two operators
```

Paper profile: single-operator resume allowed.

---

## Step 3 — One full venue loop (Hyperliquid)

Depth-first on **one** venue before expanding mesh.

1. **Recon** — built-in Hyperliquid clearinghouse (`HYPERLIQUID_WALLET_ADDRESS`) or `TITAN_RECON_FETCHER_URL`
2. **Simulate** — paper or shadow fill; kernel ALLOW on `paper` / gated venue
3. **Sign** — `titan-safety gate sign` after ExecutionGate receipt (still disarmed until Step 6)
4. **Submit** — Tier 0 broadcast authority (`trench-ops` caller only)
5. **Confirm** — fill ledger + recon match
6. **Flatten** — `POST /v1/flatten` or kill-switch; verify positions zero

See [`TIER0_MONEY_PATH.md`](./TIER0_MONEY_PATH.md) § Operator checklist.

---

## Step 4 — Shadow (2+ weeks live data)

- Run full gate path on **live market data**; **no** capital broadcast (`paper` venue or shadow flag).
- Promotion stats: `min_shadow_days: 3` minimum; **2+ weeks** recommended before micro-live.
- Gates green: DSR, PSR, walk-forward, shadow divergence, TCA scorecard.

```bash
titan-safety promotion stats --strategy P1
titan-safety promotion gate --category strategy_promotion --subject P1
```

---

## Step 5 — Micro-live dust

- Phase 5 human **YES** in promotion audit (TIMEOUT → HOLD, never auto-promote).
- Set `capital_profile: live` in deployed policy **only after** YES.
- `TITAN_LIVE_SIGNING_READY=1` only after Trezor bridge health OK.
- Micro-live caps: `tier2_promotion_quality.micro_live_caps` (`micro_live_conservative` default).
- **Recon zero divergence 48h+** before scaling notional.

```bash
python3 scripts/ci/check_live_config.py --policy ~/.openclaw/risk_kernel/policy.yaml
```

---

## Step 6 — Raise equity + enforce allocator

- Increase `trading_limits.equity_usd` gradually; drawdown tiers **enforce** on live (`drawdown_notify_only: false`).
- Allocator starts **advisory** (`advisory_mode: true`); switch to **enforce** (`advisory_mode: false`) only after evidence (TCA + fills + recon stability).
- `max_active_pipelines: 2` — fund few HEALTHY lanes only.

---

## Step 7 — Deferred features (off until boring profit)

| Feature | Default | Enable when |
|---------|---------|-------------|
| Memecoin trench P22 | `memecoin_trench.enabled: false` | Separate promotion YES + Solana wiring |
| Flash loans live | `flash_loan_live.enabled: false` | Explicit enable after paper sim + policy |
| Multi-PoP mesh | `edgeMesh.mode: single_pop` (v1) | After single-PoP stable RTT + profit |
| Tier 4 ultimate | `tier4_ultimate.enabled: false` | Tiers 0–3 complete |

---

## CI / verify wiring

| Script | Purpose |
|--------|---------|
| `./verify.sh` | Operator superset (bootstrap, policy, drills docs) |
| `scripts/ci/check_live_config.py` | Template paper defaults + live mock/CEX ban |
| `scripts/ci/check_doc_policy_consistency.py` | Docs vs bounded-autonomy |
| `scripts/ci/check_execution_gate_imports.py` | Execution skills gate references |
| `tests/test_go_live_integration.py` | Paper → shadow → micro-live path |

---

## Quick checklist (printable)

- [ ] Step 1: paper profile, signing off, venues `[paper]`, flash loans off
- [ ] Step 2: `./verify.sh` green; kernel stop → DENY; kill-switch RESUME drill
- [ ] Step 3: HL recon + simulate + sign + submit + confirm + flatten
- [ ] Step 4: 2+ weeks shadow; promotion gates green
- [ ] Step 5: Phase 5 YES; micro-live dust; recon zero 48h+
- [ ] Step 6: raise equity; drawdown enforced; allocator enforce after evidence
- [ ] Step 7: memecoins / flash loans / multi-PoP still off
