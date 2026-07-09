# ENDGAME Strategies — Phase 3+ Catalog

> From TITAN §ENDGAME. **Not auto-funded.** Requires `capital.endgame_phase_unlock` (≥3),
> statistical promotion, human YES, and allocator headroom (`max_active_pipelines`).

| Strategy | Overlaps | Circuit breaker |
|----------|----------|-----------------|
| Funding rate harvest | P18 | `CB_FUNDING_FLIP` |
| Restaking engine | P10 / P15 | `CB_RESTAKING_SLASH`, `CB_RESTAKING_DEPEG` |
| Prediction market arb | P11 | `CB_PRED_MARKET_RESOLVE_RISK` |
| Vol harvest | — | `CB_VOL_HARVEST_GAP` |
| New-chain MEV | — | `CB_NEW_CHAIN_MEV_HALT` |
| Airdrop positioning | — | `CB_AIRDROP_SYBIL` |
| Rate arb / yield | — | `CB_RATE_ARB_LIQUIDITY` |
| Concentrated LP | P34 | `CB_CLMM_IL_SPIKE` |

Playbook: `playbooks/endgame_phase_gate.yaml`
Gate: `CB_ENDGAME_PHASE_GATE`
