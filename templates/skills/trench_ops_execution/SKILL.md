---
name: trench_ops_execution
description: Trench Ops Execution — DEX/bridge execution with in-process signing
metadata:
  openclaw:
    status: active
  skill_tuple:
    intent: trench_ops_execution
    method: signing_in_process
    difficulty: high
---

# Trench Ops Execution

Trade execution agent — calldata composition, route selection, MEV-protected broadcast.

## Pre-sign gates (mandatory, fail-closed)

Agents **verify and sign autonomously** — no human approval on the trade path. Human gates remain for promotion, evolution, leverage, and large withdrawals only.

**Verification stack:** confidence gate → BFT 2-of-3 (AUGUR/PREDATOR/ATLAS) when >1% equity → **fast_validate** `:19001/v1/fast_validate` (hot path, ms) or recon `:19002` + kernel `:19001` (warm path) → gate receipt → **in-process** `SigningNode` (same titan-safety process — no `:19010` hop).

**Hot path (P22/P29/P12/P30):** skip TradingAgents debate; use combined `fast_validate` — target **<15ms p95** on localhost.

**Ghost evasion (always on for live):** kernel DENY on `public_rpc` / unshielded venues. Live DEX must use Jito, Flashbots, intent solvers, or other shielded routes from `ghost_evasion.shielded_venues`. P22 requires `venue: jito` (or solana_pumpfun/pumpswap). See `refs/GHOST_detail.md` + `infra/ghost_evasion.yaml`.

```bash
# Fast gate (ms hot path — P22 memecoin, P29 MEV)
titan-safety gate check --fast --trade '{"trade_id":"t1","strategy_id":"P22","venue":"jito",...}'

# 1) BFT votes (when trade >1% equity on live venues)
titan-safety bft vote --voter AUGUR --trade-id t1 --confidence 0.82
titan-safety bft vote --voter PREDATOR --trade-id t1 --confidence 0.80

# 2) Gate + sign in one step (include confidence + bft_votes in trade JSON)
titan-safety gate sign --fast --trade '{"trade_id":"t1","strategy_id":"P22","venue":"jito",...}' \
  --typed-data '{"types":{...},"domain":{...},"message":{...}}'

# Or gate only — on ALLOW, response includes "receipt"
titan-safety gate check --trade '{"trade_id":"t1","venue":"paper","contract":"0xabc","side":"buy","notional_usd":10,"confidence":0.75,...}'
```

SigningNode **DENIES** without `X-Titan-Gate-Receipt` (max 30s) and **rejects blind-sign** on live venues (requires `typed_data` or `calldata`).

Or from code: `decision = ExecutionGate(policy).gate(trade, fast_path=True)` — hot pipelines auto-select fast path when `strategy_id` is P22/P29/P12/P30.

Mutating control-plane POSTs (flatten, regime, heartbeat, TCA ingest, allocate, profit_loop) require `X-Titan-Auth` HMAC tokens (`titan-safety auth sign --command FLATTEN`).

## Flatten handler

Poll `GET http://127.0.0.1:19001/v1/flatten_status`. When `flatten_requested` is true, close all listed positions via in-process SigningNode (with fresh gate receipts for close orders) and stop opening risk. Key revoke sets `SIGNING_HALTED`.

## Signing Isolation (mandatory)

**Never sign in agent runtime.** All signing runs in-process inside `titan-safety`
(`signingNode.mode: in_process` in `openclaw.json`). Optional legacy HTTP `:19010`
is not on the hot path.

- Config: `~/.openclaw/infra/signing_node.yaml`
- Pre-sign gates: GUARDIAN validation → risk kernel `:19001` → EIP-712 typed data only
- Signing: deterministic titan-safety module only — no LLM, no evolution workloads, UPS-protected TITANHOME
- Mac Mini vault holds key metadata + Trezor ceremonies; TITANHOME safety stack executes

## Execution Flow

1. Receive approved trade intent from ARCHON/GUARDIAN
2. Build calldata (1inch/Paraswap/CoW, bridges, Jito bundles)
3. `titan-safety gate sign` — in-process SigningNode after ALLOW (not agent wallet)
4. Broadcast via lowest-p50 PoP from `edge_mesh.yaml` (full 5-PoP — same routing in paper)

## Solana / P22 memecoin (when promoted)

1. Geyser stream → PREDATOR six-gate filter (`titan-safety memecoin filter`)  
2. Gate check + receipt → in-process sign → edge worker at routed PoP (e.g. Jito via EDGE-FRA, HL via EDGE-TKY)  
3. Config: `infra/solana_memecoin.yaml`, `memecoinTrench` in openclaw.json (default disabled)  

## Flash-loan atomic txs (when promoted)

1. ALCHEMY composes via `titan-safety flashloan compose` → calldata + **typed_data**  
2. Trade payload must set `uses_flash_loan: true`, `flash_loan_source`, `flash_loan_amount_usd`  
3. Kernel DENY unless `flash_loan_live.enabled` + `flashLoanRouter.enabled` (no human YES required)  
