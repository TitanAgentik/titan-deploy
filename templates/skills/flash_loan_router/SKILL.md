---
name: flash_loan_router
description: Multi-source flash-loan routing — Balancer/Morpho/Uni V4/Aave atomic compose
metadata:
  openclaw:
    status: active
  skill_tuple:
    intent: flash_loan_router
    method: route_compose_execute
    difficulty: high
  agent: ALCHEMY
  tier: "U"
  model: ":30002"
---

# Flash Loan Router (§FL)

Owner: **ALCHEMY** (compose) + **TRENCH-OPS** (gate + signing_node + edge broadcast).

## Source priority (lowest fee first)

| Chain | Order |
|-------|-------|
| ethereum | Balancer (0%) → Morpho (0%) → Uni V4 (0%) → Aave (0.09%) |
| arbitrum | Balancer → Morpho → Aave |
| base | Morpho → Balancer → Aave |

## Mandatory gates (live)

1. `flashLoanRouter.enabled: true` in openclaw.json **only after** promotion YES  
2. `titan-safety flashloan compose` → positive expected profit  
3. `titan-safety gate check/sign` with `uses_flash_loan: true` + **typed_data** (never blind-sign)  
4. Risk kernel `:19001` — DENY if `flash_loan_live` not approved  
5. signing_node `:19010` — requires gate receipt  

CLI:

```bash
titan-safety flashloan route --asset WETH --amount-usd 10000 --chain ethereum --strategy P3
titan-safety flashloan compose --request-json '{"asset":"WETH","amount_usd":5000,"chain":"ethereum","strategy_id":"P3","operations":[{"op":"swap","venue":"uniswap_v3","asset":"WETH","amount_wei":"1000000000000000000"},{"op":"repay_flash","venue":"flash_loan_router","asset":"WETH","amount_wei":"1000000000000000000"}]}'
titan-safety flashloan sim --count 100
titan-safety promotion approve --category flash_loan_live --subject flash_loan_global --response YES --operator hyperion --request-id fl-live-001
```

## Output schema (compose)

```json
{
  "passed": true,
  "selected_source": "balancer",
  "provider_address": "0xba12222222228d8ba445958a685a0a280785497",
  "fee_bps": 0,
  "calldata": "0x…",
  "typed_data": {},
  "expected_profit_usd": 12.5,
  "trade_hints": {
    "uses_flash_loan": true,
    "flash_loan_source": "balancer",
    "reason_code": "FLASH_LOAN_EXEC"
  }
}
```

## Pipelines (default allowlist)

P1, P2, P3, P5, P6, P7, P8, P12, P15, P16, P17 — configure in `policy.yaml` → `flash_loan_live.pipeline_ids`.

## Excluded

- Nested flash without explicit kernel approval  
- Live flash without operator YES on `flash_loan_live`  
- Blind-sign calldata (typed_data required on live path)

## Refs

- `playbooks/flash_loan_live.yaml`, `infra/flash_loan.yaml`, `refs/SKILLS_full.md`
