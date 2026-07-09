# §MEV_detail.md — MEV Shield & Intent Path

> Complements GHOST evasion. Live path: TRENCH-OPS → intent_solver_submit → edge PoP.

## Pillar: Evasion (MEV-shield)

## Mandate

- Bypass public RPC pools for DEX swaps
- Compile declarative intents signed via local TPM-SPI PCR keys
- Submit to MEV-shielded solver networks
- P29 MEV Bundle: fund only when TCA net_bps healthy; else profit_loop defund

## Edge placement

Same-AZ as exchange matching engines (TKY/SIN/FRA/USE/AMS) for &lt;1ms RTT.
Erigon archive + CRUSH batch on EDGE-FRA / TITANHOME off-peak.

## Circuit breakers

- `CB_MEV_TIP_BLEED` — tips &gt;40% of gross MEV → lane BLEEDING
- `CB_INTENT_SOLVER_TIMEOUT` — fail-closed, no public-mempool fallback for shielded lanes

## See also

- `refs/GHOST_detail.md`, AGENTS Intent Solver Routing
- Skill: `trench_ops_execution`
