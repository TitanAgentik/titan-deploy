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

Before any signing request, call the unbypassable execution gate and **pass the receipt**:

```bash
# 1) Gate check — on ALLOW, response includes "receipt"
titan-safety gate check --trade '{"trade_id":"t1","venue":"paper","contract":"0xabc","side":"buy","notional_usd":10,"leverage":1,"expected_price":100,"worst_price":100.1}'

# 2) Sign — signing node DENIES without X-Titan-Gate-Receipt (max 30s age)
curl -s -X POST http://127.0.0.1:19010/v1/sign \
  -H "Content-Type: application/json" \
  -H "X-Titan-Gate-Receipt: $RECEIPT" \
  -d '{"trade":{"trade_id":"t1","venue":"paper","contract":"0xabc","side":"buy","notional_usd":10}}'
```

Or from code: `decision = ExecutionGate(policy).gate(trade)` — if `decision.allowed`, pass `decision.receipt` to signing. Stages: mock-adapter ban → reconciliation `:19002` → risk kernel `:19001` → signed receipt. Any DENY / unreachable → **do not sign**.

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
4. Broadcast via Phase 1 edge: **EDGE-FRA** (single PoP sufficient for $2.5K)

## Solana / P22 memecoin (when promoted)

1. Geyser stream → PREDATOR six-gate filter (`titan-safety memecoin filter`)  
2. Gate check + receipt → signing_node → Jito bundle via EDGE-FRA  
3. Config: `infra/solana_memecoin.yaml`, `memecoinTrench` in openclaw.json (default disabled)  

## Integration

- Agent routing: AGENTS.md → TRENCH-OPS
- Tools reference: TOOLS.md → Signing Isolation section
- Edge mesh: `edgeMesh.phase1: single_pop` in openclaw.json
