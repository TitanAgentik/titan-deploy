---
name: memecoin_trench
description: P22 Solana memecoin trench — Pump.fun lifecycle, 6-gate filter, Jito execution
metadata:
  openclaw:
    status: live
  skill_tuple:
    intent: memecoin_trench
    method: filter_classify_execute
    difficulty: high
  agent: PREDATOR
  pipeline: P22
  tier: "1"
  model: ":30000"
---

# Memecoin Trench (P22)

Owner: **PREDATOR** (filter/vote) + **TRENCH-OPS** (Jito + signing_node).

## Lifecycle strategies (default)

| Strategy | When | Max size |
|----------|------|----------|
| first_block_snipe | G1–G6 pass at create | 0.1–0.5% equity |
| curve_climb | 15–85% curve, no cabal signal | 0.5% equity |
| graduation | ~$69k migration approach | 0.5% equity |
| post_grad_pullback | After PumpSwap migration | 1.0% equity |
| smart_money_mirror | Tracked wallet entry | 0.5% equity |

## Six-gate filter (all must PASS)

1. Mint authority revoked  
2. Freeze authority revoked  
3. Top10/insider concentration below policy caps  
4. No fast-fill cabal preload  
5. Curve progress / liquidity alive  
6. Sell simulation OK (honeypot block)

CLI: `titan-safety memecoin filter|evaluate --mint-json '{...}'` · `memecoin sim --count N`

## Real Solana path

1. Configure `~/.openclaw/infra/solana_memecoin.yaml` (Geyser + Jito)  
2. Set `memecoinTrench.enabled: true` only after `promotion approve YES`  
3. Policy: `capital_profile: live`, venues `solana_pumpfun`, `jito`  
4. Every buy: `ExecutionGate(policy).gate(trade, fast_path=True)` or `titan-safety gate check --fast` → receipt → signing_node → EDGE-FRA Jito bundle  

## Output schema

```json
{
  "pipeline_id": "P22",
  "mint": "…",
  "passed": true,
  "gates": {"G1_mint_authority": "PASS"},
  "recommended_strategy": "curve_climb",
  "max_notional_pct_equity": 0.5,
  "confidence": 0.55,
  "bft_vote_hint": "ALLOW|DENY|ABSTAIN"
}
```

## Excluded (never implement)

- §5.5.6 algorithmic token initialization / launch bundler dumps  
- Honeypot or rug construction  
- Offensive MEV against retail wallets  

## Refs

- `playbooks/memecoin_trench.yaml`, `refs/REAPER_detail.md`, `refs/MEV_detail.md`
