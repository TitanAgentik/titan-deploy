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

## P22 Solana / Jito buy path

Memecoin trench buys (when promoted) use **Jito bundles via EDGE-FRA** — not public mempool:

1. PREDATOR six-gate filter PASS  
2. `gate check --fast` (hot path) → ExecutionGate receipt  
3. signing_node signs → `JitoSubmitAdapter` / EDGE-FRA broadcast  

Fail-closed: missing receipt, tip bleed (`CB_MEMECOIN_TIP_BLEED`), or filter bypass (`CB_MEMECOIN_FILTER_BYPASS`) → DENY.

## See also

- `refs/GHOST_detail.md`, `refs/REAPER_detail.md`, AGENTS Intent Solver Routing
- Skill: `trench_ops_execution`, `memecoin_trench`
- Infra: `infra/solana_memecoin.yaml`
