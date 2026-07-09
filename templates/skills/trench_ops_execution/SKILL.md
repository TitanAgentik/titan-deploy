---
name: trench_ops_execution
description: Trench Ops Execution — DEX/bridge execution with isolated signing
metadata:
  openclaw:
    status: active
  skill_tuple:
    intent: trench_ops_execution
    method: signing_isolated
    difficulty: high
---

# Trench Ops Execution

Trade execution agent — calldata composition, route selection, MEV-protected broadcast.

## Pre-sign gates (mandatory, fail-closed)

Agents **verify and sign autonomously** — no human approval on the trade path. Human gates remain for promotion, evolution, leverage, and large withdrawals only.

**Verification stack:** confidence gate → BFT 2-of-3 (AUGUR/PREDATOR/ATLAS) when >1% equity → **fast_validate** `:19001/v1/fast_validate` (hot path, ms) or recon `:19002` + kernel `:19001` (warm path) → gate receipt → signing_node `:19010`.

**Hot path (P22/P29/P12/P30):** skip TradingAgents debate; use combined `fast_validate` — target **<15ms p95** on localhost.

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

Signing node **DENIES** without `X-Titan-Gate-Receipt` (max 30s) and **rejects blind-sign** on live venues (requires `typed_data` or `calldata`).

Or from code: `decision = ExecutionGate(policy).gate(trade, fast_path=True)` — hot pipelines auto-select fast path when `strategy_id` is P22/P29/P12/P30.

Mutating control-plane POSTs (flatten, regime, heartbeat, TCA ingest, allocate, profit_loop) require `X-Titan-Auth` HMAC tokens (`titan-safety auth sign --command FLATTEN`).

## Flatten handler

Poll `GET http://127.0.0.1:19001/v1/flatten_status`. When `flatten_requested` is true, close all listed positions via signing node (with fresh gate receipts for close orders) and stop opening risk. Key revoke sets `SIGNING_HALTED`.

## Signing Isolation (mandatory)

**Never sign in agent runtime.** All signing requests route to `signingNode.endpoint`
from `openclaw.json` (default `http://127.0.0.1:19010`, host configurable).

- Config: `~/.openclaw/infra/signing_node.yaml`
- Pre-sign gates: GUARDIAN validation → risk kernel `:19001` → EIP-712 typed data only
- Signing node: minimal OS, no evolution workloads, UPS-protected
- Mac Mini vault holds key metadata + Trezor ceremonies; signing_node executes

## Execution Flow

1. Receive approved trade intent from ARCHON/GUARDIAN
2. Build calldata (1inch/Paraswap/CoW, bridges, Jito bundles)
3. Submit signing request to signing_node (not local wallet)
4. Broadcast via lowest-p50 PoP from `edge_mesh.yaml` (full 5-PoP — same routing in paper)

## Solana / P22 memecoin (when promoted)

1. Geyser stream → PREDATOR six-gate filter (`titan-safety memecoin filter`)  
2. Gate check + receipt → signing_node → edge worker at routed PoP (e.g. Jito via EDGE-FRA, HL via EDGE-TKY)  
3. Config: `infra/solana_memecoin.yaml`, `memecoinTrench` in openclaw.json (default disabled)  

## Integration

- Agent routing: AGENTS.md → TRENCH-OPS
- Tools reference: TOOLS.md → Signing Isolation section
- Edge mesh: `edgeMesh.mode: full_mesh` in openclaw.json — see `infra/edge_mesh.yaml`
